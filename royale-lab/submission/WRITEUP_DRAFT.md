# The Gilded Ace — Decisions Beyond the Bottom Ten

Our Tableau dashboards investigate six months of synthetic casino data to distinguish wagering demand, availability, payout variation, and contribution before replacing low-earning machines.

For business planning, we compared constant-mean, weekday-average, and weekday-plus-trend demand forecasts. Model selection used pre-May validation folds; January–April data then produced fixed predictions for the untouched May–June test period. Weekday averages achieved mean absolute error of $68,699 per day versus $218,258 for the constant mean, a 68.5% reduction. Refitting through June projects $40.71 million in July 1–30 wagers and $3.60 million in expected contribution after supplied costs. Contribution assumes June game mix, food-and-beverage margin, and costs; it is not full net profit.

Machine analysis compares actual and theoretical win per available hour, accounts for differing exposure, and separates downtime from payout variation. We identified 5,021 unavailable machine-hours. A gross recovery scenario is not proven lost revenue because guests can substitute other machines. Tracked-player views report payouts minus wagers, distinct players, concentration, and redeemed comp costs; they exclude uncarded activity. The top 1% of tracked players accounted for 22.9% of tracked wagering over January–June.

Our proposed July plan funds one $1,200 inspection of M-1158 and preserves $98,800. Its full-period payout residual warrants configuration verification, not an accusation or automatic replacement. Expected inspection value is information; recovered cash is unknown. Record findings and evaluate subsequent exposure-adjusted results on new data.

We also compare unfunded alternatives: a technician package costs $11,520 against approximately $9,056 of optimistic June-rate recovery opportunity within the benefit horizon. A $15,000 promotion weekend requires about 4.9% incremental wagering lift before extra comp costs. These are break-even requirements, not causal forecasts. Any promotion should measure incremental contribution against a control and account for displaced visits.

A Gemini API companion translates audited evidence into management explanations with scope, evidence IDs, alternatives, and limitations. Successful responses export to Tableau. Token limits, a persistent request allowance, and caching constrain cost; financial calculations and forecasts remain in Python.

Code, validation results, an AI-use disclosure, and a Claims & Evidence appendix document the calculations, alternative explanations, and limitations.
