const hre = require("hardhat");

async function main() {
  console.log("Deploying MemeCoin contract...");

  const MemeCoin = await hre.ethers.getContractFactory("MemeCoin");
  const memeCoin = await MemeCoin.deploy();

  await memeCoin.waitForDeployment();

  const address = await memeCoin.getAddress();
  console.log(`MemeCoin deployed to: ${address}`);
  
  // Get some basic info
  const totalSupply = await memeCoin.totalSupply();
  const name = await memeCoin.name();
  const symbol = await memeCoin.symbol();
  
  console.log(`Token Name: ${name}`);
  console.log(`Token Symbol: ${symbol}`);
  console.log(`Total Supply: ${hre.ethers.formatEther(totalSupply)} ${symbol}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
