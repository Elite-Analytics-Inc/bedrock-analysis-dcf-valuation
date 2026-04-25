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
              info="WHAT: The price one share of this stock is trading at right now (latest close from Yahoo Finance). HOW: Think of it as a price tag at a store — it's what you pay if you click Buy today. WHY IT MATTERS: This is the number you compare every other valuation against. Every metric on this page is asking: 'is this price fair, cheap, or expensive?'" /%}
{% big_value data="$summary" value="intrinsic_per_share"  title="Intrinsic Value"      fmt="num2" prefix="$"
              info="WHAT: What ONE SHARE is worth based on the cash the company will produce in the future (not what the market thinks today). HOW: The DCF model adds up every dollar of free cash flow the company is expected to make over the next 5 years + a 'terminal value' for everything beyond that, discounts each future dollar back to today's value (because $1 next year < $1 today), then divides by shares outstanding. WHY IT MATTERS: This is the model's answer to 'what should this stock be worth?'. Compare against Current Price — if intrinsic > current, the market may be undervaluing the company." /%}
{% big_value data="$summary" value="upside_pct"           title="Margin of Safety"     fmt="num1" suffix="%"
              info="WHAT: How much higher (or lower) the model's intrinsic value is vs. the current market price, as a percent. HOW: (Intrinsic ÷ Current) − 1. Example: intrinsic $120, current $100 → +20% margin of safety. WHY IT MATTERS: A positive number means the stock looks cheap to the model — buying it gives you a 'cushion' if your DCF assumptions are slightly wrong. Value investors typically want at least +20% before buying (Benjamin Graham's rule). Negative = the market is paying more than the model thinks the stock is worth." /%}
{% big_value data="$summary" value="verdict"              title="Verdict"
              info="WHAT: A one-word summary of the model's opinion. HOW: UNDERVALUED if margin of safety > +20% (model says it's a bargain). OVERVALUED if margin of safety < −20% (model says it's expensive). FAIR VALUE in between (close to what the model expects). WHY IT MATTERS: A quick sanity check before you dig in. But — this is a rule of thumb. ALWAYS cross-reference with the Sensitivity matrix below: if small WACC/growth tweaks flip the verdict, the conclusion is fragile and you shouldn't trust the headline." /%}
{% big_value data="$summary" value="market_cap_b"         title="Market Cap"           fmt="num2" suffix=" B" prefix="$"
              info="WHAT: The total dollar value of the entire company (all shares × current price). HOW: shares outstanding × current price. Example: 15 B shares × $100/share = $1.5 trillion market cap. WHY IT MATTERS: Tells you how big the company is and which playbook to apply. Common buckets: Mega-cap >$200B (Apple, Microsoft) — slow but stable. Large-cap $10–200B — established. Mid-cap $2–10B — growing. Small-cap $300M–2B — risky but room to grow. Micro-cap <$300M — speculative." /%}

*Read these top to bottom: Current price is what you pay; Intrinsic Value is what the model thinks it's worth; Margin of Safety is the gap between them; Verdict summarizes; Market Cap puts it in context.*

## DCF Inputs & Outputs

{% data_table data="$assumptions" rows=20 rowShading=true
              info="WHAT: A complete list of every number the DCF model used as input AND every number it computed as output, in one table. HOW TO READ IT: Top half = facts about the company (ticker, market cap, latest free cash flow) + assumptions YOU chose (WACC, terminal growth, projection horizon). Bottom half = what the math produced (PV of projected cash flows, terminal value, enterprise value, equity value, intrinsic per share, verdict). WHY IT MATTERS: This is the audit trail. If the headline Verdict surprises you, find which row is doing the heavy lifting — usually it's WACC, terminal growth, or the historical FCF CAGR. Change one assumption and the bottom half changes." %}
{% column id="key"   title="Item"  contentType="text" /%}
{% column id="value" title="Value" contentType="text" /%}
{% /data_table %}

*Every value the model used and produced. Read top to bottom: company facts → user-chosen assumptions (WACC, terminal growth) → math outputs (PV of cash flows, enterprise value, intrinsic per share, verdict). If the verdict surprises you, scroll up to find which assumption is driving it.*

