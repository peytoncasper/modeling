#!/bin/bash
# Deploy Fusion 360 addin files from workspace to the Fusion AddIns directory.
# Run after editing handler/bridge files to sync changes before restarting the addin.

SRC="$(cd "$(dirname "$0")" && pwd)/fusion-addin"
DST="$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/FusionMCPBridge"

if [ ! -d "$DST" ]; then
    echo "ERROR: Addin directory not found at $DST"
    exit 1
fi

CHANGED=0
for f in "$SRC"/*.py "$SRC"/*.manifest; do
    [ -f "$f" ] || continue
    base="$(basename "$f")"
    if [ ! -f "$DST/$base" ] || ! diff -q "$f" "$DST/$base" > /dev/null 2>&1; then
        cp "$f" "$DST/$base"
        echo "  updated: $base"
        CHANGED=$((CHANGED + 1))
    fi
done

if [ "$CHANGED" -eq 0 ]; then
    echo "All files already up to date."
else
    echo "Deployed $CHANGED file(s)."
    # Auto hot-reload if the bridge is running (skip for FusionMCPBridge.py itself)
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/reload -X POST -H "Content-Type: application/json" -d '{}' 2>/dev/null | grep -q "200"; then
        echo "  Hot-reloaded successfully."
    else
        echo "  Hot-reload unavailable — restart the addin in Fusion 360."
    fi
fi
