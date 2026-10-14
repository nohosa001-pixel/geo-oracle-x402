// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ParametricInsurancePool
 * @notice On-chain parametric risk pool and autonomous claim disbursement contract.
 * Releases instant compensation upon verifying oracle proof hash and policy claim verdict.
 */
contract ParametricInsurancePool {
    string public constant NAME = "Parametric-Physical-AI-Insurance-Pool";
    
    address public oracleSigner;
    address public poolManager;
    uint256 public totalLiquidity;
    uint256 public totalClaimsPaid;

    struct Policy {
        string policyId;
        address insuredAgent;
        uint256 maxCoverageUsdc;
        uint256 premiumPaidUsdc;
        uint256 validUntil;
        bool active;
        bool claimed;
    }

    // Policy registry: policyId hash => Policy
    mapping(bytes32 => Policy) public policies;
    
    // Processed claim proof hashes to prevent duplicate claim payouts
    mapping(bytes32 => bool) public executedClaims;

    event PolicyCreated(
        bytes32 indexed policyHash,
        string policyId,
        address indexed insuredAgent,
        uint256 maxCoverageUsdc,
        uint256 premiumPaidUsdc,
        uint256 validUntil
    );

    event ClaimPaid(
        bytes32 indexed policyHash,
        bytes32 indexed proofHash,
        address indexed beneficiary,
        uint256 payoutAmountUsdc,
        string triggerCode
    );

    modifier onlyOracle() {
        require(msg.sender == oracleSigner || msg.sender == poolManager, "Unauthorized oracle");
        _;
    }

    constructor(address _oracleSigner) {
        poolManager = msg.sender;
        oracleSigner = _oracleSigner;
    }

    function setOracleSigner(address _newOracle) external {
        require(msg.sender == poolManager, "Only pool manager");
        oracleSigner = _newOracle;
    }

    /**
     * @notice Registers an underwritten policy after Proof of Insurability issuance.
     */
    function registerPolicy(
        string calldata policyId,
        address insuredAgent,
        uint256 maxCoverageUsdc,
        uint256 premiumPaidUsdc,
        uint256 durationSeconds
    ) external onlyOracle returns (bytes32) {
        bytes32 pHash = keccak256(bytes(policyId));
        require(!policies[pHash].active, "Policy already exists");

        policies[pHash] = Policy({
            policyId: policyId,
            insuredAgent: insuredAgent,
            maxCoverageUsdc: maxCoverageUsdc,
            premiumPaidUsdc: premiumPaidUsdc,
            validUntil: block.timestamp + durationSeconds,
            active: true,
            claimed: false
        });

        emit PolicyCreated(pHash, policyId, insuredAgent, maxCoverageUsdc, premiumPaidUsdc, block.timestamp + durationSeconds);
        return pHash;
    }

    /**
     * @notice Executes automatic parametric claim payout upon cryptographic oracle adjudication.
     */
    function executeParametricPayout(
        string calldata policyId,
        bytes32 proofHash,
        address payable beneficiary,
        uint256 payoutAmountUsdc,
        string calldata triggerCode,
        bytes calldata oracleSignature
    ) external returns (bool) {
        bytes32 pHash = keccak256(bytes(policyId));
        Policy storage p = policies[pHash];
        
        require(p.active, "Policy inactive or non-existent");
        require(!p.claimed, "Policy already settled");
        require(block.timestamp <= p.validUntil, "Policy expired");
        require(!executedClaims[proofHash], "Claim already executed");
        require(payoutAmountUsdc <= p.maxCoverageUsdc, "Payout exceeds coverage");

        // Verify Oracle Signature over the claim verdict
        bytes32 messageHash = keccak256(
            abi.encodePacked(
                "\x19Ethereum Signed Message:\n32",
                keccak256(abi.encode(pHash, proofHash, beneficiary, payoutAmountUsdc, keccak256(bytes(triggerCode))))
            )
        );

        address recovered = recoverSigner(messageHash, oracleSignature);
        require(recovered == oracleSigner || recovered == poolManager, "Invalid oracle signature");

        p.claimed = true;
        p.active = false;
        executedClaims[proofHash] = true;
        totalClaimsPaid += payoutAmountUsdc;

        emit ClaimPaid(pHash, proofHash, beneficiary, payoutAmountUsdc, triggerCode);
        return true;
    }

    function recoverSigner(bytes32 messageHash, bytes memory sig) internal pure returns (address) {
        require(sig.length == 65, "Invalid signature length");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        return ecrecover(messageHash, v, r, s);
    }
}
