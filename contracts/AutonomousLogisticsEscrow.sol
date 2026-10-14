// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AutonomousLogisticsEscrow
 * @notice Universal Autonomous Agent Logistics & Freight Escrow on Polygon (A.GRID Standard).
 * Supports e-commerce parcels, food delivery, moving/freight, cold-chain pharma, and high-value cargo.
 * Integrates with geo-oracle-x402 for Proof of Insurability (PoI) and Proof of Delivery (PoD).
 */
interface IERC20 {
    function transfer(address recipient, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract AutonomousLogisticsEscrow {
    string public constant NAME = "A.GRID-Autonomous-Logistics-Escrow";
    string public constant VERSION = "1.0.0";
    uint256 public immutable CHAIN_ID;
    address public immutable USDC_TOKEN;
    address public owner;
    address public oracleSigner;

    enum CargoCategory {
        MicroDelivery,   // Food, urgent documents, quick commerce
        StandardParcel,  // E-commerce boxes, packages
        ColdChainBio,    // Pharmaceuticals, vaccines, fresh perishable foods
        HeavyMoving,     // Furniture, appliances, moving logistics, bulk cargo
        HighValueAsset   // Luxury goods, high-precision electronics, precious metals
    }

    enum MissionStatus {
        Created,        // Escrow created, waiting for funding
        Funded,         // Funds locked in escrow, waiting for PoI dispatch clearance
        Dispatched,     // PoI certified by oracle, robot/drone is in-transit
        Delivered,      // PoD verified by oracle, funds disbursed
        ClaimedRefund,  // Critical breach or accident occurred, refund/insurance executed
        Cancelled       // Cancelled before dispatch
    }

    struct Mission {
        bytes32 missionId;
        CargoCategory category;
        address consignor;         // Orderer / Cargo owner (funded the escrow)
        address merchant;          // Store / Merchant (if goods purchase included)
        address carrierAgent;      // Autonomous Robot / Drone wallet address
        address carrierOwner;      // Human / Corporate owner of the robot (receives net earnings)
        uint256 goodsPriceUsdc;    // Amount allocated for merchant goods (micros: 6 decimals)
        uint256 deliveryFeeUsdc;   // Amount allocated for delivery service
        uint256 oracleFeeUsdc;     // Amount allocated for geo-oracle verification
        uint256 maxAllowedGForce;  // Max acceleration/shock tolerance (scaled x100, e.g. 250 = 2.50G)
        int256 minTempCelsius;     // Min temp limit for cold-chain (e.g. 2)
        int256 maxTempCelsius;     // Max temp limit for cold-chain (e.g. 8)
        uint256 deadline;          // Delivery expiry timestamp
        MissionStatus status;
        bytes32 poiProofHash;      // Proof of Insurability certificate hash
        bytes32 podProofHash;      // Proof of Delivery verification hash
    }

    // EIP-712 Domain Separator & Typehashes
    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );

    bytes32 public constant POI_TYPEHASH = keccak256(
        "ProofOfInsurability(bytes32 missionId,address carrierAgent,uint256 riskScorePpm,uint256 validUntil)"
    );

    bytes32 public constant POD_TYPEHASH = keccak256(
        "ProofOfDelivery(bytes32 missionId,address carrierAgent,int256 destLatE7,int256 destLonE7,uint256 completedAt)"
    );

    bytes32 public immutable DOMAIN_SEPARATOR;

    // Mission ID => Mission details
    mapping(bytes32 => Mission) internal _missions;

    function getMission(bytes32 id) external view returns (Mission memory) { return _missions[id]; }

    // Replay attack prevention for proof hashes
    mapping(bytes32 => bool) public usedProofHashes;

    event MissionCreated(
        bytes32 indexed missionId,
        CargoCategory category,
        address indexed consignor,
        address indexed carrierAgent,
        uint256 totalEscrowUsdc
    );

    event MissionDispatched(
        bytes32 indexed missionId,
        bytes32 indexed poiProofHash,
        uint256 riskScorePpm
    );

    event MissionDelivered(
        bytes32 indexed missionId,
        bytes32 indexed podProofHash,
        uint256 merchantPaid,
        uint256 carrierOwnerPaid,
        uint256 oracleFeePaid
    );

    event MissionRefunded(
        bytes32 indexed missionId,
        string reason,
        uint256 refundedAmount
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner authorized");
        _;
    }

    constructor(address _usdcToken, address _oracleSigner) {
        owner = msg.sender;
        USDC_TOKEN = _usdcToken;
        oracleSigner = _oracleSigner;
        CHAIN_ID = block.chainid;

        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                EIP712_DOMAIN_TYPEHASH,
                keccak256(bytes(NAME)),
                keccak256(bytes(VERSION)),
                CHAIN_ID,
                address(this)
            )
        );
    }

    function setOracleSigner(address _newOracle) external onlyOwner {
        require(_newOracle != address(0), "Invalid oracle address");
        oracleSigner = _newOracle;
    }

    /**
     * @notice Creates and funds a new autonomous logistics escrow.
     * Consignor locks goods price + delivery fee + oracle fee in USDC.
     */
    function createAndFundMission(
        bytes32 missionId,
        CargoCategory category,
        address merchant,
        address carrierAgent,
        address carrierOwner,
        uint256 goodsPriceUsdc,
        uint256 deliveryFeeUsdc,
        uint256 oracleFeeUsdc,
        uint256 maxAllowedGForce,
        int256 minTempCelsius,
        int256 maxTempCelsius,
        uint256 durationSeconds
    ) external {
        require(_missions[missionId].consignor == address(0), "Mission already exists");
        require(carrierAgent != address(0), "Invalid carrier agent");
        require(carrierOwner != address(0), "Invalid carrier owner");

        uint256 totalAmount = goodsPriceUsdc + deliveryFeeUsdc + oracleFeeUsdc;
        require(totalAmount > 0, "Escrow total must be > 0");

        // Lock USDC from consignor
        require(
            IERC20(USDC_TOKEN).transferFrom(msg.sender, address(this), totalAmount),
            "USDC escrow transfer failed"
        );

        _missions[missionId] = Mission({
            missionId: missionId,
            category: category,
            consignor: msg.sender,
            merchant: merchant,
            carrierAgent: carrierAgent,
            carrierOwner: carrierOwner,
            goodsPriceUsdc: goodsPriceUsdc,
            deliveryFeeUsdc: deliveryFeeUsdc,
            oracleFeeUsdc: oracleFeeUsdc,
            maxAllowedGForce: maxAllowedGForce,
            minTempCelsius: minTempCelsius,
            maxTempCelsius: maxTempCelsius,
            deadline: block.timestamp + durationSeconds,
            status: MissionStatus.Funded,
            poiProofHash: bytes32(0),
            podProofHash: bytes32(0)
        });

        emit MissionCreated(missionId, category, msg.sender, carrierAgent, totalAmount);
    }

    /**
     * @notice Carrier agent submits Proof of Insurability (PoI) signed by geo-oracle to dispatch.
     * Prevents flight in hazardous terrain, micro-weather turbulence, or illegal airspace.
     */
    function dispatchWithPoI(
        bytes32 missionId,
        uint256 riskScorePpm,
        uint256 validUntil,
        bytes calldata oracleSignature
    ) external {
        Mission storage mission = _missions[missionId];
        require(mission.status == MissionStatus.Funded, "Mission not in Funded state");
        require(block.timestamp <= validUntil, "PoI certificate expired");

        bytes32 structHash = keccak256(
            abi.encode(POI_TYPEHASH, missionId, mission.carrierAgent, riskScorePpm, validUntil)
        );
        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash)
        );

        address recovered = recoverSigner(digest, oracleSignature);
        require(recovered == oracleSigner, "Invalid oracle PoI signature");
        require(!usedProofHashes[digest], "PoI proof already consumed");

        usedProofHashes[digest] = true;
        mission.status = MissionStatus.Dispatched;
        mission.poiProofHash = digest;

        emit MissionDispatched(missionId, digest, riskScorePpm);
    }

    /**
     * @notice Releases escrow upon verifying Proof of Delivery (PoD) signed by geo-oracle.
     * Disburses funds immediately to merchant, carrier owner, and oracle.
     */
    function completeDeliveryWithPoD(
        bytes32 missionId,
        int256 destLatE7,
        int256 destLonE7,
        uint256 completedAt,
        bytes calldata oracleSignature
    ) external {
        Mission storage mission = _missions[missionId];
        require(mission.status == MissionStatus.Dispatched, "Mission not currently dispatched");
        require(block.timestamp <= mission.deadline, "Delivery deadline passed");

        bytes32 structHash = keccak256(
            abi.encode(POD_TYPEHASH, missionId, mission.carrierAgent, destLatE7, destLonE7, completedAt)
        );
        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash)
        );

        address recovered = recoverSigner(digest, oracleSignature);
        require(recovered == oracleSigner, "Invalid oracle PoD signature");
        require(!usedProofHashes[digest], "PoD proof already consumed");

        usedProofHashes[digest] = true;
        mission.status = MissionStatus.Delivered;
        mission.podProofHash = digest;

        // Instant automated on-chain disbursement
        if (mission.goodsPriceUsdc > 0 && mission.merchant != address(0)) {
            require(IERC20(USDC_TOKEN).transfer(mission.merchant, mission.goodsPriceUsdc), "Merchant payout failed");
        }
        if (mission.deliveryFeeUsdc > 0) {
            require(IERC20(USDC_TOKEN).transfer(mission.carrierOwner, mission.deliveryFeeUsdc), "Carrier owner payout failed");
        }
        if (mission.oracleFeeUsdc > 0) {
            require(IERC20(USDC_TOKEN).transfer(oracleSigner, mission.oracleFeeUsdc), "Oracle fee payout failed");
        }

        emit MissionDelivered(
            missionId,
            digest,
            mission.goodsPriceUsdc,
            mission.deliveryFeeUsdc,
            mission.oracleFeeUsdc
        );
    }

    /**
     * @notice Refund consignor if deadline expired or blackbox breach verified.
     */
    function refundConsignor(bytes32 missionId, string calldata reason) external {
        Mission storage mission = _missions[missionId];
        require(
            mission.status == MissionStatus.Funded || mission.status == MissionStatus.Dispatched,
            "Mission cannot be refunded in current status"
        );

        bool isExpired = block.timestamp > mission.deadline;
        bool isAuthorized = (msg.sender == oracleSigner || msg.sender == owner || (isExpired && msg.sender == mission.consignor));
        require(isAuthorized, "Refund not authorized");

        mission.status = MissionStatus.ClaimedRefund;
        uint256 totalRefund = mission.goodsPriceUsdc + mission.deliveryFeeUsdc + mission.oracleFeeUsdc;
        require(IERC20(USDC_TOKEN).transfer(mission.consignor, totalRefund), "Refund transfer failed");

        emit MissionRefunded(missionId, reason, totalRefund);
    }

    function recoverSigner(bytes32 digest, bytes memory signature) internal pure returns (address) {
        require(signature.length == 65, "Malformed signature");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
        return ecrecover(digest, v, r, s);
    }
}
