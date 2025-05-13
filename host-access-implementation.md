# Host Terminal Access Implementation

This document outlines the changes made to enable the PromptWatcher application to access and display terminal sessions from the host machine rather than just from within the Docker container.

## Problem Summary

The original implementation could only detect terminal sessions within the Docker container, not the host machine sessions. This limited the application's primary intended functionality.

## Solution Overview

The solution involves several key components:

1. Mount the host's `/proc` and `/dev` filesystems into the Docker container
2. Configure the application to detect and use these mounted filesystems
3. Enhance the session detection to work with the host's process information
4. Provide multiple fallback methods if one approach fails

## Implementation Details

### 1. Docker Compose Configuration

Updated the `docker-compose.yml` file to:

- Run the container in privileged mode
- Mount host `/proc` and `/dev` filesystems
- Mount additional host files for username resolution
- Use the host's PID namespace
- Configure environment variables for host access

```yaml
volumes:
  - /proc:/host/proc:ro    # Mount host's proc filesystem as read-only
  - /dev:/host/dev:ro      # Mount host's device filesystem as read-only
  - /var/run:/host/var/run:ro  # Mount run directory for socket access
  - /run:/host/run:ro      # Additional run directory on some systems
  - /etc/passwd:/host/etc/passwd:ro  # Mount passwd file for username lookup
  - /etc/group:/host/etc/group:ro    # Mount group file for group lookup
privileged: true           # Required for accessing host resources
pid: "host"                # Use host's PID namespace directly
```

### 2. Session Detector Enhancements

Modified `session_detector.py` to:

- Detect and use the mounted host proc filesystem
- Improve process information extraction
- Add multiple methods to detect terminal connections
- Enhance the interactive terminal detection logic

Key enhancements:
- Detection of host proc filesystem mount points
- Multiple strategies to find terminal connections
- Better handling of user information
- More comprehensive logging for debugging
- Advanced terminal detection heuristics

### 3. Docker Client Improvements

Updated `docker_client.py` to:

- Support direct execution with host proc access
- Add more allowed commands for better terminal detection
- Handle fallback strategies if one approach fails
- Improve error handling and logging

### 4. Monitor Manager Updates

Enhanced `monitor.py` to:

- Log environment information for debugging
- Test the session detection during initialization
- Log sample detected sessions
- Add more comprehensive error handling

### 5. Settings Updates

Added configuration option in `settings.py` for:

- Host proc path configuration for consistent access

## How It Works

The application now uses a multi-layered approach to detect host terminal sessions:

1. **Primary Method**: Direct access to host's `/proc` filesystem
   - Reads process information directly
   - Checks file descriptors for terminal connections
   - Maps process information to terminal sessions

2. **Secondary Method**: Docker execution with host PID namespace
   - Uses `ps`, `lsof`, and other commands
   - Executes in the host's process namespace
   - Parses command output to identify sessions

3. **Tertiary Method**: Additional terminal detection techniques
   - Uses `w` command to find active user sessions
   - Uses `lsof` to find processes with terminal connections
   - Combines data from multiple sources for better accuracy

## Usage Instructions

To apply these changes:

1. Ensure your Docker installation supports privileged mode and host access
2. Stop any running containers:
   ```
   docker-compose down
   ```

3. Rebuild the containers with the new configuration:
   ```
   docker-compose build
   ```

4. Start the containers:
   ```
   docker-compose up -d
   ```

5. Check the logs for session detection information:
   ```
   docker-compose logs -f api
   ```

6. Access the monitoring dashboard at:
   ```
   http://localhost:8000/monitors/dashboard
   ```

7. Start monitoring and check if host terminal sessions are now visible

## Troubleshooting

If sessions still aren't visible:

1. Check logs for errors related to `/host/proc` access
2. Verify that the Docker container has the necessary permissions
3. Try running with a different Docker configuration if your system has restrictions
4. Check if alternative session detection methods are working

## Security Considerations

This implementation requires privileged container access to the host system. This is necessary for the core functionality but does introduce security considerations:

- The container runs with elevated privileges
- It has read access to host process information
- Access is limited to read-only operations where possible
- Command execution is strictly filtered

These permissions are required for the application's primary purpose of monitoring host terminal sessions.