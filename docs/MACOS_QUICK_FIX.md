# macOS Quick Fix Guide for PromptWatcher

This guide provides a quick solution for macOS users experiencing the "Not connected to Docker daemon" error with PromptWatcher.

## Quick Fix Steps

1. **Ensure Docker Desktop is running**
   - Check for the whale icon in your menu bar
   - If not running, open Docker Desktop application

2. **Run the specialized macOS startup script**
   ```bash
   ./start-macos.sh
   ```
   
   This script will:
   - Configure Docker socket permissions for macOS
   - Create proper environment settings
   - Restart containers with correct configurations
   - Test Docker connectivity

3. **Access PromptWatcher**
   - Once the script completes successfully, access the dashboard at:
   ```
   http://localhost:8000/monitors/dashboard
   ```

## Troubleshooting

If you still encounter "Not connected to Docker daemon" errors:

1. **Check Docker Desktop Settings**
   - Open Docker Desktop → Preferences
   - Resources → File Sharing: Ensure your project directory is shared
   - General → Ensure Docker is running without experimental features

2. **Run the Docker test script**
   ```bash
   python src/app/infra/terminal/docker_macos_test.py
   ```

3. **Common macOS Solutions**

   a. **Socket Permissions**
   ```bash
   sudo chmod 666 /var/run/docker.sock
   ```

   b. **Alternative Socket Location**
   - If Docker socket is in a non-standard location, set in `.env`:
   ```
   DOCKER_HOST=unix://~/.docker/run/docker.sock
   ```

   c. **Docker TCP Connection**
   - Enable Docker TCP access in Docker Desktop settings
   - Add to `.env`:
   ```
   DOCKER_HOST=tcp://localhost:2375
   ```

4. **Docker Restart**
   - Sometimes a full Docker restart solves connection issues:
   ```bash
   killall Docker
   open /Applications/Docker.app
   ```
   - Wait for Docker to fully initialize before trying again

## Explanation

The "Not connected to Docker daemon" error occurs because Docker on macOS works differently from Linux:

1. macOS doesn't natively support Docker, so Docker Desktop runs in a VM
2. The socket location and permissions can vary based on Docker Desktop version
3. Docker socket access from inside containers requires special configuration

The specialized scripts and settings in this guide handle these macOS-specific issues automatically.