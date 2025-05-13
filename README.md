# PromptWatcher

A tool for monitoring and analyzing Claude prompts made in terminal environments.

## Overview

PromptWatcher captures prompts and responses from Claude AI in standard macOS/Linux terminal applications and stores them in OpenSearch for analysis. The tool provides a web interface for viewing, filtering, and labeling prompts.

## Features

- Terminal monitoring for capturing Claude prompts
- Storage of prompts with associated metadata
- Web interface for viewing and labeling prompts
- Analytics for prompt patterns and templates

## Architecture

The application follows a simplified Domain-Driven Design pattern with the following structure:

- **Domain Layer**: Core business logic and interfaces
- **Infrastructure Layer**: Implementation details including database and terminal monitoring
- **Presentation Layer**: Web interface and API endpoints

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)

### Running with Docker Compose

1. Clone the repository

2. Set environment variables (optional):
   ```
   export PROJECT_NAME="My Project"
   export PROJECT_GOAL="Developing a new feature"
   ```

3. Start the application:
   ```
   docker-compose up
   ```

4. Access the web interface at http://localhost:8000
   Access OpenSearch Dashboards at http://localhost:5601

### Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the API:
   ```
   python src/main.py
   ```

## Project Structure

```
promptwatcher/
│
├── src/                      # All source code
│   ├── app/                  # Application code
│   │   ├── bootstrap.py      # App initialization
│   │   ├── settings.py       # Configuration settings
│   │   │
│   │   ├── domain/           # Domain layer
│   │   │   ├── models.py     # Domain entities
│   │   │   ├── repositories.py # Repository interfaces
│   │   │   └── services.py   # Domain services
│   │   │
│   │   ├── infra/            # Infrastructure layer
│   │   │   ├── db/           # Database implementations
│   │   │   ├── opensearch/   # OpenSearch client
│   │   │   ├── terminal/     # Terminal monitoring
│   │   │   └── services_container.py # Service container
│   │   │
│   │   └── presentation/     # Presentation layer
│   │       ├── deps.py       # Route dependencies
│   │       ├── routes/       # API routes
│   │       └── templates/    # HTMX templates
│   │
│   └── main.py              # Entry point
│
├── docker/                  # Docker configuration
│   ├── opensearch/         # OpenSearch configuration
│   └── api/                # API service configuration
│
├── tests/                  # Tests
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
│
├── docker-compose.yml      # Docker Compose configuration
└── requirements.txt        # Python dependencies
```

## WIP-promps

During development, all prompts and responses are stored in the WIP-promps directory with sequential numbering until the actual prompt watcher is functional.