# Prompt 8

## User Prompt
docker-compose up

## Assistant Response
It looks like you're starting the application with docker-compose. This will launch the containers defined in your docker-compose.yml file, including:

1. OpenSearch - The database for storing prompt records
2. OpenSearch Dashboards - Web interface for OpenSearch
3. API - The PromptWatcher application

The containers should start up, and you should be able to access:
- The PromptWatcher web interface at http://localhost:8000
- OpenSearch Dashboards at http://localhost:5601

The application now has static files properly configured, so you shouldn't see the warning about missing static files anymore. The CSS styles should be properly applied to the application interface.

If you encounter any issues, you can check the container logs that are displayed in your terminal, or use `docker-compose logs` to view them.