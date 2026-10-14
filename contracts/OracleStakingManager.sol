// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OracleStakingManager
 * @notice Staking and Slashing Collateral Manager for geo-oracle nodes in A.GRID.
 * Oracles stake collateral; if proven to provide corrupted terrain/weather data causing a crash,
 * collateral is slashed and disbursed directly to the affected agent or insurance vault.
 */
interface IERC20 {
    function transfer(address recipient, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

contract OracleStakingManager {
    string public constant NAME = "A.GRID-Oracle-Staking-Manager";
    address public immutable USDC_TOKEN;
    address public owner;
    address public arbitrationDao;

    uint256 public constant MINIMUM_STAKE = 5000 * 1e6; // 5,000 USDC minimum stake per node

    struct OracleNode {
        address nodeAddress;
        uint256 stakedAmountUsdc;
        uint256 totalQueriesServed;
        uint256 slashCount;
        uint256 reputationScore; // Base 1,000
        bool isActive;
    }

    mapping(address => OracleNode) public oracles;

    event OracleStaked(address indexed node, uint256 amount);
    event OracleSlashed(address indexed node, uint256 amountSlashed, address indexed victimRecipient, string reason);
    event OracleUnstaked(address indexed node, uint256 amount);

    modifier onlyArbitrator() {
        require(msg.sender == arbitrationDao || msg.sender == owner, "Only arbitrator authorized");
        _;
    }

    constructor(address _usdcToken, address _arbitrationDao) {
        owner = msg.sender;
        USDC_TOKEN = _usdcToken;
        arbitrationDao = _arbitrationDao;
    }

    function stakeCollateral(uint256 amountUsdc) external {
        require(amountUsdc > 0, "Stake amount must be > 0");
        require(IERC20(USDC_TOKEN).transferFrom(msg.sender, address(this), amountUsdc), "Transfer failed");

        OracleNode storage node = oracles[msg.sender];
        node.nodeAddress = msg.sender;
        node.stakedAmountUsdc += amountUsdc;
        if (node.stakedAmountUsdc >= MINIMUM_STAKE) {
            node.isActive = true;
        }
        if (node.reputationScore == 0) {
            node.reputationScore = 1000;
        }

        emit OracleStaked(msg.sender, amountUsdc);
    }

    /**
     * @notice Slashes an oracle node if verified that bad data caused an autonomous mission failure.
     */
    function slashOracle(
        address nodeAddress,
        uint256 slashAmountUsdc,
        address victimRecipient,
        string calldata reason
    ) external onlyArbitrator {
        OracleNode storage node = oracles[nodeAddress];
        require(node.stakedAmountUsdc >= slashAmountUsdc, "Slash exceeds stake");

        node.stakedAmountUsdc -= slashAmountUsdc;
        node.slashCount += 1;
        if (node.reputationScore >= 100) {
            node.reputationScore -= 100;
        } else {
            node.reputationScore = 0;
        }

        if (node.stakedAmountUsdc < MINIMUM_STAKE) {
            node.isActive = false;
        }

        require(IERC20(USDC_TOKEN).transfer(victimRecipient, slashAmountUsdc), "Disbursement failed");
        emit OracleSlashed(nodeAddress, slashAmountUsdc, victimRecipient, reason);
    }
}
