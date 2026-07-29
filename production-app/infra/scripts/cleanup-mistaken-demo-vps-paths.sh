#!/bin/sh
set -eu

# Removes only the three mistaken paths created by the earlier local transfer
# script. It does not touch ~/pimascor-demo, ~/pimascor, Quadlets, secrets,
# PostgreSQL data, Caddy, Backblaze, or any other ~/bridge-ph content.

ssh gatewaysentry '
  set -eu
  rm -rf -- \
    "$HOME/bridge-ph/pimascor-demo-release" \
    "$HOME/bridge-ph/pimascor-demo-release.previous.20260729T161528Z" \
    "$HOME/bridge-ph/releases"
  printf "%s\\n" "Removed only the three mistaken demo release directories."
'
