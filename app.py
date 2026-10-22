"""Personal Portfolio Analytics — synthetic-data portfolio demonstration.

Run locally from the project root with:
    streamlit run app.py

All bundled data is fictional. The dashboard is an analytical demo, not financial,
investment, accounting, legal or tax advice.
"""
from __future__ import annotations

from collections import defaultdict, deque
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

POSITION_COLUMNS = [
    "asset", "ticker", "asset_class", "strategy_role", "quantity",
    "purchase_price_eur", "market_price_eur", "daily_change_pct",
    "risk_score", "target_weight",
]
RADAR_COLUMNS = [
    "asset", "ticker", "asset_class", "current_price_eur", "high_52w_eur",
    "target_price_eur", "target_entry_price_eur", "risk_score",
    "opportunity_score", "watch_reason",
]
SAVINGS_COLUMNS = [
    "account_name", "account_type", "country_code", "liquidity",
    "balance_eur", "annual_rate_pct", "purpose",
]
RULE_COLUMNS = [
    "monthly_gross_income_eur", "withholding_rate", "expense_share",
    "savings_share", "investment_share", "opportunity_share",
    "emergency_fund_min_eur", "emergency_months",
    "foreign_asset_monitor_threshold_eur", "tactical_score_threshold",
    "tactical_entry_buffer_pct", "tactical_rebalance_share",
    "tactical_radar_share", "underweight_threshold", "overweight_threshold",
]
TRANSACTION_COLUMNS = [
    "transaction_date", "transaction_type", "asset", "ticker", "quantity",
    "unit_price_eur", "fees_eur",
]
INCOME_COLUMNS = [
    "income_date", "source_name", "income_type", "country_code",
    "gross_income_eur", "foreign_withholding_eur", "domestic_withholding_eur",
]
BRACKET_COLUMNS = ["lower_bound_eur", "upper_bound_eur", "illustrative_rate_pct"]
HISTORY_COLUMNS = ["month", "cash_savings_eur", "fixed_savings_eur", "operating_cash_eur"]

