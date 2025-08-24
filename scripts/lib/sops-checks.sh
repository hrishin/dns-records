#!/bin/bash

set -e

function check_sops() {
    if ! command -v sops &> /dev/null; then
        echo "Error: SOPS is not installed. Please install it first:"
        echo "  brew install sops"
        exit 1
    fi
}

function check_age_key() {
    if [ -z "$AGE_KEY" ] && [ -z "$SOPS_AGE_KEY_FILE" ]; then
        echo "AGE_KEY or SOPS_AGE_KEY_FILE environment variable is not set"
        echo "Please set it with: export AGE_KEY='your-age-private-key'"
        echo "or"
        echo "export SOPS_AGE_KEY_FILE='path/to/your/.age-key'"
        exit 1
    fi
}
