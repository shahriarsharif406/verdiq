require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: { version: "0.8.24", settings: { optimizer: { enabled: true, runs: 200 }, evmVersion: "paris" } },
  paths: { sources: "./contracts", tests: "./test", artifacts: "./artifacts", cache: "./cache" },
  networks: {
    hardhat: {
      initialDate: "2021-01-01T00:00:00Z",
      hardfork: "cancun",
      blockGasLimit: 300000000,
      gas: 100000000,
      allowUnlimitedContractSize: true,
      throwOnTransactionFailures: !process.env.VERDIQ_REPLAY,
      accounts: { count: 8 },
    },
  },
};
