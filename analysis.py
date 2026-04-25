"""
DCF Valuation Analysis
======================

Pulls live financials from Yahoo Finance via yfinance, runs a discounted
cash-flow model, produces:
  - intrinsic value per share + verdict (UNDERVALUED / FAIR / OVERVALUED)
  - 5-year explicit FCF projection + Gordon Growth terminal value
  - WACC × terminal-growth sensitivity matrix
  - Historical FCF table
  - 6 analyst-style takeaways

Outputs as parquets consumed by the dashboard:
  - summary.parquet            ← hero KPIs
  - assumptions.parquet        ← input/output table
  - dcf_breakdown.parquet      ← year-by-year FCF, discount factor, PV
  - sensitivity.parquet        ← WACC × g matrix (long form)
  - historical_fcf.parquet     ← last 5 fiscal years
  - takeaways.parquet          ← 6 ranked insights
"""

import json
import os
import sys
import time

import pandas as pd
import pyarrow as pa

sys.path.insert(0, "/")
from bedrock_sdk import BedrockJob


def fnum(x, default=None):
    """Safe float conversion — yfinance returns NaN/None inconsistently."""
    try:
        if x is None:
            return default
        if isinstance(x, str):
            return float(x.replace(",", ""))
        f = float(x)
        if pd.isna(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


def fetch_yfinance(ticker: str, attempts: int = 3):
    """yfinance is rate-limited and flaky. Retry with exponential backoff."""
    import yfinance as yf
    last_err = None
    for i in range(attempts):
        try:
            t = yf.Ticker(ticker)
            info = t.info
            cashflow = t.cashflow
            balance = t.balance_sheet
            income = t.income_stmt
            if not info or info.get("regularMarketPrice") is None:
                raise RuntimeError(f"yfinance returned no info for {ticker} — check ticker symbol")
            return t, info, cashflow, balance, income
        except Exception as e:
            last_err = e
            if i < attempts - 1:
                time.sleep(2 ** i)
    raise RuntimeError(f"yfinance failed after {attempts} attempts: {last_err}")


def historical_fcf(cashflow_df) -> list:
    """Extract Free Cash Flow per fiscal year. Returns [(year_str, fcf)] newest first."""
    if cashflow_df is None or cashflow_df.empty:
        return []
    rows = []
    candidates = ["Free Cash Flow", "Operating Cash Flow", "Total Cash From Operating Activities"]
    target = None
    for c in candidates:
        if c in cashflow_df.index:
            target = c
            break
    if target is None:
        return []
    for col in cashflow_df.columns:
        year = pd.to_datetime(col).year if hasattr(col, "year") or isinstance(col, str) else col
        v = fnum(cashflow_df.loc[target, col])
        if v is not None:
            rows.append((str(year), v))
    return rows


def cagr(values: list) -> float:
    """Compound annual growth rate from oldest to newest. values in chronological order."""
    if len(values) < 2:
        return 0.0
    start, end = values[0], values[-1]
    if start <= 0 or end <= 0:
        return 0.0
    n = len(values) - 1
    return (end / start) ** (1.0 / n) - 1.0


def project_fcf(latest_fcf: float, growth: float, years: int) -> list:
    """Project FCF for `years` years given latest FCF and growth rate."""
    return [latest_fcf * ((1 + growth) ** y) for y in range(1, years + 1)]


def discount(fcfs: list, wacc: float) -> list:
    """Present value of each projected FCF."""
    return [fcf / ((1 + wacc) ** y) for y, fcf in enumerate(fcfs, start=1)]


def terminal_value(last_fcf: float, terminal_g: float, wacc: float, projection_years: int) -> tuple:
    """Gordon Growth terminal value, then discount to present."""
    if wacc <= terminal_g:
        # Avoid division-by-zero / negative TV. Return 0; flagged in takeaways.
        return 0.0, 0.0
    tv = last_fcf * (1 + terminal_g) / (wacc - terminal_g)
    pv_tv = tv / ((1 + wacc) ** projection_years)
    return tv, pv_tv


def sensitivity_matrix(latest_fcf: float, growth: float, projection_years: int,
                        wacc_grid: list, g_grid: list, shares: float, net_cash: float) -> list:
    """For each (wacc, g) pair, recompute intrinsic value per share."""
    rows = []
    for w in wacc_grid:
        for g in g_grid:
            fcfs = project_fcf(latest_fcf, growth, projection_years)
            pv_fcfs = discount(fcfs, w)
            _, pv_tv = terminal_value(fcfs[-1], g, w, projection_years)
            ev = sum(pv_fcfs) + pv_tv
            equity = ev + net_cash
            per_share = equity / shares if shares > 0 else 0.0
            rows.append({"wacc": w, "g": g, "intrinsic_per_share": per_share})
    return rows


def main() -> None:
    job = BedrockJob()
    ticker = os.environ.get("PARAM_TICKER", "AAPL").upper().strip()
    wacc = fnum(os.environ.get("PARAM_WACC"), 0.10)
    terminal_g = fnum(os.environ.get("PARAM_TERMINAL_GROWTH"), 0.03)
    projection_years = int(fnum(os.environ.get("PARAM_PROJECTION_YEARS"), 5) or 5)

    job.progress(5, f"Pulling yfinance data for {ticker}…")
    t, info, cashflow, balance, income = fetch_yfinance(ticker)

    company_name = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector") or "Unknown"
    industry = info.get("industry") or "Unknown"
    current_price = fnum(info.get("regularMarketPrice") or info.get("currentPrice"), 0.0)
    shares_out = fnum(info.get("sharesOutstanding"), 0.0)
    market_cap = fnum(info.get("marketCap"), 0.0)
    total_cash = fnum(info.get("totalCash"), 0.0)
    total_debt = fnum(info.get("totalDebt"), 0.0)
    net_cash = total_cash - total_debt

    job.progress(20, f"Computing historical FCF for {company_name}…")
    hist = historical_fcf(cashflow)  # newest first
    if not hist:
        raise RuntimeError(f"Could not extract FCF history from yfinance for {ticker}")
    hist_chrono = list(reversed(hist))
    hist_values = [v for _, v in hist_chrono]
    historical_growth = cagr(hist_values)
    latest_fcf = hist[0][1]

    job.progress(40, f"Running DCF — WACC={wacc:.2%}, g={terminal_g:.2%}, {projection_years}y horizon…")
    growth_for_projection = max(min(historical_growth, 0.25), -0.10)  # clamp -10%..+25%
    projected = project_fcf(latest_fcf, growth_for_projection, projection_years)
    pv_projected = discount(projected, wacc)
    tv, pv_tv = terminal_value(projected[-1], terminal_g, wacc, projection_years)

    enterprise_value = sum(pv_projected) + pv_tv
    equity_value = enterprise_value + net_cash
    intrinsic_per_share = equity_value / shares_out if shares_out > 0 else 0.0
    upside_pct = ((intrinsic_per_share / current_price) - 1.0) * 100.0 if current_price > 0 else 0.0
    margin_of_safety = upside_pct
    if upside_pct >= 20:
        verdict = "UNDERVALUED"
    elif upside_pct <= -20:
        verdict = "OVERVALUED"
    else:
        verdict = "FAIR VALUE"

    job.progress(60, "Building sensitivity matrix…")
    wacc_grid = [round(wacc + d, 4) for d in (-0.02, -0.01, 0.0, 0.01, 0.02)]
    g_grid = [round(terminal_g + d, 4) for d in (-0.01, -0.005, 0.0, 0.005, 0.01)]
    sens_rows = sensitivity_matrix(latest_fcf, growth_for_projection, projection_years,
                                    wacc_grid, g_grid, shares_out, net_cash)

    job.progress(75, "Writing parquet outputs…")
    conn = job.connect()

    # ── summary (hero KPIs) ──
    summary_row = [{
        "ticker": ticker,
        "company": company_name,
        "current_price": current_price,
        "intrinsic_per_share": intrinsic_per_share,
        "upside_pct": upside_pct,
        "verdict": verdict,
        "market_cap_b": market_cap / 1e9 if market_cap else 0.0,
    }]
    conn.register("summary_t", pa.Table.from_pylist(summary_row))
    job.write_parquet("summary", "SELECT * FROM summary_t")

    # ── assumptions table ──
    assumptions = [
        {"key": "Ticker",                      "value": ticker},
        {"key": "Company",                     "value": company_name},
        {"key": "Sector / Industry",           "value": f"{sector} / {industry}"},
        {"key": "Current price ($)",           "value": f"{current_price:,.2f}"},
        {"key": "Shares outstanding (B)",      "value": f"{shares_out / 1e9:,.3f}"},
        {"key": "Market cap ($B)",             "value": f"{market_cap / 1e9:,.2f}"},
        {"key": "Net cash / (debt) ($B)",      "value": f"{net_cash / 1e9:,.2f}"},
        {"key": "Latest FCF ($B)",             "value": f"{latest_fcf / 1e9:,.2f}"},
        {"key": "Historical FCF CAGR",         "value": f"{historical_growth * 100:,.1f}%"},
        {"key": "Growth used for projection",  "value": f"{growth_for_projection * 100:,.1f}% (clamped)"},
        {"key": "WACC (discount rate)",        "value": f"{wacc * 100:,.2f}%"},
        {"key": "Terminal growth rate",        "value": f"{terminal_g * 100:,.2f}%"},
        {"key": "Projection horizon",          "value": f"{projection_years} years"},
        {"key": "PV of projected FCF ($B)",    "value": f"{sum(pv_projected) / 1e9:,.2f}"},
        {"key": "PV of terminal value ($B)",   "value": f"{pv_tv / 1e9:,.2f}"},
        {"key": "Enterprise value ($B)",       "value": f"{enterprise_value / 1e9:,.2f}"},
        {"key": "Equity value ($B)",           "value": f"{equity_value / 1e9:,.2f}"},
        {"key": "Intrinsic value per share",   "value": f"${intrinsic_per_share:,.2f}"},
        {"key": "Margin of safety",            "value": f"{margin_of_safety:+,.1f}%"},
        {"key": "Verdict",                     "value": verdict},
    ]
    conn.register("assumptions_t", pa.Table.from_pylist(assumptions))
    job.write_parquet("assumptions", "SELECT * FROM assumptions_t")

    # ── dcf breakdown — `year` is always a STRING so the projection
    # rows ("1".."5") and the terminal row ("Terminal") share a column type.
    breakdown = []
    for y, (fcf, pv) in enumerate(zip(projected, pv_projected), start=1):
        breakdown.append({
            "year": str(y),
            "projected_fcf_b": fcf / 1e9,
            "discount_factor": round(1.0 / ((1 + wacc) ** y), 4),
            "present_value_b": pv / 1e9,
        })
    breakdown.append({
        "year": "Terminal",
        "projected_fcf_b": tv / 1e9,
        "discount_factor": round(1.0 / ((1 + wacc) ** projection_years), 4),
        "present_value_b": pv_tv / 1e9,
    })
    conn.register("breakdown_t", pa.Table.from_pylist(breakdown))
    job.write_parquet("dcf_breakdown", "SELECT * FROM breakdown_t")

    # ── sensitivity matrix (long form for line/heat chart) ──
    sens_for_parquet = [{
        "wacc_pct": round(r["wacc"] * 100, 2),
        "g_pct": round(r["g"] * 100, 2),
        "intrinsic_per_share": round(r["intrinsic_per_share"], 2),
    } for r in sens_rows]
    conn.register("sens_t", pa.Table.from_pylist(sens_for_parquet))
    job.write_parquet("sensitivity", "SELECT * FROM sens_t ORDER BY wacc_pct, g_pct")

    # ── historical FCF (oldest → newest) ──
    hist_rows = [{"fiscal_year": y, "fcf_b": v / 1e9} for y, v in hist_chrono]
    conn.register("hist_t", pa.Table.from_pylist(hist_rows))
    job.write_parquet("historical_fcf", "SELECT * FROM hist_t")

    # ── takeaways (6 ranked insights) ──
    takeaways = []
    takeaways.append({
        "rank": 1,
        "category": "Verdict",
        "insight": f"{ticker} appears **{verdict}** at ${current_price:,.2f} vs. intrinsic ${intrinsic_per_share:,.2f} — margin of safety {margin_of_safety:+,.1f}%.",
    })
    fcf_quality = "positive and growing" if latest_fcf > 0 and historical_growth > 0 else (
        "positive but contracting" if latest_fcf > 0 else "negative — DCF result is highly speculative"
    )
    takeaways.append({
        "rank": 2,
        "category": "FCF Quality",
        "insight": f"Latest FCF of ${latest_fcf / 1e9:,.2f}B is {fcf_quality}. Historical CAGR over {len(hist) - 1} years: {historical_growth * 100:+,.1f}%.",
    })
    tv_share = (pv_tv / enterprise_value * 100) if enterprise_value > 0 else 0
    takeaways.append({
        "rank": 3,
        "category": "Terminal Value Dependency",
        "insight": f"Terminal value contributes **{tv_share:,.1f}%** of total enterprise value — " + (
            "moderate (DCF is reasonably anchored to explicit projection)." if tv_share < 70 else
            "high (results are sensitive to terminal growth assumption)."
        ),
    })
    balance_str = "net cash" if net_cash > 0 else "net debt"
    takeaways.append({
        "rank": 4,
        "category": "Balance Sheet",
        "insight": f"{ticker} carries ${abs(net_cash) / 1e9:,.2f}B of {balance_str} — " + (
            "adds optionality for buybacks/M&A." if net_cash > 0 else "elevates equity risk above unlevered DCF."
        ),
    })
    if abs(historical_growth - growth_for_projection) > 0.001:
        takeaways.append({
            "rank": 5,
            "category": "Growth Assumption",
            "insight": f"Historical FCF growth ({historical_growth * 100:+,.1f}%) was clamped to {growth_for_projection * 100:+,.1f}% for projection — guards against extrapolating outliers.",
        })
    else:
        takeaways.append({
            "rank": 5,
            "category": "Growth Assumption",
            "insight": f"Projection uses the trailing FCF CAGR of {growth_for_projection * 100:+,.1f}% directly — no clamping applied.",
        })
    takeaways.append({
        "rank": 6,
        "category": "Sensitivity",
        "insight": f"Across the 5×5 grid (WACC ±2%, g ±1%), intrinsic value ranges roughly ${min(r['intrinsic_per_share'] for r in sens_rows):,.0f} → ${max(r['intrinsic_per_share'] for r in sens_rows):,.0f} per share. Always test these assumptions against your own conviction.",
    })
    conn.register("takeaways_t", pa.Table.from_pylist(takeaways))
    job.write_parquet("takeaways", "SELECT * FROM takeaways_t")

    job.progress(95, "Uploading dashboard…")
    job.write_dashboard_dir()

    job.update_progress(
        "running_analysis",
        progress_pct=99,
        progress_message=f"DCF complete: {ticker} {verdict} ({margin_of_safety:+.1f}%)",
        lineage={
            "inputs": [f"yfinance:{ticker}", "bedrock.finance.stock_prices"],
            "outputs": [
                f"analytics/bedrock/{job.job_id}/data/summary.parquet",
                f"analytics/bedrock/{job.job_id}/data/assumptions.parquet",
                f"analytics/bedrock/{job.job_id}/data/dcf_breakdown.parquet",
                f"analytics/bedrock/{job.job_id}/data/sensitivity.parquet",
                f"analytics/bedrock/{job.job_id}/data/historical_fcf.parquet",
                f"analytics/bedrock/{job.job_id}/data/takeaways.parquet",
            ],
        },
    )
    job.conclusion(
        f"DCF for {ticker} ({company_name}): intrinsic ${intrinsic_per_share:,.2f} vs current "
        f"${current_price:,.2f} — verdict **{verdict}** ({margin_of_safety:+,.1f}% margin of safety)."
    )
    job.complete()


if __name__ == "__main__":
    main()
