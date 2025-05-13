# macOS Docker Setup for PromptWatcher

This document provides specific instructions for setting up PromptWatcher with Docker on macOS systems.

## macOS-Specific Requirements

macOS uses a virtualized Docker environment (Docker Desktop), which requires special configuration for container-to-host communication:

1. **Docker Desktop** must be installed and running
2. **File sharing** must be enabled for the promptwatcher directory
3. **Docker socket** must be properly exposed to containers

## Setup Instructions

### 1. Install Docker Desktop

If not already installed:
1. Download Docker Desktop from [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
2. Install and launch Docker Desktop
3. Ensure Docker Desktop is running (check the whale icon in your menu bar)

### 2. Configure File Sharing

1. Open Docker Desktop preferences
2. Go to "Resources" > "File Sharing"
3. Add your promptwatcher directory to the list of shared folders
4. Apply and restart Docker Desktop

### 3. Run the macOS Fix Script

We've created a specialized script to configure Docker for macOS compatibility:

```bash
# Make the script executable
chmod +x macos-docker-fix.sh

# Run the script
./macos-docker-fix.sh
```

The script will:
- Configure Docker socket access
- Set proper environment variables
- Restart containers with the correct settings
- Provide troubleshooting information if needed

### 4. Manual Configuration (if the script doesn't work)

If the automatic script fails, you can manually configure Docker:

1. Stop existing containers:
   ```bash
   docker-compose down
   ```

2. Create a `.env` file in the project root with:
   ```
   HOST_OS=macos
   ```

3. Update Docker settings:
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```

## Troubleshooting

If you encounter "Not connected to Docker daemon" errors:

1. **Check Docker Desktop Status**
   - Make sure Docker Desktop is running
   - Try restarting Docker Desktop

2. **Check Permissions**
   - The Docker socket might need permission changes:
   ```bash
   sudo chmod 666 /var/run/docker.sock
   ```

3. **Check Socket File**
   - Verify that the Docker socket exists and is accessible:
   ```bash
   ls -la /var/run/docker.sock
   ```

4. **Try running with explicit socket location**
   - Update your .env file:
   ```
   HOST_OS=macos
   DOCKER_HOST=unix:///var/run/docker.sock
   ```

5. **Enable API Access**
   - In Docker Desktop, go to Settings > General
   - Ensure "Expose daemon on tcp://localhost:2375 without TLS" is enabled
   - Add to .env: `DOCKER_HOST=tcp://localhost:2375`

## Still Having Issues?

If you continue to experience problems:

1. Check the Docker logs:
   ```bash
   docker-compose logs api
   ```

2. Try running with a different Docker configuration:
   ```bash
   DOCKER_HOST=unix:///var/run/docker.sock docker-compose up -d
   ```

3. Consider using the mock data mode if Docker access can't be established