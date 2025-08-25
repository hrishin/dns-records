#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$0")
source "$SCRIPT_DIR/lib/sops-checks.sh"

check_sops
check_age_key

function encrypt_update_key() {
    # Encrypt the file
    echo "Encrypting bind/update-key.conf..."
    SOPS_AGE_KEY_FILE=.age-key sops -e -i bind/update-key.conf

    echo "File encrypted successfully!"
}

encrypt_update_key
