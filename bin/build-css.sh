#!/usr/bin/env bash
set -euo pipefail
tailwindcss -i static/css/src/app.css -o static/css/app.css --minify
