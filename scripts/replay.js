// Replays the whole synthetic ledger on-chain (Hardhat) in chronological order, anchors every month-end close,
// and records which transactions the contract BLOCKED. Writes data/out/chain_replay.json.
//   npx hardhat run scripts/replay.js                       (in-process chain)
//   npx hardhat run scripts/replay.js --network localhost   (persistent node, used by the dashboard's Attack Mode)
const L = require("./lib");
const { ethers } = L;

async function main() {
  const t0 = Date.now();
  const events = L.parseCsv(L.path.join(L.OUT, "reconciliation_events.csv"));
  const issuances = L.parseCsv(L.path.join(L.DATA, "registry_issuances.csv")).sort((a, b) => a.serial_start - b.serial_start);
  const hostClaims = L.parseCsv(L.path.join(L.DATA, "host_country_claims.csv"));
  const closes = JSON.parse(L.fs.readFileSync(L.path.join(L.OUT, "closes.json"), "utf8"));

  const [deployer] = await ethers.getSigners();
  const reg = await (await ethers.getContractFactory("VerdiqRegistry")).deploy();
  await reg.waitForDeployment();
  const address = await reg.getAddress();

  let lastTs = 0;
  const stamp = async (iso, endOfDay = false) => {
    let ts = L.dayStart(iso) + (endOfDay ? 86399 : 3600);
    if (ts <= lastTs) ts = lastTs + 1;
    lastTs = ts;
    await L.hre.network.provider.send("evm_setNextBlockTimestamp", [ts]);
  };

  // 1. issuance (registry authority)
  for (const i of issuances) {
    await stamp(i.issuance_date);
    const tx = await reg.issue(L.addr(i.developer), ethers.encodeBytes32String(i.project_id), i.serial_start, i.serial_end, i.vintage_year);
    await tx.wait();
  }

  // 2. timeline: events, host claims, month-end anchors
  const items = [];
  events.forEach((e, k) => items.push({ d: e.date, o: 1, k, type: "event", e }));
  hostClaims.forEach((h, k) => items.push({ d: h.date, o: 2, k, type: "host", h }));
  Object.keys(closes).forEach((d) => items.push({ d, o: 9, k: 0, type: "anchor" }));
  items.sort((a, b) => (a.d < b.d ? -1 : a.d > b.d ? 1 : a.o - b.o || a.k - b.k));

  const txs = [], anchors = [];
  let accepted = 0, reverted = 0, agree = 0;
  const disagreements = [];
  for (const it of items) {
    if (it.type === "anchor") {
      await stamp(it.d, true);
      const c = closes[it.d];
      const tx = await reg.anchorClose(Number(it.d.replaceAll("-", "")), "0x" + c.root);
      const rc = await tx.wait();
      anchors.push({ date: it.d, root: c.root, txHash: tx.hash, block: rc.blockNumber, leaves: c.n_leaves, disputed: c.n_disputed });
      continue;
    }
    if (it.type === "host") {
      const h = it.h;
      await stamp(h.date);
      const args = [L.country2(h.country), h.serial_start, h.serial_end, String(h.corresponding_adjustment) === "True"];
      let reason = "";
      try { await reg.registerHostClaim.staticCall(...args); } catch (e) { reason = L.reasonOf(e); }
      const tx = await reg.registerHostClaim(...args, { gasLimit: 5_000_000 });
      const rc = await tx.wait().catch((e) => e.receipt);
      const ok = rc && rc.status === 1;
      ok ? accepted++ : reverted++;
      txs.push({ id: h.claim_id, kind: "HOST_CLAIM", date: h.date, ok, reason: ok ? "" : reason, txHash: tx.hash, block: rc ? rc.blockNumber : null,
                 gasUsed: rc ? Number(rc.gasUsed) : null, engineStatus: String(h.corresponding_adjustment) === "True" ? "MATCHED" : "ARTICLE6_DOUBLE_CLAIM" });
      continue;
    }
    const e = it.e;
    await stamp(e.date);
    const signer = await L.signerFor(L.addr(e.actor));
    const c = reg.connect(signer);
    const isTrade = e.kind === "TRADE";
    const args = isTrade ? [e.serial_start, e.serial_end, L.addr(e.counterparty)] : [e.serial_start, e.serial_end, L.claimHash(e.counterparty)];
    const fn = isTrade ? "transfer" : "retire";
    let reason = "";
    try { await c[fn].staticCall(...args); } catch (err) { reason = L.reasonOf(err); }
    const tx = await c[fn](...args, { gasLimit: 15_000_000 });
    const rc = await tx.wait().catch((er) => er.receipt);
    const ok = rc && rc.status === 1;
    ok ? accepted++ : reverted++;
    const engineOk = e.status === "MATCHED";
    if (engineOk === ok) agree++; else disagreements.push({ id: e.event_id, engine: e.status, chain: ok ? "ACCEPTED" : reason });
    txs.push({ id: e.event_id, kind: e.kind, date: e.date, ok, reason: ok ? "" : reason, txHash: tx.hash, block: rc ? rc.blockNumber : null,
               gasUsed: rc ? Number(rc.gasUsed) : null, engineStatus: e.status });
  }

  const out = {
    events_sha256: require("crypto").createHash("sha256").update(L.fs.readFileSync(L.path.join(L.OUT, "reconciliation_events.csv"))).digest("hex"),
    network: L.hre.network.name, contract: address, authority: deployer.address, generated_by: "scripts/replay.js",
    seconds: (Date.now() - t0) / 1000, total_txs: txs.length, accepted, reverted,
    engine_chain_agreement: { agree, of: events.length, disagreements },
    blocked: txs.filter((t) => !t.ok), txs, anchors,
    parties: Object.fromEntries([...new Set(events.flatMap((e) => [e.actor, e.counterparty]).concat(issuances.map((i) => i.developer)))]
      .filter((n) => n).map((n) => [n, L.addr(n)])),
  };
  L.fs.mkdirSync(L.OUT, { recursive: true });
  L.fs.writeFileSync(L.path.join(L.OUT, "chain_replay.json"), JSON.stringify(out, null, 1));
  console.log(`replayed ${txs.length} txs on ${out.network} in ${out.seconds.toFixed(1)}s: accepted ${accepted}, BLOCKED ${reverted}`);
  console.log(`engine/contract agreement: ${agree}/${events.length}`, disagreements.length ? disagreements : "");
  for (const b of out.blocked) console.log(`  BLOCKED ${b.id} ${b.kind} -> ${b.reason}  tx ${b.txHash.slice(0, 18)}…`);
  console.log(`anchored ${anchors.length} Day-End Close roots`);
}

main().catch((e) => { console.error(e); process.exit(1); });
