import json
import os
import re
from typing import Optional, List

from google import genai
from google.genai import types


class IntentService:
    """Service for classifying user intent in chatbot messages."""

    INTENT_SYSTEM_PROMPT = """Bạn là hệ thống phân loại ý định cho ứng dụng ghi âm và ghi chú.

Các ý định hợp lệ:
- search: tìm kiếm bản ghi âm, transcript, ghi chú
- summarize: yêu cầu tóm tắt nội dung
- question: hỏi chi tiết về nội dung đã ghi âm
- manage: thao tác quản lý (xóa, lưu trữ, phân loại)
- analytics: thống kê/insight
- chat: trò chuyện chung hoặc không rõ ý định

Trích xuất thực thể khi phù hợp:
- date_range: khoảng thời gian
- keywords: từ khóa quan trọng
- categories: meeting, lecture, personal, ...
- audio_ids: ID file cụ thể
- actions: delete, archive, categorize, ...
- person_names: tên người

CHỈ trả về JSON hợp lệ theo đúng định dạng sau:
{
  "intent": "search|summarize|question|manage|analytics|chat",
  "confidence": 0.0-1.0,
  "entities": {
    "date_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
    "keywords": ["keyword1", "keyword2"],
    "categories": ["meeting"],
    "audio_ids": [123],
    "actions": ["delete", "archive"],
    "person_names": ["John"]
  }
}
"""

    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION"),
        )
        self.model_name = os.getenv("CHATBOT_INTENT_MODEL", "gemini-2.5-flash")

    def classify_intent(self, message: str, conversation_history: Optional[List[dict]] = None) -> dict:
        """Classify user intent and extract entities."""
        context = ""
        if conversation_history:
            recent = conversation_history[-3:]
            context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent])

        user_prompt = f"""Tin nhắn: {message}

Ngữ cảnh gần đây:
{context if context else "Không có"}

Hãy phân loại ý định và trích xuất thực thể theo JSON."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Content(role="user", parts=[types.Part(text=self.INTENT_SYSTEM_PROMPT)]),
                    types.Content(role="user", parts=[types.Part(text=user_prompt)]),
                ],
            )
            parsed = self._extract_json(response.text)
            if parsed:
                return parsed
        except Exception as exc:
            return {
                "intent": "chat",
                "confidence": 0.4,
                "entities": {},
                "error": str(exc),
            }

        return {
            "intent": "chat",
            "confidence": 0.4,
            "entities": {},
        }

    def _extract_json(self, text: str) -> Optional[dict]:
        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None

        try:
            return json.loads(match.group(0))
        except Exception:
            return None


intent_service = IntentService()
