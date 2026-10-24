# VERDIQ — Every tonne, verified once.

*IEEE ClimateChain Global Hackathon · Track: Carbon Markets & Emissions Transparency*

> **All data in the demo is synthetic and all vegetation series are simulated.** No real registry, company or government is involved or implied.

## Inspiration
Carbon credits fail on trust. The same credit can be sold twice, retired twice, claimed by a host country *and* a corporate buyer, or never have been issued; two projects can be paid for the same forest; a company can announce more offsets than it retired. Banks solved this decades ago with a daily three-way reconciliation of voucher, ledger and payment. Carbon markets have no equivalent. We wanted to build one, and make the result verifiable by anyone, not just insiders. The name is *verdict* + *verde*: a verdict on every carbon credit. We built Bangladesh-first (a Bangla / English interface; Sundarbans and Cumilla projects in the data) and global-ready.

## What it does
**VERDIQ is a bank-grade three-way reconciliation engine for carbon credits, with a blockchain firewall that makes double counting impossible and a public "Tonne Passport" anyone can verify.**

* **Reconciles** registry issuance × market trades × retirements on an interval ledger of serial ranges and classifies every event: MATCHED, UNISSUED, ORPHAN, DOUBLE_SOLD, DOUBLE_RETIRED, RETIRED_NOT_OWNED.
* **Detects** polygon overlaps, physically impossible yields, Article 6 host-country double claims, wash-trading loops, price spikes and greenwashing claims. Every flag carries a rule id, severity, evidence rows and a plain-language reason.
* **Blocks** double counting at the transaction: a Solidity registry reverts overlapping issuance, transfers of unowned or retired credits, second retirements and conflicting host-country claims.
* **Proves**: every day's market state is a Merkle root anchored on-chain (Day-End Close). Anyone can verify one credit with a short proof without seeing the dataset, and each credit range has a shareable **Tonne Passport** (gold certificate + QR → public verification page).
* **Explains**: 0-100 trust scores per project and credit range from rule flags + Isolation Forest + Benford's law, each with a plain-English "why".
* **Attack Mode**: one click injects a fresh random double-sale or double-retirement; the audience watches the real contract revert it (with a transaction hash) and the engine flag it within seconds.
* Plus a fraud-network graph, a month-by-month **Time Machine**, a buyer **pre-purchase check and portfolio health** score, a **greenwashing claim checker**, one-click **auditor case files** (Markdown/PDF, optional LLM summary with a template fallback), a simulated **forest-health** view and an animated **Climate Impact Counter**.

**Results on the synthetic benchmark:** 11 injected fraud cases across all 8 fraud types → **8/8 types detected, precision 1.00, recall 1.00** over 653 ledger events. A 657-transaction on-chain replay blocks 7 fraudulent transactions, and the contract and the engine agree on every ledger event. In the demo market, ~55,000 tCO₂ of claims (≈ US$1.5 M of volume) would have been counted twice.

## Track alignment — Carbon Markets & Emissions Transparency
* **Transparency:** public QR passports, evidence-backed flags, tamper-evident daily closes.
* **Market integrity:** double selling, double retiring and host-vs-buyer double claiming are blocked *when attempted*, not discovered a year later.
* **Climate impact:** a tonne that is not double-counted is a tonne of mitigation that has to actually happen. The Impact Counter converts blocked claims into car-years and tree-seedlings (US EPA factors, documented in the README).
* **Practical usefulness:** one engine, three audiences: registries and regulators, buyers, civil society and journalists. Real registries publish serial-level data, so ingestion is a column mapping.

## How we built it
* **Data:** a deterministic synthetic generator (11 projects in Bangladesh, Kenya, Peru, Indonesia and Vietnam; ~650 ledger events) with ground-truth fraud cases injected.
* **Engine (Python):** pandas, shapely (polygon intersection area), networkx (cycle detection for wash trades), scikit-learn (Isolation Forest), a sorted-interval ownership ledger with split-on-write, and a Merkle tree (sha256, sorted-pair hashing).
* **Contract (Solidity 0.8 + Hardhat):** `VerdiqRegistry` keeps a sorted array of disjoint serial segments with binary search and splitting: `issue / transfer / retire / registerHostClaim / anchorClose / verifyRecord`. 13 Hardhat tests replay each fraud case, and a Python-generated Merkle proof is verified on-chain in the suite. `scripts/replay.js` replays the full ledger with deterministic impersonated addresses.
* **App (Streamlit + Plotly):** the "Midnight Forest" design system (glass cards, hexagon motif, Space Grotesk / Inter / JetBrains Mono), animated counters, 12 pages, a public `?passport=` route, QR codes and a Bangla / English toggle. A Playwright smoke test loads every page in a real browser.

## Challenges
* Making fragmented ownership of *ranges* correct in both Python and Solidity (partial overlaps, straddling ranges, splits) and keeping the two in exact agreement.
* Deciding what a contract can and cannot know: ownership and uniqueness are enforceable on-chain; polygons, price manipulation and greenwashing are not. We made that split explicit instead of overselling the chain.
* Getting meaningful statistics from small synthetic samples: Benford's law is only a relative hint, and Isolation Forest contributes a bounded penalty.
* Keeping the demo honest: everything is labelled synthetic or simulated, and nothing implies a real partnership or dataset.

## What's next
* Ingest real public registry exports (serial-level issuance and retirement) into the three-table schema.
* Satellite-backed forest evidence in place of the simulated NDVI; cross-checks against national NDC accounting for Article 6.
* An L2 / Sepolia deployment with an interval-tree contract and role-based registry authorities.
* A public API and embeddable verification widget so any marketplace can show a passport badge.
* Full Bangla localisation of every string and a mobile-first public verifier.

## Built with
Python · pandas · shapely · networkx · scikit-learn · Streamlit · Plotly · qrcode · fpdf2 · Solidity · Hardhat · ethers · Playwright · (optional) Claude API

## Links
* GitHub: https://github.com/shahriarsharif406/verdiq
* Demo video: *(add the YouTube URL)*
