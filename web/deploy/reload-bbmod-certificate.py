#!/usr/bin/python3
"""Gracefully reload the shared proxy only when the BBMOD certificate changes."""
import hashlib
from pathlib import Path
import subprocess

certificate = Path('/home/ubuntu/gongpro-data/certbot/conf/live/bbmod.site/fullchain.pem')
state = Path('/var/lib/bbmod-cert-reload/sha256')
digest = hashlib.sha256(certificate.read_bytes()).hexdigest()
if state.is_file() and state.read_text().strip() == digest:
    print('BBMOD certificate unchanged')
else:
    subprocess.run(['docker', 'exec', 'weld_nginx', 'nginx', '-t'], check=True)
    subprocess.run(['docker', 'exec', 'weld_nginx', 'nginx', '-s', 'reload'], check=True)
    state.parent.mkdir(mode=0o700, exist_ok=True)
    state.write_text(digest + '\n')
    state.chmod(0o600)
    print('BBMOD renewed certificate loaded')
