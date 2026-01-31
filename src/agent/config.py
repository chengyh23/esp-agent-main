"""Configuration settings for ESP-IDF Agent."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for ESP-IDF Agent."""

    # API Configuration
    ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    # ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    # ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")

    # Project Configuration
    DEFAULT_PROJECT_NAME: str = os.getenv("DEFAULT_PROJECT_NAME", "esp_project")
    DESIGN_FILE_PATH: str = os.getenv("DESIGN_FILE_PATH", "design.txt")

    # ESP-IDF Configuration
    IDF_PATH: Optional[str] = os.getenv("IDF_PATH")

    # Agent Configuration
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "60"))

    # Debug Configuration
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"
    VERBOSE_LOGGING: bool = os.getenv("VERBOSE_LOGGING", "true").lower() == "true"

    # Wiring Diagram Configuration
    GENERATE_WIRING_DIAGRAM: bool = os.getenv("GENERATE_WIRING_DIAGRAM", "false").lower() == "true"

    @classmethod
    def validate(cls) -> None:
        """Validate configuration settings."""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required. Set it in .env file or environment variable.")

        if not cls.IDF_PATH:
            print("Warning: IDF_PATH not set. ESP-IDF commands may not work.")

    @classmethod
    def print_config(cls) -> None:
        """Print current configuration (without sensitive data)."""
        print("🤖 ESP-IDF Agent Configuration:")
        print(f"  Model: {cls.ANTHROPIC_MODEL}")
        print(f"  Default Project Name: {cls.DEFAULT_PROJECT_NAME}")
        print(f"  Design File: {cls.DESIGN_FILE_PATH}")
        print(f"  IDF Path: {cls.IDF_PATH or 'Not set'}")
        print(f"  Debug Mode: {cls.DEBUG_MODE}")
        print(f"  Verbose Logging: {cls.VERBOSE_LOGGING}")
        print(f"  Generate Wiring Diagram: {cls.GENERATE_WIRING_DIAGRAM}")
        print(f"  API Key Set: {'Yes' if cls.ANTHROPIC_API_KEY else 'No'}")
        print()

# Global config instance
config = Config()
config.validate()