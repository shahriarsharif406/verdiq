const { expect } = require("chai");
const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

const b32 = (s) => ethers.encodeBytes32String(s);

describe("VerdiqRegistry - the firewall replays each fraud case and blocks it", function () {
  let reg, authority, dev, alice, bob, carol, host;

  beforeEach(async () => {
    [authority, dev, alice, bob, carol] = await ethers.getSigners();
    reg = await (await ethers.getContractFactory("VerdiqRegistry")).deploy();
    await reg.issue(dev.address, b32("P03"), 1000, 1999, 2022);
    await reg.issue(dev.address, b32("P03"), 3000, 3999, 2023);
  });

  it("allows a clean issue -> transfer -> retire lifecycle and emits events", async () => {
    await expect(reg.connect(dev).transfer(1000, 1499, alice.address))
      .to.emit(reg, "Transferred").withArgs(dev.address, alice.address, 1000, 1499);
    await expect(reg.connect(alice).retire(1000, 1199, b32("FY2024")))
      .to.emit(reg, "Retired").withArgs(alice.address, 1000, 1199, b32("FY2024"));
    const [issued, owner, state] = await reg.ownerOf(1100);
    expect(issued).to.equal(true); expect(owner).to.equal(alice.address); expect(state).to.equal(1n);
    expect(await reg.dryRun(false, alice.address, 1200, 1499, ethers.ZeroHash)).to.equal("");
  });

  it("F-overlap: refuses an overlapping issuance", async () => {
    await expect(reg.issue(bob.address, b32("P99"), 1500, 2500, 2022)).to.be.revertedWith("OVERLAP_ISSUANCE");
    await expect(reg.issue(bob.address, b32("P99"), 900, 1000, 2022)).to.be.revertedWith("OVERLAP_ISSUANCE");
  });

  it("F1 double sale: same serial range sold to a second buyer reverts", async () => {
    await reg.connect(dev).transfer(1000, 1999, alice.address);
    await expect(reg.connect(dev).transfer(1000, 1999, bob.address)).to.be.revertedWith("NOT_OWNER");
    await expect(reg.connect(dev).transfer(1500, 2200, bob.address)).to.be.revertedWith("NOT_OWNER"); // partial overlap
  });

  it("F1 phantom sale: a party that never held the credits cannot sell them", async () => {
    await expect(reg.connect(carol).transfer(1000, 1100, bob.address)).to.be.revertedWith("NOT_OWNER");
  });

  it("F2 double retirement: retiring the same tonnes twice reverts", async () => {
    await reg.connect(dev).retire(1000, 1999, b32("claim-A"));
    await expect(reg.connect(dev).retire(1000, 1999, b32("claim-A"))).to.be.revertedWith("ALREADY_RETIRED");
  });

  it("F2 second claim: a different claim on the same tonnes reverts", async () => {
    await reg.connect(dev).retire(1000, 1999, b32("claim-A"));
    await reg.connect(dev).transfer(3000, 3999, alice.address);
    await expect(reg.connect(alice).retire(1500, 1600, b32("claim-B"))).to.be.revertedWith("DOUBLE_CLAIM");
  });

  it("F2 retired credits cannot be traded", async () => {
    await reg.connect(dev).retire(1000, 1100, b32("claim-A"));
    await expect(reg.connect(dev).transfer(1000, 1100, alice.address)).to.be.revertedWith("RETIRED");
  });

  it("F2 retirement by a non-owner reverts", async () => {
    await expect(reg.connect(bob).retire(3000, 3100, b32("claim-B"))).to.be.revertedWith("NOT_OWNER");
  });

  it("F3 never issued: trading or retiring unissued serials reverts", async () => {
    await expect(reg.connect(dev).transfer(2500, 2600, alice.address)).to.be.revertedWith("NOT_ISSUED");
    await expect(reg.connect(dev).transfer(1900, 2100, alice.address)).to.be.revertedWith("NOT_ISSUED"); // straddles the end
    await expect(reg.connect(dev).retire(2500, 2600, b32("x"))).to.be.revertedWith("NOT_ISSUED");
  });

  it("F6 Article 6: a host claim without corresponding adjustment blocks retirement, and vice versa", async () => {
    await reg.registerHostClaim("0x4244", 3000, 3199, false); // "BD"
    await reg.connect(dev).transfer(3000, 3999, alice.address);
    await expect(reg.connect(alice).retire(3100, 3150, b32("claim"))).to.be.revertedWith("HOST_DOUBLE_CLAIM");
    await reg.connect(alice).retire(3500, 3600, b32("claim")); // untouched tonnes are fine
    // a host claim over tonnes a buyer already retired is refused
    await expect(reg.registerHostClaim("0x4244", 3550, 3560, false)).to.be.revertedWith("HOST_DOUBLE_CLAIM");
    // authorised (corresponding adjustment applied) claims do not conflict
    await reg.registerHostClaim("0x4b45", 3550, 3560, true);
    await reg.connect(alice).retire(3700, 3710, b32("claim"));
  });

  it("only the authority can issue, register host claims and anchor closes", async () => {
    await expect(reg.connect(bob).issue(bob.address, b32("P1"), 9000, 9100, 2024)).to.be.revertedWith("NOT_AUTHORITY");
    await expect(reg.connect(bob).anchorClose(20250131, b32("r"))).to.be.revertedWith("NOT_AUTHORITY");
  });

  it("splits segments correctly across many partial operations", async () => {
    await reg.connect(dev).transfer(1100, 1199, alice.address);
    await reg.connect(dev).transfer(1300, 1399, bob.address);
    await reg.connect(alice).transfer(1150, 1160, carol.address);
    expect((await reg.ownerOf(1099))[1]).to.equal(dev.address);
    expect((await reg.ownerOf(1149))[1]).to.equal(alice.address);
    expect((await reg.ownerOf(1155))[1]).to.equal(carol.address);
    expect((await reg.ownerOf(1161))[1]).to.equal(alice.address);
    expect((await reg.ownerOf(1250))[1]).to.equal(dev.address);
    expect((await reg.ownerOf(1350))[1]).to.equal(bob.address);
  });

  it("Day-End Close: anchors a root once and verifies a Merkle proof generated by the Python engine", async function () {
    const f = path.join(__dirname, "..", "data", "out", "sample_proof.json");
    if (!fs.existsSync(f)) this.skip();
    const p = JSON.parse(fs.readFileSync(f, "utf8"));
    await expect(reg.anchorClose(p.date_int, "0x" + p.root)).to.emit(reg, "CloseAnchored");
    await expect(reg.anchorClose(p.date_int, "0x" + p.root)).to.be.revertedWith("ALREADY_ANCHORED");
    const rec = "0x" + p.record_hex;
    const proof = p.path.map((x) => "0x" + x);
    expect(await reg.verifyRecord(p.date_int, rec, proof)).to.equal(true);
    const tampered = "0x" + p.record_hex.replace(/^(..)/, (m) => (m === "7b" ? "7a" : "7b"));
    expect(await reg.verifyRecord(p.date_int, tampered, proof)).to.equal(false);
  });
});
