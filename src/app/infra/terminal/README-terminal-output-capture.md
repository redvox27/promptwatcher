# Terminal Output Capture

This module implements terminal output capture functionality for the PromptWatcher application. It provides the ability to read terminal output, process it, and detect Claude AI conversations.

## Components

### 1. TerminalOutputCapture

The `TerminalOutputCapture` class handles reading from terminal devices using the Docker client to access the host system:

- **Methods**:
  - `capture_output`: Captures output from a single terminal device
  - `capture_multiple`: Captures output from multiple terminal devices
  - `auto_detect_capture_method`: Detects the best method for capturing output
  - `_create_temp_capture_script`: Creates temporary scripts for capture when needed

- **Capture Methods**:
  - Direct: Uses `cat` to read directly from the terminal device
  - Script: Uses a temporary bash script when direct reads fail

### 2. TerminalOutputBuffer

The `TerminalOutputBuffer` class provides a buffer for storing captured terminal output:

- **Features**:
  - Configurable maximum size
  - Circular buffer implementation (drops oldest content when full)
  - Line-based access methods

- **Methods**:
  - `append`: Adds content to the buffer
  - `get_content`: Gets the entire buffer content
  - `get_lines`: Gets all lines in the buffer
  - `get_last_lines`: Gets the most recent lines
  - `clear`: Clears the buffer

### 3. TerminalOutputProcessor

The `TerminalOutputProcessor` class processes raw terminal output to detect and extract Claude conversations:

- **Processing Features**:
  - ANSI escape sequence removal
  - Line ending normalization
  - Claude conversation detection
  - Conversation extraction

- **Methods**:
  - `remove_ansi_escape_sequences`: Removes terminal color codes and other escape sequences
  - `normalize_line_endings`: Standardizes line endings
  - `clean_text`: Applies all text cleaning operations
  - `detect_claude_conversation`: Detects if text contains a Claude conversation
  - `extract_claude_conversations`: Extracts Claude conversations from terminal output
  - `extract_message_pair`: Extracts human prompt and Claude response from a conversation
  - `process_raw_capture`: Processes raw terminal captures

## Integration

Terminal output capture is integrated with the monitoring system:

1. The `TerminalMonitorCoordinator` now includes:
   - Output capture and processor components
   - Per-session output buffers 
   - Conversation tracking

2. New functionality in the coordinator:
   - Capturing output from terminal sessions
   - Processing output to detect Claude conversations
   - Extracting human/Claude message pairs
   - Hooks for storing conversations

## Usage

The components work together in the following way:

1. Terminal sessions are detected and tracked by the `SessionTrackingService`
2. The coordinator captures output from active terminal sessions
3. Output is processed to detect and extract Claude conversations
4. Conversations are stored in the coordinator and will be saved to the repository

## Testing

A detailed integration test is provided in `terminal_integration_test.py` which demonstrates how all the components work together:

- Terminal session detection
- Terminal device identification
- Session tracking
- Terminal output capture
- Terminal monitor coordination

## To Do

1. **Repository Integration**: Connect the captured conversations to the repository
2. **Configuration**: Add configuration options for buffer sizes, capture intervals, etc.
3. **Performance Optimization**: Optimize capture for busy systems
4. **Error Handling**: Improve error handling and recovery

## Implementation Notes

- Capture is performed using the Docker client to access the host system
- Terminal device access can be challenging due to permissions
- Different terminals (pts, tty, etc.) may require different capture methods
- The process is non-invasive and doesn't modify the terminal output