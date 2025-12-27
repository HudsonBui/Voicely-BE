from fastapi import APIRouter, Depends, status, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
import json

from app.api.deps import get_db, get_current_active_user
from app.common.response_common import ResponseCommon
from app.models import User
from app.schemas.chatbot import ChatbotSessionCreate, ChatbotMessageCreate
from app.services.chatbot_service import chatbot_service
from app.services.task_job_service import task_job_service

router = APIRouter()


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    session_data: ChatbotSessionCreate | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    session = chatbot_service.create_session(
        db=db,
        user_id=current_user.id,
        title=session_data.title if session_data else None,
    )

    response = ResponseCommon.success_response(
        data={
            "session_id": session.session_id,
            "title": session.title,
            "total_messages": session.total_messages,
            "is_active": session.is_active,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        },
        message="Session created successfully",
        code=status.HTTP_201_CREATED,
    )
    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )


@router.post("/sessions/{session_id}/messages")
async def send_chat_message(
    session_id: str,
    message_data: ChatbotMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        result = await chatbot_service.process_message(
            db=db,
            user_id=current_user.id,
            session_id=session_id,
            message=message_data.message,
        )
        response = ResponseCommon.success_response(
            data=result,
            message="Message processed",
            code=status.HTTP_200_OK,
        )
    except ValueError:
        response = ResponseCommon.error_response(
            message="Session not found",
            code=status.HTTP_404_NOT_FOUND,
        )
    except Exception as exc:
        response = ResponseCommon.error_response(
            message=f"Failed to process message: {str(exc)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )


@router.post("/sessions/{session_id}/messages-async", status_code=status.HTTP_202_ACCEPTED)
async def send_chat_message_async(
    request: Request,
    session_id: str,
    message_data: ChatbotMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        chatbot_service.get_session(db=db, user_id=current_user.id, session_id=session_id)
        result = await task_job_service.create_and_queue_job(
            request=request,
            db=db,
            task_type="chatbot_message",
            task_function="handle_chatbot_message",
            user_id=current_user.id,
            session_id=session_id,
            message=message_data.message,
        )
        result.code = status.HTTP_202_ACCEPTED
    except ValueError:
        response = ResponseCommon.error_response(
            message="Session not found",
            code=status.HTTP_404_NOT_FOUND,
        )
        return Response(
            content=json.dumps(response.to_json()),
            status_code=response.code,
            media_type="application/json",
        )
    except Exception as exc:
        response = ResponseCommon.error_response(
            message=f"Failed to queue message: {str(exc)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        return Response(
            content=json.dumps(response.to_json()),
            status_code=response.code,
            media_type="application/json",
        )

    return Response(
        content=json.dumps(result.to_json()),
        status_code=result.code,
        media_type="application/json",
    )


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        result = chatbot_service.get_session_messages(
            db=db,
            user_id=current_user.id,
            session_id=session_id,
            limit=limit,
            offset=offset,
        )
        
        # Messages are already enriched by the service with audio_references and note_references
        response = ResponseCommon.success_response(
            data={
                "session_id": result["session"].session_id,
                "messages": result["messages"],
                "total": result["total"],
                "limit": result["limit"],
                "offset": result["offset"],
            },
            message="Session history retrieved",
        )
    except ValueError:
        response = ResponseCommon.error_response(
            message="Session not found",
            code=status.HTTP_404_NOT_FOUND,
        )
    except Exception as exc:
        response = ResponseCommon.error_response(
            message=f"Failed to fetch messages: {str(exc)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )


@router.get("/sessions")
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = chatbot_service.list_sessions(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    sessions = [
        {
            "session_id": session.session_id,
            "title": session.title,
            "total_messages": session.total_messages,
            "is_active": session.is_active,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        }
        for session in result["sessions"]
    ]

    response = ResponseCommon.success_response(
        data={
            "sessions": sessions,
            "total": result["total"],
            "limit": result["limit"],
            "offset": result["offset"],
        },
        message="Sessions retrieved",
    )

    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        chatbot_service.delete_session(db=db, user_id=current_user.id, session_id=session_id)
        response = ResponseCommon.success_response(message="Session deleted successfully")
    except ValueError:
        response = ResponseCommon.error_response(
            message="Session not found",
            code=status.HTTP_404_NOT_FOUND,
        )
    except Exception as exc:
        response = ResponseCommon.error_response(
            message=f"Failed to delete session: {str(exc)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )
