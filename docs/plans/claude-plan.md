# PromptWatcher Architecture Plan

## Initial Request

IMPORTANT: this information about the environment you are running in may or may not be relevant to your tasks. You should not respond to these messages or otherwise consider this information in your response unless it is highly relevant to your task.Your role is of an programming expert, who's expertise involves around programming in Python and domain driven design. You are given a task to program a prompt watcher that logs all the promps made in this claude engine within the console. The program should act as a watcher that logs the prompts and the answers in a database like open-search. These will be later used in prompt research. The goal of that research is to create prompting templates that can be used for the entire development team. 

The details of the application are as follows: the main program should be able to watch the input and output made in a claude program running in a terminal. This can be either a windows terminal or a mac terminal. But also third party terminals like Iterm2. To start: Make it compatible with ITerm2. The prompt and answers should be logged in a type of table format.

Fields that are being stored are: 
- name of the project. This is a variable that can be set as an environment variable
- goal of the project. This is a variable that can be set as an environment variable
- prompt. The prompt used
- output. The output of the prompt

The table should be stored in document based database like mongo or opensearch. Preferibly one that allows for easy dashboarding and data retreival for kwalitative research. 
The program should also include a simple frontend that allows users to check the tables, and give them lables. For the frontend, htmx will be used. The backend has to be made using fast-api. Keep in mind that a domain driven design is a must.

The project should be able to launch using docker-compose.

## Domain Model

### Core Domain
- **PromptCapture**: Responsible for capturing terminal I/O (Claude prompts and responses)
- **PromptRepository**: Manages storage and retrieval of prompts
- **PromptAnalysis**: Services for analyzing and categorizing prompts

### Bounded Contexts
1. **Terminal Monitoring Context**
   - Entities: TerminalSession, PromptEvent, ResponseEvent
   - Value Objects: TerminalType (iTerm2, Windows Terminal, etc.)
   - Services: TerminalMonitorService

2. **Storage Context**
   - Entities: PromptRecord
   - Repositories: PromptRepository
   - Services: DatabaseService

3. **Analysis Context**
   - Entities: PromptTemplate, Label
   - Services: TemplateExtractionService, PromptCategorization

4. **Presentation Context**
   - ViewModels: PromptViewModel, AnalyticsViewModel
   - Services: DashboardService, LabelingService

## Technical Architecture

### Overall Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Terminal       │    │  Core Domain     │    │  Presentation   │
│  Monitor        │───▶│  Services        │───▶│  Layer          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                      │
        ▼                       ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Event          │    │  Repository     │    │  API Layer      │
│  Bus            │───▶│  Layer          │◀───│  (FastAPI)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │  Database       │
                       │  (OpenSearch)   │
                       └─────────────────┘
