# Terminal Monitoring Implementation Todo List

## Background

PromptWatcher needs to monitor terminal sessions on the host machine (not inside Docker) to capture Claude prompts and responses. This requires a bridge between the host machine and our Docker container to access terminal sessions where users are interacting with Claude.

## Host-Container Communication Implementation via Docker Socket

- [ ] **Setup Docker socket mount**
  - [ ] Update `docker-compose.yml` to add Docker socket mount:
    ```yaml
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    ```
  - [ ] Add appropriate permissions to the container user if needed
  - [ ] Verify container can access the Docker socket

- [ ] **Implement Docker API access**
  - [ ] Add Docker SDK dependency to `requirements.txt` (`docker` package for Python)
  - [ ] Create a `DockerClient` service class in `app/infra/terminal/docker_client.py`
  - [ ] Implement connection handling with proper error management
  - [ ] Add connection status checks and reconnection logic

- [ ] **Create helper container implementation**
  - [ ] Design helper container specification (Alpine-based for small footprint)
  - [ ] Implement method to run commands in host namespace:
    ```python
    def run_in_host(self, command: str) -> str:
        """Run command in the host's namespace using a helper container."""
        return self.client.containers.run(
            'alpine:latest',
            command,
            remove=True,        # Remove container after execution
            privileged=True,     # Required for accessing host processes
            pid='host',          # Use host's PID namespace
            network='host'       # Use host's network namespace
        )
    ```
  - [ ] Add security checks and command sanitization
  - [ ] Implement resource cleanup to prevent container leaks

- [ ] **Create terminal session controller**
  - [ ] Implement session discovery method using helper containers
  - [ ] Add caching mechanism to reduce container creation overhead
  - [ ] Implement session metadata tracking (start time, command, PID)

## Terminal Session Discovery

- [ ] **Implement terminal session detection**
  - [ ] Create method to list all terminal sessions using helper container:
    ```python
    def list_terminal_sessions(self) -> List[Dict]:
        """List all terminal sessions on the host machine."""
        # Run through helper container to access host processes
        result = self.run_in_host('ps aux | grep -E "Terminal|bash|zsh"')
        return self._parse_terminal_processes(result)
    ```
  - [ ] Implement process parsing logic to extract session details
  - [ ] Add detection for different terminal types (bash, zsh, etc.)
  - [ ] Filter out non-interactive terminal sessions

- [ ] **Identify terminal PTYs and file descriptors**
  - [ ] Implement command to map processes to terminal devices:
    ```python
    def get_terminal_fds(self, pid: int) -> List[str]:
        """Get file descriptors for a terminal process."""
        # Find FDs using lsof in the host namespace
        result = self.run_in_host(f'lsof -p {pid} | grep -E "tty|pts"')
        return self._parse_terminal_fds(result)
    ```
  - [ ] Create mapping between processes and their terminal devices
  - [ ] Implement platform-specific detection (macOS vs Linux)

- [ ] **Create terminal session monitoring service**
  - [ ] Implement `TerminalSessionMonitor` class in `terminal/monitor.py`
  - [ ] Add periodic polling for terminal sessions with configurable interval
  - [ ] Implement session tracking with change detection
  - [ ] Create events for new/ended terminal sessions

## Terminal Output Capture

- [ ] **Implement terminal output capture with Docker**
  - [ ] Create method to read terminal output through helper container:
    ```python
    def capture_terminal_output(self, device_path: str, timeout: int = 10) -> str:
        """Capture output from a terminal device using cat in privileged mode."""
        command = f'timeout {timeout} cat {device_path}'
        return self.run_in_host(command)
    ```
  - [ ] Implement alternate approach using `script` command for terminal recording:
    ```python
    def start_terminal_recording(self, pid: int, output_file: str) -> str:
        """Start recording a terminal session to a file."""
        # Find terminal device first
        device = self.get_terminal_device(pid)
        command = f'script -f -q -t 2>{output_file}.timing {output_file} {device}'
        return self.run_detached_in_host(command)
    ```
  - [ ] Create capture strategy selection based on terminal type

- [ ] **Implement streaming capture service**
  - [ ] Create `TerminalCaptureService` class in `terminal/capture.py`
  - [ ] Implement non-blocking capture with timeout controls
  - [ ] Add capture frequency controls and adaptive timing
  - [ ] Create content buffer with configurable size

- [ ] **Implement output processing pipeline**
  - [ ] Create streaming buffer implementation in `terminal/buffer.py`
  - [ ] Implement content chunking with overlap detection
  - [ ] Add content filtering to remove control characters and formatting
  - [ ] Implement line reconstruction for wrapped terminal output

## Claude Detection and Parsing

