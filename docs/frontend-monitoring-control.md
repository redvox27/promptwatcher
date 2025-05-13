# Frontend Monitoring Controls Implementation Plan

## Overview

This document outlines the plan for implementing frontend monitoring controls for the PromptWatcher application. These controls will enable users to start, stop, and monitor terminal session capture, view active sessions, and access real-time statistics about the capture process.

## Goals

1. Provide intuitive UI controls for terminal monitoring
2. Display real-time monitoring status and statistics
3. Allow users to view active terminal sessions
4. Enable manual triggering of capture for specific sessions
5. Visualize monitoring performance and activity

## Component Architecture

### 1. Monitoring Dashboard

**Purpose**: Central hub for monitoring controls and status visualization

**Features**:
- Overall monitoring status indicator (active/inactive)
- Start/stop monitoring controls
- Summary statistics (active sessions, total captures, success rate)
- System resource usage indicators
- Activity timeline

**Location**:
- New route: `/monitoring`
- Template: `/src/app/presentation/templates/monitoring/dashboard.html`

### 2. Terminal Sessions Panel

**Purpose**: Display and manage active terminal sessions

**Features**:
- List of active terminal sessions with metadata
- Filter controls (by user, terminal type, activity)
- Session details view (process info, command, start time)
- Manual capture triggers for specific sessions
- Visual indicators for session activity level

**Location**:
- Route: `/monitoring/sessions`
- Template: `/src/app/presentation/templates/monitoring/sessions.html`
- Partial: `/src/app/presentation/templates/partials/session_card.html`

### 3. Monitoring Configuration Panel

**Purpose**: Allow users to configure monitoring parameters

**Features**:
- Scan interval settings
- Buffer size configuration
- User filtering options
- Project context settings
- Auto-capture configuration

**Location**:
- Route: `/monitoring/config`
- Template: `/src/app/presentation/templates/monitoring/config.html`

### 4. Status Indicators

**Purpose**: Provide at-a-glance monitoring status throughout the application

**Features**:
- Monitoring status indicator (green/red)
- Active session count
- Last capture timestamp
- Quick access to start/stop controls

**Location**:
- Partial: `/src/app/presentation/templates/partials/monitor_status.html`
- Integrated into main navigation and dashboard

### 5. Statistics and Visualizations

**Purpose**: Visualize monitoring performance and activity

**Features**:
- Capture rate over time chart
- Session duration distribution
- Conversation length metrics
- Success/failure ratios
- Terminal activity heatmap

**Location**:
- Route: `/monitoring/stats`
- Template: `/src/app/presentation/templates/monitoring/stats.html`

## API Endpoints

The following API endpoints will be needed to support the frontend:

1. **GET `/api/monitors/status`**
   - Returns current monitoring status and summary statistics
   - Response includes: active status, uptime, monitor count, session count, capture count

2. **POST `/api/monitors/start`**
   - Starts a new monitoring session
   - Parameters: scan interval, buffer size, user filters
   - Returns: monitor ID and initial status

3. **POST `/api/monitors/stop/{monitor_id}`**
   - Stops a specific monitoring session
   - Returns: confirmation and final statistics

4. **GET `/api/monitors/sessions`**
   - Lists all active terminal sessions
   - Optional query parameters for filtering
   - Returns: session list with metadata

5. **POST `/api/monitors/capture/{session_id}`**
   - Triggers immediate capture for a specific session
   - Returns: capture results or status

6. **GET/PUT `/api/monitors/config`**
   - Gets or updates monitoring configuration
   - Parameters: all configurable monitoring options
   - Returns: current configuration after changes

7. **GET `/api/monitors/stats`**
   - Returns detailed monitoring statistics for visualization
   - Optional time range parameters
   - Returns: time series data and aggregate metrics

8. **GET `/api/monitors/sessions/{session_id}/conversations`**
   - Lists conversations captured from a specific session
   - Returns: conversation list with metadata

## Technical Implementation

### Real-time Updates

To ensure the UI stays updated with the latest monitoring status:

1. **HTMX Integration**:
   - Use HTMX for partial page updates without full reload
   - Implement polling for status updates (every 5-10 seconds)
   - Use event-triggered updates for user actions

2. **WebSockets** (optional future enhancement):
   - Implement WebSockets for real-time status updates
   - Push notifications for new captures and sessions

### UI Components

The following UI components will be needed:

1. **Status Cards**:
   - Visual indicators for monitoring status
   - Key metrics with counters
   - Start/stop action buttons

2. **Session List**:
   - Sortable, filterable table of sessions
   - Expandable details panel
   - Action buttons for each session

3. **Configuration Form**:
   - Input controls for all configurable parameters
   - Validation and feedback
   - Save/reset buttons

4. **Charts and Visualizations**:
   - Time series charts for capture metrics
   - Distribution charts for session data
   - Activity visualization

### Integration with Existing UI

Integration with the existing application UI:

1. **Navigation**:
   - Add "Monitoring" section to main navigation
   - Include status indicator in nav bar

2. **Dashboard Integration**:
   - Add monitoring status card to main dashboard
   - Include quick-access monitoring controls

3. **Prompt List Integration**:
   - Add terminal session source indicator to prompt list
   - Filter controls for terminal-sourced prompts

## Implementation Phases

### Phase 1: Core Monitoring Controls

1. Implement basic monitoring status endpoint
2. Create start/stop monitoring controls
3. Develop status indicator components
4. Implement basic monitoring dashboard

### Phase 2: Session Management

1. Implement session listing and details view
2. Add manual capture controls
3. Create session filtering and sorting
4. Develop session metadata display

### Phase 3: Configuration and Statistics

1. Implement configuration panel
2. Add basic statistics displays
3. Create visual charts for monitoring metrics
4. Implement export functionality for stats

### Phase 4: Advanced Features and Refinement

1. Add real-time updates via WebSockets
2. Implement advanced filtering and search
3. Create detailed activity timeline
4. Add user preferences and saved configurations

## UI/UX Considerations

### Usability

- Ensure controls are intuitive and discoverable
- Provide tooltips and help text for complex features
- Use consistent visual language for status indicators
- Implement responsive design for various screen sizes

### Performance

- Optimize API responses for quick rendering
- Implement efficient polling strategies
- Use pagination for large session lists
- Lazy-load visualizations and heavy components

### Error Handling

- Provide clear error messages for failed operations
- Implement automatic retry for temporary failures
- Show status recovery options for users
- Maintain monitoring state during page navigation

## Security Considerations

- Implement proper input validation for all parameters
- Use CSRF protection for all POST endpoints
- Rate-limit API requests to prevent abuse
- Ensure proper authentication for all monitoring controls

## Testing Strategy

- Create unit tests for all API endpoints
- Implement integration tests for UI components
- Develop end-to-end tests for monitoring workflows
- Test performance under various load conditions

## Documentation

- Create user documentation for monitoring features
- Document API endpoints for developers
- Include configuration guide for system administrators
- Provide troubleshooting section for common issues

## Dependencies

- HTMX for dynamic content updates
- Chart.js or similar for data visualization
- CSS framework for responsive design (already in use)
- Fast API for backend endpoints (already in use)

## Next Steps

After approval of this plan, implementation will proceed in the order outlined in the phases above, with regular reviews and adjustments as needed.