#!/bin/sh
set -eu
/usr/sbin/nginx -t
if /usr/bin/systemctl is-active --quiet nginx.service; then
    /usr/bin/systemctl reload nginx.service
fi
