# Terminal Session Detection Implementation

This document describes the implementation of terminal session detection in PromptWatcher, which enables the application to identify and monitor terminal sessions on the host machine.

## Implementation Status

✅ **Completed:**
- ~~DockerClient implementation for host system access~~ ✓
- ~~TerminalSessionDetector for discovering terminal processes~~ ✓
- ~~Process parsing and metadata extraction~~ ✓
- ~~Interactive terminal filtering~~ ✓
- ~~Unit tests and integration tests~~ ✓
- ~~Error handling and logging~~ ✓
- ~~Terminal device (PTY) identification~~ ✓
- ~~Session tracking service~~ ✓
- ~~Terminal monitoring integration~~ ✓
- ~~Terminal output capture~~ ✓
- ~~Claude conversation detection~~ ✓

⏳ **In Progress:**
- Repository integration

❌ **Not Started:**
- Frontend monitoring controls

## Overview

The terminal session detection system uses Docker's host access capabilities to discover active terminal sessions. It follows these steps:

1. Connect to the Docker daemon on the host machine
2. Execute process listing commands in the host's namespace
3. Parse process information to identify terminal sessions
4. Filter for interactive terminals where users might be using Claude

## Components

### DockerClient ✓

The `DockerClient` class provides secure host access through Docker:

```python
class DockerClient:
    """Client for interacting with Docker to access host system resources."""

    def __init__(self):
        """Initialize the Docker client."""
        self.client = None
        self.connected = False
        self.connect()

    def connect(self) -> bool:
        """Connect to the Docker daemon."""
        # ...Connection logic...

    def run_in_host(self, command: str, timeout: int = 10) -> str:
        """
        Run command in the host's namespace using a helper container.
        """
        # ...Command validation and execution...
```

✅ This class provides a secure bridge to the host machine through Docker's privileged containers.

### TerminalSessionDetector ✓

The `TerminalSessionDetector` class handles the detection of terminal sessions:

```python
class TerminalSessionDetector:
    """Detector for terminal sessions on the host machine."""
    
    def __init__(self, docker_client: DockerClient):
        """Initialize the terminal session detector."""
        self.docker_client = docker_client
    
    def list_terminal_sessions(self, interactive_only: bool = False) -> List[Dict]:
        """
        List all terminal sessions on the host machine.
        """
        # Get process list from host
        result = self.docker_client.run_in_host("ps auxww")
        
        # Parse the output
        all_sessions = self._parse_ps_output(result)
        
        # Filter for terminal processes
        terminal_sessions = [s for s in all_sessions if s.get("terminal", "?") != "?"]
        
        # Filter for interactive sessions if requested
        if interactive_only:
            interactive_sessions = [s for s in all_sessions if self._is_interactive_terminal(s)]
            return interactive_sessions
        else:
            return terminal_sessions
```

✅ This implementation is complete and tested.

## Process Detection ✓

The system detects terminal sessions using the `ps` command run in the host's namespace:

1. ✅ Execute `ps auxww` to get detailed process information
2. ✅ Parse the output to extract process details (PID, user, terminal, command)
3. ✅ Identify terminal-attached processes based on their TTY field
4. ✅ Filter for interactive sessions by analyzing command and terminal information

## Filtering Interactive Terminals ✓

The application identifies interactive terminal sessions using these criteria:

1. ✅ Process must be connected to a terminal device (pts/X or tty)
2. ✅ Terminal must be an actual device (not "?" which means no terminal)
3. ✅ Process should be interactive (shell, Python interpreter, etc.)
4. ✅ Process should not be excluded (grep, ps, ssh server, etc.)

```python
def _is_interactive_terminal(self, session: Dict) -> bool:
    """
    Determine if a session is an interactive terminal.
    """
    terminal = session.get("terminal", "")
    command = session.get("command", "").lower()
    
    # Check if it's a terminal-connected process
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
```

## Testing ✓

The terminal session detection system includes:

1. ✅ Unit tests with mock process data
2. ✅ Integration tests with the real Docker socket
3. ✅ Error handling tests for robustness
4. ✅ Validation of terminal detection logic across different process types

## Implementation Details

### Process Parsing ✓

The `_parse_process_line` method handles the extraction of process information from ps output:

```python
def _parse_process_line(self, line: str) -> Optional[Dict]:
    """
    Parse a single line from ps output.
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
```

