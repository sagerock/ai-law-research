#!/bin/bash

# CourtListener Bulk Data Download Script
# Downloads essential bulk data files for initial import

set -e

# Configuration
DATA_DIR="${DATA_DIR:-./data/bulk}"
BASE_URL="https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/bulk-data"

# Create data directory
mkdir -p "$DATA_DIR"

echo "Starting CourtListener bulk data download..."
echo "Data directory: $DATA_DIR"

# Function to download file with resume support
download_file() {
    local filename=$1
    local description=$2

    echo ""
    echo "Downloading $description..."

    if [ -f "$DATA_DIR/$filename" ]; then
        echo "  File exists, checking for updates..."
        wget -c -P "$DATA_DIR" "$BASE_URL/$filename"
    else
        echo "  Downloading fresh copy..."
        wget -P "$DATA_DIR" "$BASE_URL/$filename"
    fi

    echo "  ✓ $description downloaded"
}

# Download files in order of importance/size

# 1. Courts (small, essential)
download_file "courts.csv.bz2" "Courts metadata"

# 2. Opinions (large, main content)
# Get latest opinions file - you may need to check actual filename
download_file "opinions-2024-01-01.csv.bz2" "Court opinions"

# 3. Clusters (for grouping related opinions)
download_file "clusters-2024-01-01.csv.bz2" "Opinion clusters"

# 4. Citations (for building citation graph)
download_file "citations-2024-01-01.csv.bz2" "Citation relationships"

# 5. Optional: Dockets (PACER data)
# download_file "dockets-2024-01-01.csv.bz2" "Docket information"

# 6. Optional: People/Judges
# download_file "people-2024-01-01.csv.bz2" "Judge information"

echo ""
echo "Download complete! Files saved to: $DATA_DIR"
echo ""
echo "File sizes:"
ls -lh "$DATA_DIR"/*.bz2

echo ""
echo "Next steps:"
echo "1. Run 'make import-bulk' to import data into database"
echo "2. Monitor progress in logs"
echo ""