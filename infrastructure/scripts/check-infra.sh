#!/usr/bin/env bash
set -euo pipefail

echo "== Listening ports =="
sudo ss -tulpn | grep -E ':(80|443|3000|8000|5432)\b' || true

echo
echo "== nginx config test =="
sudo nginx -t

echo
echo "== systemd services =="
sudo systemctl status kyron-api --no-pager || true
sudo systemctl status kyron-frontend --no-pager || true

echo
echo "== local health checks =="
curl -s http://127.0.0.1:8000/health || true
curl -s http://127.0.0.1:3000 || true

echo
echo "== verification reminders =="
echo "- Confirm EC2 security group exposes only 80/443 publicly"
echo "- Confirm RDS is not publicly accessible"
echo "- Confirm RDS security group allows 5432 only from the EC2 security group"
echo "- Confirm systemd services restart automatically"
