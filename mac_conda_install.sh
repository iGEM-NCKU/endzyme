#!/usr/bin/env bash
# ==========================================
# Conda Auto Installer Script
# Author: Richie
# Date: 2025/9/30
# ==========================================

#!/usr/bin/env bash
set -euo pipefail

INSTALL_PATH="/opt/miniconda3"
ARCH="$(uname -m)"
case "$ARCH" in
  arm64)   CONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh" ;;
  x86_64)  CONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh" ;;
  *) echo "Unsupported CPU arch: $ARCH"; exit 1 ;;
esac

if [ "$EUID" -ne 0 ]; then
  echo "Please run with sudo/root so we can write /opt and /etc/paths.d"; exit 1
fi

echo "Downloading: $CONDA_URL"
TMP_DIR="$(mktemp -d)"
curl -fsSL "$CONDA_URL" -o "$TMP_DIR/miniconda.sh"

bash "$TMP_DIR/miniconda.sh" -b -p "$INSTALL_PATH"

mkdir -p /etc/paths.d
echo "$INSTALL_PATH/bin" > /etc/paths.d/conda

rm -rf "$TMP_DIR"
echo "Installed to: $INSTALL_PATH"
echo "Open a NEW Terminal (zsh) and run: conda --version"




