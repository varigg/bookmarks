#!/usr/bin/env bash
# Import existing bookmarks.js into Docker volume

set -e

BOOKMARKS_FILE="${1:-bookmarks.js}"
VOLUME_NAME="bookmarks_bookmarks_data"

if [ ! -f "$BOOKMARKS_FILE" ]; then
    echo "❌ Error: File '$BOOKMARKS_FILE' not found"
    echo ""
    echo "Usage: $0 [path/to/bookmarks.js]"
    echo ""
    echo "Example:"
    echo "  $0 bookmarks.js"
    echo "  $0 ~/backup/bookmarks.js"
    exit 1
fi

echo "📦 Importing bookmarks into Docker volume..."
echo "   Source: $BOOKMARKS_FILE"
echo "   Volume: $VOLUME_NAME"
echo ""

# Copy file into the volume using a temporary container
docker run --rm \
    -v "${VOLUME_NAME}:/data" \
    -v "$(pwd):/host" \
    alpine \
    cp "/host/$BOOKMARKS_FILE" /data/bookmarks.js

echo "✅ Import complete!"
echo ""
echo "Restart the service to load the new bookmarks:"
echo "  docker compose restart"
