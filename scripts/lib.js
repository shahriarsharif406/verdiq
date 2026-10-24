const fs = require("fs");
const path = require("path");
const hre = require("hardhat");
const { ethers } = hre;

const ROOT = path.join(__dirname, "..");
const DATA = path.join(ROOT, "data");
const OUT = path.join(DATA, "out");

function parseCsv(file) {
  const text = fs.readFileSync(file, "utf8").replace(/^﻿/, "");
  const rows = [];
  let row = [], cell = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (c === '"') q = false;
      else cell += c;
    } else if (c === '"') q = true;
    else if (c === ",") { row.push(cell); cell = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell); cell = "";
      if (row.length > 1 || row[0] !== "") rows.push(row);
      row = [];
    } else cell += c;
  }
  if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
  const head = rows.shift();
  return rows.map((r) => Object.fromEntries(head.map((h, i) => [h, r[i]])));
}

/** Deterministic address for a named party (synthetic identities). */
function addr(name) {
  return ethers.getAddress("0x" + ethers.keccak256(ethers.toUtf8Bytes(name)).slice(26));
}

const signers = {};
async function signerFor(address) {
  if (!signers[address]) {
    await hre.network.provider.send("hardhat_impersonateAccount", [address]);
    await hre.network.provider.send("hardhat_setBalance", [address, "0x56BC75E2D63100000"]);
    signers[address] = await ethers.getSigner(address);
  }
  return signers[address];
}

const dayStart = (iso) => Math.floor(new Date(iso + "T00:00:00Z").getTime() / 1000);
const claimHash = (s) => ethers.id(String(s));
const country2 = (name) => ethers.hexlify(ethers.toUtf8Bytes(name.slice(0, 2).toUpperCase()));

function reasonOf(e) {
  const m = e && /reason string '([^']+)'/.exec((e.message || "") + " " + (e.shortMessage || ""));
  return (m && m[1]) || (e && (e.reason || (e.revert && e.revert.args && e.revert.args[0]))) || "REVERTED";
}

module.exports = { fs, path, hre, ethers, ROOT, DATA, OUT, parseCsv, addr, signerFor, dayStart, claimHash, country2, reasonOf };
