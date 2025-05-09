# PromptWatcher Architecture Plan - Iteration 2

## User Prompt
I think the architecture is too complex for the tasks required. Study the code of the defibrion project which is located in the parent folder of the current project. To be more specific, think step-by-step on how you can achieve a similar project structure from defibrion.backend.src.app. Store the plan in a markdown file as claude-plan-iteration-2.md. In the file, store this prompt and the next architecture proposal.

## Simplified Architecture Proposal

After studying the defibrion project structure, I can see that it uses a more streamlined approach to DDD while still maintaining separation of concerns. The key difference is that it has fewer layers and simpler abstractions, making it more suitable for a smaller project like PromptWatcher.

### Key Insights from Defibrion Structure

1. **Three Main Layers**: The structure uses only three main architectural folders:
   - `domain` - Core business logic and entities
   - `infra` - Infrastructure implementations
   - `presentation` - User interface and API endpoints

2. **Central Bootstrap**: Uses a `bootstrap.py` file to manage application startup and dependency setup

3. **Simple Service Container**: Rather than complex dependency injection frameworks, uses a simpler service container approach

4. **Straight-to-the-point Repository Pattern**: Clean repository interfaces that are easy to implement

### Revised PromptWatcher Architecture

Based on these insights, here's a simplified architecture for PromptWatcher:

```
promptwatcher/
│
├── src/                      # All source code
│   ├── app/                  # Application code
│   │   ├── __init__.py
│   │   ├── bootstrap.py      # App initialization
│   │   ├── settings.py       # Configuration settings
│   │   │
│   │   ├── domain/           # Domain layer
│   │   │   ├── __init__.py
│   │   │   ├── models.py     # Domain entities
│   │   │   ├── repositories.py # Repository interfaces
│   │   │   └── services.py   # Domain services
│   │   │
│   │   ├── infra/            # Infrastructure layer
│   │   │   ├── __init__.py
│   │   │   ├── db/           # Database implementations
│   │   │   │   ├── __init__.py
│   │   │   │   └── repositories.py # Repository implementations
│   │   │   │
│   │   │   ├── opensearch/   # OpenSearch client and utilities
│   │   │   │   ├── __init__.py
│   │   │   │   └── client.py
│   │   │   │
│   │   │   ├── terminal/     # Terminal monitoring
│   │   │   │   ├── __init__.py
│   │   │   │   └── monitor.py
│   │   │   │
│   │   │   └── services_container.py # Service container
│   │   │
│   │   └── presentation/     # Presentation layer
│   │       ├── __init__.py
│   │       ├── deps.py       # Dependency handling for routes
│   │       ├── routes/       # API routes
│   │       │   ├── __init__.py
│   │       │   └── prompts.py
│   │       │
│   │       └── templates/    # HTMX templates
│   │           ├── base.html
│   │           ├── index.html
│   │           └── partials/
│   │
│   └── main.py              # Entry point
│
├── docker/                  # Docker configuration
│   ├── opensearch/         # OpenSearch configuration
│   └── api/                # API service configuration
│
├── tests/                  # Tests
│   ├── unit/
│   └── integration/
│
├── docker-compose.yml      # Docker Compose configuration
└── requirements.txt        # Python dependencies
```

### Key Simplifications

1. **Flatter Structure**: Reduced nesting of directories makes navigation easier
   
2. **Consolidated Models**: Instead of multiple model classes in separate files, we'll use a single `models.py` file for all domain entities
   
3. **Reduced DTO Usage**: We'll minimize the use of DTOs and use Pydantic models for validation directly in API routes
   
4. **Simple Service Container**: Instead of a complex DI container, use a simpler service container pattern similar to defibrion
   
5. **Direct Repository Implementations**: More straightforward repository implementations rather than multiple layers of abstraction
   
6. **Streamlined API Layer**: Simplified API layer with fewer middleware components

### Implementation Approach

1. Start with setting up the basic structure and `bootstrap.py` to handle application initialization

2. Implement the domain models and repository interfaces for prompts

3. Add OpenSearch infrastructure with repository implementations

4. Create a simplified terminal monitoring service

5. Set up FastAPI routes and HTMX templates for the frontend

6. Configure Docker Compose for development

### Advantages of This Approach

1. **Easier to Understand**: Simpler structure means easier onboarding and maintenance
  
2. **Still Following DDD**: Still maintains domain-driven design principles but with less overhead
   
3. **Faster to Implement**: Fewer abstractions means faster development time
   
4. **Better for Small/Medium Projects**: More appropriate scale for a tool like PromptWatcher
   
5. **Easier to Test**: Simpler dependencies make testing more straightforward

This revised architecture offers a good balance between proper separation of concerns and practical simplicity for the PromptWatcher project.