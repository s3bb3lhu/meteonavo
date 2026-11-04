#!/bin/sh
# Install a wrapper for this script in the certificate manager's deploy-hook directory.
set -eu
cd "${METEONAVO_PROJECT_DIR:-/opt/weather-channel-studio}"
project=${METEONAVO_COMPOSE_PROJECT:-weather-studio}
if [ -n "$(docker compose -p "$project" ps -q gateway)" ]; then
    docker compose -p "$project" exec -T gateway nginx -t
    docker compose -p "$project" kill -s HUP gateway
fi
