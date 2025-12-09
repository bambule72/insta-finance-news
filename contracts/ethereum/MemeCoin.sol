// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title MemeCoin
 * @dev Implementation of a simple meme coin ERC-20 token
 */
contract MemeCoin is ERC20, Ownable {
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10**18; // 1 billion tokens
    
    /**
     * @dev Constructor that gives msg.sender all of existing tokens.
     */
    constructor() ERC20("MemeCoin", "MEME") Ownable(msg.sender) {
        _mint(msg.sender, MAX_SUPPLY);
    }
    
    /**
     * @dev Burn tokens from the caller's account
     * @param amount The amount of tokens to burn
     */
    function burn(uint256 amount) public {
        _burn(msg.sender, amount);
    }
}
