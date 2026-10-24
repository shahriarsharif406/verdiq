# VERDIQ architecture

```mermaid
flowchart LR
  subgraph Data["Synthetic data (data/generate.py, seed 42)"]
    R[registry_issuances.csv]; T[market_trades.csv]; X[retirements.csv]; H[host_country_claims.csv]; C[corporate_claims.csv]
  end
  subgraph Engine["engine/ (Python: pandas, shapely, networkx, scikit-learn)"]
    M[match.py<br/>interval ledger replay]; G[geo.py R04]; P[plausibility.py R05]; A6[article6.py R06]; W[wash.py R07/R08]; GW[greenwash.py R09]
    S[score.py<br/>rules + IsolationForest + Benford]; MK[merkle.py<br/>Day-End Close]; N[ndvi_sim.py<br/>SIMULATED]; PP[passport.py]; CF[casefile.py]
  end
  subgraph Chain["contracts/ (Solidity + Hardhat)"]
    V[VerdiqRegistry.sol<br/>issue / transfer / retire<br/>registerHostClaim / anchorClose / verifyRecord]
  end
  subgraph App["app/ (Streamlit, 12 pages + public passport route)"]
    UI[Midnight Forest UI<br/>EN / বাংলা]
  end
  Data --> M & G & P & A6 & W & GW
  M & G & P & A6 & W & GW --> S --> UI
  M --> MK -->|root| V
  M -->|ledger events| V
  V -->|tx hashes, reverts, anchors| UI
  UI -->|Attack Mode| V
  MK --> PP --> UI
  PP & CF --> UI
```

## Data flow

1. `data/generate.py` writes five CSVs + `ground_truth.json` (seed 42).
2. `engine/pipeline.py` replays issuance → trades → retirements chronologically on an interval ledger, runs the geo / plausibility / Article 6 / wash / price / greenwashing rules, scores trust, and builds a Merkle Day-End Close at every month end (`data/out/`).
3. `scripts/replay.js` replays the same ordered events against `VerdiqRegistry.sol` (parties are impersonated deterministic addresses), records reverts and tx hashes, and anchors each close root (`data/out/chain_replay.json`).
4. The Streamlit app reads both and joins them: flags show the on-chain revert, passports show tx hashes and Merkle proofs, Attack Mode fires a fresh transaction at the live node (`scripts/attack.js`).

## Hash scheme (Python and Solidity agree)

`leaf = sha256(0x00 || canonical_json(record))`, `parent = sha256(0x01 || min(l,r) || max(l,r))`. A Python-generated proof is verified by `VerdiqRegistry.verifyRecord` in the Hardhat suite.
