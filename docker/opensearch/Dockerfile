# OpenSearch for Railway deployment
# Use platform-specific image for M1/M2 Macs
FROM --platform=linux/amd64 opensearchproject/opensearch:2.11.0

# Disable security for development (enable in production with proper certs)
ENV discovery.type=single-node
ENV plugins.security.disabled=true
ENV OPENSEARCH_JAVA_OPTS="-Xms1g -Xmx1g"
ENV bootstrap.memory_lock=true

# Performance tuning for Railway
ENV cluster.name=legal-research-cluster
ENV node.name=legal-research-node
ENV network.host=0.0.0.0
ENV http.port=9200

# Enable CORS for frontend access
ENV http.cors.enabled=true
ENV http.cors.allow-origin="*"
ENV http.cors.allow-headers="X-Requested-With,Content-Type,Content-Length,Authorization"

# Install useful plugins
RUN opensearch-plugin install -b analysis-phonetic
RUN opensearch-plugin install -b analysis-icu

EXPOSE 9200 9300

HEALTHCHECK --interval=30s --timeout=3s --start-period=45s \
  CMD curl -f http://localhost:9200/_cluster/health || exit 1