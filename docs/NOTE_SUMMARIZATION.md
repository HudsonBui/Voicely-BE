# Note Summarization Feature

## Overview

This feature allows you to automatically generate AI-powered summaries of audio transcriptions and create notes from them.

## What Was Added

### 1. Constants (`app/common/constants.py`)

Added two prompts to the `AIPrompts` class:

- **`SUMMARY_SYSTEM_PROMPT`**: Professional summarization assistant with comprehensive HTML formatting rules
- **`SUMMARY_USER_PROMPT`**: User prompt template with configurable parameters

### 2. Schemas (`app/schemas/note.py`)

Added two new schemas:

```python
class SummarizeTranscriptRequest(BaseModel):
    audio_file_id: int
    output_format: Optional[str] = "paragraph"  # paragraph or bullet
    language: Optional[str] = "vi"
    max_bullets: Optional[int] = 5
    include_keywords: Optional[bool] = False
    include_quotes: Optional[bool] = False

class SummarizeTranscriptResponse(BaseModel):
    audio_file_id: int
    summary_html: str
    note_id: Optional[int] = None
    message: str
```

### 3. Service (`app/services/note_service.py`)

Implemented two main functions:

- **`generate_transcript_summary()`**: Generates HTML summary using Vertex AI Gemini
- **`summarize_audio_transcript()`**: Orchestrates the whole process - gets audio, generates summary, creates note

### 4. Endpoint (`app/api/v1/endpoints/note_endpoints.py`)

Created new endpoint:

```
POST /notes/summarize-transcript
```

## How to Use

### API Endpoint

**URL**: `POST /api/v1/notes/summarize-transcript`

**Headers**:
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "audio_file_id": 9,
  "output_format": "paragraph",
  "language": "vi",
  "max_bullets": 5,
  "include_keywords": false,
  "include_quotes": false
}
```

**Parameters**:
- `audio_file_id` (required): ID of the audio file to summarize
- `output_format` (optional, default: "paragraph"): 
  - `"paragraph"`: Summary as paragraphs
  - `"bullet"`: Summary as bullet points
- `language` (optional, default: "vi"): Language code (vi, en, etc.)
- `max_bullets` (optional, default: 5): Maximum number of bullet points (only for bullet format)
- `include_keywords` (optional, default: false): Include keywords section
- `include_quotes` (optional, default: false): Include highlighted quotes

**Response**:
```json
{
  "audio_file_id": 9,
  "summary_html": "<article lang=\"vi\"><section><p>...summary content...</p></section></article>",
  "note_id": 123,
  "message": "Summary generated and note created successfully"
}
```

### Example Usage with cURL

```bash
# 1. Login to get token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "yourpassword"
  }'

# 2. Summarize transcript (paragraph format, Vietnamese)
curl -X POST "http://localhost:8000/api/v1/notes/summarize-transcript" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file_id": 9,
    "output_format": "paragraph",
    "language": "vi"
  }'

# 3. Summarize with bullet points and keywords
curl -X POST "http://localhost:8000/api/v1/notes/summarize-transcript" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file_id": 9,
    "output_format": "bullet",
    "language": "vi",
    "max_bullets": 7,
    "include_keywords": true,
    "include_quotes": true
  }'
```

## Workflow

1. **User uploads audio** → Audio file created (ID: 9)
2. **User transcribes audio** → `POST /transcript/transcribe` with `audio_id: 9`
3. **Audio has transcription** → `transcription` field populated
4. **User requests summary** → `POST /notes/summarize-transcript` with `audio_file_id: 9`
5. **System generates summary**:
   - Fetches audio file and transcription
   - Sends to Vertex AI Gemini with system & user prompts
   - Receives HTML formatted summary
6. **System creates note**:
   - Title from audio filename
   - Content = original transcription
   - Summary = HTML summary from AI
   - Category = "transcription"
   - Tags = "audio,transcription,{language}"
7. **Response returned** → Note ID and summary HTML

## Error Handling

The endpoint will return errors in these cases:

- **404**: Audio file not found
- **400**: Audio file has not been transcribed yet
- **500**: Failed to generate summary (Vertex AI error)
- **500**: Failed to create note (database error, but summary still returned)

## Database Changes

The note will be stored in the `notes` table with:

```sql
- id: auto-generated
- user_id: current user's ID
- audio_file_id: linked to the audio file
- title: from audio filename
- content: full transcription text
- summary: HTML formatted summary
- category: "transcription"
- tags: "audio,transcription,vi" (or other language)
- created_at: current timestamp
- updated_at: current timestamp
```

## Configuration

Make sure you have these environment variables set:

```env
GOOGLE_CLOUD_PROJECT=voicely-474001
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

The Vertex AI client is configured for:
- **Project**: From `GOOGLE_CLOUD_PROJECT` env var
- **Location**: `asia-southeast1`
- **Model**: `gemini-2.0-flash-exp`

## HTML Output Format

The summary will be in clean HTML format like:

```html
<article lang="vi">
  <section>
    <p>Main summary paragraph with key points...</p>
    <p>Additional context and details...</p>
  </section>
</article>
```

Or for bullet format:

```html
<article lang="vi">
  <section>
    <ul>
      <li>First main point with complete information</li>
      <li>Second main point</li>
      <li>Third main point</li>
    </ul>
  </section>
</article>
```

With optional keywords:

```html
<article lang="vi">
  <section>
    <p>Summary content...</p>
  </section>
  <hr>
  <section>
    <h2>Từ khóa</h2>
    <p><small>keyword1, keyword2, keyword3</small></p>
  </section>
</article>
```

## Testing

To test the endpoint:

1. Make sure Docker is running: `docker compose up -d`
2. Upload an audio file
3. Transcribe it first
4. Call the summarize endpoint
5. Check the response for `note_id` and `summary_html`
6. Query the notes table to see the created note

## Next Steps

Possible enhancements:
- Add endpoint to re-generate summary with different parameters
- Add endpoint to update existing note's summary
- Support custom prompts per user
- Add summary quality rating
- Support multiple languages in one request
