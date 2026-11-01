"""Create an unapplied candidate patch; never print proxy credentials."""
import json
import os
from pathlib import Path
import subprocess

source = Path('/usr/local/etc/xray/config.json')
candidate = Path('/opt/bbmod-hub/pending/xray-config.json')
config = json.loads(source.read_text())
matches = [inbound for inbound in config['inbounds'] if inbound.get('port') == 443
           and inbound.get('streamSettings', {}).get('security') == 'reality']
assert len(matches) == 1, 'Expected one existing REALITY listener on port 443'
inbound = matches[0]
inbound['listen'] = '127.0.0.1'
inbound['port'] = 10443
inbound['streamSettings'].setdefault('tcpSettings', {})['acceptProxyProtocol'] = True
assert not inbound['streamSettings']['realitySettings'].get('xver'), 'Review target PROXY forwarding before changing'
candidate.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
candidate.write_text(json.dumps(config, indent=2) + '\n')
candidate.chmod(0o640)
subprocess.run(['chown', 'root:xray', str(candidate)], check=True)
checked = subprocess.run(['/usr/local/bin/xray', 'run', '-test', '-config', str(candidate)], capture_output=True)
if checked.returncode:
    print('Xray candidate validation failed; service configuration unchanged.')
    raise SystemExit(1)
print('Unapplied Xray candidate validated; client credentials retained.')
