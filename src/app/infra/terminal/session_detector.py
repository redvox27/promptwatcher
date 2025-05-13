"""Terminal session detection implementation."""

import logging
import re
import os
import sys
from typing import Dict, List, Optional

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from src.app.infra.terminal.docker_client import DockerClient

logger = logging.getLogger(__name__)


class TerminalSessionDetector:
    """Detector for terminal sessions on the host machine."""
    
    def __init__(self, docker_client: DockerClient):
        """
        Initialize the terminal session detector.
        
        Args:
            docker_client: Docker client for executing commands on the host
        """
        self.docker_client = docker_client
    
    def list_terminal_sessions(self, interactive_only: bool = False) -> List[Dict]:
        """
        List all terminal sessions on the host machine.
        
        Args:
            interactive_only: Whether to include only interactive terminal sessions
            
        Returns:
            List of dictionaries with terminal session information
        """
        try:
            # Get process list from host with proper formatting
            # Add header names for clarity, wide output, and include all processes
            command = "ps auxww"
            logger.info(f"Running command: {command}")
            result = self.docker_client.run_in_host(command)
            
            # Save a few lines for debugging
            debug_sample = "\n".join(result.splitlines()[:5])
            logger.debug(f"Sample ps output: {debug_sample}")
            
            # Parse the output
            all_sessions = self._parse_ps_output(result)
            logger.info(f"Found {len(all_sessions)} total processes")
            
            # Filter for terminal processes
            terminal_sessions = [s for s in all_sessions if s.get("terminal", "?") != "?"]
            logger.info(f"Found {len(terminal_sessions)} processes attached to terminals")
            
            # Filter sessions if requested
            if interactive_only:
                interactive_sessions = [s for s in all_sessions if self._is_interactive_terminal(s)]
                logger.info(f"Found {len(interactive_sessions)} interactive terminal sessions")
                return interactive_sessions
            else:
                return terminal_sessions
            
        except Exception as e:
            logger.error(f"Error listing terminal sessions: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _parse_ps_output(self, output: str) -> List[Dict]:
        """
        Parse the output of ps command.
        
        Args:
            output: Output string from ps command
            
        Returns:
            List of dictionaries with parsed process information
        """
        sessions = []
        lines = output.strip().split("\n")
        
        if not lines:
            logger.warning("Empty output from ps command")
            return []
            
        # Check if we have any lines
        if len(lines) <= 1:
            logger.warning(f"Unexpected ps output format (only one line): {lines}")
            return []
            
        # Log header for debugging
        header = lines[0]
        logger.debug(f"PS header: {header}")
        
        # Process lines (skip header)
        process_lines = lines[1:]
        logger.debug(f"Found {len(process_lines)} process lines")
            
        for i, line in enumerate(process_lines):
            if not line.strip():
                continue
                
            # Log a sample of lines for debugging
            if i < 3:
                logger.debug(f"Process line {i+1}: {line}")
                
            # Parse the process line
            session = self._parse_process_line(line)
            if session:
                sessions.append(session)
            elif i < 3:
                # Only log the first few failures to avoid log spam
                logger.warning(f"Failed to parse line: {line}")
        
        return sessions
    
    def _parse_process_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single line from ps output.
        
        Args:
            line: A line from ps output
            
        Returns:
            Dictionary with process information or None if parsing failed
        """
        try:
            # For Alpine docker container, the output format is:
            # PID   USER     TIME  COMMAND
            parts = line.strip().split(None, 3)  # Split by whitespace, max 4 parts
            
            if len(parts) < 4:
                logger.debug(f"Line has fewer than 4 parts: {line}")
                return None
                
            pid_str = parts[0]
            user = parts[1]
            # time = parts[2]  # We don't use this
            command = parts[3]
            
            # Validate PID is numeric
            if not pid_str.isdigit():
                logger.debug(f"PID is not numeric: {pid_str}")
                return None
                
            pid = int(pid_str)
            
            # Check if this is a terminal process
            terminal = "?"  # Default to ? (no terminal)
            
            # Look for terminal-related strings in command
            if "bash" in command or "sh " in command or "terminal" in command.lower():
                # For bash and shell processes, assume pts/0 if we can't determine
                terminal = "pts/0"
            
            # Create session info
            session = {
                "pid": pid,
                "user": user,
                "terminal": terminal,
                "command": command,
                "start_time": "",  # We don't have this in Alpine PS output
                "state": "",  # We don't have this in Alpine PS output
                "is_foreground": False,  # Can't determine this
            }
            
            return session
            
        except Exception as e:
            logger.debug(f"Failed to parse process line: {line}, Error: {str(e)}")
            return None
    
    def _is_interactive_terminal(self, session: Dict) -> bool:
        """
        Determine if a session is an interactive terminal.
        
        Args:
            session: Session dictionary
            
        Returns:
            True if session is an interactive terminal, False otherwise
        """
        terminal = session.get("terminal", "")
        command = session.get("command", "").lower()
        
        # Check if it's a terminal-connected process (pts/ or tty)
        is_terminal = terminal.startswith(("pts/", "tty")) and terminal != "?"
        
        # If not connected to a terminal, it's definitely not interactive
        if not is_terminal:
            return False
        
        # Exclude processes that are clearly not interactive
        excluded_commands = [
            "ps aux", "ps -ef", "grep", "sshd", "sftp-server", 
            "bash -c", "sleep", "tail -f", "cat ", "docker "
        ]
        is_excluded = any(cmd in command for cmd in excluded_commands)
        
        # Include known interactive shells
        interactive_shells = ["bash", "sh ", "zsh", "fish", "python", "ruby", "node", "claude"]
        is_shell = any(shell in command for shell in interactive_shells)
        
        # Include terminal emulators
        terminal_emulators = ["terminal", "iterm", "xterm", "konsole", "gnome-terminal"]
        is_terminal_emulator = any(emulator in command for emulator in terminal_emulators)
        
        # Final decision
        return is_terminal and not is_excluded and (is_shell or is_terminal_emulator)