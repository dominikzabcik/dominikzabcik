#!/bin/bash
# Renders a README through GitHub's own markdown API into .preview/<name>.html,
# so you see what github.com will do with it (sanitising, theme fragments).
# Like github.com, it hides a themed image only through the link around it.
# Usage: scripts/preview.sh [README.md] [--open]
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
src="${1:-README.md}"
[ "${1:-}" = "--open" ] && src="README.md"
name="$(basename "${src%.*}")"
mkdir -p "$root/.preview"
out="$root/.preview/$name.html"
body="$(gh api -X POST /markdown -f mode=markdown -f text="$(cat "$root/$src")")"
# Relative image paths are resolved from the markdown file's folder.
base="file://$root/$(dirname "$src")/"
cat > "$out" <<HTML
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<base href="$base">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/github-markdown-css@5/github-markdown.css">
<style>body{margin:0}.markdown-body{box-sizing:border-box;max-width:894px;margin:0 auto;padding:24px}
@media (prefers-color-scheme:dark){body{background:#0d1117}a[href\$="#gh-light-mode-only"]{display:none}}
@media (prefers-color-scheme:light){a[href\$="#gh-dark-mode-only"]{display:none}}</style>
</head><body><article class="markdown-body">
$body
</article></body></html>
HTML
echo "$out"
for arg in "$@"; do [ "$arg" = "--open" ] && open -a "Google Chrome" "$out"; done
exit 0
