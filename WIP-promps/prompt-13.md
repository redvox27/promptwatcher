# Prompt 13

## User Prompt
I've made some slight adjustments to the docker-compose.yml which solved most of the issues for me. So please consider that with the next changes. Now i have the next error "failed with error: org.opensearch.performanceanalyzer.commons.config.ConfigFileException: java.io.FileNotFoundException: /usr/share/opensearch/config/opensearch-performance-analyzer/performance-analyzer.properties (No such file or directory). Disabling plugin."

think step-by-step on how to solve this

## Assistant Response
I've updated the docker-compose.yml file to fix the Performance Analyzer plugin error by adding the environment variable `DISABLE_PERFORMANCE_ANALYZER_AGENT_CLI=true`. 

This error occurs because OpenSearch is trying to load the Performance Analyzer plugin but can't find its configuration file. This plugin is a monitoring and troubleshooting tool for OpenSearch clusters, but we don't need it for our application.

By adding the `DISABLE_PERFORMANCE_ANALYZER_AGENT_CLI=true` environment variable, we're explicitly telling OpenSearch not to enable this plugin, which should prevent the error.

I also added the `DISABLE_INSTALL_DEMO_CONFIG=true` environment variable to ensure a clean configuration.

Try running:
```bash
docker-compose down -v
docker-compose up
```

This will ensure a clean restart of your containers with the new configuration. The Performance Analyzer error should no longer appear, allowing OpenSearch to start properly.