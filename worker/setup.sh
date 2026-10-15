#!/usr/bin/env bash
set -euo pipefail
# Run as root on an existing Ubuntu DigitalOcean Droplet. Does not create paid resources.
python3 -c 'import sys; assert sys.version_info >= (3,11), "Worker host requires Python 3.11+ (Ubuntu 24.04 recommended)"'
apt-get update
apt-get install -y docker.io git python3
systemctl enable --now docker
id veripatch >/dev/null 2>&1 || useradd --create-home --shell /bin/bash veripatch
usermod -aG docker veripatch
install -d -o veripatch -g veripatch /var/lib/veripatch
install -d /opt/veripatch/bin /opt/veripatch/lib/veripatch
install -m 644 worker/server.py worker/execute.py /opt/veripatch/lib/
install -m 644 app/veripatch/patches.py app/veripatch/safety.py app/veripatch/__init__.py /opt/veripatch/lib/veripatch/
printf '#!/bin/sh\nexec /usr/bin/python3 /opt/veripatch/lib/server.py\n' > /opt/veripatch/bin/worker
chmod 755 /opt/veripatch/bin/worker
docker pull python:3.12-slim
echo 'Worker installed. Add the dedicated public SSH key using the forced command described in docs/DIGITALOCEAN.md.'
