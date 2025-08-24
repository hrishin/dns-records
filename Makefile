.PHONY: help install test clean demo run-dry-run run-live lint format

# Default target
help:
	@echo "DNS Records Manager - Available Commands:"
	@echo ""
	@echo "Installation:"
	@echo "  install          Install dependencies"
	@echo "  build            Build the package"
	@echo "  install-package  Install package in development mode"
	@echo "  install-dev      Install development dependencies"
	@echo "  uninstall        Uninstall the package"
	@echo ""
	@echo "Infrastructure:"
	@echo "  bind-setup       Setup BIND DNS server container"
	@echo "  bind-rebuild     Rebuild BIND DNS server container"
	@echo "  bind-start       Start BIND DNS server"
	@echo "  bind-stop        Stop BIND DNS server"
	@echo "  bind-clean       Remove BIND DNS server container"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-package     Run package tests"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  test-package-coverage Run package tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with black"
	@echo ""
	@echo "Running:"
	@echo "  demo             Run interactive demo"
	@echo "  run-dry-run      Run with sample data (dry-run mode)"
	@echo "  run-live         Run with sample data (live mode)"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            Clean up generated files"
	@echo "  clean-all        Clean up everything including BIND"
	@echo "  clean-logs       Clean log files"
	@echo ""

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "Installation complete!"

build:
	@echo "Building package..."
	python setup.py build
	@echo "Package built successfully!"

install-package: build
	@echo "Installing package in development mode..."
	pip install -e .
	@echo "Package installed in development mode!"

install-dev: install install-package
	@echo "Installing development dependencies..."
	pip install pytest pytest-cov black flake8 mypy
	@echo "Development dependencies installed!"

test:
	@echo "Running tests..."
	python -m pytest main.py -v

lint:
	@echo "Running linting checks..."
	flake8 *.py dns_records_manager/
	@echo "Linting complete!"

format:
	@echo "Formatting code..."
	black *.py dns_records_manager/
	@echo "Code formatting complete!"

run-dry-run:
	@echo "Running DNS manager in dry-run mode..."
	python main.py --csv input.csv --config configs/config_bind.yaml --zone ib.bigbank.com --dry-run

run-live:
	@echo "Running DNS manager in live mode..."
	@echo "WARNING: This will make actual DNS changes!"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		python main.py --csv input.csv  --config configs/config_bind.yaml --zone ib.bigbank.com;\
	else \
		echo "Operation cancelled."; \
	fi

clean:
	@echo "Cleaning up generated files..."
	rm -rf __pycache__/
	rm -rf *.pyc
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -f *.log
	rm -f demo_config.yaml
	rm -f demo_records.csv
	@echo "Cleanup complete!"

clean-all: clean bind-clean
	@echo "Full cleanup complete!"

clean-logs:
	@echo "Cleaning log files..."
	rm -f *.log
	@echo "Log files cleaned!"

setup-dev: install-dev
	@echo "Setting up development environment..."
	cp configs/config.example.yaml configs/config.yaml
	@echo "Development environment ready!"
	@echo "Edit configs/config.yaml with your settings"

check-deps:
	@echo "Checking dependency versions..."
	pip list | grep -E "(boto3|PyYAML|click|dnspython|rich)"

uninstall:
	@echo "Uninstalling package..."
	pip uninstall dns-records-manager -y
	@echo "Package uninstalled!"

# BIND DNS Server Management
bind-setup:
	@echo "Setting up BIND DNS server..."
	@echo "Building and starting BIND container..."
	./scripts/run-bind.sh
	@echo "BIND DNS server setup complete!"

bind-rebuild:
	@echo "Rebuilding BIND DNS server container..."
	@if docker ps -q -f name=bind-dns-server | grep -q .; then \
		docker stop bind-dns-server; \
	fi
	@if docker ps -aq -f name=bind-dns-server | grep -q .; then \
		docker rm bind-dns-server; \
	fi
	docker build -f Dockerfile.bind -t bind-dns-server .
	@echo "BIND DNS server container rebuilt!"

bind-start:
	@echo "Starting BIND DNS server..."
	@if docker ps -q -f name=bind-dns-server | grep -q .; then \
		echo "BIND DNS server is already running."; \
	else \
		docker start bind-dns-server || ./scripts/run-bind.sh; \
	fi
	@echo "BIND DNS server started!"

bind-stop:
	@echo "Stopping BIND DNS server..."
	@if docker ps -q -f name=bind-dns-server | grep -q .; then \
		docker stop bind-dns-server; \
		echo "BIND DNS server stopped."; \
	else \
		echo "BIND DNS server is not running."; \
	fi

bind-status:
	@echo "BIND DNS Server Status:"
	@if docker ps -q -f name=bind-dns-server | grep -q .; then \
		docker ps | grep bind-dns-server; \
		echo ""; \
		echo "Testing DNS resolution:"; \
		dig @127.0.0.1 db.ib.bigbank.com +short || echo "DNS resolution failed"; \
	else \
		echo "BIND DNS server is not running."; \
	fi

bind-logs:
	@echo "BIND DNS Server Logs:"
	@if docker ps -q -f name=bind-dns-server | grep -q .; then \
		docker logs bind-dns-server | tail -20; \
	else \
		echo "BIND DNS server is not running."; \
	fi

bind-test:
	@echo "Testing BIND DNS resolution..."
	@if docker ps -q -f name=bind-dns-server | grep -q .; then \
		echo "Testing db.ib.bigbank.com:"; \
		dig @127.0.0.1 db.ib.bigbank.com; \
		echo ""; \
	else \
		echo "BIND DNS server is not running. Start it with 'make bind-start'"; \
	fi

bind-clean:
	@echo "Removing BIND DNS server container..."
	@if docker ps -q -f name=bind-dns-server | grep -q .; then \
		docker stop bind-dns-server; \
	fi
	@if docker ps -aq -f name=bind-dns-server | grep -q .; then \
		docker rm bind-dns-server; \
	fi
	@echo "BIND DNS server container removed!"

# Default help
.DEFAULT_GOAL := help
