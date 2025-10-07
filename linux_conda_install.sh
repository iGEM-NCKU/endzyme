#!/usr/bin/env bash
# ==========================================
# Conda Auto Installer Script
# Author: Richie
# Date: 2025/9/30
# ==========================================

# install location
INSTALL_PATH="/opt/conda"
REQ_FILE = "./enviroment.yml"
# Miniconda ver.
CONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"

# set root

if [ "$EUID" -ne 0 ]; then
  echo "❌ please use root user or sudo"
  exit 1
fi

echo "🚀 start  install Miniconda to : $INSTALL_PATH"

# temp folder
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR" || exit

# Download
echo "📦 Download Miniconda..."
wget -q "$CONDA_URL" -O miniconda.sh
if [ $? -ne 0 ]; then
  echo "❌ Please check your internet or URL"
  exit 1
fi

bash miniconda.sh -b -p "$INSTALL_PATH"
if [ $? -ne 0 ]; then
  echo "❌ install fail, unknown problem"
  exit 1
fi

# add PATH

echo "🔧 setting PATH..."
echo "export PATH=\"$INSTALL_PATH/bin:\$PATH\"" > /etc/profile.d/conda.sh
chmod +x /etc/profile.d/conda.sh

#restart
source /etc/profile.d/conda.sh

# check
if command -v conda &>/dev/null; then
  echo "Conda is successfull install in: $INSTALL_PATH"
  echo "Ver：$(conda --version)"
else
  echo "⚠️  conda not found"
fi

# clear
rm -rf "$TMP_DIR"
echo "delete all folder"

echo "fininsh process start create env"

"$INSTALL_PATH/bin/conda" conda env create -f $REQ_FILE