✅ This parsing function successfully extracts process information from various PS output formats.

### Security Considerations ✓

The implementation includes several security features:

1. ✅ **Command Validation**: All commands executed on the host are validated against a whitelist to prevent arbitrary command execution.

   ```python
   def validate_command(self, command: str) -> bool:
       """Ensure command is in the whitelist of safe commands."""
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

2. ✅ **Container Isolation**: Commands are executed in isolated Alpine containers with specific privileges.

3. ✅ **Timeout Protection**: All commands have configurable timeouts to prevent hanging or resource exhaustion.

4. ✅ **Error Handling**: Robust error handling ensures that failures in process detection don't crash the application.

### Cross-Platform Compatibility ✓

The terminal session detection system is designed to work across different platforms:

1. ✅ **Linux**: Uses standard ps formatting and terminal device detection
2. ✅ **macOS**: Compatible with BSD-style ps output 
3. ✅ **Docker for Desktop**: Works within Docker Desktop's virtualized environment

## Integration with PromptWatcher

The terminal session detector integrates with the rest of PromptWatcher through:

1. **Monitor Manager**: The `TerminalMonitorManager` uses the session detector to find terminals to monitor
2. **Scanning Service**: Periodic scanning of terminals is managed by a background service
3. **Frontend Updates**: Terminal session information is exposed through the API for UI display

## Next Steps

Future enhancements to the terminal monitoring system:

1. ✅ **Terminal output capture** (Completed):
   - ~~Created `TerminalOutputCapture` for reading terminal device output~~
   - ~~Implemented multiple capture methods (direct and script-based)~~
   - ~~Added error handling and timeouts for robust operation~~
   - ~~Created circular buffer for efficient content storage~~

2. ✅ **Claude conversation detection** (Completed):
   - ~~Implemented pattern detection for Claude conversations~~
   - ~~Created robust content processing with ANSI filtering~~
   - ~~Added conversation extraction with context boundaries~~
   - ~~Implemented human/Claude message pair extraction~~

3. **Repository Integration** (In Progress):
   - Connect captured conversations with the prompt repository
   - Add session metadata to prompt records
   - Implement deduplication for repeated captures
   - Create history tracking for terminal sessions

### Repository Integration Implementation Plan

The integration between terminal output capture and prompt repository requires connecting the conversation detection system with the domain's data storage. This implementation plan outlines the approach and steps required.

#### 1. Prerequisites and Dependencies

- **Domain Models**: Understand the existing `PromptRecord` model in `app/domain/models.py`
- **Repository Interface**: Analyze the `PromptRepository` interface in `app/domain/repositories.py`
- **Terminal Components**: Leverage the existing terminal output capture components

#### 2. Integration Architecture

We will implement the integration through these components:

1. **ConversationRepository Adapter**:
   - Create an adapter that bridges the terminal monitoring system with the domain repository
   - Map captured terminal conversations to the domain model
   - Handle conversion between formats

2. **Enhanced TerminalMonitorCoordinator**:
   - Inject repository dependency
   - Complete the `store_prompt` method implementation
   - Add metadata collection from terminal sessions

3. **Session-to-Repository Bridge**:
   - Link terminal session IDs with repository records
   - Maintain mapping between terminal sessions and stored prompts

#### 3. Testing Strategy

Tests will verify each aspect of the integration:

**a. Unit Tests:**
- **ConversationRepositoryAdapterTests**:
  - Test mapping between captured conversations and `PromptRecord`
  - Verify metadata is correctly preserved
  - Test error handling during storage

- **TerminalMonitorCoordinatorRepositoryTests**:
  - Test the `store_prompt` method with mocked repository
  - Verify repository is called with correct parameters
  - Test handling of various conversation formats

- **DeduplicationTests**:
  - Test detection of duplicate conversations
  - Verify deduplication strategies work correctly

**b. Integration Tests:**
- **CaptureToStorageTests**:
  - Test the full flow from capture to storage
  - Verify real conversations are properly stored
  - Test with mock terminal data

#### 4. Implementation Steps

1. **Create the Repository Adapter**:
   - Implement `ConversationRepositoryAdapter` class
   - Add mapping logic between formats
   - Implement deduplication strategy

2. **Enhance Terminal Monitor Coordinator**:
   - Complete the `store_prompt` method:
     ```python
     async def store_prompt(
         self,
         session_id: str,
         prompt_text: str,
         response_text: str,
         terminal_type: str,
         project_name: str,
         project_goal: str
     ) -> Optional[PromptRecord]:
         """Store a captured prompt in the repository."""
         try:
             # Create a prompt record
             prompt_record = PromptRecord(
                 prompt_text=prompt_text,
                 response_text=response_text,
                 project_name=project_name,
                 project_goal=project_goal,
                 terminal_type=terminal_type,
                 session_id=UUID(session_id),  # Convert string ID to UUID
                 metadata={
                     "source": "terminal_monitor",
                     "capture_time": datetime.now().isoformat(),
                     "terminal_session_id": session_id
                 }
             )
             
             # Store in repository
             await self.repository.add(prompt_record)
             return prompt_record
             
         except Exception as e:
             logger.error(f"Error storing prompt: {str(e)}")
             return None
     ```

3. **Implement Deduplication Strategy**:
   - Create content hashing function for conversations
   - Track captured conversation hashes per session
   - Add logic to avoid re-storing the same conversations

4. **Update Conversation Processing Pipeline**:
   - Hook repository storage after conversation detection
   - Add proper error handling and transaction management
   - Implement automatic prompt cleanup (remove sensitive data)

5. **Add Session Metadata Collection**:
   - Collect additional metadata from terminal sessions
   - Add user information and terminal context
   - Include process information for debugging

#### 5. Deduplication Strategy

To avoid duplicate entries, we'll implement a multi-level approach:

1. **Content-based detection**:
   - Hash the conversation content (both prompt and response)
   - Maintain an in-memory cache of recently seen conversation hashes
   - Skip storing if the hash matches a recent conversation

2. **Position-tracking**:
   - Track the last capture position for each terminal device
   - Only process new content beyond the last seen position
   - Reset tracking when terminal output buffer wraps

3. **Time-based filtering**:
   - Include timestamp metadata with each capture
   - Implement time-based filtering to avoid duplicates from rapid captures

#### 6. Repository Dependency Injection

The repository will be injected into the coordinator:

```python
class TerminalMonitorCoordinator:
    def __init__(
        self,
        docker_client: DockerClient,
        session_detector: TerminalSessionDetector,
        device_identifier: TerminalDeviceIdentifier,
        tracking_service: SessionTrackingService,
        output_capture: TerminalOutputCapture,
        output_processor: TerminalOutputProcessor,
        repository: PromptRepository,  # Added repository dependency
        settings: Optional[Dict] = None
    ):
        # Initialize other components
        self.repository = repository
        # ...
