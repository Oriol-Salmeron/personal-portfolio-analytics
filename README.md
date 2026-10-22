# Personal Portfolio Analytics Dashboard

**Interactive finance analytics built with Python, Pandas, Streamlit and Plotly.**

[**🚀 Open the live app**](https://personal-portfolio-analytics.streamlit.app/) · [**💻 Explore the source code**](https://github.com/Oriol-Salmeron/personal-portfolio-analytics)

A web-based dashboard demonstrating portfolio monitoring, Core–Satellite allocation, a rule-based market radar, Smart DCA contribution routing, cash-flow budgeting, savings and liquidity planning, net-worth projections, and FIFO transaction matching.

> **Privacy by design:** all data committed to this repository is invented. The original workbook's holdings, balances, salary figures, transaction history and tax-related records are not included. Use only synthetic or otherwise safely anonymized data in public deployments.

## Quick start (for app visitors)

**Try the live dashboard:** [Open Personal Portfolio Analytics](https://personal-portfolio-analytics.streamlit.app/)

You do not need to install Python or upload a file to explore the demo.

1. **Start on Executive Dashboard** to see the example portfolio, cash and savings overview, and 12-month scenario.
2. **Use the tabs from left to right** to explore holdings and strategy, the market radar, income/liquidity, savings projections, and tax-record examples.
3. **Try the optional controls** in the sidebar under *Customize income & allocation* to change the monthly budget assumptions. The four allocation percentages should total 100%.
4. **Keep the example data in place** for a first tour. It is fictional and is used to demonstrate calculations, not current market conditions.
5. **Optional CSV upload:** the uploader accepts a holdings file using the same schema as `data/posiciones_dummy.csv`. Uploading changes holdings-related calculations only; the other sections continue using bundled fictional data.

**Important:** the app does not use live prices, connect to a broker, execute trades, or provide financial or tax advice. Do not upload personal financial information to the public app. The tax and foreign-balance views are illustrative demonstrations, not a Spanish tax calculator.

For local installation, see [Installation and local usage](#installation-and-local-usage).

## Project goals

The project demonstrates a complete analytics workflow rather than a static spreadsheet export:

1. Ingest and validate structured CSV inputs.
2. Calculate position-level valuation, invested capital, unrealized P&L and current portfolio weights.
3. Compare current allocations with target weights using a Core–Satellite framework.
4. Screen a synthetic watchlist using target prices, 52-week highs, entry thresholds, risk labels and transparent rule-based signals.
5. Allocate a simulated recurring contribution across positive target-weight gaps, with an optional 70/30 tactical gate.
6. Reconcile monthly net income into living expenses, savings, investment contributions and an opportunity reserve.
7. Consolidate fictional cash accounts, estimate illustrative interest and calculate an emergency-reserve surplus.
8. Project portfolio and savings balances under adjustable return assumptions.
9. Match synthetic buy/sell transactions using FIFO and summarize interest/dividend records for an educational tax-reporting view.

The application has no live market-data connection and does not place trades or connect to financial accounts.

## Mapping from the original workbook workflows

The application is organized around the actual workflow groups in the source workbook rather than treating it as a single holdings table. Its main areas map as follows:

| Workbook area | Application module | Recreated analytical logic |
|---|---|---|
| Investment positions | Holdings & Strategy | Holdings valuation, invested capital, unrealized P&L, current weights, target weights and rebalancing status |
| Radar & Expectations | Market Radar | Current price, 52-week high, target price, entry threshold, modeled upside and watchlist signals |
| Investment Method | Holdings & Strategy | Core–Satellite roles, weighted risk, concentration limits, target-weight gaps and Smart DCA routing |
| Portfolio overview / projection | Executive Dashboard | Consolidated wealth view, allocation charts and 12-month scenario projection |
| Income | Income & Liquidity | Gross-to-net income, 30/20/50 allocation logic, savings capacity and investment budget |
| Remunerated savings accounts | Income & Liquidity / Savings Projection | Multi-account cash balances, illustrative rates, interest estimates and monthly balance history |
| Investable cash | Income & Liquidity | Consolidated liquidity, emergency reserve target and surplus above the reserve |
| Charts & Dashboard | Executive Dashboard | Executive KPIs, allocation-versus-target views and wealth projection charts |
| Tax & Income records | Tax & Reporting | FIFO realized P&L, passive-income/withholding ledger and foreign-balance monitoring flag |
| Navigation index | README and dashboard tabs | Clear module navigation and usage documentation |

The old workbook's live-price formulas are not copied into the public app. The dashboard recalculates metrics from documented input files, and all reference prices and records are synthetic.

## Dashboard modules

### 1. Executive dashboard

- Illustrative total net worth: investment portfolio plus cash/savings balances.
- Portfolio market value, invested capital and unrealized profit/loss.
- Market-value-weighted risk score on a user-supplied 1–5 scale.
- Core allocation, top-two concentration and weighted modeled upside.
- Interactive allocation donut and current-versus-target allocation chart.
- Twelve-month net-worth projection with adjustable annual return assumptions.

### 2. Holdings and Core–Satellite strategy

For each holding, the app calculates:

| Metric | Formula |
|---|---|
| Invested capital | Quantity × purchase price |
| Market value | Quantity × example market price |
| Unrealized P&L | Market value − invested capital |
| Position return | Unrealized P&L ÷ invested capital |
| Current portfolio weight | Position market value ÷ total portfolio market value |
| Weight deviation | Current weight − target weight |
| Weighted risk score | Sum of (market value × risk score) ÷ portfolio market value |

The demonstration labels positions as **Core** or **Satellite** and flags underweight/overweight gaps against configurable thresholds. The Smart DCA simulator directs recurring contributions toward positive target-weight gaps; it does not propose selling overweight assets.

A separate tactical gate demonstrates the hybrid rule represented in the workbook: when a watchlist candidate meets the configurable score and entry-price conditions, the model routes a configurable share of the contribution to rebalancing and the remainder to that candidate. This is a transparent coding example, not an investment recommendation.

### 3. Market radar and expectations

The radar includes synthetic current prices, 52-week highs, target prices, target-entry prices, risk scores and opportunity scores. It derives:

- Distance from the 52-week high = current price ÷ 52-week high − 1.
- Modeled upside to target = target price ÷ current price − 1.
- Distance from entry threshold = current price ÷ target-entry price − 1.
- A rule-based screen based on modeled upside and the illustrative entry-price gate.

Targets and scores are static fictional assumptions. Modeled upside is not a forecast, an expected return or a recommendation.

### 4. Income, cash flow and liquidity

Editable sidebar assumptions determine gross and net monthly income and allocate net income across:

- Living expenses
- Fixed savings
- Investment / Smart DCA
- Opportunity reserve

The dashboard validates whether the allocations sum to 100%, rather than silently reallocating an unexplained difference. It also consolidates fictional account balances and derives an indicative weighted annual savings rate and interest estimate.

The emergency-reserve target is the greater of a configured minimum reserve and a selected number of months of modeled expenses. Illustrative investable surplus is calculated as the positive amount above that reserve.

### 5. Savings history and projection

A synthetic month-end history supports an account-balance trend chart. The scenario builder projects portfolio and savings balances using fixed monthly contributions and user-defined annual return assumptions. It is deterministic and does not imply that investment returns or savings rates will remain constant.

### 6. Tax records and international-balance monitoring

The app:

- Matches purchases and sales using a FIFO cost-basis routine.
- Includes purchase fees in unit cost and subtracts sale fees from proceeds.
- Summarizes realized P&L separately from unrealized P&L.
- Displays gross interest/dividend records and recorded withholding.
- Provides an explicitly **illustrative** progressive provision using fictional bracket assumptions.
- Flags foreign-held cash against a configurable monitoring threshold.

This is not a Spanish tax calculator and does not determine whether a tax return, Form 720 or any other filing is required. The demo does not model all tax-loss offsets, allowances, tax-credit limitations, personal circumstances or jurisdiction-specific rules. Verify actual obligations using current official guidance or a qualified tax professional.

## Repository structure

```text
personal-portfolio-analytics/
├── app.py
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
├── .streamlit/
│   └── config.toml
└── data/
    ├── posiciones_dummy.csv
    ├── radar_dummy.csv
    ├── cashflow_rules_dummy.csv
    ├── savings_accounts_dummy.csv
    ├── savings_history_dummy.csv
    ├── transactions_dummy.csv
    ├── capital_income_dummy.csv
    └── tax_brackets_demo.csv
```

## Data architecture

```text
Synthetic CSV inputs
        │
        ▼
Pandas ingestion and schema checks
        │
        ├── Holdings: valuation, P&L, weights and risk
        ├── Radar: drawdown, modeled upside and entry gate
        ├── Cash flow: income allocation and reserve rules
        ├── Savings: balances, indicative interest and projections
        └── Transactions + income: FIFO realized P&L and tax-record view
        │
        ▼
Streamlit interface + Plotly visualizations
```

`app.py` derives metrics at runtime instead of storing calculated portfolio values redundantly in the CSVs. That makes the calculations auditable and easier to test.

## Dataset dictionary

### `data/posiciones_dummy.csv`

| Column | Description |
|---|---|
| `asset` | Fictional holding name |
| `ticker` | Synthetic unique identifier (`DMY001`, etc.) |
| `asset_class` | Asset/sector category |
| `strategy_role` | `Core` or `Satellite` |
| `quantity` | Number of units held |
| `purchase_price_eur` | Example purchase price per unit |
| `market_price_eur` | Static example market price per unit |
| `daily_change_pct` | Fictional daily change as a decimal (0.01 = 1%) |
| `risk_score` | Illustrative risk scale from 1 to 5 |
| `target_weight` | Target allocation as a decimal (0.30 = 30%) |

### Supporting CSV files

- `radar_dummy.csv`: watchlist targets, 52-week highs, entry prices and scores.
- `cashflow_rules_dummy.csv`: editable baseline income allocation, reserve and tactical-gate assumptions.
- `savings_accounts_dummy.csv`: fictional account balances, country codes and annual rates.
- `savings_history_dummy.csv`: fictional month-end balances by cash/savings category.
- `transactions_dummy.csv`: ordered fictional `BUY`/`SELL` events for FIFO matching.
- `capital_income_dummy.csv`: fictional interest and dividend receipts and withholdings.
- `tax_brackets_demo.csv`: fictional marginal-rate assumptions used only by the demo estimator.

All financial values, company names, account names, scores, prices, transaction histories and tax assumptions in the included datasets are invented. Codes beginning with `DMY` are placeholders, not real market tickers.

## Installation and local usage

**Prerequisites:** Python 3.10 or later.

### 1. Clone the repository

```bash
git clone https://github.com/Oriol-Salmeron/personal-portfolio-analytics.git
cd personal-portfolio-analytics
```

### 2. Create and activate a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Run the dashboard

```bash
streamlit run app.py
```

Streamlit will print a local URL. The app loads the bundled fictional datasets by default.

### Optional: use a different holdings CSV

Use the sidebar uploader with a CSV that has the same columns as `data/posiciones_dummy.csv`. Uploading a different positions file changes holdings and portfolio calculations only; radar, cash-flow, savings and tax records remain the synthetic examples included in the repository.

**Do not upload personal financial data to a publicly hosted demo.** For private analysis, run a local copy and keep your real workbook and exports outside the public repository.

## Deployment

The repository layout is compatible with [Streamlit Community Cloud](https://share.streamlit.io/): choose this GitHub repository, select the `main` branch and set `app.py` as the app entrypoint. The `requirements.txt` file is located at the repository root, as required for dependency installation by the service.

## Technical skills demonstrated

- **Python:** modular functions, defensive input validation, exception handling and transaction-ledger processing.
- **Pandas:** CSV ingestion, numeric type conversion, joins, grouping, reshaping and derived financial measures.
- **Streamlit:** interactive tabs, controls, KPI cards, file upload and formatted data tables.
- **Plotly:** allocation, contribution, market-radar and time-series visualizations.
- **Portfolio analytics:** position valuation, P&L, weighted risk, diversification, target allocation and contribution routing.
- **Personal-finance analytics:** income allocation, savings-rate calculations, emergency-fund logic and compound projections.
- **Transaction processing:** FIFO lot matching and realized-profit calculation including transaction fees.
- **Data governance:** synthetic demo records, schema validation and explicit disclosure of model limitations.

## Limitations and responsible use

- No live prices, price history, broker connections or order execution.
- Portfolio prices and watchlist targets are static invented assumptions.
- Risk scores are illustrative user inputs, not estimated volatility, Value at Risk or probability of loss.
- Projections assume fixed contributions and returns; real outcomes will differ.
- Tax-rate bands and the foreign-account threshold are configuration examples, not current legal guidance.
- The dashboard is an educational technical demonstration, not financial, investment, accounting, legal or tax advice.

## License

Released under the MIT License. See `LICENSE`.
