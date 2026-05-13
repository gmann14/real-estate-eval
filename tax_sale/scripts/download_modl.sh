#!/usr/bin/env bash
# Bulk-download MODL tax-sale PDFs into ../data/probe/modl/{year}/.
#
# Prereq: each year directory must already contain `_page.html` — the archived
# MODL page for that year, since URL slugs change year-over-year and aren't
# discoverable from a fixed pattern. See tax_sale/RUNBOOK-2027.md step 1.
#
# Usage:
#     bash tax_sale/scripts/download_modl.sh [year ...]
#
# With no arguments, processes the default historical set (2021-2026). Add
# new years to the default list or pass them explicitly.
set -u

# Resolve repo root and data dir relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATA_DIR="$REPO_ROOT/data/probe/modl"
mkdir -p "$DATA_DIR"
cd "$DATA_DIR"

# Identify ourselves politely to MODL's web server. Update the email below.
UA="Mozilla/5.0 (compatible; real-estate-eval research; replace-with-your@email)"
LOG="_download.log"
: > "$LOG"

classify() {
  # Map a docman alias to a local filename. $1 = alias slug (without leading id-).
  local s="$1"
  if [[ "$s" =~ tax-sale-award-([0-9]+) ]]; then
    printf "award-%03d.pdf" "${BASH_REMATCH[1]}"
  elif [[ "$s" =~ tax-sale-([0-9]+)-reporting-letter ]]; then
    printf "property-%03d.pdf" "${BASH_REMATCH[1]}"
  elif [[ "$s" =~ ^tax-sale-([0-9]+)(-[0-9]+)?$ ]]; then
    # 2022-style property-info naming: tax-sale-N
    printf "property-%03d.pdf" "${BASH_REMATCH[1]}"
  elif [[ "$s" =~ ^[0-9]{4}-([0-9]+)$ ]]; then
    # 2023-style property-info naming: 2022-N (year-prefixed by tender year)
    printf "property-%03d.pdf" "${BASH_REMATCH[1]}"
  elif [[ "$s" =~ tender-package ]]; then
    echo "tender-package.pdf"
  elif [[ "$s" =~ tender-bid-submission-form ]]; then
    echo "bid-form.pdf"
  elif [[ "$s" =~ tax-sale-faq|^faq ]]; then
    echo "faqs.pdf"
  elif [[ "$s" =~ tax-sale-terms ]]; then
    echo "terms.pdf"
  elif [[ "$s" =~ addendum ]]; then
    echo "$s.pdf"
  elif [[ "$s" =~ tax-sale-ad ]]; then
    echo "tax-sale-ad.pdf"
  else
    echo "_unclassified-$s.pdf"
  fi
}

download_year() {
  local year="$1"
  local page="$year/_page.html"
  if [[ ! -f "$page" ]]; then
    echo "MISS $page  (run: curl -sSL -o $page \"https://www.modl.ca/<year-page-url>\")" \
      | tee -a "$LOG"
    return
  fi

  echo "=== $year ===" | tee -a "$LOG"
  grep -oE 'href="[^"]*com_docman[^"]*(view=download|view=document)[^"]*"' "$page" \
    | sed -E 's/^href="//; s/"$//; s/&amp;/\&/g' \
    | sort -u \
    | while read -r url; do
        # Filter to tax-sale-related (skip council agenda etc)
        [[ "$url" =~ tax-sale|tender|faq|addendum ]] || continue
        # Make absolute
        [[ "$url" == /* ]] && url="https://www.modl.ca${url}"
        # Extract alias slug (strip leading numeric id)
        alias=$(echo "$url" | grep -oE 'alias=[^&]+' | sed -E 's/^alias=[0-9]+-//')
        fname=$(classify "$alias")
        out="$year/$fname"
        if [[ -e "$out" ]]; then
          echo "  SKIP $out (exists)" | tee -a "$LOG"
          continue
        fi
        echo "  GET  $out  <-  $alias" | tee -a "$LOG"
        curl -sSL --max-time 60 -A "$UA" -o "$out" "$url" 2>>"$LOG"
        sleep 0.4
      done
}

# Years to process: CLI args, or the historical default
YEARS=("$@")
if [[ ${#YEARS[@]} -eq 0 ]]; then
  YEARS=(2026 2025 2024 2023 2022 2021)
fi

for y in "${YEARS[@]}"; do
  download_year "$y"
done

echo "=== DONE ===" | tee -a "$LOG"
echo "Per-year file counts:" | tee -a "$LOG"
for y in "${YEARS[@]}"; do
  count=$(find "$y" -maxdepth 1 -name '*.pdf' 2>/dev/null | wc -l | tr -d ' ')
  echo "  $y: $count PDFs" | tee -a "$LOG"
done
