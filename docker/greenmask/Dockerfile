# Greenmask Dockerfile for Netbox anonymization
FROM greenmask/greenmask:latest

# Install additional dependencies if needed
RUN apk add --no-cache bash jq

# Create directories for configuration and mappings
RUN mkdir -p /config /mappings /scripts

# Copy Greenmask configuration
COPY greenmask-config-complete.yml /config/greenmask-config.yml

# Copy execution scripts
COPY run_greenmask.sh /scripts/run_greenmask.sh
RUN chmod +x /scripts/run_greenmask.sh

# Set working directory
WORKDIR /scripts

# Default entrypoint - can be overridden for manual execution
ENTRYPOINT ["/bin/bash"]
CMD ["/scripts/run_greenmask.sh"]