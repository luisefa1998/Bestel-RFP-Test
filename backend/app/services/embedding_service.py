import os
import logging
from typing import List
from app.core.settings import settings
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import Embeddings

# Set up logging
logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        model_id = settings.EMBEDDING_MODEL
        if "/" in model_id:
            provider, mid = model_id.split("/", 1)
            provider = "ibm" if "ibm" in provider.lower() else provider
            self.model_id = f"{provider}/{mid}"
        else:
            self.model_id = model_id

        self.embedding = Embeddings(
            model_id=self.model_id,
            credentials=Credentials(
                api_key=settings.WX_API_KEY,
                url = "https://us-south.ml.cloud.ibm.com"),
            project_id=settings.WX_PROJECT_ID
            )

    def embed_query(self, query: str) -> List[float]:
        """Synchronous method to embed a single text"""
        embedding_vector: List[float] = self.embedding.embed_query(text=query)
        return embedding_vector
        
    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Synchronous method to embed multiple documents in batches.
        Handles API limit of 1000 documents per batch.
        
        Args:
            documents: List of text documents to embed
            
        Returns:
            List of embedding vectors for each document
            
        Raises:
            ValueError: If the number of embeddings doesn't match the number of documents
            Exception: If there's an error during embedding
        """
        if not documents:
            logger.warning("Empty documents list provided to embed_documents")
            return []
        
        # Process in batches of 1000 (API limit)
        BATCH_SIZE = 1000
        all_embeddings = []
        
        logger.info(f"Starting to embed {len(documents)} documents in batches of {BATCH_SIZE}")
        
        # Process documents in batches
        for i in range(0, len(documents), BATCH_SIZE):
            batch = documents[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(documents) + BATCH_SIZE - 1) // BATCH_SIZE
            
            logger.info(f"Embedding batch {batch_num}/{total_batches}: {len(batch)} documents (indices {i}-{i+len(batch)-1})")
            
            try:
                batch_embeddings = self.embedding.embed_documents(texts=batch)
                
                # Validate that we got the expected number of embeddings
                if len(batch_embeddings) != len(batch):
                    error_msg = f"Batch {batch_num}: Expected {len(batch)} embeddings but got {len(batch_embeddings)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                all_embeddings.extend(batch_embeddings)
                logger.info(f"Batch {batch_num}/{total_batches} completed successfully")
                
            except Exception as e:
                logger.error(f"Error embedding batch {batch_num}/{total_batches}: {str(e)}")
                raise  # Re-raise the exception to stop processing
        
        # Final validation
        if len(all_embeddings) != len(documents):
            error_msg = f"Embedding count mismatch: Expected {len(documents)} embeddings but got {len(all_embeddings)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Successfully embedded all {len(documents)} documents")
        return all_embeddings
