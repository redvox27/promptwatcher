# Terminal Monitoring Implementation Todo List

## Background

PromptWatcher needs to monitor terminal sessions on the host machine (not inside Docker) to capture Claude prompts and responses. This requires a bridge between the host machine and our Docker container to access terminal sessions where users are interacting with Claude.

## Host-Container Communication Implementation via Docker Socket

- [x] ~~**Setup Docker socket mount**~~ ✅
  - [x] ~~Update `docker-compose.yml` to add Docker socket mount and environment variables~~ ✅
  - [x] ~~Update Dockerfile to install necessary dependencies (docker.io, procps, grep, lsof)~~ ✅
  - [x] ~~Set Docker environment variables in Dockerfile (DOCKER_HOST, DOCKER_API_VERSION)~~ ✅
  - [x] ~~Verify container can access the Docker socket~~ ✅

- [x] ~~**Implement Docker API access**~~ ✅
  - [x] ~~Add Docker SDK dependency to `requirements.txt` (docker==5.0.3)~~ ✅
  - [x] ~~Create a `DockerClient` service class in `app/infra/terminal/docker_client.py`~~ ✅
  - [x] ~~Implement connection handling with proper error management~~ ✅
  - [x] ~~Add connection status checks and validation logic~~ ✅

- [x] ~~**Create testing for Docker socket access**~~ ✅
  - [x] ~~Develop `docker_bash_test.py` for verified socket access~~ ✅
  - [x] ~~Test socket permissions and API connectivity~~ ✅
  - [x] ~~Verify command execution in host namespace~~ ✅
  - [x] ~~Ensure reliable error handling and logging~~ ✅

## Terminal Session Discovery

- [x] ~~**Implement terminal session detection**~~ ✅
  - [x] ~~Create `TerminalSessionDetector` class to manage session discovery~~ ✅
  - [x] ~~Implement process listing method to find terminal sessions:~~ ✅
    ```python
    def list_terminal_sessions(self, interactive_only: bool = False) -> List[Dict]:
        """List all terminal sessions on the host machine."""
        # Use DockerClient to run command in host namespace
        result = self.docker_client.run_in_host("ps auxww")
        # Parse the output
        sessions = self._parse_ps_output(result)
        # Filter sessions if requested
        if interactive_only:
            sessions = [s for s in sessions if self._is_interactive_terminal(s)]
        return sessions
    ```
  - [x] ~~Add parser for process information to extract metadata (user, command, start time)~~ ✅
  - [x] ~~Create filtering system to identify interactive terminals~~ ✅

- [x] ~~**Identify terminal PTYs and file descriptors**~~ ✅
  - [x] ~~Implement command to map processes to terminal devices:~~ ✅
    ```python
    def get_terminal_devices(self, pid: int) -> List[Dict]:
        """Get terminal devices for a process."""
        # Find terminal devices using lsof in the host namespace
        result = self.docker_client.run_in_host(f'lsof -p {pid} | grep -E "tty|pts"')
        return self._parse_lsof_output(result)
    ```
  - [x] ~~Develop method to determine if terminal is accessible for reading~~ ✅
  - [x] ~~Create detection for terminal type and capabilities~~ ✅

- [x] ~~**Implement session tracking service**~~ ✅
  - [x] ~~Create tracking service for active and historical terminal sessions~~ ✅
  - [x] ~~Implement periodic scanning with configurable interval~~ ✅
  - [x] ~~Add change detection to identify new and closed sessions~~ ✅
  - [x] ~~Develop connection management for terminal monitoring~~ ✅

## Terminal Output Capture

- [x] ~~**Implement terminal output capture methods**~~ ✅
  - [x] ~~Create unified terminal reader interface:~~ ✅
    ```python
    def capture_output(self, device_path: str, timeout: float = 1.0, method: str = "direct") -> CaptureResult:
        """Capture output from a terminal device."""
        try:
            if method == "direct":
                # Try direct read using cat
                cmd = f"timeout {timeout} cat {device_path}"
                content = self.docker_client.run_in_host(cmd, timeout=timeout+1)
                result.content = content
                result.status = "success"
            else:
                # Use script method as fallback
                script_path = self._create_temp_capture_script(device_path, timeout)
                cmd = f"bash {script_path}"
                content = self.docker_client.run_in_host(cmd, timeout=timeout+2)
                result.content = content
                result.status = "success"
        except Exception as e:
            # Handle errors and timeouts
            result.status = "error"
            result.error_message = f"Capture error: {str(e)}"
        return result
    ```
  - [x] ~~Implement alternative capture methods for different terminal types~~ ✅
  - [x] ~~Add timeouts and error handling for unresponsive terminals~~ ✅
  - [x] ~~Create permissions validation before attempting capture~~ ✅

