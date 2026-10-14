// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MachineCreditScorer
 * @notice On-chain autonomous agent credit bureau for Physical AI (A.GRID Standard).
 * Tracks cumulative operational mileage, mission success rate, accident history, and stability.
 * Computes deterministic machine credit score (300 - 850) and collateral-free loan borrowing capacity.
 */
contract MachineCreditScorer {
    string public constant NAME = "A.GRID-Machine-Credit-Scorer";
    address public owner;
    address public oracleSigner;

    struct AgentCreditProfile {
        address agentAddress;
        address ownerAddress;
        uint256 registeredAt;
        uint256 totalMissionsCompleted;
        uint256 totalMissionsFailed;
        uint256 totalMileageMeters;
        uint256 totalRevenueEarnedUsdc;  // Cumulative USDC earned (micros)
        uint256 accidentCount;
        uint256 avgStabilityScorePpm;    // Scaled 0 to 1,000,000 (1.0 = perfect)
        uint256 hardwareHealthScorePpm; // Battery/motor health (0 to 1,000,000)
        uint256 lastUpdated;
        bool isBlacklisted;
    }

    // Agent address => Credit Profile
    mapping(address => AgentCreditProfile) public profiles;

    event AgentRegistered(address indexed agent, address indexed owner);
    event MissionRecordLogged(
        address indexed agent,
        bool success,
        uint256 mileageMeters,
        uint256 revenueUsdc,
        uint256 stabilityPpm
    );
    event CreditScoreUpdated(
        address indexed agent,
        uint256 newScore,
        uint256 borrowingCapacityUsdc
    );

    modifier onlyOracle() {
        require(msg.sender == oracleSigner || msg.sender == owner, "Unauthorized oracle");
        _;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner authorized");
        _;
    }

    constructor(address _oracleSigner) {
        owner = msg.sender;
        oracleSigner = _oracleSigner;
    }

    function setOracleSigner(address _newOracle) external onlyOwner {
        oracleSigner = _newOracle;
    }

    function registerAgent(address agentAddress, address ownerAddress) external {
        require(profiles[agentAddress].registeredAt == 0, "Agent already registered");
        require(agentAddress != address(0) && ownerAddress != address(0), "Invalid addresses");

        profiles[agentAddress] = AgentCreditProfile({
            agentAddress: agentAddress,
            ownerAddress: ownerAddress,
            registeredAt: block.timestamp,
            totalMissionsCompleted: 0,
            totalMissionsFailed: 0,
            totalMileageMeters: 0,
            totalRevenueEarnedUsdc: 0,
            accidentCount: 0,
            avgStabilityScorePpm: 850000,     // Default baseline 0.85
            hardwareHealthScorePpm: 1000000,  // Factory new 1.00
            lastUpdated: block.timestamp,
            isBlacklisted: false
        });

        emit AgentRegistered(agentAddress, ownerAddress);
    }

    /**
     * @notice Logs a completed delivery or freight mission record.
     */
    function recordMission(
        address agentAddress,
        bool success,
        uint256 mileageMeters,
        uint256 revenueEarnedUsdc,
        uint256 stabilityPpm,
        uint256 currentHealthPpm,
        bool hadAccident
    ) external onlyOracle {
        AgentCreditProfile storage p = profiles[agentAddress];
        require(p.registeredAt > 0, "Agent profile not found");
        require(!p.isBlacklisted, "Agent is blacklisted");

        if (success) {
            p.totalMissionsCompleted += 1;
        } else {
            p.totalMissionsFailed += 1;
        }

        if (hadAccident) {
            p.accidentCount += 1;
        }

        p.totalMileageMeters += mileageMeters;
        p.totalRevenueEarnedUsdc += revenueEarnedUsdc;

        // Exponential moving average for stability and health
        p.avgStabilityScorePpm = (p.avgStabilityScorePpm * 7 + stabilityPpm * 3) / 10;
        p.hardwareHealthScorePpm = currentHealthPpm;
        p.lastUpdated = block.timestamp;

        (uint256 score, uint256 borrowingLimit) = calculateCreditScore(agentAddress);
        emit MissionRecordLogged(agentAddress, success, mileageMeters, revenueEarnedUsdc, stabilityPpm);
        emit CreditScoreUpdated(agentAddress, score, borrowingLimit);
    }

    /**
     * @notice Deterministic FICO-style credit score calculation (300 to 850).
     * Weighted by:
     * - Success rate & volume (35%)
     * - Safety & accident history (30%)
     * - Hardware health & stability (20%)
     * - Revenue track record (15%)
     */
    function calculateCreditScore(address agentAddress) public view returns (uint256 score, uint256 maxLoanCapacityUsdc) {
        AgentCreditProfile storage p = profiles[agentAddress];
        if (p.registeredAt == 0 || p.isBlacklisted) {
            return (300, 0);
        }

        uint256 total = p.totalMissionsCompleted + p.totalMissionsFailed;
        if (total == 0) {
            return (580, 500 * 1e6); // Baseline starting credit score (580, $500 limit)
        }

        // 1. Success component (0 - 192 pts)
        uint256 successRatePpm = (p.totalMissionsCompleted * 1000000) / total;
        uint256 successPts = (successRatePpm * 192) / 1000000;

        // 2. Accident component (0 - 165 pts)
        uint256 accidentPenalty = p.accidentCount * 50;
        uint256 accidentPts = accidentPenalty >= 165 ? 0 : 165 - accidentPenalty;

        // 3. Health & Stability component (0 - 110 pts)
        uint256 healthStabilityPpm = (p.avgStabilityScorePpm + p.hardwareHealthScorePpm) / 2;
        uint256 healthPts = (healthStabilityPpm * 110) / 1000000;

        // 4. Revenue & Volume track record (0 - 83 pts)
        uint256 volumePts = p.totalMissionsCompleted >= 500 ? 83 : (p.totalMissionsCompleted * 83) / 500;

        score = 300 + successPts + accidentPts + healthPts + volumePts;
        if (score > 850) score = 850;

        // Compute collateral-free loan borrowing capacity based on score
        // Score 750+: up to $25,000 USDC; 700+: $15,000; 650+: $7,500; 600+: $2,500
        if (score >= 750) {
            maxLoanCapacityUsdc = 25000 * 1e6;
        } else if (score >= 700) {
            maxLoanCapacityUsdc = 15000 * 1e6;
        } else if (score >= 650) {
            maxLoanCapacityUsdc = 7500 * 1e6;
        } else if (score >= 600) {
            maxLoanCapacityUsdc = 2500 * 1e6;
        } else {
            maxLoanCapacityUsdc = 500 * 1e6;
        }
    }
}
