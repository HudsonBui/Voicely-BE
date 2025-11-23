# Note Endpoints Documentation

Complete REST API documentation for note CRUD operations.

## Base URL
```
/api/v1/notes
```

All endpoints require authentication via Bearer token in the `Authorization` header.

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/notes` | Get paginated list of notes |
| GET | `/notes/{note_id}` | Get single note by ID |
| POST | `/notes` | Create a new note |
| PUT | `/notes/{note_id}` | Update a note |
| DELETE | `/notes/{note_id}` | Delete a note |
| GET | `/notes/categories` | Get user's note categories |
| GET | `/notes/priorities` | Get available priorities |
| POST | `/notes/summarize-transcript` | Generate AI summary from audio transcript |

---

## 1. List Notes

**GET** `/notes`

Get a paginated list of notes with optional filters.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int | 0 | Number of records to skip (for pagination) |
| `limit` | int | 20 | Maximum records to return (1-100) |
| `category` | string | null | Filter by category |
| `is_favorite` | bool | null | Filter by favorite status |
| `is_archived` | bool | null | Filter by archived status (default: false) |
| `search` | string | null | Search in title, content, summary, tags |

### Example Request

```bash
# Get first page of notes
curl -X GET "http://localhost:8000/api/v1/notes?skip=0&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get favorite notes only
curl -X GET "http://localhost:8000/api/v1/notes?is_favorite=true" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search for notes
curl -X GET "http://localhost:8000/api/v1/notes?search=meeting" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get archived notes
curl -X GET "http://localhost:8000/api/v1/notes?is_archived=true" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by category
curl -X GET "http://localhost:8000/api/v1/notes?category=transcription" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response

```json
{
  "notes": [
    {
      "id": 1,
      "user_id": 123,
      "audio_file_id": 9,
      "title": "Meeting Notes",
      "content": "Full transcript content...",
      "summary": "<article>...</article>",
      "category": "transcription",
      "priority": "normal",
      "is_favorite": false,
      "is_archived": false,
      "color": "#FFFFFF",
      "tags": "audio,transcription",
      "audio_timestamp": null,
      "audio_transcript_excerpt": null,
      "is_shared": false,
      "shared_with": null,
      "created_at": "2025-10-27T15:00:00Z",
      "updated_at": "2025-10-27T15:00:00Z"
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 20
}
```

---

## 2. Get Single Note

**GET** `/notes/{note_id}`

Get a specific note by ID.

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `note_id` | int | Yes | Note ID |

### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/notes/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response

```json
{
  "id": 1,
  "user_id": 123,
  "audio_file_id": 9,
  "title": "Meeting Notes",
  "content": "Full transcript content...",
  "summary": "<article>...</article>",
  "category": "transcription",
  "priority": "normal",
  "is_favorite": false,
  "is_archived": false,
  "color": "#FFFFFF",
  "tags": "audio,transcription",
  "audio_timestamp": null,
  "audio_transcript_excerpt": null,
  "is_shared": false,
  "shared_with": null,
  "created_at": "2025-10-27T15:00:00Z",
  "updated_at": "2025-10-27T15:00:00Z"
}
```

### Error Responses

- **404 Not Found**: Note doesn't exist or user doesn't own it

---

## 3. Create Note

**POST** `/notes`

Create a new note.

### Request Body

```json
{
  "title": "My Note",
  "content": "Note content here",
  "summary": "Optional summary",
  "category": "general",
  "priority": "normal",
  "is_favorite": false,
  "color": "#FFFFFF",
  "tags": "tag1,tag2",
  "audio_file_id": 9,
  "audio_timestamp": 123.45,
  "audio_transcript_excerpt": "Excerpt from audio",
  "is_shared": false
}
```

### Field Details

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `title` | string | **Yes** | - | Note title |
| `content` | string | No | null | Note content |
| `summary` | string | No | null | Note summary (HTML or text) |
| `category` | string | No | "general" | Category (general, meeting, lecture, etc.) |
| `priority` | string | No | "normal" | Priority (low, normal, high, urgent) |
| `is_favorite` | bool | No | false | Favorite flag |
| `color` | string | No | "#FFFFFF" | Hex color for UI |
| `tags` | string | No | null | Comma-separated tags |
| `audio_file_id` | int | No | null | Link to audio file |
| `audio_timestamp` | float | No | null | Timestamp in audio (seconds) |
| `audio_transcript_excerpt` | string | No | null | Related transcript portion |
| `is_shared` | bool | No | false | Sharing flag |

### Example Request

```bash
curl -X POST "http://localhost:8000/api/v1/notes" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Important Meeting",
    "content": "Discussion points...",
    "category": "meeting",
    "priority": "high",
    "is_favorite": true,
    "tags": "work,meeting,urgent"
  }'
```

### Response (201 Created)

```json
{
  "message": "Note created successfully",
  "note": {
    "id": 2,
    "user_id": 123,
    "title": "Important Meeting",
    "content": "Discussion points...",
    "category": "meeting",
    "priority": "high",
    "is_favorite": true,
    "is_archived": false,
    "color": "#FFFFFF",
    "tags": "work,meeting,urgent",
    "audio_file_id": null,
    "audio_timestamp": null,
    "audio_transcript_excerpt": null,
    "is_shared": false,
    "shared_with": null,
    "summary": null,
    "created_at": "2025-10-27T15:30:00Z",
    "updated_at": "2025-10-27T15:30:00Z"
  }
}
```

