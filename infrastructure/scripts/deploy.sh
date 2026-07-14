#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/kyron"
REPO_URL="${1:-}"

if [[ -z "${REPO_URL}" ]]; then
  echo "Usage: ./deploy.sh <git-repo-url>"
  exit 1
fi

sudo apt-get update
sudo apt-get install -y git nginx python3 python3-venv python3-pip curl

if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

if [[ ! -d "${APP_ROOT}" ]]; then
  sudo mkdir -p "${APP_ROOT}"
  sudo chown -R "${USER}:${USER}" "${APP_ROOT}"
fi

if [[ ! -d "${APP_ROOT}/.git" ]]; then
  git clone "${REPO_URL}" "${APP_ROOT}"
else
  git -C "${APP_ROOT}" pull --ff-only
fi

cd "${APP_ROOT}/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd "${APP_ROOT}/frontend"
npm install
npm run build

echo "Deployment files updated."
echo "Next steps:"
echo "1. Place backend and frontend runtime env files in /opt/kyron/backend/.env and /opt/kyron/frontend/.env.local"
echo "2. Run Alembic migrations from /opt/kyron/backend"
echo "3. Install systemd unit files from infrastructure/systemd/"
echo "4. Install nginx config from infrastructure/nginx/kyron.conf"
echo "5. Configure TLS certificate and reload nginx"
