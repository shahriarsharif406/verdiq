// Fires ONE attack transaction at the live registry (persistent Hardhat node) and reports whether the firewall blocked it.
//   ATTACK_SPEC='{"kind":"TRADE","actor":"...","counterparty":"...","start":1,"end":2}' npx hardhat run scripts/attack.js --network localhost
// Prints a single line:  RESULT {json}
const L = require("./lib");

async function main() {
  const spec = JSON.parse(process.env.ATTACK_SPEC);
  const replay = JSON.parse(L.fs.readFileSync(L.path.join(L.OUT, "chain_replay.json"), "utf8"));
  const reg = await L.ethers.getContractAt("VerdiqRegistry", replay.contract);
  const signer = await L.signerFor(L.addr(spec.actor));
  const c = reg.connect(signer);
  const isTrade = spec.kind === "TRADE";
  const fn = isTrade ? "transfer" : "retire";
  const args = isTrade ? [spec.start, spec.end, L.addr(spec.counterparty)] : [spec.start, spec.end, L.claimHash(spec.counterparty)];
  const t0 = Date.now();
  let reason = "";
  try { await c[fn].staticCall(...args); } catch (e) { reason = L.reasonOf(e); }
  // advance time by a block so the attack happens "now" on the chain
  const tx = await c[fn](...args, { gasLimit: 15_000_000 });
  const rc = await tx.wait().catch((e) => e.receipt);
  const ok = !!rc && rc.status === 1;
  const block = await L.ethers.provider.getBlock(rc.blockNumber);
  console.log("RESULT " + JSON.stringify({
    source: "hardhat-node", contract: replay.contract, accepted: ok, reason: ok ? "" : reason, txHash: tx.hash,
    block: rc.blockNumber, gasUsed: Number(rc.gasUsed), ms: Date.now() - t0, chainTime: block.timestamp,
  }));
}

main().catch((e) => { console.log("RESULT " + JSON.stringify({ error: String(e.message || e) })); process.exit(0); });
