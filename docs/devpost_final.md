## Inspiration
Carbon credits fail on trust. The same credit can be sold twice, retired twice, or never have been issued. Two projects can be paid for overlapping project areas, and a host country and a corporate buyer can both claim the same tonne. I come from a banking-reconciliation background, where voucher, ledger and payment are matched every day. Carbon markets have no equivalent, so I set out to build one and make the result verifiable by anyone, not just insiders. The name is verdict + verde: a verdict on every carbon credit. Track: Carbon Markets & Emissions Transparency.

## What it does
VERDIQ is a three-way reconciliation engine for carbon credits: registry issuance x market trades x retirements, matched on an interval ledger of serial ranges. Every event is classified (matched, unissued, orphan, double sold, double retired, retired but not owned).

- Smart-contract firewall: a Solidity registry reverts overlapping issuance, transfers of unowned or retired credits, second retirements and conflicting host-country claims.
- Attack Mode: one click injects a fresh double sale or double retirement; the real contract blocks it with a transaction hash and the engine flags it.
- Day-End Close: each day's market state is a Merkle root anchored on-chain, so one credit can be verified with a short proof.
- Tonne Passport: a shareable certificate with a QR code that opens a public verification page.
- Trust Score: 0-100 per project and credit range, with a plain-English reason.
- Fraud Network graph, Time Machine (month by month), Greenwashing Checker, Portfolio Health for buyers, and an impact counter.
- Bangla / English toggle.

## How we built it
Python engine with pandas, shapely (polygon overlap), networkx (wash-trade cycles) and scikit-learn (Isolation Forest). The contract is Solidity with Hardhat tests that replay each fraud case. The app is Streamlit with Plotly, with a public passport route and QR codes. A deterministic synthetic generator injects ground-truth fraud cases. Built with Claude Code under my direction.

## Challenges we ran into
- Keeping fragmented ownership of serial ranges (partial overlaps, splits) in exact agreement between Python and Solidity.
- Being honest about limits. All data is synthetic and the NDVI vegetation series is simulated. Detection was verified only against fraud cases we injected ourselves, so our recall there says nothing about real-world recall.
- The contract cannot see wash trading, price spikes, polygons or greenwashing. The engine covers those, and we made that split explicit instead of overselling the chain.
- It runs on a local Hardhat chain, not a testnet.

## Accomplishments that we're proud of
- All 8 injected fraud types were detected in our synthetic test.
- Real contract blocking in Attack Mode: the transaction reverts on-chain, live.
- A public repo that runs from a clean clone.

## What we learned
Ownership and uniqueness can be enforced at the transaction, while geometry, statistics and claims need an off-chain engine. The two work best together, with both sets of rules tested for exact agreement. Bank-style reconciliation transfers well to carbon markets because serial numbers give every tonne an identity. Small synthetic samples make statistics like Benford's law only a relative hint.

## What's next for VERDIQ
- Ingest real registry data from serial-level public registries.
- Testnet deployment of the contract.
- Real satellite data in place of the simulated NDVI.
- Pilot with a verifier.

Demo video: https://youtu.be/Oz-Mwghk9Zw
Repo: https://github.com/shahriarsharif406/verdiq
