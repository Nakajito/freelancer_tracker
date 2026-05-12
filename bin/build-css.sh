#!/usr/bin/env bash
set -euo pipefail
tailwindcss -i src/css/app.css -o static/css/app.css --minify
