"""
Simple test script to test the embedding service with dummy sentences.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.embedding_service import EmbeddingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def test_embed_documents():
    """
    Test the embed_documents function with dummy sentences
    """
    # Create the embedding service
    logger.info("Initializing embedding service...")
    embedding_service = EmbeddingService()
    
    # Dummy sentences to embed
    dummy_sentences = [
        "This is the first test sentence for embedding.",
        "Here is another sentence about machine learning.",
        "The quick brown fox jumps over the lazy dog.",
        "Natural language processing is fascinating.",
        "Embeddings convert text into numerical vectors."
    ]
    
    logger.info(f"Embedding {len(dummy_sentences)} dummy sentences...")
    logger.info("Sentences:")
    for i, sentence in enumerate(dummy_sentences, 1):
        logger.info(f"  {i}. {sentence}")
    
    try:
        # Embed the documents
        embeddings = embedding_service.embed_documents(dummy_sentences)
        
        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("EMBEDDING RESULTS:")
        logger.info("=" * 80)
        logger.info(f"Number of embeddings generated: {len(embeddings)}")
        
        for i, embedding in enumerate(embeddings, 1):
            logger.info(f"\nSentence {i}: '{dummy_sentences[i-1]}'")
            logger.info(f"  Embedding dimension: {len(embedding)}")
            logger.info(f"  First 5 values: {embedding[:5]}")
            logger.info(f"  Last 5 values: {embedding[-5:]}")
        
        logger.info("=" * 80)
        logger.info("✓ Embedding test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during embedding: {str(e)}", exc_info=True)


if __name__ == "__main__":
    logger.info("Starting embedding service test...")
    test_embed_documents()
    logger.info("Test completed.")

# Made with Bob