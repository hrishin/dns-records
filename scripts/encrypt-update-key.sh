#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$0")
source "$SCRIPT_DIR/lib/sops-checks.sh"

check_sops
check_age_key

function encrypt_update_key() {
    echo "Encrypting bind/update-key.conf..."
    sops -e -i bind/update-key.conf || true

    echo "File encrypted successfully"
}

encrypt_update_key
