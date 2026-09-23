import os
import logging
from typing import Callable, Any
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.ai.llm.provider import LLMProvider
from app.ai.llm.providers.mock_provider import MockProvider
from app.ai.llm.providers.openai_provider import OpenAIProvider
from app.ai.llm.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)



def with_retry(max_retries: int = 3, fallback_to_mock: bool = True):
    """
    Robust decorator that wraps LLM calls with automatic retries and exponential backoff.
    If the API continually fails (e.g. timeout, rate limit), it optionally falls back to the MockProvider
    so the AI pipeline doesn't crash in production for non-critical explanations.
    """
    def decorator(func: Callable) -> Callable:
        
        # We use tenacity to handle the retry loop internally
        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(Exception),
            reraise=True
        )
        def robust_call(*args, **kwargs) -> Any:
            return func(*args, **kwargs)
            
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return robust_call(*args, **kwargs)
            except Exception as e:
                logger.error(f"LLM Provider failed after {max_retries} retries: {str(e)}")
                if fallback_to_mock:
                    logger.warning("Falling back to MockProvider for this request.")
                    
                    # Instantiate mock and dynamically call the same method name
                    mock = MockProvider()
                    method_name = func.__name__
                    mock_method = getattr(mock, method_name)
                    
                    # Remove 'self' from args if present (since wrapper passes provider instance)
                    # For a method call, args[0] is the provider instance.
                    mock_args = args[1:] if args and isinstance(args[0], LLMProvider) else args
                    return mock_method(*mock_args, **kwargs)
                else:
                    raise e
                    
        return wrapper
    return decorator
