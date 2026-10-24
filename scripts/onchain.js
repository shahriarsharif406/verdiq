// Reads the Day-End Close root anchored on-chain for DATE (yyyymmdd) from the live node. Prints: ROOT <hex|none>
const L = require("./lib");
async function main() {
  const replay = JSON.parse(L.fs.readFileSync(L.path.join(L.OUT, "chain_replay.json"), "utf8"));
  const reg = await L.ethers.getContractAt("VerdiqRegistry", replay.contract);
  const root = await reg.closeRoot(Number(process.env.CLOSE_DATE));
  console.log("ROOT " + (root === L.ethers.ZeroHash ? "none" : root.slice(2)));
}
main().catch((e) => { console.log("ROOT error"); process.exit(0); });
