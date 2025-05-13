"""Application settings."""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseSettings, Field


# Set HOST_OS environment variable for Docker connection
if 'HOST_OS' not in os.environ and os.path.exists('/.dockerenv'):
    # Check if we're running on macOS
    try:
        import platform
        if platform.system() == 'Darwin' or (os.path.exists('/host/proc/version') and 'darwin' in open('/host/proc/version').read().lower()):
            os.environ['HOST_OS'] = 'macos'
    except Exception:
        pass


class Settings(BaseSettings):
    """Application settings."""

    # Application settings
    APP_NAME: str = "PromptWatcher"
    DEBUG: bool = Field(default=False)
    SECRET_KEY: str = Field(default="development-secret-key")
    
    # OpenSearch settings
    OPENSEARCH_HOST: str = Field(default="localhost")
    OPENSEARCH_PORT: int = Field(default=9200)
    OPENSEARCH_USERNAME: Optional[str] = Field(default=None)
    OPENSEARCH_PASSWORD: Optional[str] = Field(default=None)
    OPENSEARCH_USE_SSL: bool = Field(default=False)
    OPENSEARCH_VERIFY_CERTS: bool = Field(default=False)
    
    # Project metadata (for prompt records)
    PROJECT_NAME: str = Field(default="default")
    PROJECT_GOAL: str = Field(default="default")
    
    # Terminal monitoring settings
    TERMINAL_TYPE: str = Field(default="Terminal")
    MONITORING_INTERVAL: float = Field(default=5.0)  # Seconds between checks
    
    # Docker settings for terminal monitoring
    DOCKER_HELPER_IMAGE: str = Field(default="alpine:latest")
    DOCKER_TIMEOUT: int = Field(default=10)  # Seconds for helper container operations
    ALLOWED_USERS: List[str] = Field(default_factory=list)  # Empty means current user only
    
    # Host access settings
    HOST_PROC: str = Field(default="/proc")  # Path to host's proc filesystem when mounted
    HOST_OS: str = Field(default=os.environ.get("HOST_OS", ""))  # Host OS type for compatibility
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    TEMPLATES_DIR: Path = Path(__file__).parent / "presentation" / "templates"
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True