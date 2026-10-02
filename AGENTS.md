## Rule: the README is generated, and zabcik.me is the source of truth

`README.md` and everything in `assets/site/` are build output. Never edit them by hand.

- **Shared facts** (roles, projects, skills, profile text, links, the About line and tagline) live in the website repo, `~/website/src/content/cv.ts` and `src/content/portfolio.ts`. Change them there, never in this repo, so the site, the CV PDF and this README say the same thing.
- **README-only content** lives in `data/readme.json`: the NFCtron product list, the hiring line, "What pulls me in", "Current focus", extra sentences for projects (`projectMore`), the live Keyhop year graph at the bottom (`keyhopWidget`, served by keyhop.app, `null` removes it), and the Simple Icons slug for each skill id. GitHub may say more than the website; it must not contradict it.
- `data/profile.json` is an export, not a source. Regenerate it, never edit it.

The sync is automatic. The website's `Profile README` workflow exports `data/profile.json`, rebuilds the README and pushes here whenever the website's content changes on `main`, and daily at 05:41 UTC, which also picks up edits to `data/readme.json`. To sync at once after editing `data/readme.json`, run `gh workflow run "Profile README" -R dominikzabcik/zabcik.me`.

To build or preview locally, run:

```bash
cd ~/website && bun run profile:export ~/orca/dominikzabcik/data/profile.json
cd ~/orca/dominikzabcik && python3 scripts/build_readme.py
scripts/preview.sh --open        # GitHub's own renderer, opens in Chrome
```

`python3 scripts/build_readme.py --out .preview/draft.md` writes a git-ignored draft instead of `README.md` (preview it with `scripts/preview.sh .preview/draft.md --open`). The build needs `fonttools` and `brotli` (`pip3 install fonttools brotli`) and reads Tanker from `~/website/src/fonts/tanker.woff2` (override with `TANKER_FONT`); the font is not committed here. A new skill with a brand mark needs its Simple Icons SVG in `scripts/readme/icons/` and a slug in `data/readme.json`; without one it gets a plain square.

Rendering rules the build follows, verified with `gh api /markdown`: themed images use `#gh-dark-mode-only` and `#gh-light-mode-only` fragments, because GitHub hoists the `<img>` out of a `<picture>` that sits in a link. SVG motion is CSS only and stops under `prefers-reduced-motion`. Text in the SVGs gets small on phones; that is the accepted trade-off for the look.