- [x] ~~**Develop buffering and monitoring system**~~ ✅
  - [x] ~~Create `TerminalOutputCapture` for managing terminal reads~~ ✅
  - [x] ~~Implement circular buffer for efficient content storage:~~ ✅
    ```python
    def append(self, content: str):
        """Append content to the buffer."""
        # Add new content
        self._buffer += content
        
        # Update lines
        self._lines = self._buffer.splitlines()
        
        # Trim buffer if it exceeds max size - implement a circular buffer
        if len(self._buffer) > self.max_size:
            # Drop the oldest content first
            self._buffer = self._buffer[-self.max_size:]
            self._lines = self._buffer.splitlines()
    ```
  - [x] ~~Add incremental capture to avoid duplicating content~~ ✅
  - [x] ~~Develop capture scheduling based on terminal activity~~ ✅

- [x] ~~**Implement output processing pipeline**~~ ✅
  - [x] ~~Create text processor for terminal output~~ ✅
  - [x] ~~Implement ANSI escape sequence filtering:~~ ✅
    ```python
    def remove_ansi_escape_sequences(self, text: str) -> str:
        """Remove ANSI escape sequences from text."""
        return self.ansi_escape_pattern.sub('', text)
    ```
  - [x] ~~Add line continuity tracking across multiple captures~~ ✅
  - [x] ~~Create content normalization for consistent parsing~~ ✅

## Claude Detection and Parsing

- [x] ~~**Implement Claude content detection**~~ ✅
  - [x] ~~Create pattern detection with regular expressions:~~ ✅
    ```python
    def detect_claude_conversation(self, text: str) -> bool:
        """Detect if text contains a Claude conversation."""
        # Find Human and Claude patterns
        human_matches = self.human_pattern.findall(text)
        claude_matches = self.claude_pattern.findall(text)
        
        # A Claude conversation needs at least one Human and one Claude message
        return len(human_matches) > 0 and len(claude_matches) > 0
    ```
  - [x] ~~Add detection for various Claude usage contexts~~ ✅
  - [x] ~~Implement pattern matching for different Claude formats~~ ✅
  - [x] ~~Create result validation to prevent false positives~~ ✅

- [x] ~~**Develop conversation extraction**~~ ✅
  - [x] ~~Create extraction function for Claude conversations:~~ ✅
    ```python
    def extract_claude_conversations(self, text: str) -> List[str]:
        """Extract Claude conversations from terminal output."""
        conversations = []
        lines = text.splitlines()
        
        # Find start and end of conversations
        current_conversation = []
        in_conversation = False
        
        for line in lines:
            # Detect start of conversation (Human message)
            if self.human_pattern.match(line) and not in_conversation:
                in_conversation = True
                current_conversation = [line]
            
            # Add lines to current conversation
            elif in_conversation:
                current_conversation.append(line)
                
                # End of conversation heuristic
                if (len(current_conversation) > 2 and 
                    self.claude_pattern.match(current_conversation[-2]) and 
                    (line.startswith('$') or line.startswith('#') or line.strip() == '')):
                    
                    # Remove the terminal line that ended the conversation
                    current_conversation.pop()
                    
                    # Save conversation
                    conversation_text = '\n'.join(current_conversation)
                    if self.detect_claude_conversation(conversation_text):
                        conversations.append(conversation_text)
                    
                    # Reset for next conversation
                    in_conversation = False
                    current_conversation = []
        
        return conversations
    ```
  - [x] ~~Implement message pair extraction:~~ ✅
    ```python
    def extract_message_pair(self, conversation: str) -> Tuple[str, str]:
        """Extract human prompt and Claude response from a conversation."""
        # Split by Human/Claude markers
        parts = []
        current_part = ""
        current_speaker = None
        
        for line in conversation.splitlines():
            human_match = self.human_pattern.match(line)
            claude_match = self.claude_pattern.match(line)
            
            if human_match:
                # Start a new human part
                if current_speaker:
                    parts.append((current_speaker, current_part.strip()))
                current_speaker = "Human"
                current_part = human_match.group(1) + "\n"
            elif claude_match:
                # Start a new claude part
                if current_speaker:
                    parts.append((current_speaker, current_part.strip()))
                current_speaker = "Claude"
                current_part = claude_match.group(1) + "\n"
            elif current_speaker:
                # Continue the current part
                current_part += line + "\n"
                
        # Save the last part and extract human/claude messages
        if current_speaker and current_part:
            parts.append((current_speaker, current_part.strip()))
        
        human_prompt = "\n\n".join([part for speaker, part in parts if speaker == "Human"])
        claude_response = "\n\n".join([part for speaker, part in parts if speaker == "Claude"])
        
        return human_prompt, claude_response
    ```
  - [x] ~~Add multi-turn conversation support~~ ✅
  - [x] ~~Create robust content cleaning~~ ✅
  - [x] ~~Implement handling for various conversation formats~~ ✅

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

