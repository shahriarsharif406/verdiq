# Decisions log (autonomous build, no questions asked)

| # | Ambiguity | Decision | Why |
|---|---|---|---|
| 1 | Serial format | Integer serials, project *k* owns `[k*2,000,000, (k+1)*2,000,000)`; displayed as `VQ-00000000`. | Makes interval maths exact and lets the engine tell "unissued in a known project" from "outside every project" instantly. |
| 2 | Extra CSVs | Added `host_country_claims.csv` and `corporate_claims.csv`, plus `issuance_id`, `developer`, `issuance_date` columns on issuances. | Article 6 and greenwashing need data the three specified CSVs cannot hold; developer = first owner. |
| 3 | Status vocabulary | `UNISSUED` = outside issuance; `ORPHAN` = issued but the seller never held it; `DOUBLE_SOLD` = seller already sold it; `DOUBLE_RETIRED`; `RETIRED_NOT_OWNED` = retirer is not the owner / trading retired credits. | Spec lists the six statuses but not their semantics. |
| 4 | Invalid events | Flagged and **not applied** to the ledger. | Mirrors what the contract does (reverts), keeps engine and chain in lock-step (568/568 agreement). |
| 5 | Chain | Local Hardhat only (no Sepolia). Parties = deterministic addresses derived from names, driven through `hardhat_impersonateAccount`. | Spec says no testnet required; avoids needing 30+ funded signers. |
| 6 | Persistent chain | Attack Mode boots `hardhat node` (127.0.0.1:8545) and replays the ledger on first use; falls back to a Python mirror of the contract rules if Node is missing. The result says which `source` was used. | Each attack must be a real tx with a real hash and take seconds, not a minute. |
| 7 | Hash function | sha256 (not keccak) for the Merkle tree. | Native in Python `hashlib` and Solidity `sha256()`, so proofs verify in both with no extra dependency. |
| 8 | Contract vs engine scope | Contract enforces ownership/uniqueness/Article 6 conflicts; wash trading, price spikes, geo overlap, yield and greenwashing are engine-only. | A contract cannot see polygons or intent; documented honestly in the README. |
| 9 | Host claim vs retirement ordering | If a host claim without corresponding adjustment arrives after the buyer retired, the *claim* is rejected (`HOST_DOUBLE_CLAIM`); if before, the *retirement* is. | First-come wins on-chain; the engine flags the claim as R06 either way. |
| 10 | Trust tiers | Project: VERIFIED ≥ 85, RISKY 55-85, BLOCKED < 55. Range: BLOCKED if any CRITICAL flag touches it, RISKY if any flag or score < 75, else SAFE. | A clean range inside an otherwise troubled project is still safe to buy; project health only softens the score. |
| 11 | Benford | Penalty is *relative* to the portfolio median deviation. | Synthetic trade sizes are not Benford-distributed for any project; absolute thresholds would penalise everyone equally. |
| 12 | NDVI | Deterministic seeded series, P04 generated to decline; excluded from the fraud ground truth, only a −10 pt score penalty and a map card. | Required to be clearly simulated; not a detection claim. |
| 13 | Emojis / icons | Sidebar icons use emoji known to render on Windows (no 🪪). | Tofu boxes in the screenshots. |
| 14 | `make` on Windows | `verdiq.py` is the real runner; the Makefile delegates to it. | Stock Windows has no `make`; the same tasks work everywhere. |
| 15 | LLM summaries | Only used if `ANTHROPIC_API_KEY` is set and the `anthropic` package is installed (not in requirements); template otherwise. | Project must work without any key. |
| 16 | Hardhat config | `hardfork: cancun`, large block gas limit, `throwOnTransactionFailures` only off for replay (env `VERDIQ_REPLAY`). | Newer hardforks cap tx gas at 16.7M; chai `revertedWith` needs throwing mode in tests, replay needs mined failed txs for their hashes. |
