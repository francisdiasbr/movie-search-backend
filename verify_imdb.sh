#!/bin/bash
#
# Starts the backend, renewing the IMDB session first when the AWS WAF is
# blocking the scraper.
#
# Chromium locks the profile directory, so the backend has to be down while the
# profile is in use. This script handles that ordering, which is easy to get
# wrong: stop the backend -> check the session -> bring it back up.

set -e

cd "$(dirname "$0")"

PYTHON="./venv/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "❌ venv não encontrado em $PYTHON"
    exit 1
fi

# The profile can only be opened by one process at a time.
PIDS=$(lsof -ti:5000 || true)
if [ -n "$PIDS" ]; then
    echo "⏹  Parando o backend na porta 5000 (PID $PIDS)"
    echo "$PIDS" | xargs kill
    sleep 2
fi

echo "🔎 Testando a sessão do IMDB..."
if $PYTHON -c "
import sys
from favorites.scrapper import fetch_soup
sys.exit(0 if fetch_soup('tt0032138') else 1)
" > /dev/null 2>&1; then
    echo "✅ Sessão válida."
else
    echo "⚠️  Sessão bloqueada pelo WAF — abrindo o navegador para verificação."
    $PYTHON imdb_verify.py
fi

echo "▶️  Subindo o backend..."
exec $PYTHON app.py
