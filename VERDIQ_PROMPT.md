# VERDIQ: Claude Code Master Prompt

Paste everything below into Claude Code in an empty folder named `verdiq`.

---

You are my senior full-stack engineer and product designer. We have **about 20 hours** to build and submit a hackathon project. Build fast, keep it working end to end, commit often. Visual quality matters as much as engineering: judges see the demo first.

## Context
Hackathon: IEEE ClimateChain Global Hackathon (Devpost), Track: **Carbon Markets & Emissions Transparency**. Judging: Climate Impact, Innovation, Technical Execution, Practical Usefulness, Presentation. Submission: public GitHub repo, 3-5 minute demo video, project description.

## Product: VERDIQ
**Tagline: "Every tonne, verified once."**
Name = *verdict* + *verde* (green): a verdict on every carbon credit.

**One-line pitch:** VERDIQ is a bank-grade three-way reconciliation engine for carbon credits, with a blockchain firewall that makes double counting impossible and a public "Tonne Passport" anyone can verify.

Carbon credits fail on trust: the same credit is sold twice, the same forest is claimed by two projects, and the host country and the buyer both count the same tonne. VERDIQ applies banking reconciliation (voucher vs ledger vs payment, daily close) to carbon credits.

## Visual theme: "Midnight Forest"
Build a distinctive, premium look, not default Streamlit.
- **Palette:** deep forest-black background `#06130F`, panel `#0C2019`, emerald `#10B981`, aurora teal `#2DD4BF`, verified gold `#F5C451`, alert coral `#FB7185`, warn amber `#FBBF24`, text `#E7F5EE`, muted `#8FB5A3`.
- **Style:** glassmorphism cards (translucent panels, 1px emerald border, soft glow), subtle gradient aurora header, hexagon motif (logo, badges, background pattern).
- **Type:** Space Grotesk for headings, Inter for body, JetBrains Mono for serial numbers and hashes (load via Google Fonts in injected CSS).
- **Logo:** an SVG hexagon with a leaf and a check mark, drawn in code, shown in sidebar and README.
- **Charts:** Plotly with a custom dark template matching the palette. Map: pydeck or folium dark tiles.
- **Motion:** animated number counters for headline metrics, a pulsing "LIVE" dot, smooth status badges (VERIFIED gold, RISKY amber, BLOCKED coral).
- Put all theme code in `app/theme.py` (CSS + helpers) and reuse it on every page. Set `.streamlit/config.toml` to match. Must look good in a screen recording at 1080p.
- **Bangla/English toggle** in the sidebar for all UI labels and headline text (`app/i18n.py`). Bangladesh-first, global-ready.

## Core (must work, build in this order)

### 1. Synthetic data generator (`data/generate.py`)
Realistic CSVs, fixed seed:
- `registry_issuances.csv`: project_id, project_name, serial_start, serial_end, vintage_year, country, methodology, issued_tco2, polygon_wkt, area_ha
- `market_trades.csv`: trade_id, serial_start, serial_end, seller, buyer, price_usd, date
- `retirements.csv`: retirement_id, serial_start, serial_end, retiring_entity, claimed_for, date
- ~8 projects including Bangladesh (Sundarbans mangrove restoration, improved cookstoves in Cumilla), Kenya, Peru, Indonesia, Vietnam.
- Inject **known fraud cases** and write them to `data/ground_truth.json`:
  1. Same serial range sold to two buyers
  2. Same serial range retired twice
  3. Credits traded or retired that were never issued
  4. Two projects with overlapping polygons
  5. Claimed sequestration above the physical ceiling for the area
  6. Host country and corporate buyer both claim the same tonnes (Article 6 style)
  7. Wash-trading loop (A to B to A) and a suspicious volume/price spike
  8. A greenwashing claim: a company publicly claims more offsets than it actually retired

### 2. Reconciliation engine (`engine/`)
Python, pandas, shapely, networkx. Serial ranges are intervals: use proper interval overlap logic.
- Three-way match with statuses `MATCHED`, `UNISSUED`, `DOUBLE_SOLD`, `DOUBLE_RETIRED`, `RETIRED_NOT_OWNED`, `ORPHAN`.
- Geo-overlap check (polygon intersection area), physical plausibility check (tCO2/ha/year vs methodology ceiling table, assumptions documented), Article 6 double-claim check, wash-trade detector.
- Every flag carries: rule id, severity, evidence rows, plain-language reason.

### 3. Smart contract firewall (`contracts/`, Hardhat + Solidity)
- `VerdiqRegistry.sol`: issue(range), transfer(range, to), retire(range, claimedFor), anchorClose(date, merkleRoot).
- Revert on overlapping issuance, transferring unowned or retired credits, retiring twice, and a second claim on the same tonnes.
- Emit events for every state change.
- Hardhat tests replay the fraud cases and show each reverting. Local network, no testnet required (Sepolia optional if time remains).
- `scripts/replay.js` replays the ledger and logs which fraudulent transactions get blocked.

## Signature features (priority order after core works)

### A. Day-End Close + Merkle proof (priority 1)
Each run produces a reconciliation snapshot, hashed into a Merkle tree, root anchored on-chain. Anyone can verify one credit via a Merkle proof without seeing the whole dataset. Banks close the day, carbon markets don't.

