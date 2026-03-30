# Greenmask Dockerfile for Netbox anonymization
FROM greenmask/greenmask:latest

# Switch to root to install files
USER root

# Create directories for configuration and mappings
RUN mkdir -p /config /mappings /scripts

# Copy Greenmask configuration
# Using greenmask-config-v2.yml (compatible with v0.2.17)
COPY greenmask-config-v2.yml /config/greenmask-config.yml

# Copy execution scripts
COPY run_greenmask_v3.sh /scripts/run_greenmask.sh
RUN chmod +x /scripts/run_greenmask.sh

# Set working directory
WORKDIR /scripts

# Default entrypoint - can be overridden for manual execution
ENTRYPOINT ["/bin/bash"]
CMD ["/scripts/run_greenmask.sh"]