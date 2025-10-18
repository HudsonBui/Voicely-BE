"""
Database migration to create notes table
Run this script to add the notes table to your database
"""

from sqlalchemy import text
from app.db.session import engine

def create_notes_table():
    """Create the notes table with all required fields and relationships"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS notes (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        audio_file_id INTEGER REFERENCES audio_files(id) ON DELETE SET NULL,
        
        -- Content fields
        title VARCHAR(200) NOT NULL,
        content TEXT,
        summary TEXT,
        
        -- Categorization
        category VARCHAR(50) DEFAULT 'general',
        priority VARCHAR(20) DEFAULT 'normal',
        
        -- Metadata
        is_favorite BOOLEAN DEFAULT FALSE,
        is_archived BOOLEAN DEFAULT FALSE,
        color VARCHAR(7) DEFAULT '#FFFFFF',
        tags VARCHAR(500),
        
        -- Audio-related fields
        audio_timestamp FLOAT,
        audio_transcript_excerpt TEXT,
        
        -- Collaboration (future feature)
        is_shared BOOLEAN DEFAULT FALSE,
        shared_with TEXT,
        
        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Create indexes for better performance
    create_indexes_sql = """
    CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id);
    CREATE INDEX IF NOT EXISTS idx_notes_audio_file_id ON notes(audio_file_id);
    CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category);
    CREATE INDEX IF NOT EXISTS idx_notes_priority ON notes(priority);
    CREATE INDEX IF NOT EXISTS idx_notes_is_favorite ON notes(is_favorite);
    CREATE INDEX IF NOT EXISTS idx_notes_is_archived ON notes(is_archived);
    CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);
    """
    
    # Create trigger for updated_at
    create_trigger_sql = """
    CREATE OR REPLACE FUNCTION update_notes_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    
    DROP TRIGGER IF EXISTS trigger_notes_updated_at ON notes;
    CREATE TRIGGER trigger_notes_updated_at
        BEFORE UPDATE ON notes
        FOR EACH ROW
        EXECUTE FUNCTION update_notes_updated_at();
    """
    
    try:
        with engine.connect() as conn:
            print("Creating notes table...")
            conn.execute(text(create_table_sql))
            
            print("Creating indexes...")
            conn.execute(text(create_indexes_sql))
            
            print("Creating update trigger...")
            conn.execute(text(create_trigger_sql))
            
            conn.commit()
            print("✅ Notes table created successfully!")
            
    except Exception as e:
        print(f"❌ Error creating notes table: {e}")
        raise

if __name__ == "__main__":
    create_notes_table()