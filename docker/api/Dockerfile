FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for psutil and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libc6-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose the port that the application runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "src/main.py"]