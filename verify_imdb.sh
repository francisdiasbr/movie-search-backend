#!/bin/bash
#
# Checks the IMDB session used by the scraper and renews it when needed.
#
# Chromium locks the profile directory, so the backend has to be down while the
# profile is in use. This script handles that ordering, which is easy to get
# wrong: stop the backend -> check/verify -> bring it back up.
#
#   ./verify_imdb.sh              checks the session, verifies only if needed
#   ./verify_imdb.sh --force      always opens the verification window
#   ./verify_imdb.sh --no-start   does not restart the backend at the end
#   ./verify_imdb.sh tt0017136    uses another title for the check

set -e

cd "$(dirname "$0")"

PYTHON="./venv/bin/python"
PORT=5000
FORCE=0
START=1
TCONST="tt0032138"

for arg in "$@"; do
    case "$arg" in
        --force) FORCE=1 ;;
        --no-start) START=0 ;;
        tt*) TCONST="$arg" ;;
        *) echo "❌ Argumento desconhecido: $arg"; exit 1 ;;
    esac
done

if [ ! -x "$PYTHON" ]; then
    echo "❌ venv não encontrado em $PYTHON"
    exit 1
fi

# The profile can only be opened by one process at a time.
PIDS=$(lsof -ti:$PORT || true)
if [ -n "$PIDS" ]; then
    echo "⏹  Parando o backend na porta $PORT (PID $PIDS)"
    echo "$PIDS" | xargs kill
    sleep 2
fi

NEEDS_VERIFY=$FORCE

if [ "$FORCE" -eq 0 ]; then
    echo "🔎 Testando a sessão atual com $TCONST..."
    if $PYTHON -c "
import sys
from favorites.scrapper import fetch_soup
soup = fetch_soup('$TCONST')
sys.exit(0 if soup else 1)
" > /dev/null 2>&1; then
        echo "✅ Sessão válida — nenhuma verificação necessária."
    else
        echo "⚠️  Sessão bloqueada pelo WAF."
        NEEDS_VERIFY=1
    fi
fi

if [ "$NEEDS_VERIFY" -eq 1 ]; then
    echo "🔐 Abrindo o IMDB para verificação manual..."
    $PYTHON imdb_verify.py "$TCONST"
fi

if [ "$START" -eq 0 ]; then
    echo "ℹ️  Backend não reiniciado (--no-start)."
    exit 0
fi

echo "▶️  Subindo o backend..."
exec $PYTHON app.py
