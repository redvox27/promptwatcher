# Terminal Monitoring Implementation Todo List

## Background

PromptWatcher needs to monitor terminal sessions on the host machine (not inside Docker) to capture Claude prompts and responses. This requires a bridge between the host machine and our Docker container to access terminal sessions where users are interacting with Claude.

## Host-Container Communication Implementation via Docker Socket

- [x] **Setup Docker socket mount**
  - [x] Update `docker-compose.yml` to add Docker socket mount and environment variables
  - [x] Update Dockerfile to install necessary dependencies (docker.io, procps, grep, lsof)
  - [x] Set Docker environment variables in Dockerfile (DOCKER_HOST, DOCKER_API_VERSION)
  - [x] Verify container can access the Docker socket

- [x] **Implement Docker API access**
  - [x] Add Docker SDK dependency to `requirements.txt` (docker==5.0.3)
  - [x] Create a `DockerClient` service class in `app/infra/terminal/docker_client.py`
  - [x] Implement connection handling with proper error management
  - [x] Add connection status checks and validation logic

- [x] **Create testing for Docker socket access**
  - [x] Develop `docker_bash_test.py` for verified socket access
  - [x] Test socket permissions and API connectivity
  - [x] Verify command execution in host namespace
  - [x] Ensure reliable error handling and logging

- [ ] **Create helper container implementation**
  - [ ] Design system for efficient command execution on host
  - [ ] Implement method to run commands in host namespace with clear return types
  - [ ] Add security checks and command sanitization
  - [ ] Implement resource cleanup to prevent container leaks

## Terminal Session Discovery

- [ ] **Implement terminal session detection**
  - [ ] Create `TerminalSessionMonitor` class to manage session discovery
  - [ ] Implement process listing method to find terminal sessions:
    ```python
    def list_terminal_sessions(self) -> List[Dict]:
        """List all terminal sessions on the host machine."""
        # Use DockerClient to run command in host namespace
        result = self.docker_client.run_in_host('ps aux | grep -E "Terminal|bash|zsh"')
        return self._parse_terminal_processes(result)
    ```
  - [ ] Add parser for process information to extract metadata (user, command, start time)
  - [ ] Create filtering system to identify terminals likely running Claude

- [ ] **Identify terminal PTYs and file descriptors**
  - [ ] Implement command to map processes to terminal devices:
    ```python
    def get_terminal_devices(self, pid: int) -> List[str]:
        """Get terminal devices for a process."""
        # Find terminal devices using lsof in the host namespace
        result = self.docker_client.run_in_host(f'lsof -p {pid} | grep -E "tty|pts"')
        return self._parse_terminal_devices(result)
    ```
  - [ ] Develop method to determine if terminal is accessible for reading
  - [ ] Create detection for terminal type and capabilities

- [ ] **Implement session tracking service**
  - [ ] Create database for tracking active and historical terminal sessions
  - [ ] Implement periodic scanning with configurable interval
  - [ ] Add change detection to identify new and closed sessions
  - [ ] Develop connection management for terminal monitoring

## Terminal Output Capture

- [ ] **Implement terminal output capture methods**
  - [ ] Create unified terminal reader interface:
    ```python
    def capture_terminal_output(self, device_path: str, timeout: int = 10) -> str:
        """Capture output from a terminal device."""
        command = f'timeout {timeout} cat {device_path}'
        return self.docker_client.run_in_host(command)
    ```
  - [ ] Implement alternative capture methods for different terminal types
  - [ ] Add timeouts and error handling for unresponsive terminals
  - [ ] Create permissions validation before attempting capture

- [ ] **Develop buffering and monitoring system**
  - [ ] Create `TerminalCaptureService` for managing terminal reads
  - [ ] Implement circular buffer for efficient content storage
  - [ ] Add incremental capture to avoid duplicating content
  - [ ] Develop capture scheduling based on terminal activity

- [ ] **Implement output processing pipeline**
  - [ ] Create text processor for terminal output
  - [ ] Implement ANSI escape sequence filtering
  - [ ] Add line continuity tracking across multiple captures
  - [ ] Create content normalization for consistent parsing

## Claude Detection and Parsing

