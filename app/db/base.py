# Import all the models, so that Base has them before being
# imported by Alembic
from app.models.base_import import Base  # noqa
from app.models.user_model import User  # noqa
from app.models.audio_model import AudioFile  # noqa
from app.models.note_model import Note  # noqa
from app.models.task_job_model import TaskJob  # noqa
from app.models.chatbot_model import ChatbotSession, ChatbotMessage  # noqa
from app.models.user_device_model import UserDevice  # noqa
