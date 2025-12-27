"""
Embedding service for generating vector embeddings using Google's text-embedding-005 model.
"""
import logging
import os
import random
import time
from collections import deque
from threading import Lock
from typing import List, Optional
from google import genai
from google.genai import types
try:
    from google.genai.errors import ClientError
except ImportError:  # pragma: no cover - optional dependency guard
    ClientError = None
from app.common.constants import Common

logger = logging.getLogger(__name__)

# Embedding API limits for text-embedding-005
_MAX_CHARS_PER_EMBEDDING = 20000  # Google's limit
_MAX_TOKENS_PER_EMBEDDING = 5000  # Approximate token limit
_RECOMMENDED_MAX_CHUNK_SIZE = 3000  # Safe limit with margin
_MAX_TOKENS_PER_BATCH = 18000  # Safe limit for batch requests (model max is 20000)

# Initialize the GenAI client for Vertex AI
client = genai.Client(
    vertexai=True,
    project=os.getenv('GOOGLE_CLOUD_PROJECT'),
    location=os.getenv('GOOGLE_CLOUD_LOCATION')
)


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("Invalid %s=%s, using default %d", name, value, default)
        return default


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning("Invalid %s=%s, using default %.2f", name, value, default)
        return default


# Reduced default batch size from 8 to 5 to stay under token limits
_EMBEDDING_BATCH_SIZE = max(1, _get_int_env("EMBEDDING_BATCH_SIZE", 5))
_EMBEDDING_MAX_RETRIES = max(0, _get_int_env("EMBEDDING_MAX_RETRIES", 5))
# Increased backoff times to handle rate limits better
_EMBEDDING_BACKOFF_BASE_SECONDS = max(0.0, _get_float_env("EMBEDDING_BACKOFF_BASE_SECONDS", 1.0))
_EMBEDDING_BACKOFF_MAX_SECONDS = max(0.0, _get_float_env("EMBEDDING_BACKOFF_MAX_SECONDS", 32.0))
_EMBEDDING_BACKOFF_JITTER_SECONDS = max(0.0, _get_float_env("EMBEDDING_BACKOFF_JITTER_SECONDS", 0.5))
_EMBEDDING_RATE_LIMIT_PER_MIN = max(0, _get_int_env("EMBEDDING_RATE_LIMIT_PER_MIN", 0))
# Default to 1 request per second to avoid quota issues
_EMBEDDING_RATE_LIMIT_PER_SEC = max(0, _get_int_env("EMBEDDING_RATE_LIMIT_PER_SEC", 1))

_rate_limit_lock = Lock()
_rate_limit_window_min = deque()
_rate_limit_window_sec = deque()


def _trim_rate_limit_window(window: deque, now: float, window_seconds: float) -> None:
    while window and now - window[0] > window_seconds:
        window.popleft()


def _apply_rate_limit() -> None:
    if _EMBEDDING_RATE_LIMIT_PER_MIN <= 0 and _EMBEDDING_RATE_LIMIT_PER_SEC <= 0:
        return

    with _rate_limit_lock:
        now = time.monotonic()

        if _EMBEDDING_RATE_LIMIT_PER_MIN > 0:
            _trim_rate_limit_window(_rate_limit_window_min, now, 60.0)
            if len(_rate_limit_window_min) >= _EMBEDDING_RATE_LIMIT_PER_MIN:
                sleep_time = 60.0 - (now - _rate_limit_window_min[0])
                if sleep_time > 0:
                    logger.info(
                        "Embedding rate limit hit (per_min=%d). Sleeping %.2fs",
                        _EMBEDDING_RATE_LIMIT_PER_MIN,
                        sleep_time,
                    )
                    time.sleep(sleep_time)
                    now = time.monotonic()
                    _trim_rate_limit_window(_rate_limit_window_min, now, 60.0)

        if _EMBEDDING_RATE_LIMIT_PER_SEC > 0:
            _trim_rate_limit_window(_rate_limit_window_sec, now, 1.0)
            if len(_rate_limit_window_sec) >= _EMBEDDING_RATE_LIMIT_PER_SEC:
                sleep_time = 1.0 - (now - _rate_limit_window_sec[0])
                if sleep_time > 0:
                    logger.info(
                        "Embedding rate limit hit (per_sec=%d). Sleeping %.2fs",
                        _EMBEDDING_RATE_LIMIT_PER_SEC,
                        sleep_time,
                    )
                    time.sleep(sleep_time)
                    now = time.monotonic()
                    _trim_rate_limit_window(_rate_limit_window_sec, now, 1.0)

        if _EMBEDDING_RATE_LIMIT_PER_MIN > 0:
            _rate_limit_window_min.append(now)
        if _EMBEDDING_RATE_LIMIT_PER_SEC > 0:
            _rate_limit_window_sec.append(now)


