#!/bin/bash

echo "Building BIND DNS container with Podman..."
podman build -f Dockerfile.bind -t bind-dns-server .

echo "Creating BIND DNS container..."
podman run -d \
    --name bind-dns-server \
    --publish 53:53/udp \
    --publish 53:53/tcp \
    --publish 953:953/tcp \
    --volume ./zones:/etc/bind/zones:ro \
    --volume ./rndc.key:/etc/bind/rndc.key:ro \
    --restart unless-stopped \
    bind-dns-server

echo "Container started! Checking status..."
podman ps | grep bind-dns-server

echo ""
echo "Container details:"
echo "=================="
echo "Container name: bind-dns-server"
echo "DNS port: 53 (UDP/TCP)"
echo "RNDC port: 953 (TCP)"
echo "Zone files: ./zones/"
echo "RNDC key: ./rndc.key"
echo ""
echo "To view logs: podman logs bind-dns-server"
echo "To stop: podman stop bind-dns-server"
echo "To remove: podman rm bind-dns-server"
echo ""
echo "Testing DNS resolution..."
echo "Querying machine1.ib.bigbank.com:"
dig @127.0.0.1 machine1.ib.bigbank.com
