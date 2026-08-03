#!/bin/zsh

PROJECT_ROOT="${0:A:h}"

clear
print "Starting Hermes AI Attention..."
print "A health check and the small status overlay will appear first."
print "When the Hermes prompt appears, type a request or enter /voice on."
print ""

"$PROJECT_ROOT/scripts/launch_daily_hermes.sh" "$@"
exit_status=$?

if (( exit_status != 0 )); then
  print ""
  print "Hermes did not start successfully. Nothing was sent or changed externally."
  print "See START_HERE.md, then press Return to close this window."
  read -r
fi

exit "$exit_status"
