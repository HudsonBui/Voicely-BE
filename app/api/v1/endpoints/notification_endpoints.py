from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
import json

from app.api.deps import get_db, get_current_active_user
from app.models import User
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    MarkAsReadRequest,
)
from app.services.notification_service import NotificationService
from app.common.response_common import ResponseCommon

router = APIRouter()


@router.get("/")
async def get_notifications(
    is_read: bool = None,
    notification_type: str = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all notifications for the authenticated user.
    
    - **is_read**: Filter by read status (optional)
    - **notification_type**: Filter by notification type (optional)
    - **skip**: Pagination offset
    - **limit**: Items per page (max 100)
    """
    notifications, total_count, unread_count = NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        is_read=is_read,
        notification_type=notification_type,
        skip=skip,
        limit=min(limit, 100),
    )

    response_data = NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        total_count=total_count,
        unread_count=unread_count,
    )

    response = ResponseCommon.success_response(
        data=response_data.model_dump(),
        message="Notifications retrieved successfully"
    )
    return Response(
        content=json.dumps(response.to_json(), default=str),
        status_code=response.code,
        media_type="application/json",
    )


@router.get("/unread-count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get the count of unread notifications."""
    _, _, unread_count = NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        is_read=False,
        limit=1,
    )

    response = ResponseCommon.success_response(
        data={"unread_count": unread_count},
        message="Unread count retrieved successfully"
    )
    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )


@router.get("/{notification_id}")
async def get_notification_detail(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get detailed information about a specific notification."""
    notification = NotificationService.get_notification_by_id(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )

    if not notification:
        response = ResponseCommon.error_response(
            message="Notification not found",
            code=status.HTTP_404_NOT_FOUND
        )
    else:
        notification_data = NotificationResponse.model_validate(notification)
        response = ResponseCommon.success_response(
            data=notification_data.model_dump(),
            message="Notification retrieved successfully"
        )

    return Response(
        content=json.dumps(response.to_json(), default=str),
        status_code=response.code,
        media_type="application/json",
    )


@router.post("/mark-read")
async def mark_notifications_as_read(
    request: MarkAsReadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark specific notifications as read."""
    count = NotificationService.mark_as_read(
        db=db,
        notification_ids=request.notification_ids,
        user_id=current_user.id
    )

    response = ResponseCommon.success_response(
        data={"updated_count": count},
        message=f"Marked {count} notification(s) as read"
    )
    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )


@router.post("/mark-all-read")
async def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark all unread notifications as read."""
    count = NotificationService.mark_all_as_read(
        db=db,
        user_id=current_user.id
    )

    response = ResponseCommon.success_response(
        data={"updated_count": count},
        message=f"Marked all {count} notification(s) as read"
    )
    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a specific notification."""
    deleted = NotificationService.delete_notification(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )

    if not deleted:
        response = ResponseCommon.error_response(
            message="Notification not found",
            code=status.HTTP_404_NOT_FOUND
        )
    else:
        response = ResponseCommon.success_response(
            message="Notification deleted successfully"
        )

    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )

