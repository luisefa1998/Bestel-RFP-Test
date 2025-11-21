"""
Centralized rate limiter for WatsonX AI API calls.

This service provides a global rate limiter using LangChain's built-in InMemoryRateLimiter
to limit API requests across ALL AI operations (summarization, chat, embeddings, etc.)
to prevent hitting WatsonX API rate limits (8 requests/second).

The rate limiter is shared across all Celery workers and async tasks in the same process.
"""
import logging
from langchain_core.rate_limiters import InMemoryRateLimiter

logger = logging.getLogger(__name__)

# Global rate limiter for WatsonX API calls
# WatsonX API limit: 8 requests per second
# max_bucket_size: Controls burst capacity (allows up to 20 requests when idle)
watsonx_rate_limiter = InMemoryRateLimiter(
    requests_per_second=8,  # Match WatsonX API limit exactly
    check_every_n_seconds=0.1,  # Check every 100ms
    max_bucket_size=20,  # Allow bursting up to 20 requests when idle
)


def get_rate_limiter() -> InMemoryRateLimiter:
    """
    Get the global WatsonX rate limiter instance.
    
    Usage with ChatWatsonx:
        from app.services.rate_limiter_service import get_rate_limiter
        
        chat = ChatWatsonx(
            watsonx_client=api_client,
            model_id="openai/gpt-oss-120b",
            params={"temperature": 0.1, "max_tokens": 4096},
            rate_limiter=get_rate_limiter()  # <-- Add this
        )
    
    Returns:
        The global InMemoryRateLimiter instance
    """
    return watsonx_rate_limiter


# Log initialization
logger.info("=" * 80)
logger.info("Rate Limiter Service initialized using LangChain InMemoryRateLimiter")
logger.info(f"  - Requests per second: 8")
logger.info(f"  - Max bucket size: 20")
logger.info(f"  - Check interval: 0.1s")
logger.info("=" * 80)

# Made with Bob
