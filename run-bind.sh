#!/bin/bash

set -e

echo "Building BIND DNS container with docker..."
docker build -f Dockerfile.bind -t bind-dns-server .

echo "Creating BIND DNS container..."
docker run -d \
    --name bind-dns-server \
    -p 53:53/udp \
    -p 53:53/tcp \
    -p 953:953/tcp \
    -v ./bind/zones:/etc/bind/zones:ro \
    --restart unless-stopped \
    bind-dns-server

echo "Container started! Checking status..."
docker ps | grep bind-dns-server

echo ""
echo "Container details:"
echo "=================="
echo "Container name: bind-dns-server"
echo "DNS port: 53 (UDP/TCP)"
echo "RNDC port: 953 (TCP)"
echo "Zone files: ./zones/"
echo "RNDC key: ./rndc.key"
echo ""
echo "To view logs: docker logs bind-dns-server"
echo "To stop: docker stop bind-dns-server"
echo "To remove: docker rm bind-dns-server"
echo ""
echo "Testing DNS resolution..."
echo "Querying db.ib.bigbank.com:"
dig @127.0.0.1 db.ib.bigbank.com
