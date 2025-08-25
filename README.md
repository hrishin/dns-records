# DNS Records Manager

<p align="left">
  <a href="https://github.com/hriships/dns-records-manager/actions/workflows/main-deploy.yml">
    <img alt="Main Deploy Status" src="https://github.com/hriships/dns-records-manager/actions/workflows/main-deploy.yml/badge.svg">
  </a>

  <a href="https://github.com/hriships/dns-records-manager/actions/workflows/docker-publish.yml">
    <img alt="Docker Build Status" src="https://github.com/hriships/dns-records-manager/actions/workflows/docker-publish.yml/badge.svg">
  </a>
</p>


## Overview

A comprehensive, enterprise-grade automation solution for managing DNS records in the `ib.bigbank.com` zone. Provides idempotent, safe, and auditable DNS record management through CSV file input.

## Key Features

- **Idempotent Operations**: Only updates records that have actually changed
- **Zone Protection**: Never modifies records outside the specified zone
- **Dry Run Mode**: Preview all changes before applying them
- **CSV Input Processing**: Simple CSV format with FQDN and IPv4 columns
- **Multi Provider Support**: BIND, Mock provider, and extensible architecture
- **Comprehensive Logging**: Detailed audit trail of all operations

### Prerequisites
- Python 3.8+
- SOPS: `brew install sops`
- Age: `brew install age`

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd dns-records-manager
pip install -r requirements.txt

# Configure
cp configs/config.example.yaml configs/config.yaml
# Edit configs/config.yaml with your settings
```

### Basic Usage

```bash
# Process DNS records
python main.py --csv input.csv --zone ib.bigbank.com

# Preview changes (dry run)
python main.py --csv input.csv --zone ib.bigbank.com --dry-run

# Install and use as command
pip install -e .
dns-manager --csv input.csv --zone ib.bigbank.com
```

## Input Format

The system accepts a CSV file with FQDN and IPv4 columns:

```csv
FQDN,IPv4
machine1.mgmt.ib.bigbank.com,172.16.1.50
machine1.ipmi.ib.bigbank.com,172.16.20.50
db.ib.bigbank.com,10.33.0.50
netapp1.svm.ib.bigbank.com,192.168.47.11
```

## User Guide - Updating UP Addresses 

To update DNS records in the DNS system, follow the steps below:

### 1. Checkout the `main` branch and pull the latest ccode

To ensure you are working with the latest code before making changes, follow these steps:

1. **Checkout the `main` branch**  
   ```bash
   git checkout main
   ```

2. **Pull the latest changes from the remote repository**  
   ```bash
   git pull origin main
   ```

3. **Create a new branch for your update** 

   Replace `your-branch` with a descriptive branch name:
   ```bash
   git checkout -b your-branch
   ```

You are now ready to make changes to `input.csv` to make DNS records changes.


### 2. Modify the CSV File
Edit `input.csv` to reflect the new UP addresses:

User could Add, Edit or Delete records.

```csv
FQDN,IPv4
up1.ib.bigbank.com,192.168.1.100
up2.ib.bigbank.com,192.168.1.101
up3.ib.bigbank.com,192.168.1.102
```

### 3. Validate Changes
Run a dry-run to preview what will be updated:

```bash
python main.py --csv input.csv --zone ib.bigbank.com --dry-run
```

### 4. Apply Changes
Execute the updates commite the change to your branch,
raise the the pull requests.

#### Committing and Pushing Changes

1. **Stage your changes**  

   Make sure you have saved your edits to `input.csv` (and any other files you changed):

   ```bash
   git add input.csv
   ```

2. **Commit your changes**  
   Write a clear commit message describing your update:

   ```bash
   git commit -m "Update UP addresses in input.csv"
   ```

3. **Push your branch**  
   Push your branch to the remote repository (replace `your-branch` with your branch name):

   ```bash
   git push origin your-branch
   ```

4. **Open a Pull Request**  
   Go to your repository on GitHub and open a Pull Request (PR) from your branch to `main`.

5. **Wait for CI checks**  
   The CI will automatically run a dry-run and show the results in your PR. If only `input.csv` was changed.

    Following is an example of change output.
    <br>
    ![Dry-run PR Example](docs/images/1-dry-run-pr.png)
    <br>

6. **Merge after review**  
   Once your PR is approved and checks pass, merge it to apply the DNS changes.

   You can view the deployment workflow here: [Main Deploy GitHub Action](.github/workflows/main-deploy.yml)


### 5. Verify Updates
Check that the DNS records have been updated correctly:

```bash
dig up1.ib.bigbank.com
dig up2.ib.bigbank.com
```

## Configuration

Create a `config.yaml` file with your DNS provider settings:

```yaml
dns_providers:
  bind:
    nameserver: 192.168.1.10
    port: 53
    key_file: /etc/bind/rndc.key
    key_name: rndc-key
    zone_file: /etc/bind/zones/ib.bigbank.com.zone

