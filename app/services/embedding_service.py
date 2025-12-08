"""
Embedding service for generating vector embeddings using Google's text-embedding-005 model.
"""
import os
import logging
from typing import List, Optional
from google import genai
from google.genai import types
from app.common.constants import Common

logger = logging.getLogger(__name__)

# Initialize the GenAI client for Vertex AI
client = genai.Client(
    vertexai=True,
    project=os.getenv('GOOGLE_CLOUD_PROJECT'),
    location=os.getenv('GOOGLE_CLOUD_LOCATION')
)



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
    
    try:
        # Generate embedding using Google GenAI SDK
        response = client.models.embed_content(
            model=Common.EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=Common.EMBEDDING_DIMENSION
            )
        )
        
        # Extract embedding values from response
        if response and hasattr(response, 'embeddings') and len(response.embeddings) > 0:
            embedding = response.embeddings[0].values
            logger.info(
                "Successfully generated embedding (dim=%d, task=%s)", 
                len(embedding), 
                task_type
            )
            return list(embedding)
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
    Generate embeddings for multiple texts.
    
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
    
    embeddings = []
    for i, text in enumerate(texts):
        embedding = generate_embedding(text, task_type=task_type)
        embeddings.append(embedding)
        
        if (i + 1) % 10 == 0:
            logger.info("Generated embeddings for %d/%d texts", i + 1, len(texts))
    
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
