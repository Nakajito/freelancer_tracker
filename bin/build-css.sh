#!/usr/bin/env bash
set -euo pipefail
# Tailwind v4 config format differs from v3; templates target v3 utility syntax
export TAILWINDCSS_VERSION=v3.4.17
tailwindcss -i static/css/src/app.css -o static/css/app.css --minify
