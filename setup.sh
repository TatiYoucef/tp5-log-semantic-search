#!/usr/bin/env bash

set -euo pipefail

VENV_PATH="${VENV_PATH:-$HOME/Desktop/Old_ESI/Python/venv}"

if [ ! -x "$VENV_PATH/bin/python" ]; then
  echo "Erreur: environnement virtuel introuvable: $VENV_PATH"
  echo "Definis VENV_PATH ou cree l'environnement avant de lancer setup.sh."
  exit 1
fi

source "$VENV_PATH/bin/activate"
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements.txt
python -m pip install -e .

mkdir -p data/raw data/processed reports
if [ -f data/archives/OpenSSH.zip ]; then
  unzip -o data/archives/OpenSSH.zip -d data/raw
fi

cp -n .env.example .env

echo "Environnement pret."
echo "Commandes utiles:"
echo "  source $VENV_PATH/bin/activate"
echo "  docker compose up -d"
echo "  tp5-log-search run-pipeline --limit 10000"
echo "  tp5-log-search serve-api"
echo "  tp5-log-search serve-web"