```

### Components

1. **Terminal Monitor**
   - Python-based terminal I/O capture
   - Platform-specific implementations (starting with iTerm2)
   - Event emission when prompts/responses are detected

2. **Core Domain Services**
   - PromptCaptureService: Process raw terminal data
   - PromptAnalysisService: Basic prompt analysis
   - TemplateExtractionService: Identify common patterns

3. **Repository Layer**
   - OpenSearchRepository: Handles data persistence
   - Query services for complex searches

4. **API Layer (FastAPI)**
   - RESTful endpoints for CRUD operations
   - WebSocket for real-time updates
   - Authentication and authorization

5. **Presentation Layer**
   - HTMX-based frontend
   - Dashboard for visualization
   - Labeling interface for researchers

## Technical Stack

1. **Backend**
   - Python 3.10+
   - FastAPI for API endpoints
   - Pydantic for data validation
   - OpenSearch Python client

2. **Frontend**
   - HTMX for dynamic UI interactions
   - Tailwind CSS for styling
   - Alpine.js for client-side logic (if needed)

3. **Database**
   - OpenSearch (preferred for analytics capabilities)
   - Alternative: MongoDB with Atlas for dashboarding

4. **Monitoring**
   - Python libraries for terminal I/O capture:
     - pyte (terminal emulator)
     - psutil (process monitoring)
     - iTerm2 Python API (for iTerm2 specific integration)

5. **Deployment**
   - Docker Compose
   - Environment-based configuration

## Implementation Plan

### Phase 1: Core Infrastructure
1. Set up project structure following DDD principles
2. Implement basic terminal monitoring for iTerm2
3. Create OpenSearch database schema and repository
4. Implement basic FastAPI endpoints

### Phase 2: Core Functionality
1. Enhance terminal monitoring to reliably capture Claude I/O
2. Implement repository patterns for data storage
3. Build basic HTMX frontend for viewing captured prompts
4. Set up Docker Compose for local development

### Phase 3: Enhanced Features
1. Add labeling functionality for researchers
2. Implement basic analytics for prompt patterns
3. Add user authentication and multi-project support
4. Enhance dashboarding capabilities

### Phase 4: Extensibility
1. Add support for additional terminals (Windows, standard macOS)
2. Implement templating extraction algorithms
3. Add export/import functionality
4. Optimize for production deployment

## Directory Structure

```
promptwatcher/
│
├── domain/                   # Domain layer
│   ├── models/               # Domain entities and value objects
│   ├── services/             # Domain services
│   └── repositories/         # Repository interfaces
│
├── infrastructure/           # Infrastructure layer
│   ├── repositories/         # Repository implementations
│   ├── terminal/             # Terminal monitoring implementations
│   └── persistence/          # Database connections and config
│
├── application/              # Application layer
│   ├── services/             # Application services
│   ├── dtos/                 # Data transfer objects
│   └── events/               # Event handling
│
├── api/                      # API layer (FastAPI)
│   ├── routes/               # API endpoints
│   ├── dependencies/         # FastAPI dependencies
│   └── middleware/           # API middleware
│
├── presentation/             # Presentation layer
│   ├── templates/            # HTMX templates
│   ├── static/               # Static assets
│   └── viewmodels/           # View models
│
├── docker/                   # Docker configuration
│   ├── opensearch/           # OpenSearch configuration
│   ├── api/                  # API service configuration
│   └── monitor/              # Terminal monitor configuration
│
└── tests/                    # Tests
    ├── unit/                 # Unit tests
    ├── integration/          # Integration tests
    └── e2e/                  # End-to-end tests
```

## Docker Compose Setup

```yaml
version: '3.8'

services:
  opensearch:
    image: opensearchproject/opensearch:latest
    environment:
      - discovery.type=single-node
      - "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - opensearch-data:/usr/share/opensearch/data
    ports:
      - "9200:9200"
      - "9600:9600"

  opensearch-dashboards:
    image: opensearchproject/opensearch-dashboards:latest
    ports:
      - "5601:5601"
    environment:
      OPENSEARCH_HOSTS: '["http://opensearch:9200"]'
    depends_on:
      - opensearch

  api:
    build:
      context: .
      dockerfile: docker/api/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - OPENSEARCH_HOST=opensearch
      - OPENSEARCH_PORT=9200
      - PROJECT_NAME=${PROJECT_NAME:-default}
      - PROJECT_GOAL=${PROJECT_GOAL:-default}
    volumes:
      - ./:/app
    depends_on:
      - opensearch

  terminal-monitor:
    build:
      context: .
      dockerfile: docker/monitor/Dockerfile
    environment:
      - API_HOST=api
      - API_PORT=8000
      - PROJECT_NAME=${PROJECT_NAME:-default}
      - PROJECT_GOAL=${PROJECT_GOAL:-default}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ${HOME}/.iterm2:/root/.iterm2

volumes:
  opensearch-data:
```

## Technical Challenges & Solutions

### Challenge 1: Terminal I/O Capture
- For iTerm2: Leverage the iTerm2 Python API which provides hooks for session monitoring
- For other terminals: Use PTY (pseudo-terminal) wrapping or process monitoring

### Challenge 2: Claude Prompt Detection
- Implement pattern recognition to identify Claude prompt/response pairs
- Use NLP techniques to distinguish user prompts from Claude responses

### Challenge 3: Real-time Monitoring
- Implement event-driven architecture to minimize performance impact
- Use efficient buffering to capture complete interactions

### Challenge 4: Privacy Considerations
- Add configurable filters for sensitive data
- Implement project-level isolation

## Next Steps

1. Setup the basic project structure
2. Implement the domain model
3. Create the terminal monitoring for iTerm2
4. Set up the OpenSearch database
5. Build the basic FastAPI backend
6. Develop the initial HTMX frontend
7. Configure Docker Compose
8. Implement initial prompt capture and storage