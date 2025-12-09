# MemeCoin Ethereum Smart Contract

This directory contains the Ethereum implementation of the MemeCoin ERC-20 token using Solidity and Hardhat.

## Overview

MemeCoin is a simple ERC-20 token with the following features:
- Fixed supply of 1 billion tokens (1,000,000,000 MEME)
- Burnable tokens to create deflationary pressure
- Based on OpenZeppelin's secure and audited contracts
- Owner control for initial distribution

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn

## Installation

```bash
# Navigate to the ethereum contracts directory
cd contracts/ethereum

# Install dependencies
npm install
```

## Smart Contract

The main contract is `MemeCoin.sol`, which inherits from:
- `ERC20`: Standard token implementation
- `Ownable`: Access control for owner-only functions

### Key Features

- **Name**: MemeCoin
- **Symbol**: MEME
- **Decimals**: 18 (standard ERC-20)
- **Total Supply**: 1,000,000,000 MEME
- **Burn Function**: Anyone can burn their own tokens

## Configuration

Create a `.env` file in the `contracts/ethereum` directory with the following variables:

```env
# Network RPC URLs
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_INFURA_KEY
MAINNET_RPC_URL=https://mainnet.infura.io/v3/YOUR_INFURA_KEY

# Private key for deployment (DO NOT COMMIT THIS!)
PRIVATE_KEY=your_private_key_here

# Etherscan API key for contract verification
ETHERSCAN_API_KEY=your_etherscan_api_key
```

⚠️ **IMPORTANT**: Never commit your `.env` file or expose your private keys!

## Usage

### Compile the Contract

```bash
npm run compile
```

### Run Tests

```bash
npm run test
```

### Deploy to Local Network

```bash
# Start local Hardhat network
npx hardhat node

# In another terminal, deploy
npx hardhat run scripts/deploy.js --network localhost
```

### Deploy to Testnet (Sepolia)

```bash
npx hardhat run scripts/deploy.js --network sepolia
```

### Deploy to Mainnet

⚠️ **WARNING**: Deploying to mainnet costs real ETH and creates a permanent, immutable contract!

```bash
npx hardhat run scripts/deploy.js --network mainnet
```

### Verify Contract on Etherscan

After deployment, verify your contract:

```bash
npx hardhat verify --network sepolia DEPLOYED_CONTRACT_ADDRESS
```

## Testing

The test suite includes:
- Deployment verification
- Token transfers
- Burn functionality
- Balance checks
- Error handling

Run tests with:

```bash
npm run test
```

## Security Considerations

1. **Audit**: Consider getting a professional audit before mainnet deployment
2. **Private Keys**: Never share or commit private keys
3. **Testnet First**: Always test on testnet (Sepolia) before mainnet
4. **Gas Limits**: Be aware of gas costs for deployment and transactions
5. **Ownership**: The contract uses Ownable pattern - consider renouncing ownership after deployment if desired

## Token Economics

- **Total Supply**: 1,000,000,000 MEME (minted to deployer)
- **Distribution** (recommended):
  - 70% - Community distribution (airdrops, liquidity mining)
  - 20% - Liquidity pools (DEX)
  - 10% - Team and marketing

## Interacting with the Contract

After deployment, you can interact with the contract using:

1. **Etherscan**: View and interact with verified contract
2. **Web3 Libraries**: ethers.js, web3.js
3. **Wallets**: MetaMask, WalletConnect
4. **DEX**: Uniswap, SushiSwap

## Adding to MetaMask

To add MemeCoin to MetaMask:
1. Open MetaMask
2. Click "Import tokens"
3. Enter the contract address
4. Token symbol (MEME) and decimals (18) should auto-fill

## DEX Listing

To create a liquidity pool on Uniswap:
1. Go to Uniswap
2. Select "Pool" > "Create a pair"
3. Select MemeCoin and ETH
4. Add liquidity in your desired ratio
5. Confirm transaction

## Common Issues

### "Insufficient funds for gas"
- Ensure you have enough ETH in your wallet for gas fees

### "Nonce too low"
- Reset your MetaMask account or wait for pending transactions

### "Transaction reverted"
- Check that you have sufficient token balance
- Verify you're using the correct network

## Resources

- [Hardhat Documentation](https://hardhat.org/docs)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts)
- [Ethereum Development](https://ethereum.org/en/developers/)
- [Solidity Documentation](https://docs.soliditylang.org/)

## License

MIT License - See LICENSE file for details
