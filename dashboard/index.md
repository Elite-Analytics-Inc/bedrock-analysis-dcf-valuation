---
title: DCF Valuation
---

```sql summary
SELECT * FROM summary
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

{% big_value data="$summary" value="current_price"        title="Current Price"        fmt="num2" prefix="$"
              info="What the market is paying per share right now (latest close from Yahoo Finance)." /%}
{% big_value data="$summary" value="intrinsic_per_share"  title="Intrinsic Value"      fmt="num2" prefix="$"
              info="What the DCF model says one share is *worth* — the present value of all expected future cash flows, divided by shares outstanding." /%}
{% big_value data="$summary" value="upside_pct"           title="Margin of Safety"     fmt="num1" suffix="%"
              info="(Intrinsic ÷ Current) − 1. Positive = stock looks cheap vs. the model. Negative = expensive. >20% margin is usually considered a buy signal by value investors." /%}
{% big_value data="$summary" value="verdict"              title="Verdict"
              info="UNDERVALUED if margin of safety > +20%. OVERVALUED if < −20%. Otherwise FAIR VALUE. These thresholds are rules of thumb — sanity-check against the sensitivity matrix below." /%}
{% big_value data="$summary" value="market_cap_b"         title="Market Cap"           fmt="num2" suffix=" B" prefix="$"
              info="Total market value of the company = current price × shares outstanding. Useful for context (large-cap >$10B, mid $2–10B, small $0.3–2B)." /%}

*Read these top to bottom: Current price is what you pay; Intrinsic Value is what the model thinks it's worth; Margin of Safety is the gap between them; Verdict summarizes; Market Cap puts it in context.*

## DCF Inputs & Outputs

{% data_table data="$assumptions" rows=20 rowShading=true
              info="Every input the DCF used (top half) and every number it produced (bottom half). Read top to bottom: company facts → user assumptions (WACC, terminal growth) → math outputs (PV of cash flows, enterprise value, intrinsic per share, verdict). If the verdict surprises you, scroll up to find which assumption is driving it." %}
{% column id="key"   title="Item"  contentType="text" /%}
{% column id="value" title="Value" contentType="text" /%}
{% /data_table %}

*Every value the model used and produced. Read top to bottom: company facts → user-chosen assumptions (WACC, terminal growth) → math outputs (PV of cash flows, enterprise value, intrinsic per share, verdict). If the verdict surprises you, scroll up to find which assumption is driving it.*

## Projected vs Discounted FCF

{% data_table data="$breakdown" rows=12 rowShading=true
              info="Year-by-year projected free cash flow and its present value (discounted at WACC). The Terminal row at the bottom captures all cash flows beyond the explicit horizon as a single Gordon-Growth lump sum. Greener cell = bigger contribution to total enterprise value." %}
{% column id="year"             title="Year"                  /%}
{% column id="projected_fcf_b"  title="Projected FCF ($B)"   fmt="num2" /%}
{% column id="discount_factor"  title="Discount Factor"      fmt="num4" /%}
{% column id="present_value_b"  title="Present Value ($B)"   fmt="num2" /%}
{% /data_table %}

*Each projection year takes the previous year's FCF and grows it by the historical CAGR. Future dollars are worth less than today's dollars — the **discount factor** column shows how much less. **Present Value** is what those future dollars are worth in today's terms (greener = bigger contribution to the company's value). The **Terminal** row at the bottom captures all cash flows beyond year 5 in a single Gordon-Growth lump sum.*

{% bar_chart data="$breakdown" x="year" y=["present_value_b"]
              title="Contribution to Enterprise Value (PV by year)"
              yAxisTitle="Present Value ($B)"
              colors=["#3b82f6"]
              info="How much each year (and the terminal lump-sum) contributes to total enterprise value, in today's dollars. If the Terminal bar dwarfs every projection year, the valuation is heavily dependent on what happens after year 5 — risky." /%}

*If the rightmost (Terminal) bar dominates everything else, the model is largely betting on the company's long-run steady-state — small changes to the terminal growth rate will swing the verdict.*

## Sensitivity — WACC × Terminal Growth

{% line_chart data="$sensitivity" x="g_pct" y=["intrinsic_per_share"]
              title="Intrinsic value vs. terminal growth (across WACC scenarios)"
              yAxisTitle="Intrinsic value per share ($)"
              xAxisTitle="Terminal growth rate (%)"
              colors=["#7c3aed"]
              info="How intrinsic value moves when you flex the two most-fragile assumptions: WACC (discount rate) and terminal growth. Use this to stress-test the verdict — if a small change in either knob flips the verdict, the conclusion is fragile." /%}

*The flatter this line, the more robust the valuation. A steeply rising line means the model is hyper-sensitive to growth assumptions and you should treat the headline verdict skeptically.*

{% data_table data="$sensitivity" rows=25 rowShading=true
              info="The 5×5 stress-test grid: WACC ±2%, terminal g ±1% around the user's chosen values. Greener = higher intrinsic value. Find the (WACC, g) cell closest to your own conviction and use that number — it is more honest than the single hero KPI which assumes one fixed pair." %}
{% column id="wacc_pct"             title="WACC (%)"                fmt="num2" /%}
{% column id="g_pct"                title="Terminal g (%)"          fmt="num2" /%}
{% column id="intrinsic_per_share"  title="Intrinsic / share ($)"   contentType="colorscale" scaleColor=["#059669","#022c22"] fmt="num2" /%}
{% /data_table %}

*The 5×5 grid of intrinsic-value outcomes (WACC ±2%, g ±1%). Greener = higher intrinsic value. Find your conviction-weighted assumption pair and read the cell — that's a more honest single number than the hero KPI.*

## Historical Free Cash Flow

{% bar_chart data="$historical" x="fiscal_year" y=["fcf_b"]
              title="Reported Free Cash Flow by fiscal year"
              yAxisTitle="FCF ($B)"
              colors=["#22c55e"]
              info="The actual FCF the company has produced over the last few fiscal years (from Yahoo Finance). The DCF projection uses the trailing CAGR of these numbers as its growth assumption." /%}

*Free Cash Flow = cash from operations minus capital spending. It's the cash the business actually generates that's available to shareholders (dividends, buybacks, debt reduction, acquisitions). A flat or declining trend here is a yellow flag — DCF projections assume the past extends into the future.*

{% data_table data="$historical" rows=10 rowShading=true
              info="Reported free cash flow per fiscal year (oldest → newest). The DCF projection's growth rate is the trailing CAGR of these numbers. A flat or declining trend is a yellow flag — DCF assumes the past extends forward." %}
{% column id="fiscal_year" title="Fiscal Year" /%}
{% column id="fcf_b"       title="FCF ($B)" fmt="num2" /%}
{% /data_table %}

## Key Takeaways

{% data_table data="$takeaways" rows=6 rowShading=true
              info="Six analyst-style observations to anchor the verdict. Read these BEFORE acting on the intrinsic-value number — they explain how confident the model is and which assumptions are doing the heavy lifting." %}
{% column id="rank"     title="#" /%}
{% column id="category" title="Category"   contentType="text" /%}
{% column id="insight"  title="Insight"    contentType="text" /%}
{% /data_table %}

*Six analyst-style observations to anchor the verdict. Read these BEFORE acting on the intrinsic-value number — they explain how confident the model is and which assumptions are doing the heavy lifting.*
