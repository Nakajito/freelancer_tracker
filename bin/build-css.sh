#!/usr/bin/env bash
set -euo pipefail
uv run tailwindcss -i src/css/app.css -o static/css/app.css --minify
