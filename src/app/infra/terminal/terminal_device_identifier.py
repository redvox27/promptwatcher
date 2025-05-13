"""Terminal device identification implementation."""

import logging
import os
import re
import sys
from typing import Dict, List, Optional, Set

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from src.app.infra.terminal.docker_client import DockerClient

logger = logging.getLogger(__name__)


class TerminalDeviceIdentifier:
    """Identifier for terminal devices on the host system."""
    
    def __init__(self, docker_client: DockerClient):
        """
        Initialize the terminal device identifier.
        
        Args:
            docker_client: Docker client for executing commands on the host
        """
        self.docker_client = docker_client
    
    def get_terminal_devices(self, pid: int) -> List[Dict]:
        """
        Get terminal devices associated with a process.
        
        Args:
            pid: Process ID to check
            
        Returns:
            List of dictionaries with terminal device information
        """
        try:
            # Use lsof to find terminal devices for the process
            command = f"lsof -p {pid} | grep -E 'tty|pts'"
            result = self.docker_client.run_in_host(command)
            
            # Parse the output
            return self._parse_lsof_output(result)
            
        except Exception as e:
            logger.error(f"Error getting terminal devices for PID {pid}: {str(e)}")
            return []
    
    def _parse_lsof_output(self, output: str) -> List[Dict]:
        """
        Parse the output of lsof command.
        
        Args:
            output: Output string from lsof command
            
        Returns:
            List of dictionaries with terminal device information
        """
        if not output.strip():
            return []
        
        devices = {}
        
        # Process each line
        for line in output.strip().split("\n"):
            parts = line.split()
            if len(parts) < 9:
                continue
            
            # Extract relevant fields
            command = parts[0]
            file_descriptor = parts[3]
            device_type = parts[4]
            device_path = parts[8]
            
            # Skip non-character devices
            if device_type != "CHR":
                continue
            
            # Extract numeric file descriptor
            fd_match = re.match(r'(\d+)[uwr]?', file_descriptor)
            if not fd_match:
                continue
                
            fd = int(fd_match.group(1))
            
            # Group by device path
            if device_path not in devices:
                devices[device_path] = {
                    "device_path": device_path,
                    "command": command,
                    "file_descriptors": []
                }
                
            # Add file descriptor
            devices[device_path]["file_descriptors"].append(fd)
        
        # Convert to list
        return list(devices.values())
    
    def is_terminal_readable(self, device_path: str) -> bool:
        """
        Check if a terminal device is readable.
        
        Args:
            device_path: Path to terminal device
            
        Returns:
            True if terminal is readable, False otherwise
        """
        try:
            # Try to read from the device
            command = f"timeout 1 head -c 1 {device_path} || echo 'Access check successful'"
            self.docker_client.run_in_host(command)
            return True
        except Exception as e:
            logger.debug(f"Terminal {device_path} is not readable: {str(e)}")
            return False
    
    def get_terminal_type(self, device_path: str) -> Optional[str]:
        """
        Get the type of a terminal device.
        
        Args:
            device_path: Path to terminal device
            
        Returns:
            Terminal type (e.g., xterm, vt100) or None if not found
        """
        try:
            # Try to get environment variables for the terminal
            command = f"ps -o command= -t {device_path} | grep -o 'TERM=[^[:space:]]*' | head -1"
            result = self.docker_client.run_in_host(command)
            
            # Extract terminal type
            term_match = re.search(r'TERM=(\S+)', result)
            if term_match:
                return term_match.group(1)
                
            # If not found, try a different approach
            command = f"ps aux | grep {device_path.split('/')[-1]} | grep -v grep"
            result = self.docker_client.run_in_host(command)
            
            # Look for common terminal types
            term_types = ["xterm", "vt100", "ansi", "screen", "tmux"]
            for term_type in term_types:
                if term_type in result.lower():
                    return f"{term_type}"
            
            # Return a default value if we couldn't determine the type
            return "unknown"
            
        except Exception as e:
            logger.error(f"Error getting terminal type for {device_path}: {str(e)}")
            return None
    
    def get_active_terminal_devices(self) -> List[str]:
        """
        Get all active terminal devices on the system.
        
        Returns:
            List of terminal device paths
        """
        try:
            # Find all terminal devices
            command = "find /dev -regex '.*pts/[0-9]+|.*tty[0-9]+|.*ttys[0-9]+' 2>/dev/null || echo ''"
            result = self.docker_client.run_in_host(command)
            
            # Parse the output
            devices = []
            for line in result.strip().split("\n"):
                if line and any(pattern in line for pattern in ["/pts/", "/tty", "/ttys"]):
                    devices.append(line)
            
            return devices
            
        except Exception as e:
            logger.error(f"Error getting active terminal devices: {str(e)}")
            return []