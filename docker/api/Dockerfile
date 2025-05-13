FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for psutil, Docker CLI, and other tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libc6-dev \
    curl \
    docker.io \
    iproute2 \
    procps \
    grep \
    lsof \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Set Docker-related environment variables
ENV DOCKER_HOST=unix:///var/run/docker.sock
ENV DOCKER_API_VERSION=1.41

# Expose the port that the application runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "src/main.py"]