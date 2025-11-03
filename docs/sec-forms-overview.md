# 📊 SEC Forms Ranked by Market Impact

| **Form**     | **Purpose**                                                                 | **Typical Market Reaction**                                                                 | **Real Example**                                                                 |
|--------------|------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| **8-K**      | Discloses major events (e.g., earnings, mergers, resignations, breaches)    | 🔥 High impact: Can cause immediate price swings depending on event type                    | Clorox 8-K breach disclosure (2023) → Stock dropped ~2%                          |
| **S-1**      | IPO registration with financials and risk disclosures                       | 🔥 High impact: Signals upcoming IPO; attracts investor attention                           | Momentus S-1 (2025) → Pre-IPO buzz and speculative interest                     |
| **13D**      | >5% ownership with intent to influence company                              | 🔥 High impact: Activist involvement often boosts stock or triggers governance changes      | Carl Icahn 13D on Illumina (2023) → Stock surged on activist pressure           |
| **10-K**     | Annual financial report with risk and governance disclosures                | 🔥 High impact: Investors analyze for earnings, risks, and strategy                         | Meta 10-K (2024) → Scrutiny over AI investments and privacy risks               |
| **10-Q**     | Quarterly financial report                                                   | ⚡ Moderate to high impact: Confirms trends or reveals surprises                            | Nvidia Q2 2023 10-Q → Strong results drove stock up 6%                          |
| **144**      | Insider intent to sell restricted/control securities                        | ⚡ Moderate impact: May signal insider selling pressure                                     | Amphenol execs filed to sell $151M (2025) → Stock dipped 1.3%                   |
| **S-4**      | Registration for mergers or business combinations                           | ⚡ Moderate impact: Signals strategic moves; depends on deal terms                          | Broadcom S-4 for VMware merger (2022) → Mixed reaction pending approval         |
| **13G**      | >5% passive ownership disclosure                                             | ⚡ Moderate impact: Indicates institutional interest without activist intent                | BlackRock 13G on Apple (2023) → Seen as long-term confidence                    |
| **DEF 14A**  | Proxy statement for shareholder votes (e.g., board, compensation)           | ⚡ Moderate impact: Can trigger governance debates or activist campaigns                    | Disney proxy battle (2024) → Stock volatility amid board shakeup                |
| **Form 4**   | Insider buying/selling activity                                              | ⚡ Moderate impact: Buying seen as bullish, selling may raise concerns                      | Elon Musk Form 4 sales (2022) → Tesla dipped on large sell-off                  |
| **20-F**     | Annual report for foreign companies listed in the U.S.                      | ⚡ Moderate impact: Similar to 10-K; depends on company profile                             | Alibaba 20-F (2023) → Focus on regulatory risks and growth outlook              |
| **6-K**      | Interim reports for foreign issuers                                          | ⚡ Low to moderate impact: Depends on content                                                | Tencent 6-K updates (2023) → Minor movement unless earnings are included        |
| **11-K**     | Annual report for employee stock/savings plans                              | 💤 Low impact: Informational only                                                           | Microsoft 11-K (2023) → No market movement                                      |
| **Form 3**   | Initial insider ownership disclosure                                         | 💤 Low impact: Informational unless tied to influential figures                            | New CFO Form 3 at Rivian (2022) → Minimal reaction                              |
| **Form 5**   | Annual summary of insider transactions not reported earlier                 | 💤 Low impact: Mostly catch-up filings                                                      | Catch-up Form 5 at Salesforce (2023) → No price movement                        |
| **Form 15**  | Termination of registration (e.g., delisting)                               | ⚠️ Low to moderate impact: May signal going private or reduced visibility                  | Twitter Form 15 post-acquisition (2022) → Delisting confirmed                   |
| **Form 25**  | Notification of delisting                                                    | ⚠️ High impact: Often negative; signals reduced liquidity                                   | Luckin Coffee Form 25 (2020) → Stock collapsed post-delisting                   |

## Currently Supported Forms

- **Form 144**: Insider intent to sell restricted/control securities (✅ Implemented)

## Planned Support (High Priority)

Based on market impact, the following forms are prioritized for implementation:

1. **8-K** - Major event disclosures (highest impact)
2. **S-1** - IPO registrations
3. **13D** - Activist ownership disclosures
4. **10-K** - Annual reports
5. **10-Q** - Quarterly reports
6. **Form 4** - Insider trading activity
