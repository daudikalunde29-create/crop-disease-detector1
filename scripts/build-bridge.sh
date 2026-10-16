#!/usr/bin/env bash
# Rebuilds public/site/js/cloud.bundle.js from src/cloud-bridge/entry.ts
set -e
set -a; [ -f .env ] && . ./.env; set +a
bunx esbuild src/cloud-bridge/entry.ts --bundle --format=iife --minify --target=es2019 \
  --alias:@=./src \
  --define:import.meta.env.VITE_SUPABASE_URL="\"$VITE_SUPABASE_URL\"" \
  --define:import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY="\"$VITE_SUPABASE_PUBLISHABLE_KEY\"" \
  "--define:import.meta.env={}" \
  --outfile=public/site/js/cloud.bundle.js
