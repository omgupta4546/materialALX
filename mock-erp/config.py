"""
Mock ERP Configuration Module

Settings for the synthetic ERP API adapter. Controls how legacy system behavior
is simulated for development without touching real SAP/ERP instances.
"""
import os
from pydantic_settings import BaseSettings

class MockERPConfig(BaseSettings):
    # Behavior settings for the mock adapter
    MOCK_DELAY_MS: int = 200  # Simulate network latency (milliseconds)
    ERROR_RATE: float = 0.05  # Simulate 5% error rate from legacy systems
    
    # Source data for synthetic responses
    SYNTHETIC_DATA_PATH: str = "./data/synthetic"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Global mock ERP config instance
mock_erp_config = MockERPConfig()
