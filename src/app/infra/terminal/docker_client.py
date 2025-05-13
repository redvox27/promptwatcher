"""Docker client for accessing host system."""

import logging
import re
import subprocess
import shlex
from typing import Dict, List, Optional, Union

# Try to import docker library but provide fallback
try:
    import docker
    from docker.errors import DockerException
    DOCKER_SDK_AVAILABLE = True
except ImportError:
    DOCKER_SDK_AVAILABLE = False
    
    # Define a dummy exception class for consistency
    class DockerException(Exception):
        pass

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
        # Check if docker command is available using direct command
        try:
            result = subprocess.run(
                ["docker", "version"], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("Docker CLI is available")
                self.connected = True
                return True
            else:
                logger.error(f"Docker CLI check failed: {result.stderr}")
                self.connected = False
                return False
        except Exception as e:
            logger.error(f"Failed to check Docker CLI: {str(e)}")
            self.connected = False
            return False

    def is_connected(self) -> bool:
        """
        Check if connected to Docker daemon.
        
        Returns:
            bool: True if connected, False otherwise
        """
        # Re-check connection
        return self.connect()

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
            # Construct docker run command
            docker_run_cmd = [
                "docker", "run",
                "--rm",                 # Remove container after execution
                "--privileged",         # Required for accessing host processes
                "--pid=host",           # Use host's PID namespace
                "--network=host",       # Use host's network namespace
                "alpine:latest",
                "sh", "-c", command     # Run command
            ]
            
            # Run the command with timeout
            result = subprocess.run(
                docker_run_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )
            
            # Return stdout, or stderr if stdout is empty
            output = result.stdout
            
            # Log output for debugging (truncated)
            if output:
                sample_lines = output.splitlines()[:3]
                sample = "\n".join(sample_lines)
                logger.debug(f"Command output sample (first 3 lines):\n{sample}")
                logger.debug(f"Output length: {len(output)} characters, {len(output.splitlines())} lines")
            else:
                logger.warning("Command produced no output")
                
            if not output and result.stderr:
                logger.warning(f"Command produced stderr: {result.stderr}")
                output = result.stderr
                
            return output
        except subprocess.CalledProcessError as e:
            logger.error(f"Docker command failed: {str(e)}")
            if e.stderr:
                logger.error(f"Error output: {e.stderr}")
            raise DockerException(f"Docker command failed: {str(e)}")
        except subprocess.TimeoutExpired as e:
            logger.error(f"Docker command timed out after {timeout} seconds")
            raise DockerException(f"Docker command timed out: {str(e)}")
        except Exception as e:
            logger.error(f"Docker command failed with unexpected error: {str(e)}")
            raise DockerException(f"Docker command failed: {str(e)}")