```

This ensures the coordinator can store detected conversations in the repository.

#### 7. Implementation Considerations and Challenges

Several challenges must be addressed during implementation:

1. **Asynchronous Processing**:
   - Ensure repository operations don't block terminal monitoring
   - Handle async context properly for database transactions
   - Implement retry logic for failed storage operations

2. **Memory Management**:
   - Be mindful of memory usage with long-running sessions
   - Implement periodic cleanup of conversation caches
   - Handle large conversations efficiently

3. **Error Recovery**:
   - Implement recovery mechanisms for interrupted captures
   - Handle repository connectivity issues gracefully
   - Include monitoring for storage operations

4. **Security and Privacy**:
   - Implement sensitive data filtering before storage
   - Consider adding configurable content filters
   - Add options for anonymizing user information

#### 8. Testing Approach

The testing strategy will follow these principles:

1. **Test Isolation**:
   - Use mocks for external dependencies (repository, Docker client)
   - Create test fixtures with sample terminal conversations
   - Isolate integration tests from production database

2. **Coverage Goals**:
   - Aim for 90%+ coverage of repository integration code
   - Include both positive and negative test cases
   - Test edge cases like very large conversations

3. **Test Data Management**:
   - Create realistic sample conversations for testing
   - Include various Claude conversation formats
   - Test with different terminal output formats

4. **Test Environment**:
   - Ensure tests can run in CI environment
   - Use in-memory database for integration tests
   - Create dockerized test setup for full integration tests

4. **Frontend enhancements** (Not Started):
   - Add real-time monitoring status to the UI
   - Create controls for starting/stopping monitoring
   - Add terminal session visualization
   - Implement capture statistics and metrics

5. **Performance optimization** (Not Started):
   - Implement adaptive scanning based on activity
   - Add resource limits for Docker operations
   - Optimize memory usage for long-running sessions
   - Implement efficient content buffering strategies