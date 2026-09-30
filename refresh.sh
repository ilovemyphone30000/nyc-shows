#!/bin/bash
# Refresh every city for today through a week ahead, rebuild, test, and publish.
#   ./refresh.sh            scrape, process, merge clients, build, check, push
#   ./refresh.sh --no-push  everything but the push (for a look first)
# Runs daily on GitHub Actions (.github/workflows/refresh.yml); also runs locally.
set -euo pipefail
cd "$(dirname "$0")"

# Today through a week ahead (python: works the same on macOS and GitHub's Linux runners).
FROM=$(python3 -c 'import datetime as d; print(d.date.today())')
TO=$(python3 -c 'import datetime as d; print(d.date.today() + d.timedelta(days=7))')
PY=${PY:-.venv/bin/python}
echo "== window $FROM .. $TO"

# Cities in parallel: each is a different site, and within a city pages still go one at
# a time. A city that fails (or hits a bot check) keeps its last good data.
mkdir -p logs
pids=()
for c in nyc chi la; do
  ( "$PY" scrape.py "$c" "$FROM" "$TO" && "$PY" scrape.py "$c" --announced ) > "logs/scrape_$c.log" 2>&1 &
  pids+=($!)
done
failed=0
for i in 0 1 2; do
  c=(nyc chi la); c=${c[$i]}
  if wait "${pids[$i]}"; then tail -2 "logs/scrape_$c.log"; else echo "!! $c scrape failed:"; tail -5 "logs/scrape_$c.log"; failed=1; fi
done

SNAP=$(mktemp -d)
cp data/shows_*.json "$SNAP"/ 2>/dev/null || true
for c in nyc chi la; do
  python3 process.py "$c"
  python3 clients.py "$c"
  python3 announce.py "$c"
done
python3 changes.py "$SNAP"
python3 build.py
"$PY" check.py

if [[ "${1:-}" == "--no-push" ]]; then
  echo "== built and checked; not pushed"
  exit 0
fi

git add -A
if git grep --cached -q -e "RESPONSIBLE AGENT" -e "SERVICE AGENT" -- ':!refresh.sh'; then  # sheet headers = raw sheet data
  echo "refusing to commit: client sheet data is staged"; exit 1
fi
if git diff --cached --quiet; then
  echo "== nothing changed"; exit 0
fi
git commit -q -m "Refresh listings $FROM to $TO"
git push -q origin main
echo "== pushed; live within a couple of minutes"
exit $failed
