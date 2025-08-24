#!/bin/bash

# Script to decrypt the update-key.conf file using SOPS
# Usage: ./scripts/decrypt-update-key.sh

set -e

# Check if SOPS is installed
if ! command -v sops &> /dev/null; then
    echo "Error: SOPS is not installed. Please install it first:"
    echo "  brew install sops"
    exit 1
fi

# Check if age key exists
if [ ! -f ".age-key" ]; then
    echo "Error: Age private key not found. Please ensure .age-key exists in the project root."
    exit 1
fi

# Decrypt the file
echo "Decrypting bind/update-key.conf..."
SOPS_AGE_KEY_FILE=.age-key sops -d -i bind/update-key.conf

echo "File decrypted successfully!"
echo "Note: The file is now in plain text. Remember to re-encrypt it after making changes:"
echo "  sops -e -i bind/update-key.conf"
