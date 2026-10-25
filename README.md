# Starbucks Rewards Value Realization & Incrementality Lab

**An end-to-end sandbox-isolated experimentation and warehouse optimization pipeline.**

[![SQL Pipeline](https://img.shields.io/badge/SQL-BigQuery--Sandbox-green?style=flat&logo=googlecloud)](./sql/) 
[![Inference Engine](https://img.shields.io/badge/Python-3.13%2B-blue?style=flat&logo=python)](./src/) 
[![BI Reporting](https://img.shields.io/badge/BI-Looker--Studio-yellow?style=flat&logo=google)](./dashboard/)

---

## Project Overview
This portfolio project provides a robust, enterprise-grade data warehouse and experimentation architecture built to evaluate the causal incremental impact of promotional reward incentives within a simulated Starbucks Rewards ecosystem. Using statistically rigorous synthetic data generators, this project implements an end-to-end analytics workflow—from raw unstructured data generation and BigQuery schema architecture design, to predictive inference and interactive executive dashboarding.

---

## The Business Problem & Hypothesis

### **The Question**
Does the launch of the customized "Spring Spark" rewards multiplier campaign drive **incremental customer lifetime value (CLV)**, or does it merely subsidize existing organic purchasing behavior among loyalty members?

### **The Challenge**
Promotional offers in loyalty programs frequently suffer from a lack of true incrementality. Members who are already highly active redeem rewards for purchases they would have made anyway (subsidization), causing artificial margin compression. 

### **The Hypothesis**
Targeted reward multiplier incentives deployed with a controlled 80% exposure rate to active loyalty members will drive a statistically significant increase in cumulative 3-month (Q2) post-period contribution margin ($) per randomized member, outweighing the associated intervention and reward costs.

---

## Executive Summary & Key Findings

Through rigorous causal inference modeling (Intent-to-Treat Welch's t-test) and enterprise BigQuery analytics modeling, we evaluated $N = 18,866$ eligible randomized members ($9,454$ Treatment, $9,412$ Control) over a 6-month period (January - June 2026):

* **Causal Incremental Lift:** Deploying the campaign generated an incremental lift of **+$2.21 per member** in cumulative post-period net contribution (treatment mean: `$31.94`, control mean: `$29.73`).
* **Extreme Statistical Significance:** The treatment effect is highly robust, yielding a **p-value of $6.29 \times 10^{-10}$**, far surpassing the canonical alpha threshold of $0.05$.
* **Interval Reliability:** The 95% Welch Confidence Interval ranges securely from **+$1.51 to +$2.91** per member, guaranteeing positive ROI under all plausible execution scenarios.
* **Margin Realization:** Despite a total modeled cost overhead of **$0.96 per treatment member** (comprising benefit and intervention overhead), the incremental top-line lift successfully offset costs, leading to a strong net positive financial payoff.

---

## Visual Assets & Dashboard Mockups

Below is the structured relational architecture of the BigQuery warehouse designed to support the pipeline:

```text
             [ raw_members ] ──────────────► [ dim_member ]
                    │                              │
                    ▼                              ▼
           [ raw_member_month ] ───────────► [ fact_member_month ]
                    │                              │
                    ▼                              ▼
          [ raw_benefit_events ] ──────────► [ fact_benefit_events ]
```

### **Executive Dashboard Architecture (Looker Studio)**
Our production BI dashboard contains three specific reporting views configured via BigQuery analytical schemas:
1. **Executive Summary Canvas:** Houses the Primary ITT Effect Scorecard (`+$2.21`), sample sizes, p-values, and the pre/post monthly trajectory.
2. **Financial P&L Sheet:** Captures net sales vs. reward/benefit cost structures, broken down by Green, Gold, and Reserve customer tiers.
3. **Conversion Funnel Page:** Visualizes campaign performance metrics (Eligibility $\rightarrow$ Exposure $\rightarrow$ Redemption) to isolate behavioral bottlenecks.

---

## Data Sources, Scope & Schema Design

### **Data Scope**
The dataset spans **6 consecutive months (Jan 1, 2026 - Jun 30, 2026)** and covers $20,000$ simulated Starbucks loyalty members. The pre-intervention baseline runs from Jan-Mar, and the active campaign experiment is executed during Apr-Jun (Q2).

### **Clean Warehouse Schema Design (BigQuery)**
* **`raw_members` (20,000 rows):** Demographic and static baseline profiles of all registered members.
* **`raw_member_month` (120,000 rows):** Monthly granular financial panel capturing transactions, net sales, variable costs, and promotional cost tracking.
* **`raw_benefit_events` (60,000 rows):** Granular transaction-level logs capturing eligibility, delivery, and redemption of specific member incentives.
* **`raw_market_context` (6 rows):** Country-level seasonality indices applied to model baseline organic behaviors.

---

## Tech Stack & Tools Used
* **Data Orchestration & Automation:** Python (3.13), Pandas, NumPy, JSON-schema.
* **Statistical Causal Engine:** SciPy, Statsmodels (Welch's t-test with unequal variances).
* **Cloud Data Warehousing:** Google Cloud Platform, BigQuery SQL Engine.
* **Reporting BI Platform:** Google Looker Studio, BigQuery Views (`vw_dashboard_*`).
* **Executive Output Generation:** Python-PPTX (automated PowerPoint decks), OpenPyXL (Excel P&L models).

---

## Methodology Deep Dive
Our analysis enforces a strict separation of concerns through an isolated sandbox-safe multi-phase pipeline:

1. **Data Ingestion and Alignment:** Pipeline components programmatically align raw directories, generating statistically consistent data based on real-world retail behavioral assumptions (using a static random seed to guarantee reproducibility).
2. **Intent-to-Treat (ITT) Inference:** By comparing the entire treatment-assigned cohort against the control cohort (regardless of whether they actively used the rewards), we prevent self-selection bias and yield the true "programmatic" causal impact of the campaign.
3. **BigQuery ETL modeling:** Implements DDL structures using explicit data clustering (`CLUSTER BY month_start, member_id`) and builds star-schema optimized views (`vw_member_month`, `vw_experiment_member_outcomes`) for low-latency BI queries.
4. **Database Validation Assertions:** Explicit SQL-level assertions check table volumes and keys before analytical rendering to prevent dirty pipelines.

---

## Repository Structure
```text
📂 starbucks-rewards-value-realization-lab-restart/
├── 📄 README.md                        # Production Portfolio Overview
├── 📄 Executive_Summary.md             # Written Business Case Narrative
├── 📁 sql/                             # BigQuery DDL, ETL, and Validation Queries
│   ├── 02_create_tables.sql            # Table DDL & Clustered Structures
│   ├── 03_build_analytics.sql          # Dimensional modeling ETL
│   ├── 04_quality_checks.sql           # Integrity assertions & validation checks
│   └── 07_create_dashboard_views.sql   # Looker Studio-optimized analytical views
├── 📁 src/                             # Python Modules
│   ├── generate_data.py                # Synthetic Data Engine
│   ├── analyze_experiment.py           # Statistical Welch Engine
│   └── build_executive_artifacts.py    # Automated Deck & Sheet Generators
├── 📁 outputs/                         # Pipeline Deliverables
│   └── 📁 executive_artifacts/         # Automated Slide Decks & Spreadsheets
└── 📁 dashboard/                       # Looker Studio Integration Specifications
```

---

## Limitations & Challenges
* **Synthetic Nature:** While statistically aligned with realistic retail outcomes, the dataset is synthetic and does not represent real-world Starbucks customer data or operational metrics.
* **No Long-term Seasonality:** With only a 6-month tracking window, we cannot control for year-over-year seasonality trends or determine if the post-period lift experiences decay over a 12-month horizon.
* **Fixed Randomization Probabilities:** Real-world assignment probabilities fluctuate dynamically; our pipeline assumes a static 50% randomization splits.

---

## Business Recommendations & Next Steps
1. **Approve Full Rollout to Green & Reserve Tiers:** The Reserve tier showed massive sensitivity and lift. Scale the "Spring Spark" program immediately for premium tier cohorts.
2. **Optimize Control Group Overhead:** Introduce localized, machine-learning-driven targeting (e.g. lift modeling) to identify "sure things" and avoid subsidizing rewards for highly loyal members who would purchase anyway.
3. **Extend Tracking Window:** Run a 6-month post-period extension test to evaluate post-incentive fatigue and monitor if customer transaction frequencies return to baseline.

---

##  Interactive Links
* **Interactive Jupyter Execution Notebook:** [`notebooks/01_run_pipeline.ipynb`](./notebooks/01_run_pipeline.ipynb)
* **Production SQL Warehouse Scripts:** [`sql/`](./sql/)
* **Automated PowerPoint Slides Template:** [`outputs/executive_artifacts/Rewards_Experiment_Executive_Readout.pptx`](./outputs/executive_artifacts/Rewards_Experiment_Executive_Readout.pptx)

---
*Disclaimer: This is a simulated business laboratory for portfolio presentation purposes. "Starbucks" is a registered trademark of Starbucks Corporation. No real customer or internal corporate data was accessed, modified, or exposed in this workspace.*
