import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone

from firebase_admin import messaging
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.firebase_config import init_firebase
from app.models.user_device_model import UserDevice
from app.models.notification_model import Notification
from app.schemas.notification import NotificationCreate

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications and sending push notifications via FCM."""

    # ==================== Database Methods ====================

    @staticmethod
    async def create_notification(
        db: Session,
        notification_data: NotificationCreate,
    ) -> Notification:
        """Create and store a notification in the database."""
        notification = Notification(
            user_id=notification_data.user_id,
            title=notification_data.title,
            body=notification_data.body,
            notification_type=notification_data.notification_type,
            related_id=notification_data.related_id,
            data=notification_data.data,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        logger.info("Created notification %s for user %s", notification.id, notification_data.user_id)
        return notification

    @staticmethod
    async def send_and_store_notification(
        db: Session,
        user_id: int,
        title: str,
        body: str,
        notification_type: str,
        related_id: Optional[int] = None,
        data: Optional[Dict[str, str]] = None,
    ) -> Tuple[Notification, Dict[str, int]]:
        """
        Create notification in DB and send push notification via FCM.
        Returns the notification object and FCM stats.
        """
        # Store in database
        notification_data = NotificationCreate(
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            related_id=related_id,
            data=data,
        )
        notification = await NotificationService.create_notification(db, notification_data)

        # Send push notification
        fcm_stats = await NotificationService.send_to_user(
            db=db,
            user_id=user_id,
            title=title,
            body=body,
            data=data,
        )

        return notification, fcm_stats

    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        is_read: Optional[bool] = None,
        notification_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Notification], int, int]:
        """
        Get notifications for a user with filters.
        Returns: (notifications, total_count, unread_count)
        """
        query = db.query(Notification).filter(Notification.user_id == user_id)

        # Apply filters
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        if notification_type:
            query = query.filter(Notification.notification_type == notification_type)

        # Get total count
        total_count = query.count()

        # Get unread count
        unread_count = db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).scalar()

        # Get paginated results
        notifications = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()

        return notifications, total_count, unread_count or 0

    @staticmethod
    def get_notification_by_id(db: Session, notification_id: int, user_id: int) -> Optional[Notification]:
        """Get a specific notification if it belongs to the user."""
        return db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

    @staticmethod
    def mark_as_read(db: Session, notification_ids: List[int], user_id: int) -> int:
        """
        Mark notifications as read.
        Returns the number of notifications updated.
        """
        count = db.query(Notification).filter(
            Notification.id.in_(notification_ids),
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update(
            {
                "is_read": True,
                "read_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            },
            synchronize_session=False
        )
        db.commit()
        logger.info("Marked %d notifications as read for user %s", count, user_id)
        return count

    @staticmethod
    def mark_all_as_read(db: Session, user_id: int) -> int:
        """Mark all unread notifications as read for a user."""
        count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update(
            {
                "is_read": True,
                "read_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            },
            synchronize_session=False
        )
        db.commit()
        logger.info("Marked all (%d) notifications as read for user %s", count, user_id)
        return count

    @staticmethod
    def delete_notification(db: Session, notification_id: int, user_id: int) -> bool:
        """Delete a notification if it belongs to the user."""
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        if notification:
            db.delete(notification)
            db.commit()
            logger.info("Deleted notification %s for user %s", notification_id, user_id)
            return True
        return False

    # ==================== FCM Methods ====================

    @staticmethod
    async def send_to_user(
        db: Session,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, int]:
        """
        Send push notification to all active devices of a user.
        """
        init_firebase()

        devices = (
            db.query(UserDevice)
            .filter(UserDevice.user_id == user_id, UserDevice.is_active == True)
            .all()
        )

        stats = {"total_devices": len(devices), "successful": 0, "failed": 0, "deactivated": 0}
        if not devices:
            logger.warning("No active devices found for user %s", user_id)
            return stats

        notification = messaging.Notification(title=title, body=body)
        payload = NotificationService._coerce_data_payload(data)

        for device in devices:
            message = messaging.Message(
                notification=notification,
                token=device.fcm_token,
                data=payload,
            )
            try:
                response = messaging.send(message)
                stats["successful"] += 1
                logger.info("Notification sent to device %s: %s", device.id, response)
            except messaging.UnregisteredError:
                logger.warning("Token %s unregistered. Deactivating device %s", device.fcm_token, device.id)
                device.is_active = False
                stats["deactivated"] += 1
            except messaging.SenderIdMismatchError:
                logger.error("Sender ID mismatch for token %s. Deactivating device %s", device.fcm_token, device.id)
                device.is_active = False
                stats["deactivated"] += 1
            except messaging.QuotaExceededError:
                logger.error("FCM quota exceeded for device %s", device.id)
                stats["failed"] += 1
            except messaging.InvalidArgumentError as exc:
                logger.error("Invalid token for device %s: %s", device.id, exc)
                device.is_active = False
                stats["deactivated"] += 1
            except Exception as exc:
                logger.error("Unexpected error sending to device %s: %s", device.id, exc)
                stats["failed"] += 1

        if stats["deactivated"] > 0:
            db.commit()

        logger.info("Notification stats for user %s: %s", user_id, stats)
        return stats

    @staticmethod
    async def send_to_devices(
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """Send notification to specific device tokens (without database)."""
        init_firebase()
        failed_tokens: List[str] = []
        notification = messaging.Notification(title=title, body=body)
        payload = NotificationService._coerce_data_payload(data)

        for token in tokens:
            message = messaging.Message(notification=notification, token=token, data=payload)
            try:
                messaging.send(message)
            except Exception as exc:
                logger.error("Failed to send to token %s: %s", token, exc)
                failed_tokens.append(token)

        return failed_tokens

    @staticmethod
    def _coerce_data_payload(data: Optional[Dict[str, str]]) -> Dict[str, str]:
        if not data:
            return {}
        return {str(key): "" if value is None else str(value) for key, value in data.items()}
