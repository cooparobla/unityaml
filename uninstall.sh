#!/bin/bash
set -e

echo "=== Uninstalling UnityYAML ==="

export PATH="$HOME/.local/bin:$PATH"
export UV_TOOL_BIN_DIR="${UV_TOOL_BIN_DIR:-$HOME/.local/bin}"

if command -v uv &> /dev/null; then
    echo "Uninstalling unityaml tool via uv..."
    uv tool uninstall unityaml || true
fi

echo "============================================="
echo "UnityYAML tool uninstalled!"
echo "Note: User configuration in ~/.unityaml/ was preserved."
echo "============================================="
