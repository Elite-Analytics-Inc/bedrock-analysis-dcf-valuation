---
title: DCF Valuation
---

```sql summary
SELECT * FROM summary
```

```sql summary_with_arrow
SELECT
  ticker,
  company,
  current_price,
  intrinsic_per_share,
  upside_pct,
  ROUND(upside_pct, 1) AS upside_round,
  verdict,
  market_cap_b
FROM summary
```

```sql assumptions
SELECT * FROM assumptions
```

```sql breakdown
SELECT
  CAST(year AS VARCHAR) AS year,
  ROUND(projected_fcf_b, 2) AS projected_fcf_b,
  discount_factor,
  ROUND(present_value_b, 2) AS present_value_b
FROM dcf_breakdown
```

```sql sensitivity
SELECT wacc_pct, g_pct, intrinsic_per_share
FROM sensitivity
ORDER BY wacc_pct, g_pct
```

```sql historical
SELECT fiscal_year, ROUND(fcf_b, 2) AS fcf_b
FROM historical_fcf
ORDER BY fiscal_year
```

```sql takeaways
SELECT rank, category, insight FROM takeaways ORDER BY rank
```

# DCF Valuation

Discounted cash-flow model on live Yahoo Finance fundamentals. Pulls cashflow,
balance-sheet, and income statements; projects free cash flow over the explicit
horizon; discounts at WACC; adds Gordon-growth terminal value; derives intrinsic
value per share. Verdict + 6 takeaways below the model.

## Hero

{% big_value data="$summary" value="current_price"        title="Current Price"        fmt="num2" prefix="$" /%}
{% big_value data="$summary" value="intrinsic_per_share"  title="Intrinsic Value"      fmt="num2" prefix="$" /%}
{% big_value data="$summary" value="upside_pct"           title="Margin of Safety"     fmt="num1" suffix="%" /%}
{% big_value data="$summary" value="verdict"              title="Verdict" /%}
{% big_value data="$summary" value="market_cap_b"         title="Market Cap"           fmt="num2" suffix=" B" prefix="$" /%}

## DCF Inputs & Outputs

Every value the model used and produced. Read top-to-bottom: inputs first,
intermediate calculations next, intrinsic value and verdict at the bottom.

{% data_table data="$assumptions" rows=20 rowShading=true %}
{% column id="key"   title="Item" /%}
{% column id="value" title="Value" /%}
{% /data_table %}

## Projected vs Discounted FCF

Year-by-year explicit projection followed by terminal value. The discount factor
column shows how much each future dollar is worth today at the chosen WACC.

{% data_table data="$breakdown" rows=12 rowShading=true %}
{% column id="year"             title="Year"                  /%}
{% column id="projected_fcf_b"  title="Projected FCF ($B)"   fmt="num2" /%}
{% column id="discount_factor"  title="Discount Factor"      fmt="num4" /%}
{% column id="present_value_b"  title="Present Value ($B)"   contentType="colorscale" scaleColor=["#fef3c7","#22c55e"] fmt="num2" /%}
{% /data_table %}

{% bar_chart data="$breakdown" x="year" y=["present_value_b"]
              title="Contribution to Enterprise Value (PV by year)"
              yAxisTitle="Present Value ($B)"
              colors=["#3b82f6"] /%}

## Sensitivity — WACC × Terminal Growth

How the intrinsic-value-per-share number moves when you flex WACC ±2% and
terminal growth ±1%. Read each row as "if WACC were X%, intrinsic at varying g".

{% line_chart data="$sensitivity" x="g_pct" y=["intrinsic_per_share"]
              title="Intrinsic value vs. terminal growth (across WACC scenarios)"
              yAxisTitle="Intrinsic value per share ($)"
              xAxisTitle="Terminal growth rate (%)"
              colors=["#7c3aed"] /%}

{% data_table data="$sensitivity" rows=25 rowShading=true %}
{% column id="wacc_pct"             title="WACC (%)"                fmt="num2" /%}
{% column id="g_pct"                title="Terminal g (%)"          fmt="num2" /%}
{% column id="intrinsic_per_share"  title="Intrinsic / share ($)"   contentType="colorscale" scaleColor=["#fecaca","#22c55e"] fmt="num2" /%}
{% /data_table %}

## Historical Free Cash Flow

The actual reported FCF series the projection is anchored on.

{% bar_chart data="$historical" x="fiscal_year" y=["fcf_b"]
              title="Reported Free Cash Flow by fiscal year"
              yAxisTitle="FCF ($B)"
              colors=["#22c55e"] /%}

{% data_table data="$historical" rows=10 rowShading=true %}
{% column id="fiscal_year" title="Fiscal Year" /%}
{% column id="fcf_b"       title="FCF ($B)" fmt="num2" /%}
{% /data_table %}

## Key Takeaways

Six analyst-style observations to anchor the verdict. Read these BEFORE acting on
the intrinsic-value number — they explain how confident the model is.

{% data_table data="$takeaways" rows=6 rowShading=true %}
{% column id="rank"     title="#" /%}
{% column id="category" title="Category" /%}
{% column id="insight"  title="Insight" /%}
{% /data_table %}
