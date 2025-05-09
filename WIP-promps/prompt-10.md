# Prompt 10

## User Prompt
now solve the next issue "No custom admin password found. Please provide a password via the environment variable OPENSEARCH_INITIAL_ADMIN_PASSWORD."

## Assistant Response
I've fixed the OpenSearch admin password issue by updating the docker-compose.yml file with the following changes:

1. Added the missing `OPENSEARCH_INITIAL_ADMIN_PASSWORD` environment variable with a value of "admin"

2. Added additional security-related environment variables to ensure the security plugin is properly disabled:
   - `DISABLE_INSTALL_DEMO_CONFIG=true`
   - `DISABLE_SECURITY_PLUGIN=true`

These changes will resolve the password error message. The `OPENSEARCH_INITIAL_ADMIN_PASSWORD` is needed because newer versions of OpenSearch require setting an initial admin password, even when security is disabled.

The combination of these settings ensures that:
1. The security plugin is completely disabled
2. A default admin password is provided to satisfy the startup requirements
3. Demo configurations are not installed

Try running `docker-compose down` and then `docker-compose up` again to see if the issue is resolved.