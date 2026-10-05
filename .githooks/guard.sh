#!/bin/bash
# Refuse any commit that would put THE·TEAM client data in this public repo.
# Client acts may appear only inside the StatiCrypt-locked index.html; agent names never.
# Used by .githooks/pre-commit and by refresh.sh before it commits.
cd "$(git rev-parse --show-toplevel)"
bad=$(git grep --cached -l -e '"clients"' -- data/ '*.json' '*.csv' 2>/dev/null)  # client matches in a data file
bad+=$(git grep --cached -l -e 'RESPONSIBLE AGENT' -e 'SERVICE AGENT' -- . ':!.githooks' 2>/dev/null)  # client sheet headers
bad+=$(git diff --cached --name-only | grep -E '(^|/)clients_raw|\.xlsx$|shows_merged|\.clients-key|\.staticrypt-password|^plain/|^artifact\.html$' || true)
if [ -n "$bad" ]; then
  echo "REFUSING TO COMMIT: client data is staged in a public repo:" >&2
  echo "$bad" >&2
  exit 1
fi