def _is_retryable_error(exc: Exception) -> bool:
    if ClientError and isinstance(exc, ClientError):
        status_code = getattr(exc, "status_code", None)
        if status_code == 429:
            return True
    text = str(exc).lower()
    return "429" in text or "resource_exhausted" in text or "quota" in text


def _get_backoff_seconds(attempt: int) -> float:
    base = _EMBEDDING_BACKOFF_BASE_SECONDS * (2 ** attempt)
    backoff = min(_EMBEDDING_BACKOFF_MAX_SECONDS, base)
    if _EMBEDDING_BACKOFF_JITTER_SECONDS > 0:
        backoff += random.uniform(0.0, _EMBEDDING_BACKOFF_JITTER_SECONDS)
    return backoff


def _embed_content_with_retry(contents, task_type: str):
    for attempt in range(_EMBEDDING_MAX_RETRIES + 1):
        try:
            _apply_rate_limit()
            return client.models.embed_content(
                model=Common.EMBEDDING_MODEL,
                contents=contents,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=Common.EMBEDDING_DIMENSION
                ),
            )
        except Exception as exc:
            if not _is_retryable_error(exc) or attempt >= _EMBEDDING_MAX_RETRIES:
                raise
            sleep_time = _get_backoff_seconds(attempt)
            logger.warning(
                "Embedding request failed with retryable error: %s. Retrying in %.2fs (attempt %d/%d)",
                exc,
                sleep_time,
                attempt + 1,
                _EMBEDDING_MAX_RETRIES,
            )
            time.sleep(sleep_time)


def _extract_embeddings(response) -> List[Optional[List[float]]]:
    if response and hasattr(response, 'embeddings') and response.embeddings:
        result = []
        for embedding in response.embeddings:
            values = getattr(embedding, "values", None)
            result.append(list(values) if values is not None else None)
        return result
    return []


def _estimate_token_count(text: str) -> int:
    """Estimate token count for a text. Rough estimate: 1 token ≈ 4 characters."""
    return len(text) // 4 + 1


def _create_token_aware_batches(texts: List[str], max_batch_size: int) -> List[List[int]]:
    """
    Create batches of text indices that respect both batch size and token limits.
    
    Args:
        texts: List of texts to batch
        max_batch_size: Maximum number of texts per batch
        
    Returns:
        List of batches, where each batch is a list of indices into the texts list
    """
    batches = []
    current_batch = []
    current_tokens = 0
    
    for i, text in enumerate(texts):
        text_tokens = _estimate_token_count(text)
        
        # If single text exceeds limit, it will be processed individually
        if text_tokens > _MAX_TOKENS_PER_BATCH:
            # Finish current batch first
            if current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
            # Add this text as its own batch (will be truncated during embedding)
            batches.append([i])
            continue
        
        # Check if adding this text would exceed limits
        would_exceed_tokens = current_tokens + text_tokens > _MAX_TOKENS_PER_BATCH
        would_exceed_size = len(current_batch) >= max_batch_size
        
        if would_exceed_tokens or would_exceed_size:
            # Start a new batch
            if current_batch:
                batches.append(current_batch)
            current_batch = [i]
            current_tokens = text_tokens
        else:
            current_batch.append(i)
            current_tokens += text_tokens
    
    # Don't forget the last batch
    if current_batch:
        batches.append(current_batch)
    
    return batches



