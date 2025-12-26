# Fantasy Football League Review: Outcome-Linked Analysis

**Analysis Period:** 2024-2024

## Assumptions & Methodology

- **Replacement Baseline:** Points of player ranked at `num_teams * starters_per_position` for each position
- **VAR Calculation:** Player Points - Replacement Baseline Points
- **Price Normalization:** Prices normalized to baseline season accounting for keeper inflation
- **Consistency Score:** Normalized score = `(1 / (1 + std)) * median`, scaled to 0-100
- **Archetype Definitions:**
  - CONSISTENT_CONTENDER: median_wins ≥ league_median AND std_wins ≤ league_median_std
  - BOOM_BUST: std_wins ≥ league_75th_percentile_std
  - LOTTERY: championships ≥ 1 AND median_wins < league_median
  - STEADY_BUT_UNLUCKY: median_wins ≥ league_60th_percentile AND championships = 0
- **Gini Coefficient:** Measure of VAR concentration (0 = perfectly equal, 1 = all value in one team)
- **Expected Wins (All-Play Model):** For each week, rank all teams by points. Team earns (num_teams - rank) / (num_teams - 1) expected wins. Sum across weeks.
- **Win Luck:** actual_wins - expected_wins. Positive = lucky, negative = unlucky
- **PA_diff:** points_against - league_avg_PA. Positive = faced tougher schedule (more points allowed)
- **Schedule Difficulty:** Normalized opponent strength. Positive = harder schedule
- **Lineup Efficiency:** actual_points / optimal_points (proportion of maximum points achieved)
- **Bench Waste Rate:** total_bench_points / total_optimal_points (wasted potential)
- **Loss Types:** UNLUCKY_LOSS (high score but lost), LINEUP_LOSS (inefficient lineup), DEPTH_LOSS (insufficient roster), SKILL_LOSS (otherwise)

---

## A. League Inefficiencies

### Spending Efficiency by Position

| Position | Avg $/VAR | Avg VAR/$ | Avg VAR | Avg Price | Players |
|----------|-----------|-----------|---------|-----------|---------|
| QB | $inf | -0.208 | -24.7 | $2182.9 | 30 |
| RB | $inf | -0.184 | -3.7 | $1397.8 | 52 |
| TE | $inf | 0.044 | 27.4 | $908.7 | 17 |
| WR | $inf | -0.072 | -6.0 | $1388.8 | 55 |

**Best Value Position:** TE ($0.044 VAR per dollar)

**Worst Value Position:** QB ($-0.208 VAR per dollar)

## B. Manager Efficiency Leaderboard

### Top Managers by VAR per Dollar (Career)

| Rank | Manager | VAR/$ | Total VAR | Total Spend | Wins | Championships | Seasons |
|------|---------|-------|-----------|-------------|------|---------------|---------|
| 1 | djharry01 | 1.680 | 335.9 | $200 | 10 | 0 | 1 |
| 2 | Zach | 1.614 | 322.7 | $200 | 7 | 0 | 1 |
| 3 | James | 1.134 | 226.9 | $200 | 6 | 0 | 1 |
| 4 | Connor | 0.902 | 180.4 | $200 | 10 | 0 | 1 |
| 5 | Adam | 0.399 | 79.8 | $200 | 7 | 0 | 1 |
| 6 | Kyle | 0.098 | 19.3 | $197 | 10 | 0 | 1 |
| 7 | Bhavik | -0.171 | -34.0 | $199 | 6 | 1 | 1 |
| 8 | Ryan | -0.459 | -90.1 | $196 | 7 | 0 | 1 |
| 9 | Andrew | -0.498 | -98.6 | $198 | 6 | 0 | 1 |
| 10 | Michael J. | -1.259 | -232.9 | $185 | 9 | 0 | 1 |

### Manager VAR Sources (Average % by Source)

| Manager | Draft % | Keeper % | Waiver % | Trade % |
|---------|---------|----------|----------|---------|
| Adam | 0.0% | 100.0% | 0.0% | 0.0% |
| Andrew | 0.0% | 0.0% | 0.0% | 0.0% |
| Ashkaun Razmara | 0.0% | 0.0% | 0.0% | 0.0% |
| Bhavik | 0.0% | 0.0% | 0.0% | 0.0% |
| Connor | 0.0% | 100.0% | 0.0% | 0.0% |
| James | 0.0% | 100.0% | 0.0% | 0.0% |
| Kyle | 0.0% | 100.0% | 0.0% | 0.0% |
| Michael J. | 0.0% | 0.0% | 0.0% | 0.0% |
| Mitchell | 0.0% | 0.0% | 0.0% | 0.0% |
| Ohad | 0.0% | 0.0% | 0.0% | 0.0% |

## C. Draft Skill Analysis

### Hit Rates (Career)

| Manager | Hit Rate | Bust Rate | Top 3 Pick VAR | Avg VAR |
|---------|----------|-----------|----------------|---------|
| Adam | 100.0% | 41.7% | 46.8 | 6.7 |
| Andrew | 100.0% | 40.0% | 8.8 | -9.9 |
| Ashkaun Razmara | 100.0% | 61.5% | 43.8 | -21.9 |
| Bhavik | 100.0% | 45.5% | 308.1 | -3.1 |
| Connor | 100.0% | 30.0% | 196.8 | 18.0 |
| James | 100.0% | 45.5% | 165.6 | 20.6 |
| Kyle | 100.0% | 46.2% | 204.3 | 1.5 |
| Michael J. | 100.0% | 45.5% | -75.2 | -21.2 |
| Mitchell | 100.0% | 63.6% | 18.9 | -32.3 |
| Ohad | 100.0% | 63.6% | 187.2 | -39.9 |