- [ ] **Implement Claude pattern detection**
  - [ ] Create `ClaudePatternDetector` class in `terminal/claude_detector.py`:
    ```python
    def is_claude_session(self, terminal_content: str) -> bool:
        """Determine if terminal content contains Claude interaction patterns."""
        # Look for Claude signature patterns
        patterns = [
            r"Claude\s+\d+\.\d+",  # Claude version number
            r"(Human|Assistant):\s+",  # Human/Assistant dialog format
            r"\[Claude thinking\]",  # Claude thinking pattern
            # Add more patterns as needed
        ]
        return any(re.search(pattern, terminal_content) for pattern in patterns)
    ```
  - [ ] Implement improved detection with context awareness
  - [ ] Add confidence scoring for Claude detection
  - [ ] Create version-specific detection patterns

- [ ] **Create Claude conversation parser**
  - [ ] Implement `ClaudeConversationParser` in `terminal/claude_parser.py`:
    ```python
    def extract_conversations(self, content: str) -> List[Dict[str, str]]:
        """Extract Claude conversations from terminal content."""
        conversations = []
        # Use regex to find Human/Assistant patterns with content
        conversation_pattern = r"Human:\s+(.*?)(?=Assistant:|$)"
        response_pattern = r"Assistant:\s+(.*?)(?=Human:|$)"
        
        # Extract prompts and match with responses
        prompts = re.findall(conversation_pattern, content, re.DOTALL)
        responses = re.findall(response_pattern, content, re.DOTALL)
        
        # Pair them up (handling possible mismatches)
        for i, prompt in enumerate(prompts):
            response = responses[i] if i < len(responses) else ""
            conversations.append({
                "prompt": prompt.strip(),
                "response": response.strip(),
                "timestamp": datetime.now()
            })
            
        return conversations
    ```
  - [ ] Implement robust multi-line handling
  - [ ] Add support for code blocks and special formatting
  - [ ] Create content cleanup for control characters and artifacts

- [ ] **Connect to OpenSearch storage**
  - [ ] Integrate with existing `PromptRepository` 
  - [ ] Create `PromptRecord` instances from parsed conversations
  - [ ] Add terminal metadata (PID, user, command, etc.)
  - [ ] Implement batched saving for efficiency

## Frontend Integration

- [ ] **Complete the monitor manager interface**
  - [ ] Update `TerminalMonitorManager` in `terminal/monitor.py`:
    ```python
    async def start_monitor(self) -> UUID:
        """Start the terminal monitor process."""
        # Initialize Docker client
        docker_client = DockerClient()
        
        # Create a monitor instance
        monitor_id = uuid4()
        self.monitors[monitor_id] = {
            "docker_client": docker_client,
            "session_monitor": TerminalSessionMonitor(docker_client),
            "capture_service": TerminalCaptureService(docker_client),
            "start_time": datetime.now(),
            "status": "active"
        }
        
        # Start monitoring in background task
        self.tasks[monitor_id] = asyncio.create_task(
            self._monitor_loop(monitor_id)
        )
        
        return monitor_id
    ```
  - [ ] Implement the monitor loop with proper error handling:
    ```python
    async def _monitor_loop(self, monitor_id: UUID):
        """Main monitoring loop for terminal sessions."""
        try:
            monitor = self.monitors[monitor_id]
            while monitor["status"] == "active":
                # Get terminal sessions
                sessions = await monitor["session_monitor"].list_sessions()
                
                # Check for Claude sessions
                for session in sessions:
                    if session.get("is_claude", False):
                        # Capture and process terminal content
                        content = await monitor["capture_service"].capture(
                            session["device"]
                        )
                        # Parse conversations
                        conversations = self.claude_parser.extract_conversations(content)
                        # Store in repository
                        for conv in conversations:
                            await self._store_conversation(conv, session)
                
                # Prevent CPU overload with configurable delay
                await asyncio.sleep(self.settings.MONITORING_INTERVAL)
        except Exception as e:
            logger.error(f"Error in monitor loop: {str(e)}")
            # Update status to error
            if monitor_id in self.monitors:
                self.monitors[monitor_id]["status"] = "error"
                self.monitors[monitor_id]["error"] = str(e)
    ```
  - [ ] Add proper cleanup and resource management

- [ ] **Connect frontend start/stop endpoints**
  - [ ] Complete the `/api/monitors/start` endpoint:
    ```python
    @router.post("/api/monitors/start", response_model=MonitorResponse)
    async def start_monitor(
        request: Request,
        monitor_manager: TerminalMonitorManager = Depends(get_monitor_manager),
    ):
        """Start the prompt monitor."""
        logger.info("Starting terminal monitor")
        
        try:
            monitor_id = await monitor_manager.start_monitor()
            return MonitorResponse(
                message=f"Monitor started successfully with ID: {monitor_id}"
            )
        except Exception as e:
            logger.error(f"Error starting monitor: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))
    ```
  - [ ] Update the stop monitor endpoint with proper cleanup
  - [ ] Add status endpoint for monitor information