def generate_embedding(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> Optional[List[float]]:
    """
    Generate embedding for a single text using text-embedding-005 model.
    
    Args:
        text: The text to generate embedding for
        task_type: The task type for embedding. Options:
            - RETRIEVAL_DOCUMENT: For documents that will be searched
            - RETRIEVAL_QUERY: For search queries
            - SEMANTIC_SIMILARITY: For comparing text similarity
            - CLASSIFICATION: For text classification
            - CLUSTERING: For text clustering
            
    Returns:
        List of floats representing the embedding vector (768 dimensions)
        Returns None if embedding generation fails
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for embedding generation")
        return None
    
    # Validate text size to prevent API errors
    text_length = len(text)
    if text_length > _MAX_CHARS_PER_EMBEDDING:
        logger.error(
            "Text length=%d exceeds API limit=%d. Cannot generate embedding.",
            text_length,
            _MAX_CHARS_PER_EMBEDDING
        )
        # Truncate to safe limit instead of failing completely
        logger.warning("Truncating text to %d characters", _MAX_CHARS_PER_EMBEDDING)
        text = text[:_MAX_CHARS_PER_EMBEDDING]
    elif text_length > _RECOMMENDED_MAX_CHUNK_SIZE:
        logger.warning(
            "Text length=%d exceeds recommended size=%d. Consider chunking this text.",
            text_length,
            _RECOMMENDED_MAX_CHUNK_SIZE
        )
    
    try:
        # Generate embedding using Google GenAI SDK
        response = _embed_content_with_retry(text, task_type)
        
        # Extract embedding values from response
        embeddings = _extract_embeddings(response)
        if embeddings and embeddings[0] is not None:
            embedding = embeddings[0]
            logger.info(
                "Successfully generated embedding (dim=%d, task=%s)", 
                len(embedding), 
                task_type
            )
            return embedding
        else:
            logger.error("No embeddings found in response")
            return None
            
    except Exception as e:
        logger.error("Failed to generate embedding: %s", e, exc_info=True)
        return None


def generate_embeddings_batch(
    texts: List[str], 
    task_type: str = "RETRIEVAL_DOCUMENT"
) -> List[Optional[List[float]]]:
    """
    Generate embeddings for multiple texts using token-aware batching.
    
    Args:
        texts: List of texts to generate embeddings for
        task_type: The task type for embedding
        
    Returns:
        List of embeddings (each embedding is a list of floats)
        Returns None for texts that fail to generate embeddings
    """
    if not texts:
        logger.warning("Empty texts list provided for batch embedding generation")
        return []
    
    embeddings: List[Optional[List[float]]] = [None] * len(texts)
    
    # Create token-aware batches to avoid exceeding API limits
    batches = _create_token_aware_batches(texts, _EMBEDDING_BATCH_SIZE)
    
    logger.info(
        "Processing %d texts in %d token-aware batches (max_batch_size=%d, max_tokens=%d)",
        len(texts), len(batches), _EMBEDDING_BATCH_SIZE, _MAX_TOKENS_PER_BATCH
    )
    
    processed_count = 0
    for batch_idx, batch_indices in enumerate(batches):
        batch_texts = [texts[i] for i in batch_indices]
        
        if len(batch_texts) == 1:
            # Single text - use individual embedding function
            embeddings[batch_indices[0]] = generate_embedding(batch_texts[0], task_type=task_type)
        else:
            try:
                response = _embed_content_with_retry(batch_texts, task_type)
                batch_embeddings = _extract_embeddings(response)
                
                if len(batch_embeddings) != len(batch_texts):
                    logger.warning(
                        "Embedding response size mismatch: expected %d, got %d",
                        len(batch_texts),
                        len(batch_embeddings),
                    )
                    if len(batch_embeddings) < len(batch_texts):
                        batch_embeddings.extend([None] * (len(batch_texts) - len(batch_embeddings)))
                    else:
                        batch_embeddings = batch_embeddings[:len(batch_texts)]
                
                for i, embedding in enumerate(batch_embeddings):
                    embeddings[batch_indices[i]] = embedding
                    
            except Exception as exc:
                logger.error(
                    "Failed to generate embedding batch %d (indices %s): %s",
                    batch_idx + 1,
                    batch_indices[:3],  # Log first 3 indices only
                    exc,
                    exc_info=True,
                )
                # Fall back to individual embedding for each text in failed batch
                for idx, text in zip(batch_indices, batch_texts):
                    embeddings[idx] = generate_embedding(text, task_type=task_type)

        processed_count += len(batch_indices)
        if processed_count % 10 == 0 or processed_count == len(texts):
            logger.info("Generated embeddings for %d/%d texts", processed_count, len(texts))
    
    logger.info(
        "Batch embedding complete: %d/%d successful", 
        sum(1 for e in embeddings if e is not None),
        len(texts)
    )
    
    return embeddings


def generate_query_embedding(query: str) -> Optional[List[float]]:
    """
    Generate embedding specifically for search queries.
    
    Args:
        query: The search query text
        
    Returns:
        List of floats representing the embedding vector
        Returns None if embedding generation fails
    """
    return generate_embedding(query, task_type="RETRIEVAL_QUERY")


def generate_document_embedding(document: str) -> Optional[List[float]]:
    """
    Generate embedding specifically for documents/content.
    
    Args:
        document: The document text
        
    Returns:
        List of floats representing the embedding vector
        Returns None if embedding generation fails
    """
    return generate_embedding(document, task_type="RETRIEVAL_DOCUMENT")


def calculate_cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Cosine similarity score between -1 and 1
        Returns 0.0 if calculation fails
    """
    try:
        if not embedding1 or not embedding2:
            return 0.0
        
        if len(embedding1) != len(embedding2):
            logger.error(
                "Embedding dimensions don't match: %d vs %d", 
                len(embedding1), 
                len(embedding2)
            )
            return 0.0
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        
        # Calculate magnitudes
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        # Calculate cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)
        
        return similarity
        
    except Exception as e:
        logger.error("Failed to calculate cosine similarity: %s", e, exc_info=True)
        return 0.0


def chunk_text(
    text: str, 
    chunk_size: int = 1500,  # Increased default from 500 to 1500
    chunk_overlap: int = 200,  # Increased default from 100 to 200
    chunk_type: str = "content"
) -> List[dict]:
    """
    Split text into overlapping chunks for better RAG performance.
    
    Args:
        text: The text to chunk
        chunk_size: Target number of characters per chunk (default: 1500)
        chunk_overlap: Number of characters to overlap between chunks (default: 200)
        chunk_type: Type of chunk - "content" or "summary"
        
    Returns:
        List of dictionaries containing chunk information:
        - chunk_text: The text content of the chunk
        - chunk_index: Order of chunk in original text
        - chunk_type: Type of chunk
        - start_char: Starting character position
        - end_char: Ending character position
        - token_count: Approximate token count (chars / 4)
    
    Raises:
        ValueError: If chunk_size exceeds recommended limits
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for chunking")
        return []
    
    # Validate chunk size to prevent exceeding API limits
    if chunk_size > _RECOMMENDED_MAX_CHUNK_SIZE:
        logger.warning(
            "chunk_size=%d exceeds recommended limit=%d. Adjusting to safe value.",
            chunk_size,
            _RECOMMENDED_MAX_CHUNK_SIZE
        )
        chunk_size = _RECOMMENDED_MAX_CHUNK_SIZE
    
    # Ensure overlap is reasonable
    if chunk_overlap >= chunk_size:
        logger.warning(
            "chunk_overlap=%d >= chunk_size=%d. Adjusting overlap to 20%% of chunk_size.",
            chunk_overlap,
            chunk_size
        )
        chunk_overlap = chunk_size // 5  # 20% overlap
    
    text = text.strip()
    chunks = []
    start = 0
    chunk_index = 0
    
    while start < len(text):
        # Calculate end position for this chunk
        end = start + chunk_size
        
        # If this is not the last chunk, try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings within the next 50 characters
            sentence_endings = ['. ', '! ', '? ', '\n\n', '\n']
            best_break = end
            
            for i in range(min(end + 50, len(text)) - 1, end - 50, -1):
                for ending in sentence_endings:
                    if text[i:i+len(ending)] == ending:
                        best_break = i + len(ending)
                        break
                if best_break != end:
                    break
            
            end = best_break
        else:
            end = len(text)
        
        # Extract chunk text
        chunk_text = text[start:end].strip()
        
        if chunk_text:  # Only add non-empty chunks
            chunks.append({
                "chunk_text": chunk_text,
                "chunk_index": chunk_index,
                "chunk_type": chunk_type,
                "start_char": start,
                "end_char": end,
                "token_count": len(chunk_text) // 4  # Rough estimate: 1 token ≈ 4 chars
            })
            chunk_index += 1
        
        # Move start position with overlap
        start = end - chunk_overlap
        
        # Avoid infinite loop if chunk is too small
        if start >= len(text) or (end == len(text)):
            break
    
    logger.info(
        "Successfully chunked text: %d chars → %d chunks (type=%s, size=%d, overlap=%d)",
        len(text), len(chunks), chunk_type, chunk_size, chunk_overlap
    )
    
    return chunks


def generate_chunk_embeddings(chunks: List[dict]) -> List[dict]:
    """
    Generate embeddings for a list of text chunks.
    
    Args:
        chunks: List of chunk dictionaries from chunk_text()
        
    Returns:
        List of chunk dictionaries with 'embedding' field added
        Chunks that fail to generate embeddings will have embedding=None
    """
    if not chunks:
        logger.warning("Empty chunks list provided for embedding generation")
        return []
    
    result_chunks = []
    
    texts = [chunk["chunk_text"] for chunk in chunks]
    embeddings = generate_embeddings_batch(texts, task_type="RETRIEVAL_DOCUMENT")

    for i, chunk in enumerate(chunks):
        chunk_copy = chunk.copy()
        chunk_copy["embedding"] = embeddings[i] if i < len(embeddings) else None
        result_chunks.append(chunk_copy)

        if (i + 1) % 10 == 0:
            logger.info("Generated embeddings for %d/%d chunks", i + 1, len(chunks))
    
    successful = sum(1 for c in result_chunks if c["embedding"] is not None)
    logger.info(
        "Chunk embedding complete: %d/%d successful",
        successful, len(chunks)
    )
    
    return result_chunks
