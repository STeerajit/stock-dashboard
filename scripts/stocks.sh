#!/usr/bin/env bash
# Open the dashboard in the browser, starting it in the background first if needed.
#   stocks        start (if not running) and open http://localhost:8501
#   stocks stop   stop it
# The app keeps running after the terminal is closed. Its output goes to stocks.log.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT=8501
URL="http://localhost:${PORT}"
LOG="${ROOT}/stocks.log"
OPEN="${STOCKS_OPEN:-open}"  # tests set this to "true" so no browser window opens

running_pids() {
    lsof -ti "tcp:${PORT}" -sTCP:LISTEN 2>/dev/null || true
}

case "${1:-start}" in
    start)
        if [ -z "$(running_pids)" ]; then
            if [ ! -x "${ROOT}/.venv/bin/streamlit" ]; then
                echo "No .venv found. Set it up first (see README, 'How to run')." >&2
                exit 1
            fi
            echo "Starting the dashboard (log: ${LOG})..."
            cd "${ROOT}"
            nohup .venv/bin/streamlit run app.py --server.port "${PORT}" --server.headless true \
                >"${LOG}" 2>&1 </dev/null &
            disown
            for _ in $(seq 1 60); do
                if curl -s -o /dev/null "${URL}"; then break; fi
                sleep 1
            done
            if ! curl -s -o /dev/null "${URL}"; then
                echo "The dashboard did not start within 60 s. See ${LOG}." >&2
                exit 1
            fi
        fi
        "${OPEN}" "${URL}"
        echo "Dashboard: ${URL}"
        ;;
    stop)
        pids="$(running_pids)"
        if [ -z "${pids}" ]; then
            echo "The dashboard is not running."
            exit 0
        fi
        kill ${pids}
        for _ in $(seq 1 10); do
            if [ -z "$(running_pids)" ]; then break; fi
            sleep 1
        done
        echo "Dashboard stopped."
        ;;
    *)
        echo "Usage: stocks [stop]" >&2
        exit 2
        ;;
esac
