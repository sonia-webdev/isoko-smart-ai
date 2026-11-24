# Isoko Smart AI: brief for MINAGRI and district planners

**What it is.** A tool that turns Esoko farmgate prices into (1) advice for farmers on where to sell and (2) a national view for planners.

**What you can see (Government dashboard)**
- National overview: price change by crop since May 2026, the gap between dearer and cheaper markets, markets that stopped reporting.
- Monthly movement for each crop; market-by-market comparison; data coverage. Tables can be copied to Excel, or read as
  CSV at `/api/prices.csv` and `/api/monthly.csv`.
- Data and trust: how reliable the prices are, and an honest test of whether AI models beat simple rules (today they do not).

**What it does not claim.** It is not a price forecast and does not prove seasonal patterns: it has about six months of data.
Prices are farmgate prices reported by Esoko; markets that report rarely are marked Low reliability.

**What would make it stronger**
1. Regular price reports (at least twice a week per market and crop), starting with the 10 busiest markets.
2. Real transport quotes from drivers, by route.
3. A year or more of data to show real seasonal patterns.
4. An SMS short code and, later, a USSD menu through the operators.

**What we need from MINAGRI:** access to or a partnership for regular price collection, a data-sharing agreement, and support
for a field test in two districts.
