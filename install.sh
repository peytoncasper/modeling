#!/usr/bin/env bash
set -euo pipefail

# ── Fusion MCP Bridge installer ──────────────────────────────
#
# Syncs the bridge add-in into Fusion 360's AddIns directory,
# makes the CLI tools executable, and optionally symlinks them
# into a directory on PATH.
#
# Usage:
#   ./install.sh              # install add-in + make CLIs executable
#   ./install.sh --link       # also symlink CLIs into ~/.local/bin
#   ./install.sh --uninstall  # remove the add-in from Fusion

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADDIN_SRC="$SCRIPT_DIR/fusion-addin"
TOOLS_SRC="$SCRIPT_DIR/tools"
ADDIN_NAME="FusionMCPBridge"
LINK_DIR="$HOME/.local/bin"

# ── Detect Fusion AddIns directory ────────────────────────────

detect_addins_dir() {
    local candidates=(
        "$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns"
        "$HOME/Library/Application Support/Autodesk/Autodesk Fusion/API/AddIns"
        "${APPDATA:-__none__}/Autodesk/Autodesk Fusion 360/API/AddIns"
        "${APPDATA:-__none__}/Autodesk/Autodesk Fusion/API/AddIns"
    )
    for dir in "${candidates[@]}"; do
        if [[ -d "$dir" ]]; then
            echo "$dir"
            return 0
        fi
    done
    return 1
}

# ── Sync add-in files ─────────────────────────────────────────

install_addin() {
    local addins_dir
    if ! addins_dir="$(detect_addins_dir)"; then
        echo "ERROR: Could not find Fusion 360 AddIns directory."
        echo "       Is Fusion 360 installed?"
        echo ""
        echo "Expected one of:"
        echo "  macOS:   ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns"
        echo "  Windows: %APPDATA%/Autodesk/Autodesk Fusion 360/API/AddIns"
        exit 1
    fi

    local dest="$addins_dir/$ADDIN_NAME"
    echo "Source:  $ADDIN_SRC"
    echo "Target:  $dest"
    echo ""

    mkdir -p "$dest"

    # Clear stale bytecode
    rm -rf "$dest/__pycache__"

    # Sync Python files + manifest (skip .bak files)
    local count=0
    for f in "$ADDIN_SRC"/*.py "$ADDIN_SRC"/*.manifest; do
        [[ ! -f "$f" ]] && continue
        local base
        base="$(basename "$f")"
        # Skip backup files
        [[ "$base" == *.bak ]] && continue
        cp "$f" "$dest/$base"
        echo "  copied  $base"
        ((count++))
    done

    echo ""
    echo "Installed $count files into $dest"
}

# ── Make CLIs executable + optional symlink ───────────────────

install_tools() {
    local do_link="${1:-false}"

    if [[ ! -d "$TOOLS_SRC" ]]; then
        echo "No tools/ directory found — skipping CLI setup."
        return
    fi

    echo ""
    echo "Setting up CLI tools..."

    for tool in "$TOOLS_SRC"/*; do
        [[ ! -f "$tool" ]] && continue
        chmod +x "$tool"
        local name
        name="$(basename "$tool")"
        echo "  chmod +x  tools/$name"

        if [[ "$do_link" == "true" ]]; then
            mkdir -p "$LINK_DIR"
            ln -sf "$tool" "$LINK_DIR/$name"
            echo "  symlinked $LINK_DIR/$name → tools/$name"
        fi
    done

    if [[ "$do_link" == "true" ]]; then
        echo ""
        if [[ ":$PATH:" != *":$LINK_DIR:"* ]]; then
            echo "NOTE: $LINK_DIR is not on your PATH."
            echo "      Add this to your shell profile:"
            echo "        export PATH=\"$LINK_DIR:\$PATH\""
        else
            echo "CLIs available on PATH."
        fi
    else
        echo ""
        echo "Run CLIs directly:   tools/fusion-sketch list"
        echo "Or re-run with:      ./install.sh --link"
        echo "  to symlink into $LINK_DIR"
    fi
}

# ── Uninstall ─────────────────────────────────────────────────

uninstall() {
    local addins_dir
    if ! addins_dir="$(detect_addins_dir)"; then
        echo "Fusion AddIns directory not found — nothing to uninstall."
        exit 0
    fi

    local dest="$addins_dir/$ADDIN_NAME"
    if [[ ! -d "$dest" ]]; then
        echo "Add-in not installed at $dest"
        exit 0
    fi

    echo "Removing $dest ..."
    rm -rf "$dest"
    echo "Add-in removed."

    # Remove CLI symlinks
    if [[ -d "$LINK_DIR" ]]; then
        for tool in "$TOOLS_SRC"/*; do
            [[ ! -f "$tool" ]] && continue
            local name
            name="$(basename "$tool")"
            if [[ -L "$LINK_DIR/$name" ]]; then
                rm "$LINK_DIR/$name"
                echo "Removed symlink $LINK_DIR/$name"
            fi
        done
    fi

    echo "Done."
}

# ── Main ──────────────────────────────────────────────────────

main() {
    echo "╔══════════════════════════════════════╗"
    echo "║   Fusion MCP Bridge Installer        ║"
    echo "╚══════════════════════════════════════╝"
    echo ""

    case "${1:-}" in
        --uninstall)
            uninstall
            ;;
        --link)
            install_addin
            install_tools true
            echo ""
            echo "Done. Restart Fusion 360 and enable '$ADDIN_NAME' in Add-Ins."
            ;;
        --help|-h)
            echo "Usage:"
            echo "  ./install.sh              Install add-in, make CLIs executable"
            echo "  ./install.sh --link       Also symlink CLIs into ~/.local/bin"
            echo "  ./install.sh --uninstall  Remove add-in and symlinks"
            ;;
        "")
            install_addin
            install_tools false
            echo ""
            echo "Done. Restart Fusion 360 and enable '$ADDIN_NAME' in Add-Ins."
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run ./install.sh --help for usage."
            exit 1
            ;;
    esac
}

main "$@"
