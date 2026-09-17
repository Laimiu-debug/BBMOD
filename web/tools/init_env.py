"""Generate deployment settings without printing the secret or overwriting existing ones."""
import argparse
import ipaddress
import os
import re
import secrets
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--host', required=True, help='服务器公网 IP 或域名，不含 http、端口或路径')
parser.add_argument('--port', type=int, default=8080)
args = parser.parse_args()
try:
    ipaddress.ip_address(args.host.strip('[]'))
except ValueError:
    if not re.fullmatch(r'[a-zA-Z0-9.-]+', args.host) or not args.host or '..' in args.host:
        parser.error('请输入有效的 IP 或域名。')
if not 1 <= args.port <= 65535:
    parser.error('端口须在 1 至 65535 之间。')
path = Path(__file__).resolve().parents[1] / '.env'
data = f'''BBMOD_SECRET_KEY={secrets.token_urlsafe(64)}
BBMOD_ALLOWED_HOSTS=localhost,127.0.0.1,{args.host}
BBMOD_DEBUG=0
BBMOD_HTTPS=0
BBMOD_BIND=0.0.0.0
BBMOD_PORT={args.port}
BBMOD_MAX_UPLOAD_MB=100
BBMOD_AUTHOR_QUOTA_MB=2048
'''
try:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    parser.error('.env 已存在，为避免覆盖密钥已停止。请直接编辑原文件。')
with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
    stream.write(data)
print('已生成 .env（密钥不显示）。现在可以 docker compose up -d --build。')
