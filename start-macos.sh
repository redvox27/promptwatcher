#!/bin/bash
# macOS-specific startup script for PromptWatcher

echo "🚀 Starting PromptWatcher with macOS optimizations..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "⚠️  Docker is not running! Please start Docker Desktop first."
  echo "   Look for the whale icon in your menu bar."
  exit 1
fi

# Create .env file with macOS settings
echo "🔧 Configuring environment for macOS..."
cat > .env << EOF
HOST_OS=macos
DOCKER_HOST=unix:///var/run/docker.sock
EOF

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
docker-compose down

# Check Docker socket
if [ ! -e /var/run/docker.sock ]; then
  echo "⚠️  Docker socket not found at /var/run/docker.sock"
  
  # Try to find alternative socket location
  if [ -e ~/.docker/run/docker.sock ]; then
    echo "🔍 Found alternative Docker socket at ~/.docker/run/docker.sock"
    echo "DOCKER_HOST=unix://${HOME}/.docker/run/docker.sock" >> .env
  else
    echo "⚠️  Could not find Docker socket!"
    echo "   Try enabling Docker socket exposure in Docker Desktop settings."
  fi
else
  echo "✅ Docker socket found at /var/run/docker.sock"
fi

# Ensure Docker socket is accessible
echo "🔐 Setting Docker socket permissions..."
if [ -e /var/run/docker.sock ]; then
  sudo chmod 666 /var/run/docker.sock || echo "⚠️  Could not set socket permissions (you may need to enable Docker API access in settings)"
fi

# Start the containers
echo "🚀 Starting containers..."
docker-compose up -d

# Wait for containers to start
echo "⏳ Waiting for containers to initialize..."
sleep 8

# Check container status
if docker-compose ps | grep -q "Up"; then
  echo "✅ Containers are running!"
else
  echo "⚠️  Containers failed to start properly."
  echo "   See logs with: docker-compose logs"
fi

# Run the Docker macOS test
echo "🧪 Running Docker connection test..."
python src/app/infra/terminal/docker_macos_test.py

echo "📊 PromptWatcher dashboard is available at: http://localhost:8000/monitors/dashboard"