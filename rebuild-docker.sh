#!/bin/bash
# Rebuild and restart the Docker containers with host terminal access

echo "Stopping any running containers..."
docker-compose down

echo "Rebuilding containers with no cache..."
docker-compose build --no-cache

echo "Starting containers..."
docker-compose up -d

echo "Waiting for containers to start..."
sleep 10

echo "Showing logs (press Ctrl+C to exit)..."
docker-compose logs -f api