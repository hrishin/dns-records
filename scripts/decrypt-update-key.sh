#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$0")
source "$SCRIPT_DIR/lib/sops-checks.sh"

check_sops
check_age_key

function decrypt_update_key() {
    echo "Decrypting bind/update-key.conf..."
    sops -d -i bind/update-key.conf || true

    echo "File decrypted successfully"
    echo "Note: The file is now in plain text. Remember to re-encrypt it after making changes:"
    echo "  sops -e -i bind/update-key.conf"
}

decrypt_update_key
