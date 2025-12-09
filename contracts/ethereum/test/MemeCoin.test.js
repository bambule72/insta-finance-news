const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("MemeCoin", function () {
  let memeCoin;
  let owner;
  let addr1;
  let addr2;

  beforeEach(async function () {
    [owner, addr1, addr2] = await ethers.getSigners();
    const MemeCoin = await ethers.getContractFactory("MemeCoin");
    memeCoin = await MemeCoin.deploy();
  });

  describe("Deployment", function () {
    it("Should set the right token name and symbol", async function () {
      expect(await memeCoin.name()).to.equal("MemeCoin");
      expect(await memeCoin.symbol()).to.equal("MEME");
    });

    it("Should assign the total supply to the owner", async function () {
      const ownerBalance = await memeCoin.balanceOf(owner.address);
      expect(await memeCoin.totalSupply()).to.equal(ownerBalance);
    });

    it("Should have correct max supply", async function () {
      const maxSupply = ethers.parseEther("1000000000");
      expect(await memeCoin.totalSupply()).to.equal(maxSupply);
    });
  });

  describe("Transactions", function () {
    it("Should transfer tokens between accounts", async function () {
      const amount = ethers.parseEther("100");
      await memeCoin.transfer(addr1.address, amount);
      expect(await memeCoin.balanceOf(addr1.address)).to.equal(amount);

      await memeCoin.connect(addr1).transfer(addr2.address, amount);
      expect(await memeCoin.balanceOf(addr2.address)).to.equal(amount);
    });

    it("Should fail if sender doesn't have enough tokens", async function () {
      const initialOwnerBalance = await memeCoin.balanceOf(owner.address);
      await expect(
        memeCoin.connect(addr1).transfer(owner.address, 1)
      ).to.be.reverted;

      expect(await memeCoin.balanceOf(owner.address)).to.equal(
        initialOwnerBalance
      );
    });
  });

  describe("Burning", function () {
    it("Should burn tokens from caller's account", async function () {
      const burnAmount = ethers.parseEther("1000");
      const initialSupply = await memeCoin.totalSupply();
      
      await memeCoin.burn(burnAmount);
      
      expect(await memeCoin.totalSupply()).to.equal(initialSupply - burnAmount);
    });
  });
});
