#!/bin/bash

# Script to encrypt the update-key.conf file using SOPS
# Usage: ./scripts/encrypt-update-key.sh

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

# Encrypt the file
echo "Encrypting bind/update-key.conf..."
SOPS_AGE_KEY_FILE=.age-key sops -e -i bind/update-key.conf

echo "File encrypted successfully!"
echo "The file is now encrypted and safe to commit to version control."
