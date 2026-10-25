# PROGRESS (live checklist)

## Done
- [x] 1 scaffold + synthetic data generator (11 projects, fixed seed, 11 injected fraud cases, ground_truth.json)
- [x] 2 engine (match, geo, plausibility, article6, wash, score, merkle, greenwash, ndvi_sim, passport, casefile) + 24 pytest tests, 8/8 fraud types, precision = recall = 1.00
- [x] 3 VerdiqRegistry.sol + 13 Hardhat tests + replay.js (657 txs, 7 blocked, 653/653 engine parity, 44 anchored closes) + attack.js + persistent-node bridge
- [x] 4 dashboard: Midnight Forest theme, 12 pages + public ?passport= route, all smoke-tested in a real browser (Playwright)
- [x] 5 features A-K: Day-End Close+Merkle, Attack Mode, Tonne Passport (QR), Trust Score, Fraud Network, Time Machine, Greenwashing, Pre-Purchase, Case Files (MD+PDF), Forest Health (simulated), Impact Counter
- [x] 6 Bangla/English toggle, README, architecture, screenshots (docs/screenshots)
- [x] 7 docs/demo_script.md, docs/devpost_description.md, docs/DECISIONS.md, HUMAN_TODO.md
- [x] clean-clone verification: setup -> data -> test -> replay OK; app runs with no chain replay present (fallbacks work)

## Next (human): see HUMAN_TODO.md

## Final-run log (Oct 25)
- [x] 1 Video: final encode re-run (earlier encode was cut off). docs/demo/verdiq_demo.mp4 267.0 s (4:27) = narration.mp3 267.0 s; 53 frames inspected every 5 s, no errors/stack traces/empty maps; two ~0.5 s navigation flashes (at ~230 s and ~237 s) accepted. Also verdiq_demo_silent.mp4, narration.mp3, demo.srt.
- [x] 2 Regression: pytest 24 passed, Hardhat 13 passing; fresh clone in temp folder (python verdiq.py data/replay/chain) = 8/8 fraud types, precision/recall 1.00, 44 closes anchored; Attack Mode in the clone via Playwright: double sale + double retirement both BLOCKED with green REAL CONTRACT LIVE (no PYTHON MIRROR), no exceptions.
- [x] 3 README: Windows / no make section + AI assistance disclosure (honest limits section already present)
- [x] 4 Secret scan: working tree + all 8 commits clean (no API keys/tokens/.env/personal paths; VERDIQ_PROMPT.md (the build brief, no secrets) was committed in bc04250 and removed in e50b15d; it stays visible in history, judged harmless); .gitignore extended (.env.*, *.pem, *.key, *.log, secrets). Only public identity in history = git author name/email.
- [x] 5 docs/devpost_description.md rewritten (problem, solution, track, how it works, stack, challenges, next, limits, AI disclosure, repo link; only the YouTube URL is a placeholder) + docs/devpost_short_fields.md (tagline, 188-char summary, tags, YouTube title/description with chapters).
- [x] 6 Screenshots refreshed (scripts/smoke.py --shots: all 14 pages OK, Attack Mode shows REAL CONTRACT LIVE). DECISIONS 21-24 added. HUMAN_TODO.md rewritten as short checklist.
- [x] 7 Pushed to origin/main (f778b95), verified with git log origin/main. 8 HUMAN_TODO final. ALL DONE.
- [x] Follow-up: final tests 24+13 pass, Attack Mode real contract OK; contact_sheet.png added. gh release FAILED: gh account shahariar-ai has READ-only on shahriarsharif406/verdiq (and lacks workflow scope).
