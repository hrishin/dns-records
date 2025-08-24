#!/usr/bin/env python3
"""
Setup script for DNS Records Manager package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="dns-records-manager",
    version="1.0.0",
    author="DNS Records Manager Team",
    author_email="team@example.com",
    description="Automated DNS record management for enterprise environments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/dns-records-manager",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: Name Service (DNS)",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "dns-manager=dns_records_manager.cli.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "dns_records_manager": ["*.yaml", "*.yml"],
    },
)
