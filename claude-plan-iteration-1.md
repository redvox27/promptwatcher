# PromptWatcher Architecture Plan - Iteration 1

## Improvements to the Initial Plan

After reviewing the initial architecture plan, I've identified several areas for improvement to create a more iterative, testable, and visually trackable development process:

1. **Shift to Iterative Development**: The original plan followed a somewhat linear approach. We should prioritize getting a minimal viable product running quickly with end-to-end functionality.

2. **Early Visual Progress Tracking**: By establishing the frontend, API, and database connections early, we can visually track progress throughout development.

3. **Testable Infrastructure**: Setting up Docker Compose immediately after the basic structure will allow for consistent testing environments from the start.

4. **Continuous Integration Focus**: Implementing CI practices earlier in the development process to ensure quality.

5. **More Detailed Database Schema**: Better define the OpenSearch schema for prompt storage.

6. **Error Handling Strategy**: Add explicit strategy for handling errors across the application.

7. **Clearer Dependency Injection**: Add a specific approach for dependency injection to support DDD principles.

8. **Mock Terminal Data**: Create mock terminal data early to test without needing the actual terminal monitor working.

## Revised Domain Model

### Core Domain (unchanged)
- **PromptCapture**: Responsible for capturing terminal I/O (Claude prompts and responses)
- **PromptRepository**: Manages storage and retrieval of prompts
- **PromptAnalysis**: Services for analyzing and categorizing prompts

### Enhanced Database Schema

```
PromptRecord {
  id: UUID
  project_name: String
  project_goal: String
  timestamp: DateTime
  prompt_text: Text
  response_text: Text
  terminal_type: String
  session_id: UUID
  labels: Array<String>
  metadata: Object
}
```

## Revised Technical Architecture

The overall architecture remains the same, but with an emphasis on early integration and testing:

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

## Enhanced Technical Stack

Additional components:

1. **Testing**
   - Pytest for unit and integration testing
   - Testcontainers for integration testing with Docker
   - Mock library for unit testing

2. **Dependency Injection**
   - Python dependency-injector library to implement DI pattern
   - Clear container configuration for all components

3. **Error Handling**
   - Custom exception hierarchy
   - Consistent error response format across API
   - Centralized error logging and monitoring

4. **Mock Data Generation**
   - Factory Boy for generating test data
   - Predefined prompt/response datasets for development

## Revised Implementation Plan

### Phase 1: Minimal End-to-End Setup (Core Focus)
1. Set up basic project structure following DDD principles
2. Configure Docker Compose for development environment
3. Create basic OpenSearch schema and repository
4. Implement minimal FastAPI endpoints
5. Build simple HTMX frontend with basic viewing capability
6. Create mock terminal data generator for testing

### Phase 2: Core Functionality with Continuous Testing
1. Implement real terminal monitoring for iTerm2
2. Enhance API with CRUD operations for prompts
3. Add basic labeling functionality to frontend
4. Implement comprehensive testing suite
5. Set up CI pipeline for automated testing

### Phase 3: Enhanced Features with Iterative Feedback
1. Implement prompt analysis and categorization
2. Add advanced filtering and search capabilities
3. Enhance frontend with visualization and analytics
4. Add user authentication and access control

### Phase 4: Extensibility and Optimization
1. Support additional terminals (Windows, standard macOS)
2. Implement templating extraction algorithms
3. Add export/import functionality
4. Optimize for production deployment

## Revised Directory Structure

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
│   ├── persistence/          # Database connections and config
│   └── di/                   # Dependency injection container
│
├── application/              # Application layer
│   ├── services/             # Application services
│   ├── dtos/                 # Data transfer objects
│   ├── events/               # Event handling
│   └── exceptions/           # Application exceptions
│
├── api/                      # API layer (FastAPI)
│   ├── routes/               # API endpoints
│   ├── dependencies/         # FastAPI dependencies
│   ├── middleware/           # API middleware
│   └── errors/               # Error handlers
│
├── presentation/             # Presentation layer
│   ├── templates/            # HTMX templates
│   ├── static/               # Static assets
│   └── viewmodels/           # View models
│
├── mock/                     # Mock data generators
│   ├── generators/           # Data generators
│   └── datasets/             # Sample datasets
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

## Docker Compose Setup (unchanged)

The Docker Compose configuration remains the same as in the original plan, as it provides a solid foundation for development.

## Technical Challenges & Solutions (Enhanced)

### Challenge 1: Terminal I/O Capture (unchanged)
- For iTerm2: Leverage the iTerm2 Python API which provides hooks for session monitoring
- For other terminals: Use PTY (pseudo-terminal) wrapping or process monitoring

### Challenge 2: Development without Terminal Monitor
- Implement a mock data generator for development and testing
- Create a simple UI for manually entering prompts during early development

### Challenge 3: Error Handling and Resilience
- Implement circuit breaker patterns for external dependencies
- Use retries with exponential backoff for transient failures
- Comprehensive logging for troubleshooting

### Challenge 4: Maintaining Clean Architecture
- Use dependency injection to enforce boundaries between layers
- Create clear interfaces between bounded contexts
- Regular architecture reviews to prevent drift

## Revised Next Steps

1. Setup the basic project structure with DDD principles
2. Configure Docker Compose for development
3. Implement basic domain models and interfaces
4. Create OpenSearch repository with schema
5. Build minimal FastAPI endpoints
6. Develop simple HTMX frontend for viewing data
7. Create mock data generator for testing
8. Implement basic terminal monitoring for iTerm2
9. Add testing infrastructure and initial tests
10. Develop labeling functionality in the frontend