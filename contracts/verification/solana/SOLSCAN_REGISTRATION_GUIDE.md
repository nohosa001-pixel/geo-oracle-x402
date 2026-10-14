# 🪐 Solscan 등록 및 검증 완료 가이드 (A.GRID geo-oracle-x402)

본 가이드는 **Polygon, Base, Arbitrum 멀티체인 녹색 체크마크 검증 완료**에 이어, **Solana 메인넷 탐색기(Solscan.io)** 에 **A.GRID Physical AI & Autonomous Logistics Escrow** 프로그램 및 프로젝트 프로필을 등록/공인화하는 절차입니다.

---

## 📌 1. 솔라나 등록 핵심 메타데이터 요약

| 항목 | 상세 값 |
| :--- | :--- |
| **프로젝트명** | `A.GRID Physical AI & Autonomous Logistics Oracle Suite` |
| **태그 / 심볼** | `AGRID-GEO` / `A.GRID` |
| **카테고리** | `DePIN / Physical AI / Autonomous Logistics Escrow` |
| **공식 금고 지갑 (Treasury)** | `411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp` (Phantom 지갑) |
| **솔라나 에스크로 코어 (UniversalEscrowCore)** | `AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC` |
| **솔라나 AI 결제 볼트 (AgentPaymentVault)** | `7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y` |
| **결제/정산 토큰** | Solana Canonical SPL USDC (`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`) |
| **Anchor IDL 파일** | [`contracts/verification/solana/autonomous_logistics_escrow.idl.json`](file:///c:/Users/nohos/OneDrive/바탕%20화면/geo-oracle-x402/contracts/verification/solana/autonomous_logistics_escrow.idl.json) |
| **Solscan 메타데이터** | [`contracts/verification/solana/solscan_metadata.json`](file:///c:/Users/nohos/OneDrive/바탕%20화면/geo-oracle-x402/contracts/verification/solana/solscan_metadata.json) |

---

## 🚀 2. Solscan 등록 2단계 실행 방법

### 【방법 1】 Solscan 웹 탐색기에서 Anchor IDL 업로드 (권장)

Solscan은 Anchor 프레임워크로 작성된 스마트 컨트랙트의 IDL(인터페이스 정의 파일)을 직접 업로드하여 모든 명령어와 계정을 자동 디코딩합니다.

1. **Solscan 프로그램 페이지 접속:**
   - 🔗 [UniversalEscrowCore 탐색기](https://solscan.io/account/AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC) 또는 [AgentPaymentVault 탐색기](https://solscan.io/account/7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y) 및 [Treasury Wallet](https://solscan.io/account/411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp)
2. **"Anchor" 또는 "Program IDL" 탭 클릭**
3. **[Upload IDL] 또는 [Verify IDL] 버튼 클릭**
4. 다음 파일의 내용을 업로드하거나 붙여넣기합니다:
   - 파일 경로: `contracts/verification/solana/autonomous_logistics_escrow.idl.json`
5. 제출 완료 시 Solscan 상에서 다음 3개 핵심 인스트럭션이 공인 디코딩됩니다:
   - `initializeMission`: 자율주행 로지스틱스 미션 에스크로 예치
   - `verifyPoiDispatch`: Ed25519 운송적합성(PoI) 오라클 서명 승인 및 출격
   - `verifyPodAndDisburse`: 3방향 실시간 도착증명(PoD) USDC 자동 즉시 정산

---

### 【방법 2】 Solscan 공식 프로젝트 태그 및 프로필 등록 (공식 라벨 획득)

Solscan에서 검색 시 **"A.GRID Physical AI"** 공식 배지와 태그가 표시되도록 공식 지원 티켓을 등록합니다.

1. **Solscan 공식 지원 포털 접속:**
   - 🔗 [Solscan Submit Request / Support Desk](https://solscan.freshdesk.com/support/tickets/new) 또는 [Solscan Contact](https://solscan.io/contact-us)
2. **신청 양식 입력 (아래 템플릿 복사 후 사용):**

```text
Subject: Project Profile & Tag Registration for A.GRID Physical AI Oracle (geo-oracle-x402)

Project Name: A.GRID Physical AI & Autonomous Logistics Oracle Suite
Token / Tag Symbol: AGRID-GEO
Category: DePIN / Physical AI & Autonomous Logistics

Solana Treasury Wallet: 411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp
Solana Universal Escrow Program ID: AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC
Solana Agent Payment Vault Program ID: 7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y
Settlement Token Mint: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v (USDC)

Official Website: https://agrid.network
GitHub Repository: https://github.com/autonomous-oracles/global-geo-oracle-x402
Project Description:
Universal Physical AI & Autonomous Logistics Escrow Oracle Suite on Solana Mainnet-Beta and EVM Multi-Chain. Delivers WGS84 3D terrain physics, boundary layer micro-weather turbulence analytics, and automated 3-way SPL USDC escrow settlement for autonomous rovers, drones, and heavy cargo agents.

Cross-Chain Verified Deployments (Green Checkmark Verified on Polygonscan, BaseScan, ArbiScan):
• Polygon PoS (Chain ID 137):
  - AutonomousLogisticsEscrow: 0x0b6f3aeb26aCb6a6e451406503131Aaced83a3ad
  - ParametricInsurancePool: 0x1a56D8b8f13234d83e6F3b682ff51eacdBA58B89
  - MachineCreditScorer: 0xd816a7c801229f2264259F414B28E92645Be9596
  - OracleStakingManager: 0xb9a0d0cA18bf728c23A84f8DA60541963836EEb5
  - x402Settlement: 0x54786360Db4582AEC2435E216479FD4ff093CB80
• Base L2 (Chain ID 8453):
  - AutonomousLogisticsEscrow: 0xaA03fB8eD6c015858d35616F45761BcB9dE39cfA
  - ParametricInsurancePool: 0x0b6f3aeb26aCb6a6e451406503131Aaced83a3ad
  - MachineCreditScorer: 0x1a56D8b8f13234d83e6F3b682ff51eacdBA58B89
  - OracleStakingManager: 0xd816a7c801229f2264259F414B28E92645Be9596
  - x402Settlement: 0xb9a0d0cA18bf728c23A84f8DA60541963836EEb5
• Arbitrum One (Chain ID 42161):
  - AutonomousLogisticsEscrow: 0xaA03fB8eD6c015858d35616F45761BcB9dE39cfA
  - ParametricInsurancePool: 0x0b6f3aeb26aCb6a6e451406503131Aaced83a3ad
  - MachineCreditScorer: 0x1a56D8b8f13234d83e6F3b682ff51eacdBA58B89
  - OracleStakingManager: 0xd816a7c801229f2264259F414B28E92645Be9596
  - x402Settlement: 0xb9a0d0cA18bf728c23A84f8DA60541963836EEb5
```

---

## 🛡️ 3. SolanaFM 및 타 솔라나 탐색기 동시 등록

Solana 생태계의 대표적인 또 다른 탐색기인 **SolanaFM**에서도 동일한 IDL 파일로 즉시 검증이 가능합니다:

- 🔗 [SolanaFM Program Verifier](https://solana.fm/)
- 해당 페이지에서 `autonomous_logistics_escrow.idl.json`을 업로드하면 SolanaFM과 Solscan 양대 탐색기 모두에서 완벽한 컨트랙트 디코딩과 공인 마크가 부여됩니다.


