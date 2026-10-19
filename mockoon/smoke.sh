#!/usr/bin/env bash
# Smoke test for the Mockoon mock API. Usage: bash mockoon/smoke.sh [base-url]
# Exits non-zero if any request returns an unexpected status or body.
set -u
BASE=${1:-http://localhost:3001/api/v1}
fail=0
A='Authorization: Bearer mock-artist'
P='Authorization: Bearer mock-planner'
N='Authorization: Bearer mock-new'
J='Content-Type: application/json'

# expect <status> <grep-pattern|-> <curl args...>
expect() {
  local want=$1 pattern=$2; shift 2
  local out code body
  out=$(curl -s -w '\n%{http_code}' "$@")
  code=${out##*$'\n'}; body=${out%$'\n'*}
  if [ "$code" != "$want" ]; then
    echo "FAIL $want != $code :: $*"; echo "     $body" | head -c 300; echo; fail=1; return
  fi
  if [ "$pattern" != "-" ] && ! grep -q -- "$pattern" <<<"$body"; then
    echo "FAIL body !~ /$pattern/ :: $*"; echo "     $body" | head -c 300; echo; fail=1; return
  fi
  if [ -n "$body" ] && ! python3 -c 'import json,sys; json.loads(sys.stdin.read())' <<<"$body" 2>/dev/null; then
    echo "FAIL invalid JSON :: $*"; echo "     $body" | head -c 300; echo; fail=1; return
  fi
  echo "OK   $code $*" | cut -c1-110
}

curl -s -X POST "$BASE/_mock/reset" >/dev/null

# --- me ---
expect 401 '"unauthenticated"' "$BASE/me"
expect 200 '"role": *"artist"' -H "$A" "$BASE/me"
expect 200 '"role": *"planner"' -H "$P" "$BASE/me"
expect 404 '"profile_required"' -H "$N" "$BASE/me"
expect 401 '"unauthenticated"' -H 'Authorization: Bearer expired-or-junk' "$BASE/me"
expect 200 '"fullName": *"Neha K."' -X PATCH -H "$P" -H "$J" -d '{"fullName":"Neha K."}' "$BASE/me"
# --- public ---
expect 200 '"Mumbai"' "$BASE/locations"
expect 200 '"total": *12' "$BASE/search/artists"
expect 200 '"total": *2' "$BASE/search/artists?artistType=dj"
expect 200 '"total": *1' "$BASE/search/artists?artistType=dj&city=Pune"
expect 200 '"total": *1' "$BASE/search/artists?area=Juhu"
expect 200 '"isFeatured": *true' "$BASE/search/artists?featuredOnly=true"
expect 200 '"items"' "$BASE/search/suggestions?q=dj"
expect 200 '"isFeatured": *true' "$BASE/artists/featured"
expect 200 '"slug": *"dj-krish"' "$BASE/artists/dj-krish"
expect 404 '"artist_not_found"' "$BASE/artists/no-such-artist"
expect 200 '"reviewerName"' "$BASE/artists/dj-krish/reviews"
expect 200 '"artistType": *"dj"' "$BASE/artists/dj-krish/similar"
expect 204 - -X POST "$BASE/artists/dj-krish/contact-click"
# --- plans ---
expect 200 '"tier": *"premium"' "$BASE/subscriptions/plans"
# --- leads ---
expect 401 '"unauthenticated"' -X POST -H "$J" -d @contracts/examples/leads/post.request.json "$BASE/leads"
expect 201 '"contactPhone": *"9820011002"' -X POST -H "$P" -H "$J" -d '{"artistId":"art-002","plannerName":"Neha","plannerPhone":"9920012345","plannerEmail":null,"eventType":"wedding","eventDate":null,"eventCity":"Mumbai","budgetRange":"15k_25k","notes":null,"source":"profile"}' "$BASE/leads"
expect 200 '"isLocked": *true' -H "$A" "$BASE/leads/artist"
expect 200 '"total": *3' -H "$A" "$BASE/leads/artist?status=new"
expect 200 '"status": *"converted"' -X PATCH -H "$A" -H "$J" -d '{"status":"converted"}' "$BASE/leads/lead-015"
expect 200 '"upcoming"' -H "$P" "$BASE/leads/planner"
expect 200 '"total": *2' -H "$P" "$BASE/leads/planner?status=pending"
# --- artist self ---
expect 200 '"contactPhone"' -H "$A" "$BASE/artists/me"
expect 200 '"greetingName"' -H "$A" "$BASE/artists/me/dashboard"
expect 200 '"quota"' -H "$A" "$BASE/artists/me/media"
expect 200 '"uploadUrl"' -X POST -H "$A" -H "$J" -d @contracts/examples/media/upload-url.request.json "$BASE/artists/me/media/upload-url"
expect 200 - -X PUT --data-binary 'fake-bytes' "$BASE/_mock/upload/abc123"
expect 201 '"kind": *"image"' -X POST -H "$A" -H "$J" -d @contracts/examples/media/create.request.json "$BASE/artists/me/media"
expect 200 '"profileImageUrl"' -X POST -H "$A" -H "$J" -d @contracts/examples/media/avatar.request.json "$BASE/artists/me/avatar"
expect 204 - -X DELETE -H "$A" "$BASE/artists/me/media/med-001-2"
expect 200 '"items"' -X PUT -H "$A" -H "$J" -d @contracts/examples/media/order.request.json "$BASE/artists/me/media/order"
expect 200 '"plan"' -H "$A" "$BASE/subscriptions/me"
expect 201 '"razorpaySubscriptionId"' -X POST -H "$A" -H "$J" -d '{"tier":"pro","billingCycle":"monthly"}' "$BASE/subscriptions"
expect 200 '"status": *"active"' -X POST -H "$A" -H "$J" -d @contracts/examples/subscriptions/verify.request.json "$BASE/subscriptions/verify"
expect 200 '"cancelAtPeriodEnd": *true' -X POST -H "$A" "$BASE/subscriptions/cancel"
# --- new-user journey (stateful via Mockoon global vars) ---
expect 404 '"artist_profile_not_found"' -H "$N" "$BASE/artists/me"
expect 404 '"artist_profile_not_found"' -H "$N" "$BASE/artists/me/dashboard"
expect 404 '"artist_profile_not_found"' -H "$N" "$BASE/leads/artist"
expect 201 '"role": *"artist"' -X POST -H "$N" -H "$J" -d '{"role":"artist","fullName":"Tanvi Rao"}' "$BASE/me"
expect 200 '"artistSlug": *null' -H "$N" "$BASE/me"
expect 200 '"trialAvailable": *true' -H "$N" "$BASE/subscriptions/me"
expect 201 '"contactPhone"' -X POST -H "$N" -H "$J" -d @contracts/examples/artists/post.request.json "$BASE/artists"
expect 200 '"artistSlug": *"arjun-malhotra-magic"' -H "$N" "$BASE/me"
expect 200 '"contactPhone"' -H "$N" "$BASE/artists/me"
expect 200 '"greetingName"' -H "$N" "$BASE/artists/me/dashboard"
expect 200 '"status": *"trial"' -X POST -H "$N" -H "$J" -d '{"tier":"pro"}' "$BASE/subscriptions/trial"
curl -s -X POST "$BASE/_mock/reset" >/dev/null

[ $fail -eq 0 ] && echo "SMOKE PASS" || { echo "SMOKE FAIL"; exit 1; }
