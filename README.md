# DNS Records Manager

[![PR Dry-Run](https://github.com/{owner}/{repo}/workflows/DNS%20Records%20Manager%20PR%20Dry-Run/badge.svg)](https://github.com/{owner}/{repo}/actions/workflows/pr-dry-run.yml)

## Overview

The DNS Records Manager is a comprehensive, enterprise-grade automation solution for managing DNS records in the `ib.bigbank.com` zone. 
The system provides idempotent, safe, and auditable DNS record management through CSV file input, ensuring that even 
small mistakes in DNS records cannot have significant consequences.

## Key Features

### Safety & Reliability
- **Idempotent Operations**: Only updates records that have actually changed
- **Zone Protection**: Never modifies records outside the specified zone
- **Dry Run Mode**: Preview all changes before applying them
- **Comprehensive Validation**: FQDN and IPv4 format validation
- **Rollback Support**: Ability to revert changes if needed

### Automation & Efficiency
- **CSV Input Processing**: Simple CSV format with FQDN and IPv4 columns
- **Batch Operations**: Process multiple records efficiently
- **Change Analysis**: Intelligent detection of what needs to be created, updated, or deleted
- **Progress Tracking**: Real-time progress indicators and detailed logging

### Multi DNS Provider Support
- **BIND**: Traditional DNS server integration using dig and nsupdate
- **Mock Provider**: Safe testing and demonstration without affecting production
- **Extensible Architecture**: Easy to add new DNS providers

### Monitoring & Audit
- **Comprehensive Logging**: Detailed audit trail of all operations
- **Change Impact Analysis**: Risk assessment and affected services identification
- **Performance Metrics**: API response times and operation statistics
- **Health Checks**: System health monitoring and alerting

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DNS Records Manager                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │   CSV Parser    │    │  Record Manager │    │     DNS Client          │  │
│  │                 │    │                 │    │                         │  │
│  │ • Parse CSV     │───▶│ • Analyze       │───▶│ • Unified Interface     │  │
│  │ • Validate      │    │   Changes       │    │ • Provider Selection    │  │
│  │ • Sanitize      │    │ • Zone Safety   │    │ • Error Handling        │  │
│  │                 │    │ • Idempotency   │    │                         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
│           │                       │                       │                 │
│           │                       │                       │                 │
│           ▼                       ▼                       ▼                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │   Validators    │    │  Change Impact  │    │   DNS Providers         │  │
│  │                 │    │   Analysis      │    │                         │  │
│  │ • FQDN          │    │ • Risk Level    │    │ • BIND (Traditional)    │  │
│  │ • IPv4          │    │ • Affected      │    │ • Mock (Testing)        │  │
│  │ • CSV Structure │    │   Services      │    │ • AWS R53(extendible)   │  │
│  │                 │    │ • Rollback      │    │                         │  │
│  │                 │    │                 │    │                         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Input Format

The system accepts a simple CSV file with the exact structure specified in the requirements:

```csv
FQDN,IPv4
machine1.mgmt.ib.bigbank.com,172.16.1.50
machine1.ipmi.ib.bigbank.com,172.16.20.50
db.ib.bigbank.com,10.33.0.50
netapp1.svm.ib.bigbank.com,192.168.47.11
```

## How It Works

### 1. CSV Processing
- Validates CSV structure and content
- Ensures FQDN and IPv4 format compliance
- Handles edge cases and provides clear error messages

### 2. Change Analysis
- Compares current DNS state with desired state
- Identifies records to create, update, or delete
- Ensures zone boundary safety

### 3. Idempotent Operations
- **Create**: Only if record doesn't exist
- **Update**: Only if IP address changed
- **Delete**: Only if FQDN removed from desired state
- **No Change**: Skip if identical

### 4. Safe Execution
- Dry-run mode for preview
- Comprehensive logging and audit trail

## Encrypted Configuration Files

The `bind/update-key.conf` file contains sensitive DNS update keys and is encrypted using SOPS with age encryption for security.

### Prerequisites
- **SOPS**: Install with `brew install sops`
- **Age**: Install with `brew install age`

### Working with Encrypted Files

#### Decrypt for editing:
```bash
./scripts/decrypt-update-key.sh
```

#### Re-encrypt after changes:
```bash
./scripts/encrypt-update-key.sh
```

#### Manual operations:
```bash
# Decrypt
SOPS_AGE_KEY_FILE=.age-key sops -d -i bind/update-key.conf

# Encrypt
SOPS_AGE_KEY_FILE=.age-key sops -e -i bind/update-key.conf
```

### Security Notes
- The private age key (`.age-key`) is automatically added to `.gitignore`
- Never commit the private key to version control
- The public key is stored in `.sops.yaml` for team collaboration
- All team members can decrypt using their own age keys


### Prerequisites
- Python 3.8+
- Access to DNS provider API (BIND)
- Required environment variables or configuration files

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd dns-records-manager

# Install dependencies
pip install -r requirements.txt

# Configure your DNS provider credentials
cp configs/config.example.yaml configs/config.yaml
# Edit configs/config.yaml with your settings
```

### Usage

The DNS Records Manager can be run in several ways:

#### Method 1: Direct Python execution
```bash
# Process a CSV file
python main.py --csv input.csv --zone ib.bigbank.com

# Dry run to preview changes
python main.py --csv input.csv --zone ib.bigbank.com --dry-run

# Dry run with output saved to file
python main.py --csv input.csv --zone ib.bigbank.com --dry-run --output-file changes.txt

# Use custom configuration file
python main.py --csv input.csv --zone ib.bigbank.com --config my-config.yaml

# Enable verbose logging
python main.py --csv input.csv --zone ib.bigbank.com --verbose
```

#### Method 2: After installation (recommended)
```bash
# Install the package
pip install -e .

# Use the installed command
dns-manager --csv input.csv --zone ib.bigbank.com

# Dry run to preview changes
dns-manager --csv input.csv --zone ib.bigbank.com --dry-run

# Dry run with output saved to file
dns-manager --csv input.csv --zone ib.bigbank.com --dry-run --output-file changes.txt
```

#### CLI Options
- `--csv, -f`: CSV file containing DNS records (required)
- `--zone, -z`: DNS zone to manage (required)
- `--config, -c`: Configuration file path (default: configs/config.yaml)
- `--dry-run`: Show what would be changed without making changes
- `--verbose, -v`: Enable verbose logging

## Configuration

Create a `config.yaml` file with your DNS provider settings:

```yaml
dns_providers:
  bind:
    nameserver: 192.168.1.10  # BIND server IP address
    port: 53                  # DNS port (default: 53)
    key_file: /etc/bind/rndc.key  # Optional: RNDC key file for authenticated updates
    key_name: rndc-key        # Optional: Key name for authenticated updates
    zone_file: /etc/bind/zones/ib.bigbank.com.zone  # Optional: Zone file path

default_provider: bind
logging:
  level: INFO
  file: dns_manager.log
```

## Security Features

### Authentication & Authorization
- BIND key-based authentication

### Data Protection
- Secure credential storage using sops
- Environment variable support

### Compliance & Audit
- Change tracking and documentation
- Security audit trails

## Future Enhancements

### Advanced DNS Features
- DNSSEC support
- Geographic routing
- Load balancing integration
- Traffic management policies
- Backup DNS records for resiliecny - periodic or on-demaond

### Integration Capabilities
- Rest API Service to manage the DNS entires
- Configuration management tools (Ansible)
- CLI or bash scripting
- Monitoring systems (Prometheus, Grafana)


## Summary
The system successfully addresses the core requirements:
- Automated DNS record management
- CSV input processing
- Idempotent operations
- Safe zone management
- Comprehensive logging and audit
- Multiple DNS provider support(extensible)
- CI/CD automation flow
