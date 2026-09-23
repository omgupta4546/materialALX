import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")
ConfigType = TypeVar("ConfigType", bound=BaseModel)

class BaseAIModule(ABC, Generic[InputType, OutputType, ConfigType]):
    """
    Abstract base class for all independent AI Engine Modules.
    Ensures strict adherence to interface, configuration, logging, and versioning.
    """

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the current version of the module."""
        pass

    def __init__(self, config: Optional[ConfigType] = None):
        """
        Initialize the AI module with its configuration and logger.
        """
        self.logger = logging.getLogger(f"ai.{self.__class__.__name__.lower()}")
        # Setup basic logging if not configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            
        # Handle default configuration if not provided
        self.config = config if config is not None else self.get_default_config()

    @abstractmethod
    def get_default_config(self) -> ConfigType:
        """Return the default Pydantic configuration for this module."""
        pass

    @abstractmethod
    def process(self, input_data: InputType) -> OutputType:
        """
        Core execution logic for the module.
        Must NOT accept database sessions or modify external DB state.
        """
        pass
