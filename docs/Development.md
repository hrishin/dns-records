# Development Guide

This document provides comprehensive instructions for developing, testing, and running the DNS Records Manager locally.

## Prerequisites

Before you start developing, ensure you have the following installed:

- **Python 3.8+**
- **SOPS**: `brew install sops` (macOS) or `snap install sops` (Linux)
- **Age**: `brew install age` (macOS) or `snap install age` (Linux)
- **GNU Make**
- **Docker/Podman** (for running the BIND DNS server container locally)
- **Git**

## Development Environment Setup

### 1. Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd dns-records-manager

# Install dependencies
make install
. venv/bin/activate
```

### 2. Development Environment Configuration

```bash
# Setup development environment (installs dev dependencies and creates config)
make setup-dev

# This will:
# - Install all development dependencies
# - Install the package in development mode
# - Copy config.example.yaml to config.yaml
```

### 3. Configuration

Edit `configs/config.yaml` with your local default settings:

```yaml
dns_providers:
  mock:
  
  bind:
    nameserver: "127.0.0.1"
    port: 53
    key_file: "/etc/bind/rndc.key"
    key_name: "rndc-key"
    zone_file: "/etc/bind/zones/ib.bigbank.com.zone"

default_provider: mock  # Use mock for local development
logging:
  level: DEBUG
  file: "dns_manager.log"
```

## Development Workflow

### 1. Code Quality

```bash
# Format code with black
make format

# Run linting checks
make lint

# Check dependency versions
make check-deps
```

### 2. Testing

```bash
# Run all tests
make test

# Run integration tests only
make test-integration

# Clean test artifacts
make test-clean
```

### 3. Building and Installation

```bash
# Build the package
make build

# Install package in development mode
make install-package

# Install development dependencies
make install-dev

# Uninstall package
make uninstall
```

## Running Demos Locally

### 1. Demo with Mock DNS Server (Recommended for Development)

The mock DNS server is perfect for local development and testing as it doesn't require external services.

#### Dry Run Demo
```bash
# Run demo in dry-run mode (no actual changes)
make demo-dry-run

# This will:
# - Parse input.csv
# - Validate DNS records
# - Show what changes would be made
# - Use mock DNS provider (safe for development)
```

#### Live Demo
```bash
# Run demo in live mode (actual changes to mock server)
make demo-live

# This will:
# - Parse input.csv
# - Apply actual DNS record changes
# - Use mock DNS provider (changes are in-memory only)
```


### 2. Demo with BIND DNS Server (Production-like Environment)

For testing against a real DNS server locally:


### Working with Encrypted Files

> **Note:**  
> `update-key.conf` contains the authentication key used to securely update the local BIND server. It must be decrypted before making live changes or running integration tests.
The `update-key.conf` file is required for authenticating updates to the local BIND server. By default, it should be located at `bind/update-key.conf`.

If you do not have an `update-key.conf` file (for example, when setting up a new development or test environment), you can generate a test key using the following command:

To use SOPS with age encryption for managing secrets (such as `update-key.conf`), you need to generate an age key pair and set the appropriate environment variable so SOPS can find your private key.

#### 1. Generate an age key pair

```bash
# Generate a new age key pair
age-keygen -o .age-key

# This creates:
# - .age-key (private key - keep this secret!)
# - Public key will be displayed in the terminal
```

#### 2. Set the SOPS age key environment variable

```bash
# Set the environment variable to point to your private key
export SOPS_AGE_KEY_FILE="$(pwd)/.age-key"

# Add to your shell profile for persistence
echo 'export SOPS_AGE_KEY_FILE="$(pwd)/.age-key"' >> ~/.bashrc
# Or for zsh:
echo 'export SOPS_AGE_KEY_FILE="$(pwd)/.age-key"' >> ~/.zshrc

# Verify the environment variable is set
echo $SOPS_AGE_KEY_FILE
```

#### 3. Configure SOPS for the project

Create or update `.sops.yaml` in your project root:

```yaml
creation_rules:
  - path_regex: \.conf$
    age: >-
      age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfj9pqyac8tk
      # Replace with your actual public key from step 1
```

### 4. Decrypting for Editing

```bash
# Decrypt update-key.conf for editing
make decrypt-key

# Edit the decrypted file
vim bind/update-key.conf
```

### 5. Re-encrypting After Changes

```bash
# Re-encrypt after making changes
make encrypt-key
```

#### Setup BIND Server
```bash
# Setup and start BIND DNS server container
make bind-setup

# Check BIND server statuste
make bind-status

# View BIND server logs
make bind-logs
```

#### Run Against BIND
```bash
# Dry run against BIND server
make run-dry-run

# Live run against BIND server (WARNING: actual changes)
make run-live
```

#### BIND Management
```bash
# Stop BIND server
make bind-stop

# Start BIND server
make bind-start

# Rebuild BIND container
make bind-rebuild

# Clean up BIND container
make bind-clean
```

## Testing

### 1. Integration Tests

> **Note:**  
> Integration tests run against an existing BIND server instance, which must be running and accessible. The integration environment uses the `test.bigbank.com` zone for testing. The BIND server image is built from this repository and is hosted on AWS for CI and remote testing purposes on 44.216.94.190 endpoint port 53.

```bash
# Run integration tests (requires decrypted update-key.conf)
make test-integration

# This will:
# - Decrypt update-key.conf
# - Run behave integration tests
# - Re-encrypt update-key.conf after completion
```

### 3. Manual Testing

```bash
# Test DNS resolution (if BIND is running)
make bind-test

# Test with custom CSV file
python main.py --csv test_data/test.csv --config configs/config.yaml --zone test.bigbank.com --dry-run
```

## Development Tips

### 1. Using Mock Provider for Development

The mock provider is ideal for development because:
- No external dependencies
- Fast execution
- Safe for testing
- In-memory changes (resets on restart)

### 2. Debugging

```bash
# Enable debug logging in config.yaml
logging:
  level: DEBUG

# Run with verbose output
python main.py --csv input.csv --config configs/config.yaml --zone ib.bigbank.com --verbose --dry-run
```

### 3. Testing Different Scenarios

```bash
# Test with different zones
python main.py --csv input.csv --config configs/config.yaml --zone test.bigbank.com --dry-run

# Test with different configs
python main.py --csv input.csv --config configs/config_mock.yaml --zone ib.bigbank.com --dry-run
```

## Troubleshooting

### 1. Common Issues

#### Virtual Environment Issues
```bash
# If venv activation fails
deactivate  # Deactivate any active environment
rm -rf venv  # Remove corrupted venv
make install  # Recreate and setup
```

#### Dependency Issues
```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Check for conflicts
pip check
```

#### BIND Container Issues
```bash
# Check container status
docker ps -a | grep bind-dns-server

# View container logs
docker logs bind-dns-server

# Rebuild container
make bind-rebuild
```

### 2. Log Files

Check these log files for debugging:
- `dns_manager.log` - Main application logs
- Docker logs for BIND container
- Test output in `test_reports/`

## Contributing

### 1. Before Submitting Changes

```bash
# Ensure all tests pass
make test

# Check code quality
make lint
make format

# Verify demo works
make demo-dry-run
```

### 2. Testing Your Changes

```bash
# Test with mock provider
make demo-dry-run

# Test with BIND provider (if available)
make run-dry-run

# Run integration tests
make test-integration
```

## Next Steps

- Review the [Architecture section](../README.md#architecture) in the main README
- Check the [Makefile](../Makefile) for all available targets
- Explore the [test files](../features/) for examples
- Review the [configuration examples](../configs/) for different setups

For questions or issues, please refer to the main project documentation or create an issue in the repository.
