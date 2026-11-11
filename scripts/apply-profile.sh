#!/usr/bin/env bash
# Applies the GitHub metadata that the repository itself cannot hold:
# the profile name and bio, and the description and topics of repositories
# whose settings page was never filled in.
#
# Requires a token that may edit the account profile — a classic PAT with the
# `user` scope, or `gh auth login` as the account owner — and admin rights on
# each repository. The GitHub App token used by the agent has neither, which is
# why this lives here instead of running in CI.
#
#   ./scripts/apply-profile.sh            # apply
#   ./scripts/apply-profile.sh --dry-run  # show the calls, touch nothing
#
# Pinned repositories have no API: the script prints the order to set by hand.

set -euo pipefail

LOGIN="RUdolf1517"
NAME="Rudolf Zinovev"
BIO="Rust & Python. tzim shrinks files, tafas catches video, tummler converts anything."

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

run() {
  if (( DRY_RUN )); then
    printf '  + %s\n' "$*"
  else
    "$@"
  fi
}

# repo|description|topic,topic,topic
REPOS=(
  "mivta|Telegram bot that translates your own outgoing messages in place — inline mode and Secretary mode, no userbot|telegram,bot,translation,python,tool"
  "tafas|YouTube, TikTok and X to one playable MP4 — no ffmpeg, no re-encoding|cli,rust,video,downloader,youtube"
  "Morid|A GUI for command-line media downloaders — pre-alpha|gui,downloader,cpp,qt"
  "MOBSORT|Interactive console demo of mobilization sort — step-by-step integer array sorting|rust,cli,sorting,algorithm,visualization"
  "KOMP|Offline RU/EN voice assistant — wake word «комп», Tauri app and daemon (dormant)|rust,voice-assistant,tauri,offline,vosk"
)

echo "Profile"
run gh api -X PATCH user -f "name=$NAME" -f "bio=$BIO" --silent
echo "  name: $NAME"
echo "  bio:  $BIO"

echo
echo "Repositories"
for entry in "${REPOS[@]}"; do
  IFS='|' read -r repo desc topics <<<"$entry"
  echo "  $repo"
  run gh api -X PATCH "repos/$LOGIN/$repo" -f "description=$desc" --silent

  args=()
  IFS=',' read -ra names <<<"$topics"
  for topic in "${names[@]}"; do
    args+=(-f "names[]=$topic")
  done
  run gh api -X PUT "repos/$LOGIN/$repo/topics" "${args[@]}" --silent
done

echo
echo "Pinned repositories — set by hand at https://github.com/$LOGIN"
echo "  1 tzim   2 tafas   3 mivta   4 tummler"
echo "  (pi-clock and KremleXYZ-Detect come off: one is a toy, the other is old)"

if (( ! DRY_RUN )); then
  echo
  echo "Read back:"
  gh api "users/$LOGIN" --jq '"  name: \(.name // "—")\n  bio:  \(.bio // "—")"'
fi
