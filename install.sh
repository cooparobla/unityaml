#!/bin/bash
set -e

echo "=== Installing UnityYAML ==="

# 1. Check if uv is installed, download and install it if not
if ! command -v uv &> /dev/null && [ ! -f "$HOME/.local/bin/uv" ]; then
    echo "Installing uv (fast python package installer)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Ensure ~/.local/bin is in execution PATH for this session
export PATH="$HOME/.local/bin:$PATH"

# 2. Install unityaml as an editable tool using uv
echo "Installing unityaml CLI and GUI tools..."
uv tool install --editable . --force

# Ensure ~/.local/bin is in PATH for future shell sessions
if [ -f "$HOME/.bashrc" ] && ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$HOME/.bashrc" && [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo "Added $HOME/.local/bin to ~/.bashrc"
fi

echo "============================================="
echo "Installation complete!"
echo "You can now run:"
echo "  unityaml         # Open the PySide6 file explorer GUI"
echo "============================================="
