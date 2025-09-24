#!/bin/bash

# Run OpenSearch locally without Docker (for M1/M2 Macs)
echo "Starting OpenSearch locally..."

# Check if OpenSearch is already installed
if [ ! -d "opensearch-2.11.0" ]; then
    echo "Downloading OpenSearch..."
    curl -O https://artifacts.opensearch.org/releases/bundle/opensearch/2.11.0/opensearch-2.11.0-darwin-x64.tar.gz
    tar -xzf opensearch-2.11.0-darwin-x64.tar.gz
    rm opensearch-2.11.0-darwin-x64.tar.gz
fi

# Disable security for development
export OPENSEARCH_JAVA_OPTS="-Xms512m -Xmx512m"

cd opensearch-2.11.0

# Configure for development
cat > config/opensearch.yml << EOF
cluster.name: legal-research-cluster
node.name: legal-research-node
network.host: 0.0.0.0
http.port: 9200
discovery.type: single-node
plugins.security.disabled: true
http.cors.enabled: true
http.cors.allow-origin: "*"
EOF

# Start OpenSearch
./bin/opensearch