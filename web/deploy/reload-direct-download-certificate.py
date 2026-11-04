#!/usr/bin/env python3
"""Reload host Nginx after the existing certbot renews the relay certificate."""
import hashlib
from pathlib import Path
import subprocess

certificate = Path('/srv/gongpro-data/certbot/conf/live/dl.gongpro.app/fullchain.pem')
state = Path('/var/lib/bbmod-downloads/relay-certificate.sha256')
current = hashlib.sha256(certificate.read_bytes()).hexdigest()
if not state.exists() or state.read_text().strip() != current:
    subprocess.run(['nginx', '-t'], check=True)
    subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(current + '\n')
