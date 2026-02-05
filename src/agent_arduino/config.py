"""Configuration settings for Arduino Agent."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for Arduino Agent."""

    # API Configuration
    ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    # ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    # ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")

    # Project Configuration
    DEFAULT_PROJECT_NAME: str = os.getenv("DEFAULT_PROJECT_NAME", "arduino_project")
    DESIGN_FILE_PATH: str = os.getenv("DESIGN_FILE_PATH", "design.txt")

    # Arduino Configuration
    ARDUINO_CLI_PATH: Optional[str] = os.getenv("ARDUINO_CLI_PATH", "arduino-cli")
    DEFAULT_BOARD_FQBN: str = os.getenv("DEFAULT_BOARD_FQBN", "arduino:avr:uno")
    DEFAULT_PORT: Optional[str] = os.getenv("DEFAULT_PORT")

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

        # Check if arduino-cli is available
        import shutil
        if not shutil.which(cls.ARDUINO_CLI_PATH):
            print(f"Warning: arduino-cli not found at '{cls.ARDUINO_CLI_PATH}'. Arduino commands may not work.")

    @classmethod
    def print_config(cls) -> None:
        """Print current configuration (without sensitive data)."""
        print("🤖 Arduino Agent Configuration:")
        print(f"  Model: {cls.ANTHROPIC_MODEL}")
        print(f"  Default Project Name: {cls.DEFAULT_PROJECT_NAME}")
        print(f"  Design File: {cls.DESIGN_FILE_PATH}")
        print(f"  Arduino CLI Path: {cls.ARDUINO_CLI_PATH}")
        print(f"  Default Board FQBN: {cls.DEFAULT_BOARD_FQBN}")
        print(f"  Default Port: {cls.DEFAULT_PORT or 'Not set'}")
        print(f"  Debug Mode: {cls.DEBUG_MODE}")
        print(f"  Verbose Logging: {cls.VERBOSE_LOGGING}")
        print(f"  Generate Wiring Diagram: {cls.GENERATE_WIRING_DIAGRAM}")
        print(f"  API Key Set: {'Yes' if cls.ANTHROPIC_API_KEY else 'No'}")
        print()

# Global config instance
config = Config()
config.validate()
