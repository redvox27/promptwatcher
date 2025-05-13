# Docker Socket Setup for PromptWatcher

This document explains how the Docker socket is used to monitor terminal sessions on the host machine from within the PromptWatcher container.

## Overview

PromptWatcher uses the Docker socket to access and monitor terminal sessions on the host machine. The Docker socket provides a secure way for the container to interact with the host system, allowing it to capture Claude prompts and responses from terminal sessions.

## How It Works

1. The Docker socket (`/var/run/docker.sock`) is mounted from the host into the PromptWatcher container
2. The container uses the Docker API to launch temporary "helper" containers with access to the host's process and network namespaces
3. These helper containers execute specific read-only commands to discover and capture terminal sessions
4. The terminal output is analyzed to identify Claude interactions, which are then stored in OpenSearch

## Security Considerations

- The Docker socket provides significant access to the host system, so security measures are implemented:
  - Only whitelisted read-only commands can be executed (ps, grep, cat, etc.)
  - All commands are validated before execution
  - The helper containers are short-lived and removed immediately after use
  - Resource limits are applied to helper containers to prevent DoS attacks

## Setup Instructions

1. Ensure Docker is installed and running on your host machine
2. If needed, update socket permissions (this may be required depending on your host configuration):
   ```bash
   sudo chmod 666 /var/run/docker.sock
   ```
   Note: This makes the socket readable and writable by any user. For production, consider using a more restrictive approach.

3. Start PromptWatcher with Docker Compose:
   ```bash
   docker-compose up
   ```

4. Verify Docker socket access:
   ```bash
   docker-compose exec api python -m src.app.infra.terminal.docker_test
   ```

## Troubleshooting

If you encounter issues with Docker socket access:

1. Check socket permissions:
   ```bash
   ls -la /var/run/docker.sock
   ```
   The permissions should allow the container to read/write to the socket.

2. Verify Docker API access:
   ```bash
   curl --unix-socket /var/run/docker.sock http://localhost/version
   ```
   This should return Docker version information.

3. Check container logs for specific errors:
   ```bash
   docker-compose logs api
   ```

4. If you see permission errors, you may need to adjust the user in the Dockerfile or the permissions of the Docker socket.

## Configuration Options

The following environment variables can be set in docker-compose.yml to configure Docker socket behavior:

- `MONITORING_INTERVAL`: Interval between terminal checks (default: 5.0 seconds)
- `DOCKER_HELPER_IMAGE`: Image used for helper containers (default: alpine:latest)
- `DOCKER_TIMEOUT`: Timeout for Docker operations (default: 10 seconds)
- `ALLOWED_USERS`: Comma-separated list of users to monitor (default: current user only)

## Limitations

- The Docker socket approach requires Docker to be running on the host
- Some host security configurations may block this approach
- Performance impact should be monitored when running in production