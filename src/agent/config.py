"""Configuration settings for IoT Agent (supports both Arduino and ESP-IDF)."""

import os
from typing import Optional, Literal
from dotenv import load_dotenv

load_dotenv()

PlatformType = Literal["Arduino", "ESP-IDF"]


class BaseConfig:
    """Base configuration shared by all platforms."""

    PROJECT_NAME: str
    PLATFORM: PlatformType
    
    # API Configuration
    ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

    # Project Configuration
    DESIGN_FILE_PATH: str = os.getenv("DESIGN_FILE_PATH", "design.txt")

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

    @classmethod
    def print_config(cls) -> None:
        """Print current configuration (without sensitive data)."""
        print(f"🤖 IoT Agent Configuration ({cls.PLATFORM}):")
        print(f"  Model: {cls.ANTHROPIC_MODEL}")
        print(f"  Platform: {cls.PLATFORM}")
        print(f"  Default Project Name: {cls.DEFAULT_PROJECT_NAME}")
        print(f"  Design File: {cls.DESIGN_FILE_PATH}")
        print(f"  Debug Mode: {cls.DEBUG_MODE}")
        print(f"  Verbose Logging: {cls.VERBOSE_LOGGING}")
        print(f"  Generate Wiring Diagram: {cls.GENERATE_WIRING_DIAGRAM}")
        print(f"  API Key Set: {'Yes' if cls.ANTHROPIC_API_KEY else 'No'}")


class ArduinoConfig(BaseConfig):
    """Configuration for Arduino platform."""

    PLATFORM: PlatformType = "Arduino"

    ARDUINO_CLI_PATH: Optional[str] = os.getenv("ARDUINO_CLI_PATH", "arduino-cli")
    DEFAULT_BOARD_FQBN: str = os.getenv("DEFAULT_BOARD_FQBN", "arduino:avr:mega:cpu=atmega2560")
    DEFAULT_PORT: Optional[str] = os.getenv("DEFAULT_PORT")

    @classmethod
    def validate(cls) -> None:
        super().validate()
        import shutil
        if not shutil.which(cls.ARDUINO_CLI_PATH):
            print(f"Warning: arduino-cli not found at '{cls.ARDUINO_CLI_PATH}'. Arduino commands may not work.")

    @classmethod
    def print_config(cls) -> None:
        super().print_config()
        print(f"  Arduino CLI Path: {cls.ARDUINO_CLI_PATH}")
        print(f"  Default Board FQBN: {cls.DEFAULT_BOARD_FQBN}")
        print(f"  Default Port: {cls.DEFAULT_PORT or 'Not set'}")
        print()


class ESPIDFConfig(BaseConfig):
    """Configuration for ESP-IDF platform."""

    PLATFORM: PlatformType = "ESP-IDF"

    IDF_PATH: Optional[str] = os.getenv("IDF_PATH")

    @classmethod
    def validate(cls) -> None:
        super().validate()
        if not cls.IDF_PATH:
            print("Warning: IDF_PATH not set. ESP-IDF commands may not work.")

    @classmethod
    def print_config(cls) -> None:
        super().print_config()
        print(f"  IDF Path: {cls.IDF_PATH or 'Not set'}")
        print()


def get_config(platform: PlatformType) -> BaseConfig:
    """Get configuration for the specified platform."""
    if platform == "ESP-IDF":
        cfg = ESPIDFConfig()
    elif platform == "Arduino":
        cfg = ArduinoConfig()
    else:
        raise NotImplementedError
    cfg.validate()
    return cfg


# Backwards-compatible alias for shared config values (API key, model, etc.)
config = BaseConfig

