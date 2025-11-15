#!/usr/bin/env bash
set -euo pipefail

# This script creates/updates systemd services for the chatbot frontend and backend.
# Run it on the EC2 instance after cloning the repository.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPO_DIR/backend"
FRONTEND_DIR="$REPO_DIR/frontend"

DEFAULT_VENV="$BACKEND_DIR/.venv"
if [[ -n "${VENV_PATH:-}" ]]; then
  VENV_BIN="$VENV_PATH/bin/python"
elif [[ -x "$DEFAULT_VENV/bin/python" ]]; then
  VENV_BIN="$DEFAULT_VENV/bin/python"
else
  VENV_BIN=""
fi

PYTHON_BIN="${PYTHON_BIN:-${VENV_BIN:-$(command -v python3 || true)}}"
NPM_BIN="${NPM_BIN:-$(command -v npm || true)}"
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"
SERVICE_USER="${SERVICE_USER:-$USER}"
SERVICE_GROUP="${SERVICE_GROUP:-$SERVICE_USER}"

if [[ -z "$PYTHON_BIN" ]]; then
  echo "python3 not found. Install Python 3 before running this script." >&2
  exit 1
fi

if [[ -z "$NPM_BIN" ]]; then
  echo "npm not found. Install Node.js/npm before running this script." >&2
  exit 1
fi

if [[ -z "$NODE_BIN" ]]; then
  echo "node not found. Install Node.js before running this script." >&2
  exit 1
fi

NODE_VERSION="$("$NODE_BIN" -v | sed 's/^v//')"
NODE_MAJOR="${NODE_VERSION%%.*}"
if (( NODE_MAJOR < 20 )); then
  echo "Node.js 20+ is required (detected $NODE_VERSION). Please upgrade Node.js on the EC2 instance." >&2
  exit 1
fi

sudo install -d -m 755 /etc/chatbot-inclusivo

sudo tee /etc/systemd/system/chatbot-backend.service > /dev/null <<EOF
[Unit]
Description=Chatbot Inclusivo Backend (FastAPI + Uvicorn)
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$BACKEND_DIR
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-/etc/chatbot-inclusivo/backend.env
ExecStart=$PYTHON_BIN -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/chatbot-frontend.service > /dev/null <<EOF
[Unit]
Description=Chatbot Inclusivo Frontend (Vite preview)
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$FRONTEND_DIR
Environment=NODE_ENV=production
Environment=NPM_CONFIG_PRODUCTION=false
EnvironmentFile=-/etc/chatbot-inclusivo/frontend.env
ExecStartPre=/usr/bin/env bash -lc '$NPM_BIN ci'
ExecStartPre=/usr/bin/env bash -lc '$NPM_BIN run build'
ExecStart=/usr/bin/env bash -lc '$NPM_BIN run preview -- --host 0.0.0.0 --port 4173'
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable chatbot-backend.service chatbot-frontend.service
sudo systemctl restart chatbot-backend.service chatbot-frontend.service

echo "Services created. Use 'sudo systemctl status chatbot-backend' and 'sudo systemctl status chatbot-frontend' to check their state."
