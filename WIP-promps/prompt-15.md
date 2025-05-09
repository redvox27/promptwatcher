# Prompt 15

## User Prompt
now im having this error ERROR: setting [plugins.security.disabled] already set, saw [true] and [true]

## Assistant Response
I've identified and fixed the duplicate setting issue in the docker-compose.yml file.

The error "ERROR: setting [plugins.security.disabled] already set, saw [true] and [true]" occurs because we had both:
- A direct setting of `plugins.security.disabled=true` in the environment variables
- The `DISABLE_SECURITY_PLUGIN=true` environment variable, which also sets `plugins.security.disabled=true` internally

I've updated the docker-compose.yml file to remove the duplicate setting by:
- Keeping only the `DISABLE_SECURITY_PLUGIN=true` environment variable
- Removing the explicit `plugins.security.disabled=true` setting

This should resolve the conflict and allow OpenSearch to start properly. The security plugin will still be disabled, but now there won't be duplicate configurations causing errors.

This is a common issue when working with OpenSearch containers because some environment variables internally set other configuration values, leading to these kinds of conflicts.