default_provider: bind
logging:
  level: INFO
  file: dns_manager.log
```

## Encrypted Configuration

The `bind/update-key.conf` file is encrypted using SOPS with age encryption.

### Working with Encrypted Files

```bash
# Decrypt for editing
./scripts/decrypt-update-key.sh

# Re-encrypt after changes
./scripts/encrypt-update-key.sh
```

### Security Notes
- Private age key (`.age-key`) is automatically added to `.gitignore`
- Never commit the private key to version control
- Public key is stored in `.sops.yaml` for team collaboration

## CLI Options

- `--csv, -f`: CSV file containing DNS records (required)
- `--zone, -z`: DNS zone to manage (required)
- `--config, -c`: Configuration file path (default: configs/config.yaml)
- `--dry-run`: Show what would be changed without making changes
- `--verbose, -v`: Enable verbose logging
- `--output-file`: Save dry-run output to file

## Architecture

### Service components
```mermaid
graph LR
    A[CSV Input] --> B[CSV Parser]
    B --> C[Validators]
    C --> D[Record Manager]
    D --> E[Change Analysis]
    E --> F[DNS Client]
    F --> G[Unified Interface]
    G --> H[DNS Providers]
    
    H --> I[BIND Provider]
    H --> J[Mock Provider]
    
    C --> K[FQDN Validation]
    C --> L[IPv4 Validation]
    C --> M[CSV Structure Validation]
    
    E --> N[Create Records]
    E --> O[Update Records]
    E --> P[Delete Records]
    
    style A fill:#e1f5fe
    style H fill:#f3e5f5
    style I fill:#e8f5e8
    style J fill:#fff3e0
```
<br>
<br>

### Deployment Flow
```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub
    participant CI as CI/CD Pipeline
    participant Sys as DNS Manager System
    participant Bind as BIND Server
    
    Note over Dev,Bind: Pull Request Workflow
    
    Dev->>GH: Push changes to branch
    Dev->>GH: Create Pull Request
    GH->>CI: Trigger CI checks
    
    Note over CI: CI Pipeline Execution
    CI->>Sys: Clone repository
    CI->>Sys: Install dependencies
    Sys->>Sys: Parse CSV & validate records
    Sys->>Sys: Analyze DNS changes
    CI->>Sys: Run dry-run validation
    Sys->>CI: Return validation results
    CI->>GH: Update PR with CI status and diff. result
    
    Note over Dev,GH: PR Review & Approval
    Dev->>GH: Address review comments
    GH->>Dev: Approve PR
    Dev->>GH: Merge PR to main
    
    Note over CI,Bind: Production Deployment
    GH->>CI: Trigger main-deploy workflow
    CI->>Sys: Clone main branch
    CI->>Sys: Install dependencies
    CI->>Sys: Process input.csv
    Sys->>Sys: Parse CSV & validate records
    Sys->>Sys: Analyze DNS changes
    Sys->>Bind: Connect to BIND server
    Sys->>Bind: Authenticate with update key
    Sys->>Bind: Apply DNS record changes
    Bind->>Sys: Confirm record updates
    Sys->>CI: Return deployment results
    CI->>GH: Update deployment status
    
    Note over Dev,Bind: Verification
    Dev->>Bind: Query updated DNS records
    Bind->>Dev: Return new record values
```
<br>
<br>

## Future Enhancements

- DNSSEC support
- Geographic routing
- Load balancing integration
- REST API service
- Configuration management tools integration
- Monitoring systems integration
