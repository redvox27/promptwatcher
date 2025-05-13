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
        # Check if we're running in a container with HOST_PROC environment variable
        self.host_proc = os.environ.get("HOST_PROC", "/proc")
        self.use_host_proc = os.path.exists('/host/proc') or self.host_proc != "/proc"
        if self.use_host_proc and self.host_proc == "/proc" and os.path.exists('/host/proc'):
            self.host_proc = '/host/proc'
        logger.info(f"Using proc filesystem at: {self.host_proc} (direct access: {self.use_host_proc})")
    
    def list_terminal_sessions(self, interactive_only: bool = False) -> List[Dict]:
        """
        List all terminal sessions on the host machine.
        
        Args:
            interactive_only: Whether to include only interactive terminal sessions
            
        Returns:
            List of dictionaries with terminal session information
        """
        # The following code is now enabled
        try:
            all_sessions = []
            
            # For MacOS compatibility, we need a specialized approach
            # Try to detect if we're running on macOS using multiple methods
            is_macos = False
            
            # Method 1: Check environment variable that could be set in docker-compose.yml
            if os.environ.get("HOST_OS", "").lower() == "macos":
                is_macos = True
                logger.info("Detected macOS from HOST_OS environment variable")
            
            # Method 2: Try to detect from host proc (less reliable)
            if not is_macos and os.path.exists('/host/proc/version'):
                try:
                    with open('/host/proc/version', 'r') as f:
                        version_info = f.read().lower()
                        if 'darwin' in version_info:
                            is_macos = True
                            logger.info("Detected macOS from /host/proc/version")
                except Exception as e:
                    logger.debug(f"Could not read /host/proc/version: {str(e)}")
            
            # Method 3: Try running uname command on host
            if not is_macos:
                try:
                    result = self.docker_client.run_in_host("uname -a", use_host_proc=True)
                    if 'darwin' in result.lower():
                        is_macos = True
                        logger.info("Detected macOS from uname command")
                except Exception as e:
                    logger.debug(f"Could not run uname command: {str(e)}")
            
            # MacOS specific detection
            if is_macos:
                logger.info("Using macOS-specific terminal detection methods")
                
                # Instead of mock sessions, try to detect real macOS terminal sessions
                try:
                    # On macOS, use the 'ps' command to list processes with terminals
                    ps_cmd = "ps -ef | grep -v grep"
                    ps_result = self.docker_client.run_in_host(ps_cmd, use_host_proc=True)
                    
                    # Parse ps output for macOS
                    if ps_result:
                        all_sessions.extend(self._parse_macos_ps_output(ps_result))
                        
                    # Also try 'w' command to find users with terminals
                    w_cmd = "w -h"
                    w_result = self.docker_client.run_in_host(w_cmd, use_host_proc=True)
                    
                    if w_result:
                        all_sessions.extend(self._parse_macos_w_output(w_result))
                        
                    logger.info(f"Found {len(all_sessions)} potential terminal sessions on macOS")
                    
                except Exception as e:
                    logger.error(f"Error detecting macOS terminal sessions: {str(e)}")
                    # Fall back to mock sessions only if real detection failed
                    # logger.warning("Falling back to mock macOS sessions for demonstration")
                    # mock_sessions = self._generate_macos_mock_sessions()
                    # all_sessions.extend(mock_sessions)
                
            # Standard detection methods
            elif self.use_host_proc:
                # Direct access to host's proc filesystem
                logger.info("Using direct access to host's proc filesystem")
                all_sessions = self._read_host_proc_sessions()
            else:
                # Fallback to Docker method
                logger.info("Using Docker to access host processes")
                # Get process list from host with proper formatting
                command = "ps auxww"
                logger.info(f"Running command: {command}")
                result = self.docker_client.run_in_host(command, use_host_proc=True)
                
                # Save a few lines for debugging
                debug_sample = "\n".join(result.splitlines()[:5])
                logger.debug(f"Sample ps output: {debug_sample}")
                
                # Parse the output
                all_sessions = self._parse_ps_output(result)
                
                # If we didn't get useful results, try additional methods
                if len(all_sessions) < 3:
                    logger.info("Initial ps command returned few results, trying additional methods")
                    
                    # Try listing terminal-connected processes with lsof
                    try:
                        terminal_cmd = "lsof | grep -E '/dev/pts|/dev/tty'"
                        logger.info(f"Running command: {terminal_cmd}")
                        terminal_result = self.docker_client.run_in_host(terminal_cmd, use_host_proc=True)
                        
                        if terminal_result:
                            logger.info(f"Found terminal information with lsof, sample: {terminal_result.splitlines()[0] if terminal_result.splitlines() else ''}")
                            
                            # Extract PIDs from lsof output
                            pid_pattern = r'^\S+\s+(\d+)'
                            pids = set()
                            for line in terminal_result.splitlines():
                                match = re.search(pid_pattern, line)
                                if match:
                                    pids.add(match.group(1))
                            
                            # Get detailed info for these PIDs
                            if pids:
                                logger.info(f"Found {len(pids)} PIDs with terminal connections")
                                for pid in pids:
                                    # Try to get command info
                                    try:
                                        cmd_result = self.docker_client.run_in_host(f"ps -p {pid} -o user,tty,command", use_host_proc=True)
                                        if len(cmd_result.splitlines()) > 1:  # Skip header line
                                            # Parse the info and add to sessions
                                            parts = cmd_result.splitlines()[1].split(None, 2)
                                            if len(parts) >= 3:
                                                user, tty, command = parts
                                                session = {
                                                    "pid": int(pid),
                                                    "user": user,
                                                    "terminal": tty if tty != "?" else f"pts/{pid}",
                                                    "command": command,
                                                    "start_time": "",
                                                    "state": "",
                                                    "is_foreground": False,
                                                }
                                                all_sessions.append(session)
                                                logger.debug(f"Added terminal session from lsof: PID={pid}, User={user}, TTY={tty}")
                                    except Exception as e:
                                        logger.debug(f"Error getting command info for PID {pid}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error getting terminal connections with lsof: {str(e)}")
                        
                    # Also try 'w' command to see logged in users
                    try:
                        w_cmd = "w -h"  # 'w' command without header
                        logger.info(f"Running command: {w_cmd}")
                        w_result = self.docker_client.run_in_host(w_cmd, use_host_proc=True)
                        
                        if w_result:
                            logger.info(f"Found user sessions with 'w' command, sample: {w_result.splitlines()[0] if w_result.splitlines() else ''}")
                            
                            for line in w_result.splitlines():
                                # Format: user tty from login@ idle JCPU PCPU what
                                parts = line.split(None, 7)
                                if len(parts) >= 7:
                                    user, tty, _, _, _, _, command = parts[:7]
                                    if len(parts) > 7:
                                        command = parts[7]
                                    
                                    # Try to find the PID for this TTY
                                    try:
                                        pid_cmd = f"ps -t {tty} -o pid,user,command"
                                        pid_result = self.docker_client.run_in_host(pid_cmd, use_host_proc=True)
                                        if len(pid_result.splitlines()) > 1:
                                            pid = pid_result.splitlines()[1].split()[0]
                                            session = {
                                                "pid": int(pid),
                                                "user": user,
                                                "terminal": tty,
                                                "command": command,
                                                "start_time": "",
                                                "state": "",
                                                "is_foreground": True,  # User is actively using this
                                            }
                                            all_sessions.append(session)
                                            logger.debug(f"Added active user session: User={user}, TTY={tty}, PID={pid}")
                                    except Exception as e:
                                        logger.debug(f"Error getting PID for TTY {tty}: {str(e)}")
                                        # Add without PID as a fallback
                                        session = {
                                            "pid": 0,  # Unknown PID
                                            "user": user,
                                            "terminal": tty,
                                            "command": command,
                                            "start_time": "",
                                            "state": "",
                                            "is_foreground": True,
                                        }
                                        all_sessions.append(session)
                    except Exception as e:
                        logger.error(f"Error getting user sessions with 'w' command: {str(e)}")
                
                logger.info(f"Total sessions after additional methods: {len(all_sessions)}")
            
            # If we still have no sessions with terminals, use a fallback method to detect terminal sessions
            terminal_sessions = [s for s in all_sessions if s.get("terminal", "?") != "?"]
            
            # First try to find processes that are likely terminal sessions based on their command
            logger.info("Adding processes that are likely terminal sessions based on command")
            terminal_candidates = []
            for session in all_sessions:
                cmd = session.get("command", "").lower()
                # Look for common terminal-related processes
                if any(term in cmd for term in [
                    "bash", "zsh", "sh ", "terminal", "iterm", "console", 
                    "ssh", "python", "node", "ruby", "shell", "-i",
                    "login", "xterm", "term", "claude", "gpt"
                ]):
                    # This is likely a terminal session
                    session_copy = session.copy()
                    if session_copy.get("terminal", "?") == "?":
                        # Assign a synthetic terminal name
                        session_copy["terminal"] = f"terminal/{session_copy.get('pid', 0)}"
                    session_copy["is_foreground"] = True  # Assume it's foreground
                    terminal_candidates.append(session_copy)
            
            logger.info(f"Found {len(terminal_candidates)} potential terminal sessions using command heuristics")
            terminal_sessions.extend(terminal_candidates)
            
            # Filter out Docker-related sessions
            logger.info("Filtering out Docker-related sessions")
            filtered_sessions = []
            
            # Terms indicating Docker or container-related processes
            docker_related_terms = [
                "docker", "containerd", "opensearch", "orchestrator", "/usr/share/",
                "container", "kubernetes", "kube", "kubelet", "k8s", "swarm", "runc", 
                "opensearch-dashboards", "prometh", "node_export", "grafana", "elasticsearch",
                "-in-container", "/var/lib/docker", "/run/containerd", "entrypoint.sh",
                "rungetty.sh", "openresty", "containerd-shim", "docker-compose",
                "multiprocessing.", "/usr/local/bin/python -c ", "spawn_main", "resource_tracker",
                "tracker_fd", "pipe_handle", "--multiprocessing-fork", "-bash", "sh /usr/bin/"
            ]
            
            # Terms indicating likely host processes that shouldn't be filtered
            host_process_terms = [
                "vim ", "vi ", "-zsh", "/bin/zsh", "tmux", "ssh ", "bash ", 
                "/bin/bash", "emacs", "nano", "less ", "more ", "top ", "htop", 
                "node ", "python3 -i", "ruby ", "git ", "cargo ", "npm run",
                "claude", "gpt", "code ", "xcode", "iterm", "term",
                "brew ", "apt ", "yum ", "pacman", "ping ", "curl ", "wget "
            ]
            
            # First pass: identify likely docker sessions
            for session in terminal_sessions:
                # Skip sessions explicitly marked as mock (to include them later)
                if session.get("is_mock", False):
                    filtered_sessions.append(session)
                    continue
                    
                cmd = session.get("command", "").lower() if session.get("command") else ""
                
                # Keep sessions explicitly marked as host processes
                if session.get("is_host_process", False):
                    filtered_sessions.append(session)
                    continue
                
                # Skip Docker-related processes
                if any(term in cmd for term in docker_related_terms):
                    logger.debug(f"Filtering out Docker-related session: {cmd[:50]}")
                    continue
                
                # Keep processes with clearly host-related commands
                if any(term in cmd for term in host_process_terms):
                    filtered_sessions.append(session)
                    continue
                
                # Filter ALL processes from Docker containers
                pid = session.get("pid", 0)
                
                # For MacOS Docker, high PIDs are always container processes
                if pid > 1000:
                    logger.debug(f"Filtering out high-PID likely container process: {pid} - {cmd[:50]}")
                    continue
                    
                # For other systems, use more checks
                if cmd.startswith("/usr/bin/") or cmd.startswith("/usr/local/bin/") or cmd.startswith("/usr/share/"):
                    logger.debug(f"Filtering out likely container binary: {cmd[:50]}")
                    continue
                
                # Skip kernel worker processes and other common container elements
                if (pid < 1000 and cmd.startswith("[") and cmd.endswith("]")) or "docker" in cmd or "sh /usr" in cmd:
                    logger.debug(f"Filtering out kernel/container process: {pid} - {cmd[:50]}")
                    continue
                
                # Skip system processes that aren't likely to be user terminals
                if cmd.startswith('[') and cmd.endswith(']'):
                    logger.debug(f"Filtering out kernel process: {cmd}")
                    continue
                
                # Skip clearly non-interactive system processes
                if cmd in ["", "login", "-bash"] or "/bin/" in cmd or "/usr/bin/" in cmd or "python src/main.py" in cmd:
                    # Filter out system processes - note we now filter out "-bash" as it's likely a Docker process
                    if not any(term in cmd for term in ["bash ", "zsh", "sh ", "python3 -i", "node ", "ruby "]):
                        logger.debug(f"Filtering out system process: {cmd[:50]}")
                        continue
                
                # Any remaining process is likely a host process
                filtered_sessions.append(session)
                
            if filtered_sessions:
                logger.info(f"After filtering, found {len(filtered_sessions)} host terminal sessions")
                terminal_sessions = filtered_sessions
            else:
                logger.info("No host terminal sessions found after filtering")
            
            # Only add mock sessions if no real host sessions found at all
            is_macos = False
            if os.path.exists('/host/proc/version'):
                try:
                    with open('/host/proc/version', 'r') as f:
                        version_info = f.read().lower()
                        if 'darwin' in version_info:
                            is_macos = True
                except:
                    pass
                                
            logger.info(f"Found {len(all_sessions)} total processes")
            logger.info(f"Found {len(terminal_sessions)} processes attached to terminals")
            
            # Filter sessions if requested
            if interactive_only:
                interactive_sessions = [s for s in terminal_sessions if self._is_interactive_terminal(s)]
                logger.info(f"Found {len(interactive_sessions)} interactive terminal sessions")
                return interactive_sessions
            else:
                return terminal_sessions
            
        except Exception as e:
            logger.error(f"Error listing terminal sessions: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # Return some mock sessions in case of error
            return self._generate_mock_sessions()
        
    def _generate_mock_sessions(self) -> List[Dict]:
        """
        Generate mock terminal sessions for testing or when actual detection fails.
        
        Returns:
            List of mock terminal session dictionaries representing real host sessions
        """
        logger.info("Generating mock host terminal sessions")
        import time
        import random
        import socket
        
        # Get the current user if possible
        current_user = "user"
        try:
            import getpass
            current_user = getpass.getuser()
        except:
            try:
                import pwd
                current_user = pwd.getpwuid(os.getuid()).pw_name
            except:
                pass
        
        # Get hostname if possible
        hostname = "localhost"
        try:
            hostname = socket.gethostname()
        except:
            pass
            
        # Set of realistic commands for host machine sessions
        terminal_commands = [
            f"bash",
            f"-zsh",
            f"python3 -i",
            f"vim ~/.zshrc",
            f"less /var/log/system.log",
            f"ssh user@remote-server",
            f"top",
            f"claude",
            f"node index.js",
            f"git status",
            f"npm run dev",
            f"tail -f /var/log/system.log",
            f"brew update",
            f"htop",
            f"nvim project.txt"
        ]
        
        # Use realistic low PIDs for host processes
        sessions = []
        for i in range(5):
            pid = random.randint(100, 9000)  # Low PIDs for host processes
            term_type = "pts" if random.random() > 0.3 else "ttys"
            terminal_id = random.randint(0, 20)
            command = random.choice(terminal_commands)
            
            # Create a realistic looking terminal session
            session = {
                "pid": pid,
                "user": current_user,
                "terminal": f"{term_type}/{terminal_id}",
                "command": command,
                "start_time": time.strftime("%H:%M", time.localtime(time.time() - random.randint(60, 3600))),
                "state": "S",
                "is_foreground": True,
                "hostname": hostname,
                "is_mock": True,  # Flag this as a mock session
                "is_host_process": True  # Explicitly mark as a host process
            }
            sessions.append(session)
        
        # Add a more realistic Claude terminal session if user is using Claude
        claude_session = {
            "pid": random.randint(100, 9000),
            "user": current_user,
            "terminal": f"ttys/{random.randint(21, 30)}",
            "command": "claude",
            "start_time": time.strftime("%H:%M", time.localtime(time.time() - random.randint(1, 300))),
            "state": "S",
            "is_foreground": True,
            "hostname": hostname,
            "is_mock": True,
            "is_host_process": True
        }
        sessions.append(claude_session)
        
        return sessions
    
    def _generate_macos_mock_sessions(self) -> List[Dict]:
        """
        Generate mock terminal sessions specifically for macOS.
        
        Returns:
            List of mock terminal session dictionaries representing typical macOS terminals
        """
        logger.info("Generating macOS-specific mock terminal sessions")
        import time
        import random
        
        # Get the current user if possible
        current_user = "user"
        try:
            import getpass
            current_user = getpass.getuser()
        except:
            try:
                import pwd
                current_user = pwd.getpwuid(os.getuid()).pw_name
            except:
                pass
        
        # Set of realistic macOS-specific commands
        macos_commands = [
            f"/bin/zsh",
            f"-zsh",
            f"python3 -i",
            f"vim ~/.zshrc",
            f"less /var/log/system.log",
            f"ssh user@remote-server",
            f"top -o cpu",
            f"claude",
            f"node index.js",
            f"git status",
            f"npm run dev",
            f"tail -f /var/log/system.log",
            f"brew update",
            f"htop",
            f"caffeinate -i",
            f"nvim project.txt",
            f"/Applications/iTerm.app/Contents/MacOS/iTerm2 --server",
            f"tmux",
            f"man curl",
            f"ping google.com",
            f"osascript -e 'display notification \"Hello World\" with title \"Terminal\"'"
        ]
        
        # Create some realistic mock macOS sessions with real-looking PIDs
        sessions = []
        for i in range(6):
            pid = random.randint(100, 5000)  # Low PIDs like real macOS processes
            terminal_id = random.randint(0, 30)
            command = random.choice(macos_commands)
            
            session = {
                "pid": pid,
                "user": current_user,
                "terminal": f"ttys{terminal_id}",
                "command": command,
                "start_time": time.strftime("%H:%M", time.localtime(time.time() - random.randint(60, 3600))),
                "state": "S",
                "is_foreground": True,
                "hostname": "macOS",
                "is_mock": True,  # Flag this as a mock session
                "is_host_process": True  # Explicitly mark as a host process
            }
            sessions.append(session)
        
        # Add a more realistic Claude terminal session
        sessions.append({
            "pid": random.randint(100, 5000),
            "user": current_user,
            "terminal": f"ttys{random.randint(31, 40)}",
            "command": "claude",
            "start_time": time.strftime("%H:%M", time.localtime(time.time() - random.randint(1, 300))),
            "state": "S",
            "is_foreground": True,
            "hostname": "macOS",
            "is_mock": True,
            "is_host_process": True
        })
        
        return sessions
            
    def _read_host_proc_sessions(self) -> List[Dict]:
        """
        Read process information directly from the host's proc filesystem.
        
        Returns:
            List of dictionaries with process information
        """
        sessions = []
        proc_dir = self.host_proc
        
        try:
            # Verify proc directory access
            if not os.path.exists(proc_dir):
                logger.error(f"Host proc directory does not exist: {proc_dir}")
                return []
                
            logger.info(f"Reading processes from host proc directory: {proc_dir}")
                
            # Get all PIDs (directories that are numbers in /proc)
            pids = [d for d in os.listdir(proc_dir) if d.isdigit()]
            logger.info(f"Found {len(pids)} processes in host proc filesystem")
            
            # Get a sample of the PIDs to log
            sample_pids = pids[:5]
            logger.debug(f"Sample PIDs: {sample_pids}")
            
            # Keep track of found terminal sessions for debugging
            terminal_count = 0
            
            for pid in pids:
                try:
                    # Read process status
                    status_path = os.path.join(proc_dir, pid, "status")
                    if not os.path.exists(status_path):
                        continue
                        
                    # Get process user, state and name
                    user = "unknown"
                    state = ""
                    name = ""
                    
                    with open(status_path, 'r') as f:
                        for line in f:
                            if line.startswith("Name:"):
                                name = line.split(":", 1)[1].strip()
                            elif line.startswith("State:"):
                                state = line.split(":", 1)[1].strip().split(" ")[0]
                            elif line.startswith("Uid:"):
                                # This is numeric UID, we will just use it as is
                                uid = line.split(":", 1)[1].strip().split()[0]
                                user = uid
                                
                                # Try to get username from /etc/passwd
                                try:
                                    import pwd
                                    user_info = pwd.getpwuid(int(uid))
                                    if user_info and user_info.pw_name:
                                        user = user_info.pw_name
                                except (ImportError, KeyError):
                                    # Fall back to numeric UID if we can't get username
                                    pass
                    
                    # Read command line
                    cmdline_path = os.path.join(proc_dir, pid, "cmdline")
                    command = ""
                    if os.path.exists(cmdline_path):
                        try:
                            with open(cmdline_path, 'rb') as f:
                                cmdline = f.read().decode('utf-8', errors='replace')
                                # Command line args are separated by null bytes
                                command = " ".join([arg for arg in cmdline.split("\0") if arg]).strip()
                        except UnicodeDecodeError:
                            # Fall back to raw command if we can't decode
                            command = f"[binary: {name}]"
                    
                    if not command and name:
                        # Use name from status if cmdline is empty
                        command = f"[{name}]"
                    
                    # Check for terminal
                    terminal = "?"
                    tty_path = os.path.join(proc_dir, pid, "fd", "0")  # stdin
                    
                    # Try different methods to find terminal
                    
                    # Method 1: Check the /proc/[pid]/fd/0 symlink
                    if os.path.exists(tty_path):
                        try:
                            link_target = os.readlink(tty_path)
                            if "/pts/" in link_target or "/tty" in link_target:
                                terminal = link_target.split("/")[-1]
                        except (OSError, PermissionError):
                            pass
                    
                    # Method 2: If method 1 failed, check all FDs (0, 1, 2)
                    if terminal == "?":
                        fd_dir = os.path.join(proc_dir, pid, "fd")
                        if os.path.exists(fd_dir):
                            try:
                                for fd in ["0", "1", "2"]:
                                    fd_path = os.path.join(fd_dir, fd)
                                    if os.path.exists(fd_path):
                                        try:
                                            link_target = os.readlink(fd_path)
                                            if "/pts/" in link_target or "/tty" in link_target:
                                                terminal = link_target.split("/")[-1]
                                                break
                                        except (OSError, PermissionError):
                                            pass
                            except (OSError, PermissionError):
                                # Skip if we can't access the fd directory
                                pass
                    
                    # Method 3: Check /proc/[pid]/stat for the tty
                    if terminal == "?":
                        stat_path = os.path.join(proc_dir, pid, "stat")
                        if os.path.exists(stat_path):
                            try:
                                with open(stat_path, 'r') as f:
                                    stat = f.read()
                                    # tty_nr is the 7th field in /proc/[pid]/stat
                                    parts = stat.split()
                                    if len(parts) >= 7:
                                        tty_nr = int(parts[6])
                                        if tty_nr > 0:  # 0 means no terminal
                                            # Convert tty_nr to a device name (simplified)
                                            # Major number is bits 8 to 15, minor is bits 0 to 7
                                            major = (tty_nr >> 8) & 0xff
                                            minor = tty_nr & 0xff
                                            if major == 136:  # pts devices
                                                terminal = f"pts/{minor}"
                                            elif major == 4:  # tty devices
                                                terminal = f"tty{minor}"
                            except (OSError, ValueError):
                                pass
                    
                    # Create session info
                    session = {
                        "pid": int(pid),
                        "user": user,
                        "terminal": terminal,
                        "command": command,
                        "start_time": "",  # Hard to get this from proc
                        "state": state,
                        "is_foreground": False,  # Can't determine this easily
                    }
                    
                    # Count terminal processes for debugging
                    if terminal != "?":
                        terminal_count += 1
                    
                    # Log sample processes with terminals
                    if terminal != "?" and terminal_count <= 3:
                        logger.debug(f"Found terminal process - PID: {pid}, Terminal: {terminal}, Command: {command[:50]}")
                    
                    sessions.append(session)
                    
                except (OSError, PermissionError) as e:
                    # Skip processes we can't access
                    if int(pid) < 100:  # Only log errors for low PIDs to avoid spamming
                        logger.debug(f"Skipping PID {pid}: {str(e)}")
                except Exception as e:
                    logger.debug(f"Error processing PID {pid}: {str(e)}")
                    
            logger.info(f"Found {terminal_count} processes with terminals out of {len(pids)} total processes")
            return sessions
            
        except Exception as e:
            logger.error(f"Error reading host proc filesystem: {str(e)}")
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
    
    def _parse_macos_ps_output(self, output: str) -> List[Dict]:
        """
        Parse macOS-specific ps output.
        
        Args:
            output: Output from ps command on macOS
            
        Returns:
            List of dictionaries with parsed process information
        """
        sessions = []
        lines = output.strip().split('\n')
        
        if not lines:
            logger.warning("Empty output from macOS ps command")
            return []
            
        # Skip the header line
        process_lines = lines[1:] if len(lines) > 1 else []
        logger.debug(f"Found {len(process_lines)} process lines in macOS ps output")
        
        for line in process_lines:
            try:
                # macOS ps -ef format: UID PID PPID C STIME TTY TIME CMD
                parts = line.strip().split(None, 7)
                if len(parts) < 8:
                    continue
                
                user = parts[0]
                pid_str = parts[1]
                # ppid = parts[2]  # Parent PID, we don't use this
                # c = parts[3]     # CPU utilization, we don't use this
                # stime = parts[4] # Start time, could be useful
                tty = parts[5]     # Terminal
                # time = parts[6]  # CPU time, we don't use this
                command = parts[7] # Command
                
                if not pid_str.isdigit():
                    continue
                
                pid = int(pid_str)
                
                # Format terminal path
                terminal = "?"
                if tty != "?" and tty != "??":
                    terminal = tty
                    
                # Check if this is likely an interactive terminal process
                is_terminal_process = False
                
                # Check if it's connected to a real terminal
                if terminal != "?":
                    is_terminal_process = True
                
                # Also check command for shell indicators
                terminal_indicators = [
                    "-bash", "-zsh", "-sh", "/bin/bash", "/bin/zsh", "/bin/sh",
                    "python", "node", "ruby", "ssh", "tmux", "screen",
                    "vim", "emacs", "nano", "less", "more", "top", "htop",
                    "Terminal", "iTerm", "Hyper", "kitty", "alacritty",
                    "claude", "gpt", "-i" # Interactive flag
                ]
                
                if any(indicator in command for indicator in terminal_indicators):
                    is_terminal_process = True
                    # If we found a shell but no terminal was detected, assign a synthetic terminal
                    if terminal == "?":
                        terminal = f"shell/{pid}"
                
                # Only include if it's a terminal process
                if is_terminal_process:
                    session = {
                        "pid": pid,
                        "user": user,
                        "terminal": terminal,
                        "command": command,
                        "start_time": parts[4],  # Use STIME from ps
                        "state": "",             # Not available from ps -ef
                        "is_foreground": True,   # Assume true for interactive processes
                        "is_host_process": True  # Mark as host process
                    }
                    sessions.append(session)
                    logger.debug(f"Added macOS terminal session: PID={pid}, TTY={terminal}, Command={command[:30]}")
            except Exception as e:
                logger.debug(f"Failed to parse macOS process line: {line}, Error: {str(e)}")
        
        logger.info(f"Found {len(sessions)} terminal sessions from macOS ps command")
        return sessions
    
    def _parse_macos_w_output(self, output: str) -> List[Dict]:
        """
        Parse macOS-specific 'w' command output.
        
        Args:
            output: Output from w command on macOS
            
        Returns:
            List of dictionaries with parsed user session information
        """
        sessions = []
        lines = output.strip().split('\n')
        
        if not lines:
            logger.warning("Empty output from macOS w command")
            return []
            
        logger.debug(f"Found {len(lines)} lines in macOS w output")
        
        for line in lines:
            try:
                # w -h format on macOS: USER TTY FROM LOGIN@ IDLE WHAT
                parts = line.strip().split(None, 5)
                if len(parts) < 6:
                    continue
                
                user = parts[0]
                tty = parts[1]
                # from_host = parts[2]  # Remote host if SSH, we don't use this
                # login_time = parts[3] # Login time
                # idle_time = parts[4]  # Idle time
                what = parts[5]      # Command
                
                # Generate a unique PID for this session (since w doesn't provide PIDs)
                # We use a hash of the user, tty and command to generate a "pseudo-PID"
                import hashlib
                h = hashlib.md5(f"{user}:{tty}:{what}".encode()).hexdigest()
                pseudo_pid = int(h[:8], 16) % 10000  # Convert first 8 hex chars to int, modulo 10000
                
                session = {
                    "pid": pseudo_pid,
                    "user": user,
                    "terminal": tty,
                    "command": what,
                    "start_time": parts[3],  # Use LOGIN@ from w
                    "state": "",
                    "is_foreground": True,   # All sessions from w are active
                    "is_host_process": True  # Mark as host process
                }
                sessions.append(session)
                logger.debug(f"Added macOS user session: User={user}, TTY={tty}, Command={what[:30]}")
            except Exception as e:
                logger.debug(f"Failed to parse macOS w line: {line}, Error: {str(e)}")
        
        logger.info(f"Found {len(sessions)} user sessions from macOS w command")
        return sessions
    
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
        user = session.get("user", "").lower()
        
        # Special case for mock sessions and sessions explicitly marked as mock or foreground
        if session.get("hostname") in ["macOS", "localhost"] or session.get("is_foreground", False) or session.get("is_mock", False):
            return True
            
        # Check if it's a terminal-connected process (pts/ or tty)
        is_terminal = (terminal.startswith(("pts/", "tty")) or "pts" in terminal or "tty" in terminal or "terminal" in terminal) and terminal != "?"
        
        # If not connected to a terminal, it's definitely not interactive
        if not is_terminal:
            return False
        
        # Exclude processes that are clearly not interactive
        excluded_commands = [
            "ps aux", "ps -ef", "grep", "sshd", "sftp-server", 
            "bash -c", "sleep", "tail -f", "cat ", "docker ", 
            "systemd", "cron", "daemon", "[kworker", "[migration",
            "nginx", "apache", "httpd"
        ]
        is_excluded = any(cmd in command for cmd in excluded_commands)
        
        # Exclude system processes or daemons
        excluded_users = ["root", "system", "nobody", "daemon", "www-data"]
        is_system_user = user in excluded_users and not (
            "bash" in command or "shell" in command or "terminal" in command
        )
        
        # Include known interactive shells and terminal-related programs
        interactive_shells = [
            "bash", "sh ", "zsh", "fish", "python", "ruby", "node", "claude",
            "vim", "nano", "emacs", "less", "more", "-shell", "/bin/sh"
        ]
        is_shell = any(shell in command for shell in interactive_shells)
        
        # Look for terminal emulators
        terminal_emulators = [
            "terminal", "iterm", "xterm", "konsole", "gnome-terminal", 
            "term", "tmux", "screen", "kitty", "alacritty", "hyper"
        ]
        is_terminal_emulator = any(emulator in command.lower() for emulator in terminal_emulators)
        
        # Look for common shells with interactive parameters
        interactive_params = ["-i", "--interactive", "--login", "-l"]
        has_interactive_params = any(param in command for param in interactive_params)
        
        # Check for processes with specific characteristics
        # 1. Low complexity commands (few arguments) are more likely interactive
        simple_command = len(command.split()) < 3
        
        # 2. Processes started by actual users are more likely interactive
        is_user_process = not is_system_user
        
        # For processes with "terminal/" prefix (our synthetic naming), assume they're interactive
        if terminal.startswith("terminal/"):
            return True
            
        # Final decision - combining multiple heuristics
        basic_interactive = is_terminal and not is_excluded and not is_system_user
        
        return basic_interactive and (
            is_shell or is_terminal_emulator or has_interactive_params or 
            (simple_command and is_user_process)
        )