## Projected vs Discounted FCF

{% data_table data="$breakdown" rows=12 rowShading=true
              info="WHAT: The year-by-year math behind the DCF. HOW TO READ EACH COLUMN: 'Projected FCF ($B)' = how much free cash the model thinks the company will produce that year (latest FCF grown by historical CAGR). 'Discount Factor' = 1 / (1 + WACC)^year — how much less a future dollar is worth in today's terms (year 1 = ~0.91, year 5 = ~0.62 at 10% WACC). 'Present Value ($B)' = projected FCF × discount factor. The 'Terminal' row at the bottom captures EVERY cash flow beyond year 5 in a single Gordon-Growth lump sum. WHY IT MATTERS: Sum the Present Value column = enterprise value. If the Terminal row dominates the sum, your valuation is mostly a bet on the long-run steady state — fragile to terminal growth assumptions." %}
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
              info="WHAT: A visual of the same Present Value column from the table above — each bar is one year's contribution to enterprise value, in today's dollars. HOW TO READ IT: Bar height = how much that year (or the Terminal lump-sum) is worth right now. The Terminal bar lumps together everything beyond year 5. WHY IT MATTERS: This is the single most important chart for spotting fragility. If the Terminal bar dwarfs every projection year (very common), the valuation is mostly a bet on what happens AFTER the 5-year horizon. Tiny changes in terminal growth → huge swings in intrinsic value. If projection years and Terminal are roughly comparable, the valuation is more anchored to the explicit forecast and is more robust." /%}

*If the rightmost (Terminal) bar dominates everything else, the model is largely betting on the company's long-run steady-state — small changes to the terminal growth rate will swing the verdict.*

## Sensitivity — WACC × Terminal Growth

{% line_chart data="$sensitivity" x="g_pct" y=["intrinsic_per_share"]
              title="Intrinsic value vs. terminal growth (across WACC scenarios)"
              yAxisTitle="Intrinsic value per share ($)"
              xAxisTitle="Terminal growth rate (%)"
              colors=["#7c3aed"]
              info="WHAT: A 'what-if' chart. Each line shows what intrinsic value PER SHARE would be if WACC were different (the colored lines), as you slide terminal growth from -1% to +1% around your chosen value (the x-axis). HOW TO READ IT: A FLAT line = the model is robust (changing growth doesn't move the answer much). A STEEP line = the model is fragile (small assumption changes swing intrinsic value a lot). WHY IT MATTERS: WACC and terminal growth are the two assumptions DCF authors fight about most. If your verdict survives across the whole grid, you can have confidence in it. If a 0.5% change in either flips UNDERVALUED → OVERVALUED, the headline KPI is essentially a coin flip and you should not act on it." /%}

*The flatter this line, the more robust the valuation. A steeply rising line means the model is hyper-sensitive to growth assumptions and you should treat the headline verdict skeptically.*

{% heatmap data="$sensitivity" x="g_pct" y="wacc_pct" value="intrinsic_per_share"
            title="Intrinsic value per share — WACC × terminal growth"
            colors=["#fee2e2","#fca5a5","#f87171","#fbbf24","#86efac","#22c55e","#15803d"]
            chartAreaHeight=360 /%}

*Each cell is the intrinsic value per share at that (WACC, g) pair. Red = lower than the headline KPI, green = higher. Find the cell closest to your own conviction and treat it as the honest single number.*

{% data_table data="$sensitivity" rows=25 rowShading=true
              info="Same 5×5 grid as a sortable table — exact dollar values for every (WACC, g) pair. Greener cell = higher intrinsic value. Use the heatmap above for the visual story, this table for the precise numbers." %}
{% column id="wacc_pct"             title="WACC (%)"                fmt="num2" /%}
{% column id="g_pct"                title="Terminal g (%)"          fmt="num2" /%}
{% column id="intrinsic_per_share"  title="Intrinsic / share ($)"   contentType="colorscale" palette="greens" fmt="num2" /%}
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
