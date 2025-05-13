# PromptWatcher Project - Todo List

## Project Overview

PromptWatcher is a tool for monitoring and analyzing Claude prompts made in terminal environments. The application captures prompts and responses from Claude AI in terminal applications (starting with iTerm2) and stores them in OpenSearch for analysis, providing a web interface for viewing, filtering, and labeling prompts.

## What's Been Implemented

### Core Structure
- ✅ Basic project setup with Domain-Driven Design architecture
- ✅ Docker Compose configuration for OpenSearch and the application
- ✅ Core domain models (PromptRecord)

### Infrastructure
- ✅ OpenSearch client integration with connection retry logic
- ✅ Basic repository pattern implementation
- ✅ Mock prompt capture service
- ✅ Service container for dependency management
- ✅ Basic terminal monitor manager interface

### API & Frontend
- ✅ FastAPI endpoints for CRUD operations on prompts
- ✅ Basic HTMX-based UI for viewing prompt list
- ✅ Simple interface for prompt details
- ✅ Mock data generation endpoint
- ✅ Real-time polling for prompt list updates

## What Still Needs To Be Done

### Terminal Monitoring
- ❌ Implement actual terminal monitoring for iTerm2
- ❌ Create process for detecting Claude prompts/responses
- ❌ Add monitoring start/stop functionality (endpoints already stubbed)
- ❌ Add session management for grouped prompts

### Prompt Analysis
- ❌ Implement prompt categorization
- ❌ Add template extraction features
- ❌ Create analytics dashboard

### Frontend Enhancements
- ❌ Add more advanced filtering options
- ❌ Improve visualization of prompts/responses
- ❌ Add user authentication and multi-project support
- ❌ Implement export functionality

### Infrastructure & DevOps
- ❌ Add unit and integration tests
- ❌ Improve error handling and logging
- ❌ Add deployment documentation
- ❌ Create CI/CD pipeline

## Current Focus Areas

### High Priority
1. **Terminal Monitoring Implementation**: The core functionality of monitoring Claude in terminals
2. **Session Management**: Properly group related prompts together
3. **Testing**: Add comprehensive tests for existing functionality

### Medium Priority
1. **Frontend Improvements**: Enhance the UI for better usability
2. **Prompt Analysis**: Implement basic analytics
3. **Documentation**: Improve project documentation

### Low Priority
1. **User Authentication**: Add multi-user support
2. **Advanced Analytics**: Implement more complex analysis features
3. **Support for Additional Terminal Types**: Beyond iTerm2

## Implementation Notes

- The application follows a three-layer architecture:
  - Domain layer: Core business logic and interfaces
  - Infrastructure layer: Implementation details
  - Presentation layer: API endpoints and UI

- The frontend uses HTMX for dynamic interaction and already has a polling mechanism for real-time updates of prompt data.

- The terminal monitoring functionality is currently stubbed with mock implementations ready to be replaced with actual terminal monitoring code.