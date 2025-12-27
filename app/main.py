from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import time
import logging
import os

from app.api.v1.router import api_router
from arq import create_pool
from app.core.redis_config import REDIS_SETTINGS
from app.socket_manager import sio
import socketio
from app.core.firebase_config import init_firebase

load_dotenv()  # Load environment variables from .env file

app = FastAPI(title="Voicely API", version="1.0.0", docs_url="/docs")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

# Mount uploads directory to serve static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include API routes
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    """Create database tables on startup with retry logic"""
    from app.db.session import engine
    from app.models import User, AudioFile, TaskJob, ChatbotSession, ChatbotMessage

    init_firebase()

    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Create database tables
            User.metadata.create_all(bind=engine)
            logging.info("Database tables created successfully")
            break
        except Exception as e:
            logging.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logging.error("Failed to connect to database after all retries")
                raise

    app.state.arq_pool = await create_pool(REDIS_SETTINGS)


@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "arq_pool"):
        await app.state.arq_pool.close()


sio_app = socketio.ASGIApp(sio, other_asgi_app=app)

# @app.get("/")
# async def root():
#     return {"message": "Welcome to Voicely API"}

# @app.get("/health")
# async def health_check():
#     return {"status": "healthy"}
