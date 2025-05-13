"""Docker client for accessing host system."""

import logging
import re
from typing import Dict, List, Optional, Union

import docker
from docker.errors import DockerException

logger = logging.getLogger(__name__)


class DockerClient:
    """Client for interacting with Docker to access host system resources."""

    def __init__(self):
        """Initialize the Docker client."""
        self.client = None
        self.connected = False
        self.connect()

    def connect(self) -> bool:
        """
        Connect to the Docker daemon.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Use the Docker socket directly with correct URL format
            self.client = docker.from_env()
            # Alternatively, try direct socket path if from_env() doesn't work
            # self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')
            # Test connection
            self.client.ping()
            self.connected = True
            logger.info("Successfully connected to Docker daemon")
            return True
        except DockerException as e:
            self.connected = False
            logger.error(f"Failed to connect to Docker daemon: {str(e)}")
            return False

    def is_connected(self) -> bool:
        """
        Check if connected to Docker daemon.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if not self.connected or not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except DockerException:
            self.connected = False
            return False

    def validate_command(self, command: str) -> bool:
        """
        Ensure command is in the whitelist of safe commands.
        
        Args:
            command: Command to validate
            
        Returns:
            bool: True if command is safe, False otherwise
        """
        # Only allow specific read-only commands
        allowed_patterns = [
            r'^ps\s',
            r'^lsof\s',
            r'^cat\s',
            r'^grep\s',
            r'^timeout\s+\d+\s+cat\s',
            r'^script\s'
        ]
        return any(re.match(pattern, command) for pattern in allowed_patterns)

    def run_in_host(self, command: str, timeout: int = 10) -> str:
        """
        Run command in the host's namespace using a helper container.
        
        Args:
            command: Command to run
            timeout: Command timeout in seconds
            
        Returns:
            str: Command output
            
        Raises:
            ValueError: If command is not allowed
            DockerException: If Docker operation fails
        """
        if not self.is_connected():
            if not self.connect():
                raise DockerException("Not connected to Docker daemon")
        
        if not self.validate_command(command):
            raise ValueError(f"Command not allowed: {command}")
        
        try:
            result = self.client.containers.run(
                'alpine:latest',
                command,
                remove=True,        # Remove container after execution
                privileged=True,     # Required for accessing host processes
                pid='host',          # Use host's PID namespace
                network='host',      # Use host's network namespace
                stdout=True,         # Capture stdout
                stderr=True,         # Capture stderr
                detach=False,        # Run in foreground
                timeout=timeout      # Set timeout
            )
            
            # Convert bytes to string if needed
            if isinstance(result, bytes):
                result = result.decode('utf-8', errors='replace')
                
            return result
        except DockerException as e:
            logger.error(f"Docker command failed: {str(e)}")
            raise