### Hit Rates by Draft Tier (League-Wide)

| Tier | Hit Rate | Bust Rate | Avg VAR | Players |
|------|----------|-----------|---------|---------|
| Tier 1 | 100.0% | 46.2% | -0.9 | 65 |
| Tier 2 | 100.0% | 48.5% | -5.3 | 66 |
| Tier 3 | 100.0% | 52.2% | -16.8 | 23 |

## D. Keeper Skill

### Keeper Surplus Analysis

| Position | Avg Surplus | Avg VAR | Surplus-VAR Correlation |
|----------|-------------|---------|------------------------|
| QB | $2159.82 | -24.7 | 0.424 |
| RB | $1383.10 | -3.7 | 0.424 |
| TE | $899.08 | 27.4 | 0.424 |
| WR | $1374.15 | -6.0 | 0.424 |

## F. Champion Blueprint

### What Champions Did Differently

**Top 3 Differentiators:**

1. **total_VAR**: Champions -42.1% different (effect size: 0.00)
2. **VAR_per_dollar**: Champions -43.4% different (effect size: 0.00)
3. **pct_VAR_from_draft**: Champions +0.0% different (effect size: 0.00)
4. **pct_VAR_from_keeper**: Champions -100.0% different (effect size: 0.00)
5. **pct_VAR_from_waiver**: Champions +0.0% different (effect size: 0.00)
6. **pct_VAR_from_trade**: Champions +0.0% different (effect size: 0.00)
7. **draft_VAR**: Champions +0.0% different (effect size: 0.00)
8. **keeper_VAR**: Champions -42.1% different (effect size: 0.00)
9. **waiver_VAR**: Champions +0.0% different (effect size: 0.00)
10. **trade_VAR**: Champions +0.0% different (effect size: 0.00)
11. **keeper_spending_pct**: Champions +0.0% different (effect size: 0.00)

### Champion Seasons

| Season | Manager | VAR/$ | Total VAR | Draft % | Keeper % | Waiver % | Trade % |
|--------|---------|-------|-----------|---------|----------|----------|---------|
| 2024 | Bhavik | -0.171 | -34.0 | 0.0% | 0.0% | 0.0% | 0.0% |

### Champions vs Non-Champions Comparison

| Metric | Champion Mean | Non-Champion Mean | Difference | Effect Size |
|--------|---------------|-------------------|------------|-------------|
| total_VAR | -34.04 | -58.76 | +24.72 | 0.00 |
| VAR_per_dollar | -0.17 | -0.30 | +0.13 | 0.00 |
| pct_VAR_from_draft | 0.00 | 0.00 | +0.00 | 0.00 |
| pct_VAR_from_keeper | 0.00 | 46.15 | -46.15 | 0.00 |
| pct_VAR_from_waiver | 0.00 | 0.00 | +0.00 | 0.00 |
| pct_VAR_from_trade | 0.00 | 0.00 | +0.00 | 0.00 |
| draft_VAR | 0.00 | 0.00 | +0.00 | 0.00 |
| keeper_VAR | -34.04 | -58.76 | +24.72 | 0.00 |
| waiver_VAR | 0.00 | 0.00 | +0.00 | 0.00 |
| trade_VAR | 0.00 | 0.00 | +0.00 | 0.00 |

---

## Visualizations

![price_vs_var_by_position.png](plots/price_vs_var_by_position.png)

![var_per_dollar_by_manager.png](plots/var_per_dollar_by_manager.png)

![champions_vs_field_shares.png](plots/champions_vs_field_shares.png)

## G. Consistency vs Volatility

### Most Consistent Managers

**Most Consistent (Wins):** Connor (Score: 100.0)
- Median Wins: 10.0
- Std Wins: nan

**Most Volatile (Wins):** Ashkaun Razmara (Score: 0.0)
- Median Wins: 2.0
- Std Wins: nan

### Champions vs Non-Champions: Consistency

- **Champions Avg Std Wins:** nan
- **Non-Champions Avg Std Wins:** nan
- **Insight:** Champions are more volatile (higher std)

### Consistency Score Rankings (Top 5)

| Rank | Manager | Consistency Score (Wins) | Median Wins | Std Wins |
|------|---------|-------------------------|-------------|----------|
| 1 | Connor | 100.0 | 10.0 | nan |
| 2 | djharry01 | 100.0 | 10.0 | nan |
| 3 | Kyle | 100.0 | 10.0 | nan |
| 4 | Michael J. | 87.5 | 9.0 | nan |
| 5 | Zach | 62.5 | 7.0 | nan |

### Manager Archetypes

- **STEADY_BUT_UNLUCKY**: 8 managers
- **LOW_SAMPLE**: 5 managers
- **LOTTERY**: 1 managers

**LOTTERY Examples:**
- Bhavik: 6.0 median wins, nan std, 1 championships

**STEADY_BUT_UNLUCKY Examples:**
- Connor: 10.0 median wins, nan std, 0 championships
- Ryan: 7.0 median wins, nan std, 0 championships
- Zach: 7.0 median wins, nan std, 0 championships

### Is High Variance Rewarded?

- **Correlation (Std Wins vs Championships):** nan
- **Insight:** No strong relationship between variance and championships

## H. Schedule Luck & Points Against

## I. Lineup Skill, Bench Waste & True Luck

*Weekly lineup analysis requires weekly roster snapshots which are not currently available in the data.*
*To enable this analysis, weekly roster data must be fetched from the Yahoo API or derived from transactions.*

---

## Key Takeaways

- **Most Efficient Manager:** djharry01 ($1.680 VAR per dollar)
- **Biggest Champion Differentiator:** total_VAR
- **Most Consistent Manager:** Connor
- **Most Championships:** Bhavik (1)
