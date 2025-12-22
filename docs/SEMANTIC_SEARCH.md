# Semantic Search with Embeddings

## Overview

Ứng dụng đã được tích hợp tính năng semantic search sử dụng vector embeddings từ Google's `text-embedding-005` model. Tính năng này cho phép tìm kiếm notes dựa trên ý nghĩa ngữ nghĩa thay vì chỉ khớp từ khóa.

## Features

### 1. Automatic Embedding Generation

Khi tạo hoặc cập nhật note, hệ thống tự động tạo embeddings cho:
- **Content Embedding**: Vector 768 chiều từ nội dung note
- **Summary Embedding**: Vector 768 chiều từ phần tóm tắt

### 2. Embedding Service

File: `app/services/embedding_service.py`

**Functions:**
- `generate_document_embedding(text)`: Tạo embedding cho document/content
- `generate_query_embedding(text)`: Tạo embedding cho search query
- `generate_embeddings_batch(texts)`: Tạo embeddings cho nhiều texts
- `calculate_cosine_similarity(emb1, emb2)`: Tính độ tương đồng giữa 2 vectors

**Model Configuration:**
- Model: `text-embedding-005`
- Dimension: 768
- Task Types: 
  - `RETRIEVAL_DOCUMENT`: Cho documents
  - `RETRIEVAL_QUERY`: Cho search queries

### 3. Semantic Search API

#### Endpoint
```
POST /api/v1/notes/semantic-search
```

#### Request Body
```json
{
  "query": "search text here",
  "limit": 10,
  "search_in": "both",
  "similarity_threshold": 0.5
}
```

**Parameters:**
- `query` (required): Chuỗi tìm kiếm
- `limit` (optional, default=10): Số kết quả tối đa
- `search_in` (optional, default="both"): Tìm trong:
  - `"content"`: Chỉ tìm trong content
  - `"summary"`: Chỉ tìm trong summary
  - `"both"`: Tìm cả hai, lấy similarity cao nhất
- `similarity_threshold` (optional, default=0.5): Ngưỡng tương đồng (0-1)

#### Response
```json
{
  "results": [
    {
      "note": {
        "id": 1,
        "title": "Note title",
        "content": "...",
        "summary": "...",
        ...
      },
      "similarity_score": 0.85
    }
  ],
  "total_count": 5,
  "query": "search text here",
  "search_in": "both",
  "message": "Found 5 relevant notes"
}
```

## Database Schema

### Vector Extension
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Notes Table Columns
```sql
content_embedding VECTOR(768)  -- Embedding của content
summary_embedding VECTOR(768)  -- Embedding của summary
```

### Similarity Function
Sử dụng `cosine_distance` từ pgvector:
```sql
1 - cosine_distance(embedding1, embedding2) = similarity_score
```

## Usage Examples

### Example 1: Basic Semantic Search
```bash
curl -X POST "http://localhost:8000/api/v1/notes/semantic-search" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning models",
    "limit": 5
  }'
```

### Example 2: Search Only in Summaries
```bash
curl -X POST "http://localhost:8000/api/v1/notes/semantic-search" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI ethics",
    "search_in": "summary",
    "similarity_threshold": 0.7
  }'
```

### Example 3: High Precision Search
```bash
curl -X POST "http://localhost:8000/api/v1/notes/semantic-search" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "climate change impact",
    "limit": 3,
    "similarity_threshold": 0.8
  }'
```

## How It Works

1. **When Creating/Updating Note:**
   - User creates or updates a note với content/summary
   - System tự động gọi `generate_document_embedding()` 
   - Embedding được lưu vào cột `content_embedding` và `summary_embedding`

2. **When Searching:**
   - User gửi search query
   - System tạo query embedding bằng `generate_query_embedding()`
   - PostgreSQL tính cosine similarity giữa query embedding và note embeddings
   - Kết quả được sắp xếp theo similarity score cao nhất

3. **Similarity Score:**
   - Range: 0.0 - 1.0
   - 1.0 = Hoàn toàn giống nhau
   - 0.0 = Hoàn toàn khác nhau
   - Threshold mặc định: 0.5 (50% similarity)

## Performance Considerations

### Indexing (Optional)
Để tăng tốc độ search cho large datasets, có thể tạo index:

```sql
-- IVFFlat index (faster but approximate)
CREATE INDEX ON notes USING ivfflat (content_embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX ON notes USING ivfflat (summary_embedding vector_cosine_ops)
  WITH (lists = 100);
```

### Batch Processing
Nếu cần generate embeddings cho nhiều notes cùng lúc:
```python
from app.services.embedding_service import generate_embeddings_batch

texts = ["text 1", "text 2", "text 3"]
embeddings = generate_embeddings_batch(texts)
```

## Cost Optimization

**Google Cloud Vertex AI Pricing:**
- Text Embedding Model: ~$0.00001 per 1K characters
- 1000 embeddings (1KB mỗi text) ≈ $0.01

**Tips:**
- Chỉ generate embedding khi content/summary thay đổi
- Cache embeddings trong database
- Sử dụng batch operations khi cần

## Troubleshooting

### Issue: Embedding generation fails
**Solution:** Check Google Cloud credentials và project configuration:
```bash
echo $GOOGLE_CLOUD_PROJECT
echo $GOOGLE_CLOUD_LOCATION
```

### Issue: No results from semantic search
**Solutions:**
1. Giảm `similarity_threshold`
2. Kiểm tra xem notes đã có embeddings chưa:
```sql
SELECT COUNT(*) FROM notes 
WHERE content_embedding IS NOT NULL 
   OR summary_embedding IS NOT NULL;
```

### Issue: Slow search performance
**Solutions:**
1. Tạo vector index (xem Performance Considerations)
2. Giảm `limit` parameter
3. Filter by user_id trước khi search

## Future Enhancements

- [ ] Hybrid search: Kết hợp keyword và semantic search
- [ ] Multi-lingual embeddings support
- [ ] Embedding caching strategy
- [ ] Batch re-embedding for existing notes
- [ ] Search analytics và relevance tuning
