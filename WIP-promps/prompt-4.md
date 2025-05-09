# Prompt 4

## User Prompt
based on the architecture setup in claude-plan.md and the steps in claude-plan-iteration-1.md, setup the basic project structure 

## Assistant Response
I'll set up the basic project structure according to the DDD principles outlined in the plans.

I've created the following project structure following Domain-Driven Design principles:

1. Core domain components:
   - Prompt record model
   - Repository interface
   - Service interfaces

2. Application layer:
   - Prompt service implementation
   - DTOs for API communication
   - Application exceptions

3. Infrastructure layer:
   - OpenSearch repository implementation
   - Database client
   - Dependency injection container
   - Mock terminal monitoring service

4. API layer:
   - FastAPI routes for prompts
   - Main application entrypoint

5. Presentation layer:
   - HTMX-based frontend templates
   - Component templates for prompt listing and details

6. Docker configuration:
   - docker-compose.yml for development setup
   - Dockerfiles for API and terminal monitor services
   - OpenSearch configuration

This setup provides the foundational structure for the application with a focus on clean architecture and domain-driven design. The structure supports the iterative development approach outlined in the revised plan, with Docker Compose ready for quick startup of the development environment.