- [ ] **Implement Claude content detection**
  - [ ] Create `ClaudeDetector` class with pattern recognition:
    ```python
    def is_claude_content(self, content: str) -> bool:
        """Detect if content contains Claude conversation patterns."""
        # Look for Claude signature patterns
        patterns = [
            r"Claude\s+\d+\.\d+",  # Claude version number
            r"(Human|Assistant):\s+",  # Human/Assistant dialog format
            r"\[Claude thinking\]",  # Claude thinking indicator
        ]
        return any(re.search(pattern, content) for pattern in patterns)
    ```
  - [ ] Add detection for various Claude usage contexts
  - [ ] Implement pattern matching for different Claude versions
  - [ ] Create confidence scoring system for uncertain matches

- [ ] **Develop conversation extraction**
  - [ ] Create `ClaudeParser` for extracting structured conversations:
    ```python
    def extract_conversations(self, content: str) -> List[Dict]:
        """Extract Claude conversations from terminal content."""
        conversations = []
        
        # Find Human/Assistant exchanges
        human_pattern = r"Human:\s+(.*?)(?=Assistant:|$)"
        assistant_pattern = r"Assistant:\s+(.*?)(?=Human:|$)"
        
        prompts = re.findall(human_pattern, content, re.DOTALL)
        responses = re.findall(assistant_pattern, content, re.DOTALL)
        
        # Match prompts with responses
        for i, prompt in enumerate(prompts):
            if i < len(responses):
                conversations.append({
                    "prompt": self._clean_text(prompt),
                    "response": self._clean_text(responses[i]),
                    "timestamp": datetime.now()
                })
            
        return conversations
    ```
  - [ ] Implement robust content cleaning
  - [ ] Add multi-turn conversation support
  - [ ] Create handling for interrupted/incomplete responses

- [ ] **Integrate with prompt storage**
  - [ ] Connect with existing `PromptRepository`
  - [ ] Map extracted conversations to `PromptRecord` model
  - [ ] Add source information (terminal session, process, user)
  - [ ] Implement deduplication logic for repeated captures

## Frontend Integration

- [ ] **Update monitor manager service**
  - [ ] Complete the `TerminalMonitorManager` implementation:
    ```python
    async def start_monitor(self) -> UUID:
        """Start the terminal monitoring process."""
        # Create a new monitoring instance
        monitor_id = uuid4()
        
        # Initialize components with proper dependencies
        docker_client = DockerClient()
        session_monitor = TerminalSessionMonitor(docker_client, self.settings)
        capture_service = TerminalCaptureService(docker_client, self.settings)
        claude_detector = ClaudeDetector()
        
        # Register monitoring components
        self.monitors[monitor_id] = {
            "id": monitor_id,
            "docker_client": docker_client,
            "session_monitor": session_monitor,
            "capture_service": capture_service,
            "claude_detector": claude_detector,
            "start_time": datetime.now(),
            "status": "active",
            "sessions": [],
            "prompts_captured": 0
        }
        
        # Launch monitoring background task
        self.tasks[monitor_id] = asyncio.create_task(
            self._run_monitor_loop(monitor_id)
        )
        
        logger.info(f"Started monitor with ID {monitor_id}")
        return monitor_id
    ```
  - [ ] Implement main monitoring loop with error handling
  - [ ] Add proper resource cleanup and graceful shutdown
  - [ ] Create monitoring stats and diagnostics

- [ ] **Connect monitoring endpoints**
  - [ ] Finalize the `/api/monitors/start` endpoint
  - [ ] Update the `/api/monitors` DELETE endpoint
  - [ ] Create a new `/api/monitors/status` endpoint:
    ```python
    @router.get("/api/monitors/status", response_model=MonitorStatusResponse)
    async def get_monitor_status(
        request: Request,
        monitor_manager: TerminalMonitorManager = Depends(get_monitor_manager),
    ):
        """Get current monitoring status."""
        return MonitorStatusResponse(
            active=monitor_manager.is_active(),
            stats={
                "monitors_count": len(monitor_manager.monitors),
                "active_sessions": sum(len(m.get("sessions", [])) 
                                    for m in monitor_manager.monitors.values()),
                "total_prompts_captured": sum(m.get("prompts_captured", 0) 
                                           for m in monitor_manager.monitors.values()),
                "uptime": str(datetime.now() - next(iter(monitor_manager.monitors.values()))["start_time"]
                         if monitor_manager.monitors else timedelta(0))
            },
            monitors=[
                {
                    "id": str(monitor_id),
                    "status": monitor["status"],
                    "start_time": monitor["start_time"].isoformat(),
                    "sessions_count": len(monitor.get("sessions", [])),
                    "prompts_captured": monitor.get("prompts_captured", 0),
                }
                for monitor_id, monitor in monitor_manager.monitors.items()
            ]
        )
    ```

