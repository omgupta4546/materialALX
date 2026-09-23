import logging
import sys
from app.middleware.request_context import get_request_id, get_correlation_id

class RequestContextFilter(logging.Filter):
    """Injects request_id and correlation_id into log records."""
    def filter(self, record):
        record.request_id = get_request_id()
        record.correlation_id = get_correlation_id()
        return True

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [req_id=%(request_id)s] [corr_id=%(correlation_id)s] %(message)s"
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestContextFilter())
    logger.addHandler(handler)