### B. Attack Mode (priority 2)
Dashboard button injects a fresh random double-sale or double-retire attempt live. The audience watches the contract revert it and the engine flag it within seconds, with a coral alert animation and a "BLOCKED" stamp. This is the demo's centerpiece.

### C. Tonne Passport (priority 3)
Every credit range gets a shareable verification page: timeline (issued, traded, retired), owner chain, trust score, Merkle proof status, and a **QR code** (qrcode lib) that opens a public verify view (`?passport=<serial>` route in the Streamlit app). Styled like a gold-edged digital certificate with the hexagon seal.

### D. Trust Score with explanations (priority 4)
0-100 per project and credit range: rule flags + **Isolation Forest** on trade features + **Benford's law** on reported volumes. Show a plain-English "why" next to each score. Offline, no paid APIs.

### E. Fraud Network Graph (priority 5)
Interactive entity graph (pyvis or plotly): sellers, buyers, projects as nodes; trades as edges; wash-trade loops and double-sold clusters glow coral. Click a node to see its flags.

### F. Time Machine (priority 6)
A date slider replays the market month by month: metrics, map, and graph update, and fraud events pop in at the moment they occur. Great for the video.

### G. Greenwashing Claim Checker (priority 7)
Input a company name and a claim ("we offset 100,000 tCO2"). Output: claimed vs actually retired vs actually retired from clean, verified credits, with a verdict gauge and a case summary. Includes the injected greenwashing case.

### H. Buyer Pre-Purchase Check and Portfolio Health (priority 8)
Paste serial ranges or a whole portfolio: per-range verdict SAFE / RISKY / BLOCKED, overall portfolio health score, and "what to replace" suggestions with safer alternatives from the dataset.

### I. Auditor Case File export (priority 9)
One click generates a Markdown/PDF case file per flagged item: timeline, evidence rows, rule triggered, blocking tx hash, Merkle proof. Optional LLM-written summary if an API key is set; **must fall back to template text** when not.

### J. Forest Health Simulator (priority 10)
Synthetic NDVI-style time series per project (generated, clearly labelled simulated). Flag projects whose claimed sequestration grows while the simulated vegetation signal declines. Small sparkline cards on the project page.

### K. Climate Impact Counter (always on)
Headline metrics on the Overview: tonnes of CO2 claims protected from double counting, fraudulent USD volume blocked, plus friendly equivalents (cars off the road for a year, trees). Animated counters. Label equivalents' conversion factors in the README.

## Dashboard pages (`app/`, Streamlit multipage)
Overview (hero + animated metrics + LIVE pulse), Reconciliation, Map, Trust Scores, Fraud Network, Time Machine, Pre-Purchase Check, Greenwashing Checker, Attack Mode, Day-End Close and Verify, Tonne Passport, Case Files. Consistent theme, no clutter, empty states handled, no stack traces visible.

## Repo structure
```
verdiq/
  README.md (hero banner, badges, screenshots), LICENSE (MIT), requirements.txt, package.json, Makefile
  .streamlit/config.toml
  data/ (generate.py, ground_truth.json, *.csv)
  engine/ (match.py, geo.py, plausibility.py, article6.py, wash.py, score.py, merkle.py, greenwash.py, ndvi_sim.py)
  contracts/ (VerdiqRegistry.sol), test/, scripts/
  app/ (streamlit_app.py, theme.py, i18n.py, pages/)
  docs/ (architecture mermaid, demo_script.md, devpost_description.md, screenshots/)
```

## Quality bar
- `make setup`, `make data`, `make test`, `make run` work from a clean clone.
- Engine tests: every injected fraud case in `ground_truth.json` must be detected. Report precision/recall in the README ("detected 8/8 injected fraud types").
- README: problem, solution, architecture diagram, track alignment, run instructions, scalability (real registries such as Verra and Gold Standard publish serial-level data, so the engine can ingest it), limitations, and clear statement that all data is **synthetic** and the NDVI series is **simulated**.
- No fake claims of real partnerships or real data anywhere.
- Take polished screenshots into `docs/screenshots/` for the README and Devpost.

## Time plan, follow it
1. Hours 0-2: scaffold, theme, data generator, ground truth
2. Hours 2-5: engine plus tests
3. Hours 5-8: smart contract plus Hardhat tests plus replay
4. Hours 8-11: dashboard core pages in the Midnight Forest theme
5. Hours 11-16: signature features in the priority order above (A, B, C first)
6. Hours 16-18: polish, Bangla toggle, README, screenshots
7. Remaining time: demo video and submission

## Rules
- Small steps. After each, run tests and commit.
- If a feature threatens the schedule, cut it from the bottom of the priority list and tell me. A working core plus A, B, C beats everything half done.
- Ask me only if truly blocked; otherwise decide and note it in the README.
- Finish by writing `docs/demo_script.md` (a 4-minute script with exact clicks and talking points, opening with the problem, Attack Mode as the climax, closing with impact) and `docs/devpost_description.md` (problem, solution, track alignment, how it was built, challenges, what's next).

Start now with step 1.