- [ ] **Update UI for monitor control**
  - [ ] Enhance UI with monitoring status indicators
  - [ ] Add real-time updates using HTMX polling
  - [ ] Create visualization for active terminals
  - [ ] Display capture statistics and metrics

## Security and Privacy

- [x] **Implement command validation**
  - [x] Create command whitelist in `DockerClient`:
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
  - [ ] Add user filtering for terminal sessions
  - [ ] Implement resource limits for Docker operations
  - [ ] Create comprehensive security documentation

- [ ] **Add privacy protections**
  - [ ] Implement sensitive data filtering:
    ```python
    def redact_sensitive_data(self, content: str) -> str:
        """Remove potentially sensitive information from content."""
        patterns = [
            # Credit card numbers
            (r'\b(?:\d[ -]*?){13,16}\b', '[CREDIT_CARD]'),
            # Email addresses
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
            # API keys, tokens, passwords
            (r'\b(?:password|api[_-]?key|secret|token)[\s:=]+\S+', '[REDACTED]'),
            # Authentication headers
            (r'Authorization:\s*\S+', 'Authorization: [REDACTED]'),
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        return content
    ```
  - [ ] Add privacy configuration options to settings
  - [ ] Create content filtering system with customizable rules
  - [ ] Implement pre-save sanitization

## Testing and Validation

- [ ] **Create comprehensive test suite**
  - [ ] Develop mock content generator for testing:
    ```python
    def generate_claude_content(self, interactions: int = 3) -> str:
        """Generate sample Claude content for testing."""
        content = []
        for i in range(interactions):
            content.append(f"Human: Test prompt {i+1}\n")
            content.append(f"Assistant: This is a test response {i+1}.\n")
        return "\n".join(content)
    ```
  - [ ] Implement unit tests for all components
  - [ ] Create integration tests with Docker socket
  - [ ] Add performance and load testing

## Documentation and Configuration

- [x] **Create monitoring configuration**
  - [x] Add Docker socket configuration options to `settings.py`:
    ```python
    # Terminal monitoring settings
    TERMINAL_TYPE: str = Field(default="Terminal")
    MONITORING_INTERVAL: float = Field(default=5.0)  # Seconds
    DOCKER_HELPER_IMAGE: str = Field(default="alpine:latest")
    DOCKER_TIMEOUT: int = Field(default=10)  # Seconds for helper container operations
    ALLOWED_USERS: List[str] = Field(default_factory=list)  # Empty means current user only
    ```
  - [ ] Add detailed configuration documentation
  - [ ] Create best practices guide for monitoring setup

- [x] **Document Docker socket setup**
  - [x] Created `DOCKER_SOCKET_SETUP.md` with setup instructions
  - [x] Added `DOCKER_SOCKET_IMPLEMENTATION.md` with implementation notes
  - [ ] Add troubleshooting guide for common issues
  - [ ] Create security best practices documentation

## Next Steps and Future Enhancements

- [ ] **Improve terminal session detection**
  - [ ] Create smarter filtering for Claude terminal sessions
  - [ ] Add support for different terminal types and shells
  - [ ] Implement automatic detection of Claude CLI usage

- [ ] **Enhance monitoring performance**
  - [ ] Implement adaptive polling based on terminal activity
  - [ ] Add resource usage optimization for Docker operations
  - [ ] Create more efficient buffering and capture strategies

- [ ] **Add visualization and analytics**
  - [ ] Create dashboard for monitoring statistics
  - [ ] Add visualizations for prompt patterns
  - [ ] Implement usage analytics for Claude sessions

## Implementation Priority

1. **Terminal Session Detection**: Implement the ability to list and identify terminal sessions
2. **Basic Monitoring Loop**: Create the core monitoring functionality with Docker
3. **Claude Content Detection**: Develop pattern recognition for Claude conversations
4. **Data Storage Integration**: Connect the monitor with the prompt repository
5. **Frontend Status Updates**: Add status indicators and controls to the UI

## Completion Status

- Host-Container Communication: 100% complete
- Terminal Session Discovery: 0% complete
- Terminal Output Capture: 0% complete
- Claude Detection and Parsing: 0% complete
- Frontend Integration: 0% complete
- Security Implementation: 25% complete
- Documentation: 50% complete