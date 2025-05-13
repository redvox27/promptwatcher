"""Docker client for accessing host system."""

import logging
import os
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
            # First check if we're on macOS (for specialized error handling)
            is_macos = False
            if os.environ.get("HOST_OS", "").lower() == "macos":
                is_macos = True
                logger.info("Detected macOS environment from HOST_OS env var")
            
            # Try connection with longer timeout for macOS
            timeout = 10 if is_macos else 5
            
            result = subprocess.run(
                ["docker", "version"], 
                capture_output=True, 
                text=True,
                timeout=timeout
            )
            if result.returncode == 0:
                logger.info("Docker CLI is available")
                self.connected = True
                return True
            else:
                if is_macos:
                    logger.error(f"Docker CLI check failed on macOS: {result.stderr}")
                    logger.error("This might be due to Docker Desktop configuration issues.")
                    logger.error("Try running the macos-docker-fix.sh script in the project root.")
                else:
                    logger.error(f"Docker CLI check failed: {result.stderr}")
                self.connected = False
                return False
        except subprocess.TimeoutExpired:
            logger.error("Docker connection timed out - Docker daemon may be busy or not responding")
            logger.error("For macOS, make sure Docker Desktop is running and accessible")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Failed to check Docker CLI: {str(e)}")
            if "No such file or directory" in str(e):
                logger.error("Docker command not found. Is Docker installed?")
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
            r'^script\s',
            r'^ls\s',
            r'^find\s',
            r'^readlink\s',
            r'^stat\s',
            r'^who\s',
            r'^w\s',
            r'^tty\s'
        ]
        return any(re.match(pattern, command) for pattern in allowed_patterns)

    def run_in_host(self, command: str, timeout: int = 10, use_host_proc: bool = False) -> str:
        """
        Run command in the host's namespace using a helper container.
        
        Args:
            command: Command to run
            timeout: Command timeout in seconds
            use_host_proc: Whether to run the command with access to host's /proc
            
        Returns:
            str: Command output
            
        Raises:
            ValueError: If command is not allowed
            DockerException: If Docker operation fails
        """
        # Check if we're on macOS to provide better handling
        is_macos = os.environ.get("HOST_OS", "").lower() == "macos"
        
        if not self.is_connected():
            logger.warning("Docker connection not established, attempting to connect...")
            if not self.connect():
                error_msg = "Not connected to Docker daemon"
                if is_macos:
                    error_msg += " (macOS environment detected - make sure Docker Desktop is running and properly configured)"
                    logger.error("For macOS users: Try running the macos-docker-fix.sh script in the project root")
                raise DockerException(error_msg)
        
        if not self.validate_command(command):
            raise ValueError(f"Command not allowed: {command}")
        
        # Check if we already have direct access to host proc
        host_proc_exists = os.path.exists('/host/proc')
        
        try:
            # Different approach if we're already in a container with host access
            if host_proc_exists and use_host_proc:
                logger.info(f"Running command directly with host proc mounted: {command}")
                try:
                    # If we already have /host/proc mounted, we can just run the command directly
                    # with proper environment variables to point to host resources
                    env = os.environ.copy()
                    env['HOST_PROC'] = '/host/proc'
                    env['HOST_DEV'] = '/host/dev' if os.path.exists('/host/dev') else '/dev'
                    
                    # Adjust command to use host proc if needed
                    if command.startswith('ps '):
                        # We need to handle ps specially since it reads /proc directly
                        logger.info("Modifying ps command to use host process namespace")
                        # Simple approach for ps - we'll just list processes manually from host proc
                        if 'aux' in command or '-e' in command:
                            command = f"find /host/proc -maxdepth 1 -type d -regex '/host/proc/[0-9]+' | sort -n"
                    
                    result = subprocess.run(
                        command, 
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        check=True,
                        env=env
                    )
                    output = result.stdout
                    return output
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    logger.error(f"Direct command execution failed: {str(e)}")
                    # Fall back to docker approach
                    logger.info("Falling back to Docker approach")
                
            # Construct docker run command
            docker_run_cmd = [
                "docker", "run",
                "--rm",                 # Remove container after execution
                "--privileged",         # Required for accessing host processes
                "--pid=host",           # Use host's PID namespace
                "--network=host",       # Use host's network namespace
            ]
            
            # Mount host proc if requested and available on host
            if host_proc_exists and use_host_proc:
                docker_run_cmd.extend(["-v", "/host/proc:/proc:ro"])
                # If host dev is also available, mount it too
                if os.path.exists('/host/dev'):
                    docker_run_cmd.extend(["-v", "/host/dev:/dev:ro"])
            
            # Complete the command
            docker_run_cmd.extend([
                "alpine:latest",
                "sh", "-c", command     # Run command
            ])
            
            logger.debug(f"Running Docker command: {' '.join(docker_run_cmd)}")
            
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
            import traceback
            logger.error(traceback.format_exc())
            raise DockerException(f"Docker command failed: {str(e)}")