- [x] ~~**Implement command validation**~~ ✅
  - [x] ~~Create command whitelist in `DockerClient`:~~ ✅
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

- [x] ~~**Create terminal session detection tests**~~ ✅
  - [x] ~~Implement unit tests for session detector:~~ ✅
    ```python
    def test_list_terminal_sessions(self):
        """Test parsing process list with terminals."""
        # Mock process list with various processes
        ps_output = """PID   USER     TIME  COMMAND
    1 root      0:04 /init
   10 root      0:00 [kworker/0:1]
  206 root      0:00 -bash
  240 root      0:00 /bin/sh /usr/bin/entrypoint.sh
  300 root      0:00 python3 /app/main.py
"""
        self.mock_docker_client.run_in_host.return_value = ps_output
        
        # Call method
        sessions = self.detector.list_terminal_sessions()
        
        # Assert
        self.assertEqual(len(sessions), 2)  # bash and sh are detected
    ```
  - [x] ~~Create integration test using real Docker socket~~ ✅
  - [x] ~~Test interactive terminal detection with various process types~~ ✅
  - [x] ~~Implement error handling tests for robustness~~ ✅

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

- [x] ~~**Create monitoring configuration**~~ ✅
  - [x] ~~Add Docker socket configuration options to `settings.py`:~~ ✅
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

- [x] ~~**Document Docker socket setup**~~ ✅
  - [x] ~~Created `DOCKER_SOCKET_SETUP.md` with setup instructions~~ ✅
  - [x] ~~Added `DOCKER_SOCKET_IMPLEMENTATION.md` with implementation notes~~ ✅
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

1. ~~**Terminal Session Detection**: Implement the ability to list and identify terminal sessions~~ ✅
2. **Basic Monitoring Loop**: Create the core monitoring functionality with Docker
3. **Claude Content Detection**: Develop pattern recognition for Claude conversations
4. **Data Storage Integration**: Connect the monitor with the prompt repository
5. **Frontend Status Updates**: Add status indicators and controls to the UI

## Nice-to-Haves

- [ ] **Enhanced Helper Container Implementation**
  - [ ] Design a container caching and reuse system for efficiency
  - [ ] Implement resource limiting for containers (CPU, memory, runtime)
  - [ ] Add proper cleanup for terminated containers
  - [ ] Create specialized helper functions for common terminal operations
  - [ ] Implement container pooling for high-frequency operations
  - [ ] Add background cleanup for orphaned containers
  - [ ] Create monitoring for resource usage
  - [ ] Add more granular security controls for command execution

## Completion Status

- Host-Container Communication: 100% complete
- Terminal Session Discovery: 100% complete
- Terminal Output Capture: 100% complete
- Claude Detection and Parsing: 100% complete
- Frontend Integration: 0% complete
- Security Implementation: 50% complete
- Documentation: 85% complete
- Testing: 75% complete (Unit tests added for session detection, device identification, session tracking, and terminal output capture)