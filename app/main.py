from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import time
import logging

from app.api.v1.router import api_router

load_dotenv()  # Load environment variables from .env file

app = FastAPI(title="Voicely API", version="1.0.0", docs_url="/docs")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    """Create database tables on startup with retry logic"""
    from app.db.session import engine
    from app.models import User, AudioFile
    
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

# @app.get("/")
# async def root():
#     return {"message": "Welcome to Voicely API"}

# @app.get("/health")
# async def health_check():
#     return {"status": "healthy"}
