// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title x402Settlement
 * @notice Polygon Mainnet settlement contract for x402 EIP-712 micro-payment authorization.
 * Allows autonomous physical AI agents to authorize micro-fees via EIP-712 and oracles to batch-settle.
 */
interface IERC20Permit {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract x402Settlement {
    string public constant NAME = "x402-Polygon-Settlement";
    string public constant VERSION = "1.0.0";
    uint256 public immutable CHAIN_ID;
    
    // Polygon Native USDC Address: 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359
    address public immutable USDC_TOKEN;
    address public owner;
    
    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );
    
    bytes32 public constant PAYMENT_TYPEHASH = keccak256(
        "MicroPayment(address payer,address recipient,uint256 amountUsdcMicros,string nonce,uint256 deadline)"
    );
    
    bytes32 public immutable DOMAIN_SEPARATOR;
    
    // Track consumed nonces to prevent replay attacks on-chain
    mapping(bytes32 => bool) public consumedNonces;
    
    // Total settled volume per recipient
    mapping(address => uint256) public settledVolumeMicros;

    event PaymentSettled(
        address indexed payer,
        address indexed recipient,
        uint256 amountUsdcMicros,
        string nonce,
        bytes32 nonceHash
    );

    event BatchSettlementCompleted(
        address indexed recipient,
        uint256 totalAmountMicros,
        uint256 claimsCount
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner authorized");
        _;
    }

    constructor(address _usdcToken) {
        owner = msg.sender;
        USDC_TOKEN = _usdcToken;
        CHAIN_ID = block.chainid;
        
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                EIP712_DOMAIN_TYPEHASH,
                keccak256(bytes("x402-Polygon-Payment")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    struct PaymentClaim {
        address payer;
        address recipient;
        uint256 amountUsdcMicros; // e.g. 5000 = 0.005 USDC (6 decimals)
        string nonce;
        uint256 deadline;
        uint8 v;
        bytes32 r;
        bytes32 s;
    }

    /**
     * @notice Verifies an EIP-712 payment authorization signature.
     */
    function verifyPayment(PaymentClaim calldata claim) public view returns (bool, address) {
        if (block.timestamp > claim.deadline) {
            return (false, address(0));
        }

        bytes32 structHash = keccak256(
            abi.encode(
                PAYMENT_TYPEHASH,
                claim.payer,
                claim.recipient,
                claim.amountUsdcMicros,
                keccak256(bytes(claim.nonce)),
                claim.deadline
            )
        );

        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash)
        );

        address signer = ecrecover(digest, claim.v, claim.r, claim.s);
        return (signer == claim.payer && signer != address(0), signer);
    }

    /**
     * @notice Settles a single verified micro-payment voucher on-chain.
     */
    function settlePayment(PaymentClaim calldata claim) external returns (bool) {
        bytes32 nonceHash = keccak256(bytes(claim.nonce));
        require(!consumedNonces[nonceHash], "Nonce already consumed");
        require(block.timestamp <= claim.deadline, "Signature expired");

        (bool valid, address signer) = verifyPayment(claim);
        require(valid && signer == claim.payer, "Invalid EIP-712 signature");

        consumedNonces[nonceHash] = true;
        settledVolumeMicros[claim.recipient] += claim.amountUsdcMicros;

        emit PaymentSettled(claim.payer, claim.recipient, claim.amountUsdcMicros, claim.nonce, nonceHash);
        return true;
    }

    /**
     * @notice Batch settles multiple micro-payments in a single gas-efficient transaction.
     */
    function batchSettlePayments(PaymentClaim[] calldata claims) external returns (uint256 settledCount, uint256 totalAmount) {
        for (uint256 i = 0; i < claims.length; i++) {
            bytes32 nonceHash = keccak256(bytes(claims[i].nonce));
            if (!consumedNonces[nonceHash] && block.timestamp <= claims[i].deadline) {
                (bool valid, address signer) = verifyPayment(claims[i]);
                if (valid && signer == claims[i].payer) {
                    consumedNonces[nonceHash] = true;
                    settledVolumeMicros[claims[i].recipient] += claims[i].amountUsdcMicros;
                    totalAmount += claims[i].amountUsdcMicros;
                    settledCount++;
                    emit PaymentSettled(claims[i].payer, claims[i].recipient, claims[i].amountUsdcMicros, claims[i].nonce, nonceHash);
                }
            }
        }
        emit BatchSettlementCompleted(msg.sender, totalAmount, settledCount);
    }
}
