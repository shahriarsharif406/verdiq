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
