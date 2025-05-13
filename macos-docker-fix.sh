#!/bin/bash
# Script to fix Docker daemon connection on macOS for PromptWatcher

echo "Configuring Docker for macOS compatibility with PromptWatcher..."

# Ensure Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "ERROR: Docker is not running. Please start Docker Desktop first."
  exit 1
fi

# Stop any running containers
echo "Stopping existing containers..."
docker-compose down

# Create a special volume for Docker socket if it doesn't exist
if ! docker volume ls | grep -q promptwatcher_docker_socket; then
  echo "Creating Docker socket volume..."
  docker volume create promptwatcher_docker_socket
fi

# Update Docker settings in .env file
if [ -f .env ]; then
  echo "Updating .env file..."
  # Check if HOST_OS is already set
  if grep -q "HOST_OS" .env; then
    sed -i '' 's/^HOST_OS=.*/HOST_OS=macos/' .env
  else
    echo "HOST_OS=macos" >> .env
  fi
else
  echo "Creating .env file with macOS settings..."
  echo "HOST_OS=macos" > .env
fi

echo "Starting containers with macOS configuration..."
docker-compose up -d

echo "Waiting for containers to initialize..."
sleep 5

echo "Checking container logs for issues..."
docker-compose logs api | grep -i "error\|warning" | tail -20

echo "Setup complete. Access the PromptWatcher dashboard at: http://localhost:8000"
echo ""
echo "If you still see 'Not connected to Docker daemon' errors:"
echo "1. Make sure Docker Desktop has file sharing enabled for the promptwatcher directory"
echo "2. Check Docker Desktop settings to ensure API access is enabled"
echo "3. Try running Docker Desktop as administrator"
echo ""
echo "For detailed logs, run: docker-compose logs -f api"