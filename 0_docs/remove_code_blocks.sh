#!/usr/bin/env bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 <markdown-file>"
  exit 1
fi

input="$1"

# Ensure file exists
if [ ! -f "$input" ]; then
  echo "Error: file not found: $input"
  exit 1
fi

# Extract path, filename, and extension
dir="$(dirname "$input")"
base="$(basename "$input")"
name="${base%.*}"

output="$dir/${name}_rm_cb.md"

# Remove fenced code blocks and write to new file
sed '/^[[:space:]]*```/,/^[[:space:]]*```/d' "$input" > "$output"

echo "Code blocks removed → $output"
