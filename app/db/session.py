from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from urllib.parse import quote_plus

# Build DATABASE_URL from environment variables if not provided directly
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Construct from individual components with proper URL encoding
    POSTGRES_USER = os.getenv("POSTGRES_USER", "YourUser")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "YourPassword")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "YourDatabase")
    DB_HOST = os.getenv("DB_HOST", "db")  # Use 'db' for Docker, 'localhost' for local dev
    
    # URL encode the password to handle special characters
    encoded_password = quote_plus(POSTGRES_PASSWORD)
    
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{encoded_password}@{DB_HOST}:5432/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()