st.set_page_config(
    page_title="Personal Portfolio Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.7rem; padding-bottom: 2rem; }
      [data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.07);
        border: 1px solid rgba(128, 128, 128, 0.16);
        border-radius: 0.8rem;
        padding: 0.9rem 1rem;
      }
      .section-hint { color: #718096; font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def read_csv(name: str, required_columns: list[str]) -> pd.DataFrame:
    """Read one repository dataset and enforce its documented schema."""
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Required dataset is missing: data/{name}")
    frame = pd.read_csv(path)
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    missing = [col for col in required_columns if col not in frame.columns]
    if missing:
        raise ValueError(f"data/{name} is missing columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError(f"data/{name} contains no rows.")
    return frame[required_columns].copy()


def load_positions(uploaded_bytes: bytes | None = None) -> pd.DataFrame:
    """Load the default synthetic positions or a schema-compatible CSV upload."""
    if uploaded_bytes is None:
        frame = read_csv("posiciones_dummy.csv", POSITION_COLUMNS)
    else:
        frame = pd.read_csv(BytesIO(uploaded_bytes))
        frame.columns = [str(c).strip().lower() for c in frame.columns]
        missing = [col for col in POSITION_COLUMNS if col not in frame.columns]
        if missing:
            raise ValueError(
                "Uploaded positions CSV is missing required columns: "
                + ", ".join(missing)
            )
        frame = frame[POSITION_COLUMNS].copy()

    text_columns = ["asset", "ticker", "asset_class", "strategy_role"]
    for col in text_columns:
        frame[col] = frame[col].astype("string").str.strip()
        if frame[col].isna().any() or frame[col].eq("").any():
            raise ValueError(f"Position field '{col}' contains blank values.")

    frame["ticker"] = frame["ticker"].str.upper()
    frame["strategy_role"] = frame["strategy_role"].str.title()
    allowed_roles = {"Core", "Satellite"}
    invalid_roles = sorted(set(frame["strategy_role"]) - allowed_roles)
    if invalid_roles:
        raise ValueError(
            "'strategy_role' must be Core or Satellite. Invalid: "
            + ", ".join(invalid_roles)
        )
    if frame["ticker"].duplicated().any():
        duplicates = frame.loc[frame["ticker"].duplicated(), "ticker"].tolist()
        raise ValueError("Duplicate tickers found: " + ", ".join(duplicates))

    numeric_cols = [
        "quantity", "purchase_price_eur", "market_price_eur",
        "daily_change_pct", "risk_score", "target_weight",
    ]
    for col in numeric_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
        if frame[col].isna().any():
            raise ValueError(f"Position field '{col}' contains missing/non-numeric values.")

    if (frame["quantity"] <= 0).any():
        raise ValueError("All position quantities must be greater than zero.")
    if (frame[["purchase_price_eur", "market_price_eur"]] <= 0).any().any():
        raise ValueError("Purchase and market prices must be greater than zero.")
    if not frame["risk_score"].between(1, 5).all():
        raise ValueError("Position risk scores must be between 1 and 5.")
    if not frame["target_weight"].between(0, 1).all():
        raise ValueError("Target weights must be decimal values between 0 and 1.")
    return frame


def calculate_positions(frame: pd.DataFrame, rules: pd.Series) -> pd.DataFrame:
    """Derive market value, unrealized P&L, weights and rebalancing labels."""
    result = frame.copy()
    result["invested_capital_eur"] = result["quantity"] * result["purchase_price_eur"]
    result["market_value_eur"] = result["quantity"] * result["market_price_eur"]
    result["unrealized_pnl_eur"] = result["market_value_eur"] - result["invested_capital_eur"]
    result["return_pct"] = (
        result["unrealized_pnl_eur"] / result["invested_capital_eur"]
    )
    total_market_value = float(result["market_value_eur"].sum())
    if total_market_value <= 0:
        raise ValueError("Total portfolio market value must be greater than zero.")
    result["current_weight"] = result["market_value_eur"] / total_market_value
    result["weight_deviation"] = result["current_weight"] - result["target_weight"]
    under = float(rules["underweight_threshold"])
    over = float(rules["overweight_threshold"])
    result["rebalance_signal"] = "Within tolerance"
    result.loc[result["weight_deviation"] < under, "rebalance_signal"] = "Underweight"
    result.loc[result["weight_deviation"] > over, "rebalance_signal"] = "Overweight"
    return result


def calculate_fifo_realized_pnl(transactions: pd.DataFrame) -> pd.DataFrame:
    """Match BUY/SELL transactions by ticker using FIFO cost-basis accounting.

    Purchase fees are allocated to unit cost; sell fees reduce net sale proceeds.
    The function raises an error if a sell exceeds the previously purchased units.
    """
    frame = transactions.copy()
    frame["transaction_date"] = pd.to_datetime(frame["transaction_date"], errors="coerce")
    if frame["transaction_date"].isna().any():
        raise ValueError("Transaction ledger contains an invalid date.")
    frame["transaction_type"] = frame["transaction_type"].astype(str).str.upper().str.strip()
    if not set(frame["transaction_type"]).issubset({"BUY", "SELL"}):
        raise ValueError("Transaction type must be BUY or SELL.")
    for col in ["quantity", "unit_price_eur", "fees_eur"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
        if frame[col].isna().any() or (frame[col] < 0).any():
            raise ValueError(f"Transaction field '{col}' contains invalid values.")
    if (frame["quantity"] <= 0).any() or (frame["unit_price_eur"] <= 0).any():
        raise ValueError("Transaction quantities and unit prices must be positive.")

    frame = frame.sort_values(["transaction_date"], kind="stable").reset_index(drop=True)
    lots: dict[str, deque[dict[str, float]]] = defaultdict(deque)
    sales: list[dict[str, Any]] = []

    for row in frame.to_dict(orient="records"):
        ticker = str(row["ticker"]).upper()
        quantity = float(row["quantity"])
        unit_price = float(row["unit_price_eur"])
        fees = float(row["fees_eur"])

        if row["transaction_type"] == "BUY":
            unit_cost_including_fees = unit_price + (fees / quantity)
            lots[ticker].append(
                {"quantity": quantity, "unit_cost": unit_cost_including_fees}
            )
            continue

        remaining = quantity
        cost_basis = 0.0
        while remaining > 1e-9:
            if not lots[ticker]:
                raise ValueError(
                    f"FIFO validation failed: sell of {ticker} exceeds available prior buys."
                )
            lot = lots[ticker][0]
            matched = min(remaining, lot["quantity"])
            cost_basis += matched * lot["unit_cost"]
            remaining -= matched
            lot["quantity"] -= matched
            if lot["quantity"] <= 1e-9:
                lots[ticker].popleft()

        net_proceeds = quantity * unit_price - fees
        sales.append(
            {
                "transaction_date": row["transaction_date"],
                "asset": row["asset"],
                "ticker": ticker,
                "quantity_sold": quantity,
                "sale_price_eur": unit_price,
                "net_proceeds_eur": net_proceeds,
                "fifo_cost_basis_eur": cost_basis,
                "realized_pnl_eur": net_proceeds - cost_basis,
                "method": "FIFO",
            }
        )

    return pd.DataFrame(sales)


def progressive_demo_tax(base_eur: float, brackets: pd.DataFrame) -> float:
    """Calculate a progressive provision using fictional, editable demo brackets."""
    base = max(0.0, float(base_eur))
    due = 0.0
    for row in brackets.sort_values("lower_bound_eur").to_dict(orient="records"):
        lower = float(row["lower_bound_eur"])
        upper = float(row["upper_bound_eur"])
        rate = float(row["illustrative_rate_pct"]) / 100.0
        taxable_in_band = max(0.0, min(base, upper) - lower)
        due += taxable_in_band * rate
    return due


def calculate_smart_dca(
    positions: pd.DataFrame,
    radar: pd.DataFrame,
    monthly_contribution: float,
    rules: pd.Series,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Create a transparent contribution-routing simulation from target-weight gaps."""
    total_value = float(positions["market_value_eur"].sum())
    allocation = positions[["asset", "ticker", "strategy_role", "market_value_eur", "target_weight", "current_weight", "weight_deviation"]].copy()
    allocation["target_value_eur"] = allocation["target_weight"] * total_value
    allocation["positive_gap_eur"] = (
        allocation["target_value_eur"] - allocation["market_value_eur"]
    ).clip(lower=0)
    # The workbook methodology marks a holding as underweight only below its configured tolerance.
    allocation.loc[
        allocation["weight_deviation"] >= float(rules["underweight_threshold"]),
        "positive_gap_eur",
    ] = 0.0

    score_threshold = float(rules["tactical_score_threshold"])
    entry_buffer = float(rules["tactical_entry_buffer_pct"])
    eligible = radar[
        (radar["opportunity_score"] >= score_threshold)
        & (radar["current_price_eur"] <= radar["target_entry_price_eur"] * (1 + entry_buffer))
    ].copy()
    tactical_active = not eligible.empty
    candidate = None
    if tactical_active:
        candidate = eligible.sort_values(
            ["opportunity_score", "risk_score"], ascending=[False, True]
        ).iloc[0]
        rebalance_share = float(rules["tactical_rebalance_share"])
        radar_share = float(rules["tactical_radar_share"])
    else:
        rebalance_share = 1.0
        radar_share = 0.0

    rebalance_budget = monthly_contribution * rebalance_share
    total_gap = float(allocation["positive_gap_eur"].sum())
    deployable_rebalance = min(rebalance_budget, total_gap)
    if total_gap > 0 and deployable_rebalance > 0:
        allocation["monthly_dca_eur"] = (
            allocation["positive_gap_eur"] / total_gap * deployable_rebalance
        )
    else:
        allocation["monthly_dca_eur"] = 0.0

    planned_radar = monthly_contribution * radar_share if tactical_active else 0.0
    if tactical_active and candidate is not None:
        radar_row = pd.DataFrame(
            [{
                "asset": f"Radar allocation — {candidate['asset']}",
                "ticker": str(candidate["ticker"]),
                "strategy_role": "Tactical radar",
                "market_value_eur": 0.0,
                "target_weight": 0.0,
                "current_weight": 0.0,
                "weight_deviation": 0.0,
                "target_value_eur": 0.0,
                "positive_gap_eur": 0.0,
                "monthly_dca_eur": planned_radar,
            }]
        )
        allocation = pd.concat([allocation, radar_row], ignore_index=True)

    allocated = float(allocation["monthly_dca_eur"].sum())
    info = {
        "tactical_active": tactical_active,
        "candidate_asset": None if candidate is None else str(candidate["asset"]),
        "candidate_ticker": None if candidate is None else str(candidate["ticker"]),
        "monthly_contribution": float(monthly_contribution),
        "allocated": allocated,
        "unallocated": max(0.0, float(monthly_contribution) - allocated),
        "rebalance_budget": rebalance_budget,
        "positive_gap_total": total_gap,
    }
    return allocation.sort_values("monthly_dca_eur", ascending=False), info


def build_projection(
    portfolio_value: float,
    savings_value: float,
    monthly_investment: float,
    monthly_savings: float,
    annual_portfolio_return_pct: float,
    annual_savings_return_pct: float,
    months: int = 12,
) -> pd.DataFrame:
    """Project balances using monthly contributions and user-set annual assumptions."""
    portfolio = float(portfolio_value)
    savings = float(savings_value)
    portfolio_monthly_rate = (1 + annual_portfolio_return_pct / 100.0) ** (1 / 12) - 1
    savings_monthly_rate = (1 + annual_savings_return_pct / 100.0) ** (1 / 12) - 1
    rows = [{"Month": 0, "Investment portfolio (€)": portfolio, "Savings & cash (€)": savings, "Illustrative net worth (€)": portfolio + savings}]
    for month in range(1, months + 1):
        portfolio = portfolio * (1 + portfolio_monthly_rate) + monthly_investment
        savings = savings * (1 + savings_monthly_rate) + monthly_savings
        rows.append({
            "Month": month,
            "Investment portfolio (€)": portfolio,
            "Savings & cash (€)": savings,
            "Illustrative net worth (€)": portfolio + savings,
        })
    return pd.DataFrame(rows)


def eur(value: float) -> str:
    return f"€{value:,.2f}"


def pct(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"


def load_supporting_data() -> dict[str, Any]:
    rules_frame = read_csv("cashflow_rules_dummy.csv", RULE_COLUMNS)
    rules_frame = rules_frame.apply(pd.to_numeric, errors="coerce")
    rules = rules_frame.iloc[0].copy()
    numeric_rules = RULE_COLUMNS
    if rules[numeric_rules].isna().any():
        raise ValueError("Cash-flow rule dataset contains non-numeric assumptions.")

    radar = read_csv("radar_dummy.csv", RADAR_COLUMNS)
    for col in ["current_price_eur", "high_52w_eur", "target_price_eur", "target_entry_price_eur", "risk_score", "opportunity_score"]:
        radar[col] = pd.to_numeric(radar[col], errors="coerce")
    if radar.isna().any().any():
        raise ValueError("Market radar dataset contains missing or non-numeric values.")
    if radar["ticker"].duplicated().any():
        raise ValueError("Market radar ticker values must be unique.")
    if (radar[["current_price_eur", "high_52w_eur", "target_price_eur", "target_entry_price_eur"]] <= 0).any().any():
        raise ValueError("Radar prices must be greater than zero.")
    if not radar["risk_score"].between(1, 5).all() or not radar["opportunity_score"].between(0, 100).all():
        raise ValueError("Radar risk must be 1–5 and opportunity score 0–100.")
    radar["drawdown_from_high_pct"] = radar["current_price_eur"] / radar["high_52w_eur"] - 1
    radar["modeled_upside_pct"] = radar["target_price_eur"] / radar["current_price_eur"] - 1
    radar["entry_gap_pct"] = radar["current_price_eur"] / radar["target_entry_price_eur"] - 1
    radar["screening_signal"] = "Monitor"
    radar.loc[radar["modeled_upside_pct"] >= 0.20, "screening_signal"] = "Higher modeled upside"
    radar.loc[radar["current_price_eur"] <= radar["target_entry_price_eur"] * (1 + float(rules["tactical_entry_buffer_pct"])), "screening_signal"] = "Entry gate reached"

    savings = read_csv("savings_accounts_dummy.csv", SAVINGS_COLUMNS)
    for col in ["balance_eur", "annual_rate_pct"]:
        savings[col] = pd.to_numeric(savings[col], errors="coerce")
    if savings.isna().any().any() or (savings["balance_eur"] < 0).any() or (savings["annual_rate_pct"] < 0).any():
        raise ValueError("Savings account data contains invalid balances or rates.")

    history = read_csv("savings_history_dummy.csv", HISTORY_COLUMNS)
    history["month"] = pd.to_datetime(history["month"], errors="coerce")
    for col in HISTORY_COLUMNS[1:]:
        history[col] = pd.to_numeric(history[col], errors="coerce")
    if history.isna().any().any():
        raise ValueError("Savings history contains invalid dates or values.")
    history["total_savings_eur"] = history[HISTORY_COLUMNS[1:]].sum(axis=1)

    transactions = read_csv("transactions_dummy.csv", TRANSACTION_COLUMNS)
    capital_income = read_csv("capital_income_dummy.csv", INCOME_COLUMNS)
    for col in ["gross_income_eur", "foreign_withholding_eur", "domestic_withholding_eur"]:
        capital_income[col] = pd.to_numeric(capital_income[col], errors="coerce")
    if capital_income.isna().any().any() or (capital_income[["gross_income_eur", "foreign_withholding_eur", "domestic_withholding_eur"]] < 0).any().any():
        raise ValueError("Capital income data contains invalid amounts.")
    capital_income["income_date"] = pd.to_datetime(capital_income["income_date"], errors="coerce")
    if capital_income["income_date"].isna().any():
        raise ValueError("Capital income dataset contains invalid dates.")
    capital_income["net_income_eur"] = (
        capital_income["gross_income_eur"]
        - capital_income["foreign_withholding_eur"]
        - capital_income["domestic_withholding_eur"]
    )

    brackets = read_csv("tax_brackets_demo.csv", BRACKET_COLUMNS)
    for col in BRACKET_COLUMNS:
        brackets[col] = pd.to_numeric(brackets[col], errors="coerce")
    if brackets.isna().any().any() or (brackets["illustrative_rate_pct"] < 0).any():
        raise ValueError("Tax demonstration assumptions are invalid.")

    realized = calculate_fifo_realized_pnl(transactions)
    return {
        "rules": rules,
        "radar": radar,
        "savings": savings,
        "history": history,
        "transactions": transactions,
        "capital_income": capital_income,
        "brackets": brackets,
        "realized": realized,
    }


def render_app() -> None:
    st.title("Personal Portfolio Analytics")
    st.caption(
        "A synthetic-data dashboard for portfolio valuation, Core–Satellite rebalancing, "
        "cash-flow planning, savings projections and tax-record demonstrations."
    )

    st.info(
        "**Demo mode:** the included figures are fictional examples, not live market data. "
        "Start by exploring the tabs below; no upload is needed. To test a budget scenario, "
        "open **Customize income & allocation** in the sidebar."
    )
    with st.expander("How to use this app — quick start", expanded=False):
        st.markdown(
            """
            **1. Start with the sample data.** The app loads fictional holdings, cash accounts,
            market-radar assumptions and transaction records automatically.

            **2. Explore the six sections.**
            - **Executive Dashboard:** demo net worth, portfolio mix and a 12-month scenario.
            - **Holdings & Strategy:** position performance, Core–Satellite allocation and Smart DCA.
            - **Market Radar:** static sample prices, target-price assumptions and screening rules.
            - **Income & Liquidity:** monthly budget, available cash and emergency-fund coverage.
            - **Savings Projection:** savings history and alternative projection assumptions.
            - **Tax & Reporting:** illustrative FIFO-matched sales, investment income and withholding.

            **A few terms in plain English**
            - **Core / Satellite:** core holdings are the main long-term allocation; satellite holdings are smaller, more tactical positions.
            - **Smart DCA:** a simulation of how a monthly investment contribution could be split across holdings below their target weights.
            - **Modeled upside:** a calculation against a fictional target price, not a prediction.
            - **FIFO:** matches a sale against the oldest available recorded purchase first.

            **3. Test a budget scenario.** In the sidebar, open **Customize income & allocation**.
            The income and percentage splits feed the dashboard and simulations; the four percentages
            should add up to 100%.

            **4. Upload holdings only if needed.** Use a CSV with the same columns as
            `data/posiciones_dummy.csv`. This replaces the holdings dataset only; the other sections
            continue using fictional example data.

            **5. Treat all outputs as demonstrations.** There is no broker connection or live market feed.
            Risk scores, target prices, projections and tax calculations are not recommendations or advice.
            """
        )

    try:
        data = load_supporting_data()
        with st.sidebar:
            st.markdown("### Getting started")
            st.caption(
                "Explore the sample data first. Account balances, radar inputs and tax records are fictional."
            )
            uploaded = st.file_uploader(
                "Upload a positions CSV (optional)",
                type=["csv"],
                help=(
                    "Use the documented positions schema. On a public hosted app, "
                    "do not upload private financial data. Uploading replaces only the holdings dataset."
                ),
            )
            positions_source = uploaded.getvalue() if uploaded is not None else None
            with st.expander("Customize income & allocation (optional)", expanded=False):
                st.caption("Change these assumptions to test a scenario. Allocation percentages should total 100%.")
                gross_income = st.number_input(
                    "Monthly gross income (€)", min_value=0.0,
                    value=float(data["rules"]["monthly_gross_income_eur"]), step=50.0,
                )
                withholding_pct = st.slider(
                    "Illustrative payroll withholding (%)", 0, 45,
                    int(round(float(data["rules"]["withholding_rate"]) * 100)),
                )
                st.markdown("**Monthly net-income allocation**")
                expense_share_pct = st.slider("Living expenses (%)", 0, 100, int(round(float(data["rules"]["expense_share"]) * 100)), 5)
                savings_share_pct = st.slider("Savings (%)", 0, 100, int(round(float(data["rules"]["savings_share"]) * 100)), 5)
                investment_share_pct = st.slider("Investment / Smart DCA (%)", 0, 100, int(round(float(data["rules"]["investment_share"]) * 100)), 5)
                opportunity_share_pct = st.slider("Opportunity reserve (%)", 0, 100, int(round(float(data["rules"]["opportunity_share"]) * 100)), 5)

        positions_raw = load_positions(positions_source)
        positions = calculate_positions(positions_raw, data["rules"])
    except (OSError, ValueError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        st.error(f"The dashboard could not load its data: {exc}")
        st.stop()

    rules = data["rules"]
    radar = data["radar"]
    savings = data["savings"].copy()
    history = data["history"]
    capital_income = data["capital_income"]
    realized = data["realized"]
    brackets = data["brackets"]

    allocation_total_pct = expense_share_pct + savings_share_pct + investment_share_pct + opportunity_share_pct
    net_income = gross_income * (1 - withholding_pct / 100.0)
    monthly_expenses = net_income * expense_share_pct / 100.0
    monthly_savings = net_income * savings_share_pct / 100.0
    monthly_investment = net_income * investment_share_pct / 100.0
    monthly_opportunity = net_income * opportunity_share_pct / 100.0

    portfolio_value = float(positions["market_value_eur"].sum())
    invested_capital = float(positions["invested_capital_eur"].sum())
    unrealized_pnl = float(positions["unrealized_pnl_eur"].sum())
    unrealized_return = unrealized_pnl / invested_capital if invested_capital else 0.0
    weighted_risk = float((positions["market_value_eur"] * positions["risk_score"]).sum() / portfolio_value)
    top_two_concentration = float(positions.nlargest(2, "market_value_eur")["current_weight"].sum())
    core_weight = float(positions.loc[positions["strategy_role"] == "Core", "current_weight"].sum())
    total_liquidity = float(savings["balance_eur"].sum())
    net_worth = portfolio_value + total_liquidity
    weighted_savings_rate = (
        float((savings["balance_eur"] * savings["annual_rate_pct"]).sum() / total_liquidity)
        if total_liquidity > 0 else 0.0
    )
    monthly_interest_estimate = float((savings["balance_eur"] * savings["annual_rate_pct"] / 100.0).sum() / 12)
    emergency_target = max(
        float(rules["emergency_fund_min_eur"]),
        monthly_expenses * float(rules["emergency_months"]),
    )
    investable_surplus = max(0.0, total_liquidity - emergency_target)
    foreign_liquidity = float(savings.loc[savings["country_code"].str.upper() != "ES", "balance_eur"].sum())
    concentration_status = "Above demo limit" if top_two_concentration > 0.55 else "Within demo limit"

    # Add radar target metrics to held positions for the dashboard-level upside estimate.
    held_radar = positions.merge(
        radar[["ticker", "target_price_eur", "modeled_upside_pct"]],
        on="ticker", how="left", validate="one_to_one",
    )
    held_radar["modeled_upside_pct"] = held_radar["modeled_upside_pct"].fillna(0.0)
    weighted_upside = float((held_radar["current_weight"] * held_radar["modeled_upside_pct"]).sum())

    tabs = st.tabs([
        "Executive Dashboard", "Holdings & Strategy", "Market Radar",
        "Income & Liquidity", "Savings Projection", "Tax & Reporting",
    ])

    # 1 — Executive dashboard.
    with tabs[0]:
        st.subheader("Portfolio overview")
        if uploaded is not None:
            st.warning(
                "A custom positions CSV is active. Holdings and related portfolio metrics use that file; "
                "cash, radar, transaction and tax examples remain synthetic repository data."
            )
        if allocation_total_pct != 100:
            st.warning(
                f"Your monthly allocation totals {allocation_total_pct}%, not 100%. "
                "The unallocated amount is shown below rather than silently reassigned."
            )
        target_sum = float(positions["target_weight"].sum())
        if abs(target_sum - 1.0) > 0.01:
            st.warning(f"Holding target weights total {pct(target_sum)}, not 100%.")

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Illustrative net worth", eur(net_worth))
        k2.metric("Investment portfolio", eur(portfolio_value))
        k3.metric("Unrealized P&L", eur(unrealized_pnl), f"{unrealized_return:+.2%} return")
        k4.metric("Weighted risk score", f"{weighted_risk:.2f} / 5", risk_label(weighted_risk))

        k5, k6, k7, k8 = st.columns(4)
        k5.metric("Cash & savings", eur(total_liquidity))
        k6.metric("Core allocation", pct(core_weight))
        k7.metric("Top-two concentration", pct(top_two_concentration), concentration_status, delta_color="off")
        k8.metric("Weighted modeled upside", pct(weighted_upside), "Scenario input; not a forecast", delta_color="off")

        left, right = st.columns([1, 1.2], gap="large")
        with left:
            st.markdown("#### Current asset allocation")
            allocation = positions.groupby("asset_class", as_index=False)["market_value_eur"].sum()
            fig = px.pie(
                allocation, names="asset_class", values="market_value_eur", hole=0.58,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_traces(
                textposition="inside", textinfo="percent",
                hovertemplate="%{label}<br>Market value: €%{value:,.2f}<br>Weight: %{percent}<extra></extra>",
            )
            fig.update_layout(height=365, margin=dict(l=5, r=5, t=12, b=8), legend=dict(orientation="h", y=-0.05))
            st.plotly_chart(fig, use_container_width=True)
        with right:
            st.markdown("#### Current vs. target weights")
            weight_plot = positions[["asset", "current_weight", "target_weight"]].melt(
                id_vars="asset", var_name="weight_type", value_name="weight"
            )
            weight_plot["weight_type"] = weight_plot["weight_type"].map({"current_weight": "Current", "target_weight": "Target"})
            fig = px.bar(
                weight_plot, x="asset", y="weight", color="weight_type", barmode="group",
                labels={"asset": "Holding", "weight": "Portfolio weight", "weight_type": "Weight"},
                color_discrete_sequence=["#2563EB", "#A7B4C8"],
            )
            fig.update_yaxes(tickformat=".0%", rangemode="tozero")
            fig.update_xaxes(tickangle=-30)
            fig.update_layout(height=365, margin=dict(l=8, r=8, t=10, b=100), legend=dict(orientation="h", y=1.08))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Net-worth projection scenario")
        with st.expander("Adjust scenario assumptions", expanded=False):
            p_return = st.slider("Illustrative annual investment return (%)", -20.0, 20.0, 6.0, 0.5)
            s_return = st.slider("Annual cash/savings return assumption (%)", 0.0, 10.0, round(weighted_savings_rate, 2), 0.25)
        projection = build_projection(
            portfolio_value, total_liquidity,
            monthly_investment if allocation_total_pct == 100 else 0.0,
            monthly_savings if allocation_total_pct == 100 else 0.0,
            p_return, s_return, 12,
        )
        projection_long = projection.melt(
            id_vars="Month", var_name="Component", value_name="Value (€)"
        )
        fig = px.line(
            projection_long, x="Month", y="Value (€)", color="Component", markers=True,
            color_discrete_sequence=["#2563EB", "#10B981", "#94A3B8"],
        )
        fig.update_layout(height=360, margin=dict(l=8, r=8, t=12, b=8), legend=dict(orientation="h", y=1.08))
        fig.update_yaxes(tickprefix="€", separatethousands=True)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Projection only: constant contribution and return assumptions are illustrative; actual results will differ.")

    # 2 — Holdings and Core–Satellite strategy.
    with tabs[1]:
        st.subheader("Holdings, performance and rebalancing")
        st.caption("Position-level P&L is derived from quantity and the example purchase/market prices in the selected CSV.")
        display = positions.copy()
        for col in ["current_weight", "target_weight", "weight_deviation", "return_pct", "daily_change_pct"]:
            display[col] = display[col] * 100
        display = display.rename(columns={
            "asset": "Asset", "ticker": "Ticker", "asset_class": "Asset class", "strategy_role": "Strategy role",
            "quantity": "Quantity", "purchase_price_eur": "Purchase price (€)", "market_price_eur": "Market price (€)",
            "invested_capital_eur": "Invested capital (€)", "market_value_eur": "Market value (€)",
            "unrealized_pnl_eur": "Unrealized P&L (€)", "return_pct": "Return (%)", "daily_change_pct": "Daily change (%)",
            "current_weight": "Current weight (%)", "target_weight": "Target weight (%)",
            "weight_deviation": "Weight deviation (pp)", "risk_score": "Risk score (1–5)", "rebalance_signal": "Rebalancing status",
        })
        st.dataframe(
            display[["Asset", "Ticker", "Asset class", "Strategy role", "Quantity", "Purchase price (€)", "Market price (€)", "Invested capital (€)", "Market value (€)", "Unrealized P&L (€)", "Return (%)", "Daily change (%)", "Current weight (%)", "Target weight (%)", "Weight deviation (pp)", "Risk score (1–5)", "Rebalancing status"]],
            use_container_width=True, hide_index=True,
            column_config={
                "Purchase price (€)": st.column_config.NumberColumn(format="€%.2f"),
                "Market price (€)": st.column_config.NumberColumn(format="€%.2f"),
                "Invested capital (€)": st.column_config.NumberColumn(format="€%.2f"),
                "Market value (€)": st.column_config.NumberColumn(format="€%.2f"),
                "Unrealized P&L (€)": st.column_config.NumberColumn(format="€%.2f"),
                "Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Current weight (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Target weight (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Weight deviation (pp)": st.column_config.NumberColumn(format="%.2f"),
                "Daily change (%)": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )
        st.markdown("#### Core–Satellite composition")
        core_value = float(positions.loc[positions["strategy_role"] == "Core", "market_value_eur"].sum())
        satellite_value = float(positions.loc[positions["strategy_role"] == "Satellite", "market_value_eur"].sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Core value", eur(core_value), pct(core_value / portfolio_value if portfolio_value else 0))
        c2.metric("Satellite value", eur(satellite_value), pct(satellite_value / portfolio_value if portfolio_value else 0))
        c3.metric("Number of holdings", str(len(positions)), f"{positions['asset_class'].nunique()} asset classes")

        st.markdown("#### Smart DCA contribution-routing simulation")
        dca_contribution = monthly_investment if allocation_total_pct == 100 else 0.0
        dca, dca_info = calculate_smart_dca(positions, radar, dca_contribution, rules)
        if dca_info["tactical_active"]:
            st.warning(
                f"The illustrative tactical gate is met by {dca_info['candidate_asset']} "
                f"({dca_info['candidate_ticker']}). The demo routes {int(float(rules['tactical_rebalance_share']) * 100)}% "
                "to target-weight gaps and the remainder to the radar candidate. This is a rule demonstration, not a recommendation."
            )
        else:
            st.info("No radar candidate meets the illustrative tactical gate; the contribution is routed toward underweight holdings.")
        c1, c2, c3 = st.columns(3)
        c1.metric("Monthly investment budget", eur(monthly_investment))
        c2.metric("Simulated allocation", eur(dca_info["allocated"]))
        c3.metric("Unallocated remainder", eur(dca_info["unallocated"]))
        dca_view = dca[["asset", "ticker", "strategy_role", "current_weight", "target_weight", "weight_deviation", "positive_gap_eur", "monthly_dca_eur"]].copy()
        for percentage_column in ["current_weight", "target_weight", "weight_deviation"]:
            dca_view[percentage_column] *= 100
        dca_view = dca_view.rename(columns={
            "asset": "Asset / allocation", "ticker": "Ticker", "strategy_role": "Role", "current_weight": "Current weight",
            "target_weight": "Target weight", "weight_deviation": "Weight deviation", "positive_gap_eur": "Positive target gap (€)", "monthly_dca_eur": "Illustrative monthly allocation (€)",
        })
        st.dataframe(
            dca_view, use_container_width=True, hide_index=True,
            column_config={
                "Current weight": st.column_config.NumberColumn(format="%.2f%%"),
                "Target weight": st.column_config.NumberColumn(format="%.2f%%"),
                "Weight deviation": st.column_config.NumberColumn(format="%.2f%%"),
                "Positive target gap (€)": st.column_config.NumberColumn(format="€%.2f"),
                "Illustrative monthly allocation (€)": st.column_config.NumberColumn(format="€%.2f"),
            },
        )
        st.caption("Smart DCA allocates contributions proportionally to positive target-weight gaps; it does not recommend selling overweight positions.")

    # 3 — Market radar.
    with tabs[2]:
        st.subheader("Market radar & expectations")
        st.caption("All prices, targets and scores are fictional static inputs; there is no live market-data connection.")
        r1, r2, r3 = st.columns(3)
        r1.metric("Assets in radar", str(len(radar)))
        r2.metric("Average modeled upside", pct(float(radar["modeled_upside_pct"].mean())))
        max_drawdown = radar.loc[radar["drawdown_from_high_pct"].idxmin()]
        r3.metric("Largest drawdown from 52-week high", f"{max_drawdown['asset']}", pct(float(max_drawdown["drawdown_from_high_pct"])))

        radar_filter = st.multiselect(
            "Filter asset classes", options=sorted(radar["asset_class"].unique()),
            default=sorted(radar["asset_class"].unique()),
        )
        radar_view = radar[radar["asset_class"].isin(radar_filter)].copy()
        fig = px.scatter(
            radar_view, x="risk_score", y="modeled_upside_pct", color="asset_class",
            size="opportunity_score", hover_name="asset", hover_data={
                "ticker": True, "current_price_eur": ":.2f", "target_price_eur": ":.2f",
                "drawdown_from_high_pct": ":.1%", "opportunity_score": True,
            }, labels={"risk_score": "Illustrative risk score (1–5)", "modeled_upside_pct": "Modeled upside to target", "asset_class": "Asset class"},
        )
        fig.update_yaxes(tickformat=".0%")
        fig.update_layout(height=400, margin=dict(l=8, r=8, t=15, b=8))
        st.plotly_chart(fig, use_container_width=True)

        radar_table = radar_view.copy()
        for col in ["drawdown_from_high_pct", "modeled_upside_pct", "entry_gap_pct"]:
            radar_table[col] *= 100
        radar_table = radar_table.rename(columns={
            "asset": "Asset", "ticker": "Ticker", "asset_class": "Asset class", "current_price_eur": "Current price (€)",
            "high_52w_eur": "52-week high (€)", "target_price_eur": "Target price (€)",
            "target_entry_price_eur": "Target entry price (€)", "risk_score": "Risk score (1–5)",
            "opportunity_score": "Demo score (0–100)", "drawdown_from_high_pct": "Distance from high (%)",
            "modeled_upside_pct": "Modeled upside (%)", "entry_gap_pct": "Distance from entry (%)",
            "screening_signal": "Rule-based screen", "watch_reason": "Watchlist note",
        })
        st.dataframe(
            radar_table[["Asset", "Ticker", "Asset class", "Current price (€)", "52-week high (€)", "Target price (€)", "Target entry price (€)", "Distance from high (%)", "Modeled upside (%)", "Distance from entry (%)", "Risk score (1–5)", "Demo score (0–100)", "Rule-based screen", "Watchlist note"]],
            use_container_width=True, hide_index=True,
            column_config={
                "Current price (€)": st.column_config.NumberColumn(format="€%.2f"),
                "52-week high (€)": st.column_config.NumberColumn(format="€%.2f"),
                "Target price (€)": st.column_config.NumberColumn(format="€%.2f"),
                "Target entry price (€)": st.column_config.NumberColumn(format="€%.2f"),
                "Distance from high (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Modeled upside (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Distance from entry (%)": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )
        st.caption("Targets and rules are user-defined demo assumptions. Modeled upside is not a forecast or expected return.")

    # 4 — Cash flow and liquidity.
    with tabs[3]:
        st.subheader("Income allocation & liquidity management")
        st.caption("Adjust the monthly budget in the sidebar. These assumptions feed the emergency-reserve and Smart DCA simulations.")
        total_alloc = expense_share_pct + savings_share_pct + investment_share_pct + opportunity_share_pct
        kpi_cols = st.columns(4)
        kpi_cols[0].metric("Gross monthly income", eur(gross_income))
        kpi_cols[1].metric("Net monthly income", eur(net_income))
        kpi_cols[2].metric("Savings rate", pct(savings_share_pct / 100 + investment_share_pct / 100))
        kpi_cols[3].metric("Allocation validation", f"{total_alloc}%", "Balanced" if total_alloc == 100 else "Needs adjustment", delta_color="off")

        cashflow_rows = [
            {"Allocation bucket": "Living expenses", "Share (%)": expense_share_pct, "Monthly amount (€)": monthly_expenses},
            {"Allocation bucket": "Fixed savings", "Share (%)": savings_share_pct, "Monthly amount (€)": monthly_savings},
            {"Allocation bucket": "Investment / Smart DCA", "Share (%)": investment_share_pct, "Monthly amount (€)": monthly_investment},
            {"Allocation bucket": "Opportunity reserve", "Share (%)": opportunity_share_pct, "Monthly amount (€)": monthly_opportunity},
        ]
        cashflow_frame = pd.DataFrame(cashflow_rows)
        left, right = st.columns([1, 1], gap="large")
        with left:
            st.markdown("#### Net income allocation rule")
            st.dataframe(cashflow_frame, hide_index=True, use_container_width=True, column_config={
                "Share (%)": st.column_config.NumberColumn(format="%d%%"),
                "Monthly amount (€)": st.column_config.NumberColumn(format="€%.2f"),
            })
            unallocated = net_income * (100 - total_alloc) / 100
            st.metric("Unallocated / overallocated amount", eur(unallocated))
        with right:
            fig = px.pie(cashflow_frame, names="Allocation bucket", values="Monthly amount (€)", hole=0.50,
                         color_discrete_sequence=["#64748B", "#10B981", "#2563EB", "#F59E0B"])
            fig.update_traces(textposition="inside", textinfo="percent")
            fig.update_layout(height=330, margin=dict(l=5, r=5, t=10, b=5), legend=dict(orientation="h", y=-0.05))
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.markdown("#### Consolidated cash accounts")
        savings_display = savings.copy()
        savings_display["estimated_annual_interest_eur"] = savings_display["balance_eur"] * savings_display["annual_rate_pct"] / 100
        savings_display["estimated_monthly_interest_eur"] = savings_display["estimated_annual_interest_eur"] / 12
        st.dataframe(savings_display.rename(columns={
            "account_name": "Account", "account_type": "Account type", "country_code": "Country",
            "liquidity": "Liquidity", "balance_eur": "Balance (€)", "annual_rate_pct": "Illustrative annual rate (%)",
            "purpose": "Purpose", "estimated_annual_interest_eur": "Annual interest estimate (€)",
            "estimated_monthly_interest_eur": "Monthly interest estimate (€)",
        }), use_container_width=True, hide_index=True, column_config={
            "Balance (€)": st.column_config.NumberColumn(format="€%.2f"),
            "Illustrative annual rate (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "Annual interest estimate (€)": st.column_config.NumberColumn(format="€%.2f"),
            "Monthly interest estimate (€)": st.column_config.NumberColumn(format="€%.2f"),
        })

        required_reserve = max(float(rules["emergency_fund_min_eur"]), monthly_expenses * float(rules["emergency_months"]))
        investable = max(0.0, total_liquidity - required_reserve)
        l1, l2, l3, l4 = st.columns(4)
        l1.metric("Consolidated liquidity", eur(total_liquidity))
        l2.metric("Emergency reserve target", eur(required_reserve), f"{rules['emergency_months']:.0f} months of expenses / minimum floor")
        l3.metric("Illustrative investable surplus", eur(investable))
        l4.metric("Weighted annual cash yield", pct(weighted_savings_rate / 100))
        st.caption("Balances and rates are fictitious. Interest estimates assume static balances and do not model compounding, fees or tax.")

    # 5 — Savings and net-worth projection.
    with tabs[4]:
        st.subheader("Savings growth & compound projections")
        savings_chart = history.melt(
            id_vars="month", value_vars=["cash_savings_eur", "fixed_savings_eur", "operating_cash_eur"],
            var_name="account_type", value_name="balance_eur",
        )
        savings_chart["account_type"] = savings_chart["account_type"].map({
            "cash_savings_eur": "Interest-bearing cash", "fixed_savings_eur": "Savings platform", "operating_cash_eur": "Operating cash",
        })
        fig = px.line(
            savings_chart, x="month", y="balance_eur", color="account_type", markers=True,
            labels={"month": "Month", "balance_eur": "Balance (€)", "account_type": "Account"},
            color_discrete_sequence=["#2563EB", "#10B981", "#94A3B8"],
        )
        fig.update_layout(height=380, margin=dict(l=8, r=8, t=10, b=8))
        fig.update_yaxes(tickprefix="€", separatethousands=True)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 12-month scenario builder")
        sc1, sc2 = st.columns(2)
        with sc1:
            annual_investment_return = st.slider("Illustrative annual investment return (%)", -20.0, 20.0, 6.0, 0.5, key="projection_portfolio_return")
        with sc2:
            annual_cash_return = st.slider("Annual cash/savings return assumption (%)", 0.0, 10.0, round(weighted_savings_rate, 2), 0.25, key="projection_savings_return")
        projection = build_projection(
            portfolio_value, total_liquidity,
            monthly_investment if allocation_total_pct == 100 else 0.0,
            monthly_savings if allocation_total_pct == 100 else 0.0,
            annual_investment_return, annual_cash_return, 12,
        )
        projection_long = projection.melt(id_vars="Month", var_name="Component", value_name="Value (€)")
        fig = px.line(projection_long, x="Month", y="Value (€)", color="Component", markers=True,
                      color_discrete_sequence=["#2563EB", "#10B981", "#64748B"])
        fig.update_layout(height=370, margin=dict(l=8, r=8, t=10, b=8))
        fig.update_yaxes(tickprefix="€", separatethousands=True)
        st.plotly_chart(fig, use_container_width=True)
        final_row = projection.iloc[-1]
        a, b, c = st.columns(3)
        a.metric("Projected portfolio after 12 months", eur(float(final_row["Investment portfolio (€)"])))
        b.metric("Projected savings & cash", eur(float(final_row["Savings & cash (€)"])))
        c.metric("Projected illustrative net worth", eur(float(final_row["Illustrative net worth (€)"])))
        st.caption("The historical line chart uses synthetic monthly snapshots. The forecast uses fixed assumptions, not a probabilistic or guaranteed-return model.")

    # 6 — Tax and reporting.
    with tabs[5]:
        st.subheader("Tax-record and international-account monitoring")
        st.warning(
            "Educational demonstration only. The tax brackets are synthetic, editable assumptions—not current legal tax rates. "
            "The foreign-balance threshold is only a monitoring flag; it does not determine whether any declaration is legally required."
        )
        realized_total = float(realized["realized_pnl_eur"].sum()) if not realized.empty else 0.0
        gross_capital_income = float(capital_income["gross_income_eur"].sum())
        withheld_total = float((capital_income["foreign_withholding_eur"] + capital_income["domestic_withholding_eur"]).sum())
        illustrative_base = max(0.0, realized_total + gross_capital_income)
        illustrative_tax = progressive_demo_tax(illustrative_base, brackets)

        t1, t2, t3, t4 = st.columns(4)
        t1.metric("FIFO realized P&L", eur(realized_total))
        t2.metric("Gross interest & dividends", eur(gross_capital_income))
        t3.metric("Recorded withholding", eur(withheld_total))
        t4.metric("Demo tax provision", eur(illustrative_tax), "Before credits/deductions", delta_color="off")

        st.markdown("#### Closed transactions matched using FIFO")
        if realized.empty:
            st.info("The transaction ledger contains no completed sales.")
        else:
            realized_display = realized.copy()
            realized_display["transaction_date"] = realized_display["transaction_date"].dt.strftime("%Y-%m-%d")
            realized_display = realized_display.rename(columns={
                "transaction_date": "Sale date", "asset": "Asset", "ticker": "Ticker", "quantity_sold": "Quantity sold",
                "sale_price_eur": "Sale price (€)", "net_proceeds_eur": "Net proceeds (€)",
                "fifo_cost_basis_eur": "FIFO cost basis (€)", "realized_pnl_eur": "Realized P&L (€)", "method": "Cost-basis method",
            })
            st.dataframe(realized_display, use_container_width=True, hide_index=True, column_config={
                "Sale price (€)": st.column_config.NumberColumn(format="€%.2f"),
                "Net proceeds (€)": st.column_config.NumberColumn(format="€%.2f"),
                "FIFO cost basis (€)": st.column_config.NumberColumn(format="€%.2f"),
                "Realized P&L (€)": st.column_config.NumberColumn(format="€%.2f"),
            })
        st.caption("FIFO is implemented on the included synthetic BUY/SELL transaction ledger. It does not reconstruct or validate any real tax return.")

        st.markdown("#### Passive investment income")
        passive_display = capital_income.copy()
        passive_display["income_date"] = passive_display["income_date"].dt.strftime("%Y-%m-%d")
        passive_display = passive_display.rename(columns={
            "income_date": "Income date", "source_name": "Source", "income_type": "Type", "country_code": "Country",
            "gross_income_eur": "Gross income (€)", "foreign_withholding_eur": "Foreign withholding (€)",
            "domestic_withholding_eur": "Domestic withholding (€)", "net_income_eur": "Net received (€)",
        })
        st.dataframe(passive_display, use_container_width=True, hide_index=True, column_config={
            "Gross income (€)": st.column_config.NumberColumn(format="€%.2f"),
            "Foreign withholding (€)": st.column_config.NumberColumn(format="€%.2f"),
            "Domestic withholding (€)": st.column_config.NumberColumn(format="€%.2f"),
            "Net received (€)": st.column_config.NumberColumn(format="€%.2f"),
        })

        st.markdown("#### Foreign-account balance monitor")
        threshold = float(rules["foreign_asset_monitor_threshold_eur"])
        monitor_status = "At/above configured threshold" if foreign_liquidity >= threshold else "Below configured threshold"
        f1, f2, f3 = st.columns(3)
        f1.metric("Demo foreign-held cash", eur(foreign_liquidity))
        f2.metric("Configured monitoring threshold", eur(threshold))
        f3.metric("Monitoring status", monitor_status, delta_color="off")
        st.markdown("#### Illustrative tax assumptions used by this demo")
        st.dataframe(brackets.rename(columns={
            "lower_bound_eur": "Band starts (€)", "upper_bound_eur": "Band ends (€)", "illustrative_rate_pct": "Demo marginal rate (%)",
        }), hide_index=True, use_container_width=True, column_config={
            "Band starts (€)": st.column_config.NumberColumn(format="€%.0f"),
            "Band ends (€)": st.column_config.NumberColumn(format="€%.0f"),
            "Demo marginal rate (%)": st.column_config.NumberColumn(format="%.1f%%"),
        })
        st.caption(
            "The provision is a simple progressive calculation on max(0, FIFO realized P&L + gross passive income). "
            "It excludes loss-compensation rules, allowances, jurisdiction-specific rules, foreign-tax-credit limitations, "
            "timing effects and other personal circumstances. Consult official guidance or a qualified adviser before making decisions."
        )

    st.divider()
    st.caption(
        "Privacy by design: the repository contains synthetic sample data only. If deployed publicly, do not upload personal statements, "
        "account identifiers, salary records or real holdings. All market prices, target prices, cash balances, transaction records and tax inputs in the repository are invented."
    )


def risk_label(score: float) -> str:
    if score < 2.0:
        return "Lower illustrative risk"
    if score < 3.25:
        return "Moderate illustrative risk"
    if score < 4.25:
        return "Elevated illustrative risk"
    return "High illustrative risk"


if __name__ == "__main__":
    render_app()