- [ ] **Enhance frontend with monitoring status indicators**
  - [ ] Create monitoring status API endpoint:
    ```python
    @router.get("/api/monitors/status", response_model=MonitorStatusResponse)
    async def get_monitor_status(
        request: Request,
        monitor_manager: TerminalMonitorManager = Depends(get_monitor_manager),
    ):
        """Get current monitoring status."""
        return MonitorStatusResponse(
            active=monitor_manager.is_active(),
            monitors=[
                {
                    "id": str(monitor_id),
                    "status": monitor["status"],
                    "start_time": monitor["start_time"].isoformat(),
                    "terminal_count": len(monitor.get("sessions", [])),
                    "prompts_captured": monitor.get("prompts_captured", 0),
                }
                for monitor_id, monitor in monitor_manager.monitors.items()
            ]
        )
    ```
  - [ ] Create status indicator component in the UI
  - [ ] Add real-time status updates using polling or WebSockets
  - [ ] Show detailed monitor statistics and terminal information

## Security and Testing

- [ ] **Add security measures for Docker socket usage**
  - [ ] Implement command whitelist for Docker container execution:
    ```python
    def validate_command(self, command: str) -> bool:
        """Ensure command is in the whitelist of safe commands."""
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
    ```
  - [ ] Add user filtering to only capture the current user's terminals
  - [ ] Implement container resource limits to prevent DoS attacks
  - [ ] Create security policy document with clear permissions model

- [ ] **Add privacy controls**
  - [ ] Create content filter for sensitive information:
    ```python
    def filter_sensitive_content(self, content: str) -> str:
        """Filter potentially sensitive information from content."""
        # Filter patterns for sensitive data
        patterns = [
            (r'\b(?:\d[ -]*?){13,16}\b', '[CREDIT_CARD]'),  # Credit card numbers
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),  # Email
            (r'\b(?:password|api[_-]?key|secret|token)[\s:=]+\S+', '[REDACTED]'),  # Credentials
        ]
        
        result = content
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    ```
  - [ ] Add settings for privacy level (strict/moderate/minimal)
  - [ ] Implement pre-save filters for the repository

- [ ] **Create test suite**
  - [ ] Develop mock terminal session generator:
    ```python
    def create_mock_claude_session(self, num_interactions: int = 3) -> str:
        """Generate a mock Claude terminal session for testing."""
        content = []
        for i in range(num_interactions):
            content.append(f"Human: Test prompt {i+1}\n")
            content.append(f"Assistant: This is a test response {i+1}.\n")
        return "".join(content)
    ```
  - [ ] Create integration tests for Docker socket communication
  - [ ] Implement parser accuracy tests with various terminal formats
  - [ ] Add performance benchmark tests

## Documentation and Configuration

- [ ] **Create detailed configuration system**
  - [ ] Add Docker socket configuration options to `settings.py`:
    ```python
    # Terminal monitoring settings
    TERMINAL_TYPE: str = Field(default="Terminal")
    MONITORING_INTERVAL: float = Field(default=5.0)  # Seconds
    DOCKER_HELPER_IMAGE: str = Field(default="alpine:latest")
    DOCKER_TIMEOUT: int = Field(default=10)  # Seconds for helper container operations
    ALLOWED_USERS: List[str] = Field(default_factory=list)  # Empty means current user only
    ```
  - [ ] Create configuration guide with best practices
  - [ ] Add security warning and permission documentation

- [ ] **Document Docker socket requirements**
  - [ ] Create setup guide for Docker socket permissions
  - [ ] Document required Docker version and configuration
  - [ ] Add troubleshooting section for common Docker issues
  - [ ] Create host security checklist

## Deployment and Integration

- [ ] **Create streamlined installation process**
  - [ ] Update `docker-compose.yml` with socket mount and permissions
  - [ ] Add automated setup script for host configuration
  - [ ] Create environment check to verify Docker socket access
  - [ ] Add graceful degradation for limited permissions

- [ ] **Implement analytics dashboard**
  - [ ] Add summary statistics for monitoring
  - [ ] Create monitoring health metrics
  - [ ] Add terminal session analytics
  - [ ] Implement Claude usage patterns visualization

## Future Enhancements

- [ ] **Implement adaptive monitoring**
  - [ ] Add intelligent polling based on terminal activity
  - [ ] Implement session prioritization for active Claude sessions
  - [ ] Create resource-aware monitoring that throttles based on system load

- [ ] **Add multi-user support**
  - [ ] Implement user isolation for monitored sessions
  - [ ] Create permission model for viewing other users' prompts
  - [ ] Add organization/team separation for enterprise use