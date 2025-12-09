# MemeCoin Solana Smart Contract

This directory contains the Solana implementation of the MemeCoin SPL token using Anchor framework and Rust.

## Overview

MemeCoin on Solana is an SPL token with the following features:
- Mintable tokens for initial distribution
- Burnable tokens to create deflationary pressure
- Built with Anchor framework for security and ease of use
- 9 decimals (standard for Solana tokens)

## Prerequisites

- Rust (latest stable version)
- Solana CLI tools (v1.17 or higher)
- Anchor CLI (v0.29 or higher)
- Node.js (for testing)

## Installation

### Install Rust
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### Install Solana CLI
```bash
sh -c "$(curl -sSfL https://release.solana.com/stable/install)"
```

### Install Anchor
```bash
cargo install --git https://github.com/coral-xyz/anchor anchor-cli --locked
```

### Install Dependencies
```bash
cd contracts/solana
anchor build
```

## Smart Contract

The main program is in `src/lib.rs` and implements:
- Token mint initialization
- Token minting functionality
- Token burning functionality

### Key Features

- **Decimals**: 9 (standard for Solana)
- **Mint Authority**: Configurable
- **Burn**: Anyone can burn their own tokens
- **Anchor Framework**: Type-safe and secure

## Configuration

Create a Solana wallet if you don't have one:

```bash
solana-keygen new
```

Configure Solana CLI for the network you want to use:

```bash
# For devnet
solana config set --url https://api.devnet.solana.com

# For mainnet-beta (production)
solana config set --url https://api.mainnet-beta.solana.com
```

Request airdrop for devnet testing:
```bash
solana airdrop 2
```

## Usage

### Build the Program

```bash
anchor build
```

### Run Tests

```bash
anchor test
```

### Deploy to Devnet

```bash
# Build the program
anchor build

# Deploy to devnet
anchor deploy --provider.cluster devnet

# Note the Program ID from the output
```

### Deploy to Mainnet

⚠️ **WARNING**: Deploying to mainnet costs real SOL and creates a permanent program!

```bash
# Make sure you have enough SOL for deployment
solana balance

# Deploy to mainnet
anchor deploy --provider.cluster mainnet
```

### Update Program ID

After deployment, update the program ID in:
1. `Anchor.toml`
2. `src/lib.rs` (in the `declare_id!` macro)

Then rebuild and redeploy.

## Initializing the Token Mint

After deploying, you need to initialize the token mint:

```bash
# This will be done through your deployment script or frontend
# The mint account should be created with your desired parameters
```

## Creating Token Accounts

Users need token accounts to hold MemeCoin:

```bash
spl-token create-account <MINT_ADDRESS>
```

## Minting Tokens

To mint tokens (only mint authority can do this):

```bash
spl-token mint <MINT_ADDRESS> <AMOUNT> <RECIPIENT_TOKEN_ACCOUNT>
```

## Testing

Create test cases in the `tests/` directory:

```bash
anchor test
```

## Security Considerations

1. **Audit**: Get a professional audit before mainnet deployment
2. **Private Keys**: Secure your wallet private keys
3. **Devnet First**: Always test on devnet before mainnet
4. **Mint Authority**: Consider transferring or revoking mint authority after distribution
5. **Program Upgrades**: Anchor programs are upgradeable by default - consider making immutable after deployment

## Token Economics

Recommended distribution for 1 billion tokens:
- **Total Supply**: 1,000,000,000 MEME
- **Community**: 70% (700M tokens)
- **Liquidity**: 20% (200M tokens)
- **Team/Marketing**: 10% (100M tokens)

## Interacting with the Token

After deployment, interact using:

1. **Solana Explorer**: View token on explorer.solana.com
2. **SPL Token CLI**: Command-line interaction
3. **Phantom Wallet**: Popular Solana wallet
4. **Raydium**: For DEX trading and liquidity

## Adding to Phantom Wallet

To add MemeCoin to Phantom:
1. Open Phantom wallet
2. Click settings > "Manage Token List"
3. Click "+" to add custom token
4. Enter your mint address
5. Token should appear in wallet

## DEX Listing (Raydium)

To create a liquidity pool on Raydium:
1. Go to raydium.io
2. Navigate to "Liquidity" > "Create Pool"
3. Select MemeCoin and SOL
4. Add liquidity in your desired ratio
5. Confirm transaction

## Useful Commands

```bash
# Check program ID
anchor keys list

# Check wallet balance
solana balance

# Get token account info
spl-token account-info <TOKEN_ACCOUNT>

# Transfer tokens
spl-token transfer <MINT_ADDRESS> <AMOUNT> <RECIPIENT> --fund-recipient

# Burn tokens
spl-token burn <TOKEN_ACCOUNT> <AMOUNT>

# Get mint info
spl-token supply <MINT_ADDRESS>
```

## Program Structure

```
contracts/solana/
├── Anchor.toml           # Anchor configuration
├── Cargo.toml           # Rust dependencies
├── src/
│   └── lib.rs           # Main program logic
├── tests/               # Test files
└── target/              # Build artifacts
```

## Common Issues

### "Insufficient funds"
- Request airdrop on devnet: `solana airdrop 2`
- Check balance: `solana balance`

### "Program failed to complete"
- Check program logs: `solana logs`
- Verify account addresses and parameters

### "Account does not exist"
- Ensure token accounts are created before operations
- Use `--fund-recipient` flag when transferring

## Development Workflow

1. Write/modify program code in `src/lib.rs`
2. Build: `anchor build`
3. Test: `anchor test`
4. Deploy to devnet: `anchor deploy --provider.cluster devnet`
5. Test on devnet with real transactions
6. Deploy to mainnet when ready

## Resources

- [Anchor Documentation](https://www.anchor-lang.com/)
- [Solana Documentation](https://docs.solana.com/)
- [SPL Token Documentation](https://spl.solana.com/token)
- [Solana Cookbook](https://solanacookbook.com/)
- [Rust Book](https://doc.rust-lang.org/book/)

## Monitoring

After deployment, monitor your token:
- [Solana Explorer](https://explorer.solana.com/)
- [Solscan](https://solscan.io/)
- [Solana Beach](https://solanabeach.io/)

## License

MIT License - See LICENSE file for details