### Error Responses

- **404 Not Found**: Audio file not found (if audio_file_id provided)
- **500 Internal Server Error**: Database error

---

## 4. Update Note

**PUT** `/notes/{note_id}`

Update an existing note. Only provided fields will be updated.

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `note_id` | int | Yes | Note ID |

### Request Body

All fields are optional. Only include fields you want to update.

```json
{
  "title": "Updated Title",
  "content": "Updated content",
  "summary": "Updated summary",
  "category": "lecture",
  "priority": "urgent",
  "is_favorite": true,
  "is_archived": false,
  "color": "#FF5733",
  "tags": "updated,tags",
  "audio_timestamp": 456.78,
  "audio_transcript_excerpt": "New excerpt",
  "is_shared": true,
  "shared_with": "user123,user456"
}
```

### Example Request

```bash
# Mark as favorite
curl -X PUT "http://localhost:8000/api/v1/notes/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_favorite": true}'

# Update title and priority
curl -X PUT "http://localhost:8000/api/v1/notes/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "priority": "urgent"
  }'

# Archive note
curl -X PUT "http://localhost:8000/api/v1/notes/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_archived": true}'
```

### Response

```json
{
  "id": 1,
  "user_id": 123,
  "title": "Updated Title",
  "content": "Original content",
  "priority": "urgent",
  "is_favorite": true,
  "is_archived": false,
  "...": "..."
}
```

### Error Responses

- **404 Not Found**: Note doesn't exist or user doesn't own it
- **500 Internal Server Error**: Database error

---

## 5. Delete Note

**DELETE** `/notes/{note_id}`

Permanently delete a note.

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `note_id` | int | Yes | Note ID |

### Example Request

```bash
curl -X DELETE "http://localhost:8000/api/v1/notes/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response

```json
{
  "message": "Note deleted successfully"
}
```

### Error Responses

- **404 Not Found**: Note doesn't exist or user doesn't own it
- **500 Internal Server Error**: Database error

---

## 6. Get Categories

**GET** `/notes/categories`

Get all unique categories used by the current user.

### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/notes/categories" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response

```json
{
  "categories": [
    "general",
    "meeting",
    "lecture",
    "transcription",
    "personal"
  ]
}
```

---

## 7. Get Priorities

**GET** `/notes/priorities`

Get list of available priority levels.

### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/notes/priorities" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Response

```json
{
  "priorities": [
    "low",
    "normal",
    "high",
    "urgent"
  ]
}
```

---

## 8. Summarize Transcript (AI)

**POST** `/notes/summarize-transcript`

Generate an AI-powered summary from an audio file's transcription and create a note.

### Request Body

```json
{
  "audio_file_id": 9
}
```

### Example Request

```bash
curl -X POST "http://localhost:8000/api/v1/notes/summarize-transcript" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file_id": 9
  }'
```

### Response

```json
{
  "audio_file_id": 9,
  "summary_html": "<article lang=\"vi\">...</article>",
  "note_id": 10,
  "message": "Summary generated and note created successfully"
}
```

### Error Responses

- **404 Not Found**: Audio file not found
- **400 Bad Request**: Audio file not transcribed yet
- **500 Internal Server Error**: AI generation failed or database error

### Notes

- The audio file must be transcribed first
- A new note is automatically created with:
  - Title from audio filename
  - Content = full transcription
  - Summary = AI-generated HTML
  - Category = "transcription"
  - Tags = "audio,transcription"

---

## Common Use Cases

### 1. Get All Non-Archived Notes

```bash
curl -X GET "http://localhost:8000/api/v1/notes" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Get Favorite Notes

```bash
curl -X GET "http://localhost:8000/api/v1/notes?is_favorite=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Search Notes

```bash
curl -X GET "http://localhost:8000/api/v1/notes?search=meeting" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Create Quick Note

```bash
curl -X POST "http://localhost:8000/api/v1/notes" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Quick Note",
    "content": "Remember to..."
  }'
```

### 5. Update Note Priority

```bash
curl -X PUT "http://localhost:8000/api/v1/notes/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"priority": "urgent"}'
```

### 6. Archive Note

```bash
curl -X PUT "http://localhost:8000/api/v1/notes/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_archived": true}'
```

### 7. Get Paginated Notes

```bash
# Page 1
curl -X GET "http://localhost:8000/api/v1/notes?skip=0&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Page 2
curl -X GET "http://localhost:8000/api/v1/notes?skip=20&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Error Handling

All endpoints return standard HTTP status codes:

- **200 OK**: Request succeeded
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid authentication token
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

Error response format:

```json
{
  "detail": "Error message here"
}
```

---

## Authentication

All endpoints require JWT authentication:

```bash
# 1. Login to get token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'

# 2. Use token in subsequent requests
curl -X GET "http://localhost:8000/api/v1/notes" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Testing with Swagger UI

Visit `http://localhost:8000/docs` to test all endpoints interactively with Swagger UI.
