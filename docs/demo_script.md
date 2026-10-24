# VERDIQ — 4-minute demo script

**Format:** screen recording at 1920×1080, browser zoom 100 %, dark theme, microphone narration. Total ≈ 4:00 (limit 3-5 min).

**Before recording (not on camera):** run `make data`, then `make run`, open <http://localhost:8501>. Open **Attack Mode**, press **LAUNCH ATTACK** once and wait for the BLOCKED stamp: this boots the local Hardhat node and replays the ledger (≈ 45 s, once). Refresh the browser, make sure the language is **English**, and keep one extra tab open on `http://localhost:8501/?passport=2507189-2508936`.

Numbers on screen are deterministic (seed 42) unless a line says "≈".

---

## 0:00 – 0:25 · The problem (Overview)
**Click:** none, start on **Overview**. Let the counters animate.
**Say:** "Carbon credits only work if one credit means one tonne. Today the same credit can be sold twice, retired twice, claimed by a host country *and* a company, or never have been issued at all. Banks solved this a century ago with a daily three-way reconciliation. Carbon markets never did. This is VERDIQ: every tonne, verified once."

## 0:25 – 0:55 · What VERDIQ found (Overview → Reconciliation)
**Click:** point at the four counters, then the "8/8 · precision 100 % · recall 100 %" tile.
**Say:** "We generated a synthetic carbon market, clearly labelled as synthetic, with eight kinds of fraud injected. VERDIQ reconciles 653 ledger events and catches all eight types with zero false positives. About 55,000 tonnes of claims would have been counted twice: roughly 1.5 million dollars of fraudulent volume, the emissions of 12,000 cars for a year."
**Click:** sidebar **Reconciliation** → tab **Balance per issuance**.
**Say:** "Like a bank balance: every issuance balances to the tonne. Issued equals unsold plus in-market plus retired. The coral hexagons are tonnes the ledger refused."

## 0:55 – 1:30 · Fraud network + Time Machine
**Click:** **Fraud Network**. Hover the coral loop; choose *Tidewater Trading* in the node inspector (or click the node).
**Say:** "The same 8,000 tonnes circle between three trading desks in three weeks while the price doubles: a wash-trading loop. Select a node and you get every flag with its rule, severity and evidence."
**Click:** **Time Machine** → press **▶ Play**, let ~10 months run.
**Say:** "Replay the market month by month. Fraud events pop in at the moment they occur, and the protected-tonnes curve steps up."

## 1:30 – 2:05 · Project-level fraud: map, trust score, greenwashing
**Click:** **Map & Forest Health**: point at the project footprints, then scroll to the P01 / P04 / P08 cards.
**Say:** "Two Sundarbans projects claim 31 percent of the same mangrove polygon. Cusco claims 173 tonnes per hectare where the physical ceiling is 40. Every project gets a 0-100 trust score with a plain-English why. The vegetation series is simulated, and labelled as such."
**Click:** **Greenwashing Checker** (Meridian Airways is preselected).
**Say:** "Meridian Airways told the press it offset 400,000 tonnes. The ledger shows 126,000 validly retired, and only 113,000 from credits with no integrity flags. 28 percent of the claim is backed."

## 2:05 – 3:10 · CLIMAX: Attack Mode
**Click:** **Attack Mode**. Point at the green **REAL CONTRACT LIVE** badge.
**Say:** "Now the part that matters. A fraudster tries to double-count credits, live."
**Click:** **⚡ LAUNCH ATTACK** (type: Random). Pause on the coral shake and the **BLOCKED** stamp.
**Say:** "That was a real transaction against our Solidity registry on a local chain. The contract reverted it with a reason code. Here is the transaction hash, in about two seconds. And independently, the reconciliation engine flagged it: rule R01 or R02, with evidence. Without VERDIQ, these tonnes would have been counted twice."
**Click:** **LAUNCH ATTACK** two more times (once with **Double sale** selected, once with **Double retirement**). Point at the running counters (attacks blocked / tCO₂ protected / USD blocked) and the attack log.
**Say:** "Different attack, same result. Every attempt is blocked, counted, and added to the impact total."

## 3:10 – 3:40 · Proof anyone can check (Day-End Close → Passport)
**Click:** **Day-End Close & Verify**. Point at the root and "ANCHORED ON-CHAIN"; toggle **Tamper with the record**.
**Say:** "Banks close the day. Now carbon markets do too: every month-end snapshot is a Merkle root anchored on-chain. Pick any serial and prove it with a handful of hashes, without seeing the dataset. Change one field and the proof fails."
**Click:** **Tonne Passport** → example **⛔ Double-sold range (Kisumu)**.
**Say:** "Every range gets a passport: timeline, owner chain, trust score, Merkle proof, and the transaction hash of the blocked sale."
**Click:** switch to the open tab `?passport=2507189-2508936`.
**Say:** "This QR opens a public page, no login, so a buyer, a journalist or a regulator can verify a credit in seconds."

## 3:40 – 4:00 · Impact close
**Click:** **Overview**; toggle **বাংলা** in the sidebar, then back to English.
**Say:** "VERDIQ turns carbon credits from promises into audited facts: reconciled daily, blocked on-chain, verifiable by anyone, in Bangla and English. Every tonne, verified once. Thank you."

---

### Backup plan if something stalls
* If Attack Mode shows **PYTHON MIRROR** instead of **REAL CONTRACT LIVE**, the node did not start: run `make chain` in a terminal, refresh, and re-record that segment. The mirror applies identical rules, but the on-chain hash is the stronger shot.
* If a map basemap tile does not load, use the "Zoom to" box; it is cosmetic.
* Optional extras if you finish early: **Pre-Purchase Check** (portfolio health gauge + "what to replace") and **Case Files** (download the PDF for the wash-trade flag).
