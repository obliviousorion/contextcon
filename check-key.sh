#!/usr/bin/env bash
# Key check: credit balance (free) + one Company Identify (~0.1 credit). Usage: ./check-key.sh
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./.env; set +a
H=(-H "authorization: Bearer $CRUSTDATA_API_KEY" -H "x-api-version: 2025-11-01")
curl -sf "${H[@]}" https://api.crustdata.com/account/credits | python3 -c 'import json,sys; print("credits:", json.load(sys.stdin)["account"]["credits"])'
curl -sf -X POST "${H[@]}" -H 'content-type: application/json' https://api.crustdata.com/company/identify \
  -d '{"domains":["crustdata.com"]}' | python3 -c 'import json,sys; print("identify:", json.load(sys.stdin)[0]["matches"][0]["company_data"]["basic_info"]["name"])'
