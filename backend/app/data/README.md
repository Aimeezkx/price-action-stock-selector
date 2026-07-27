# S&P 500 Top 300 universe

`sp500_top300.json` is a generated snapshot of the 300 largest SPY holdings by index weight.

- Holdings source: State Street SPY daily holdings XLSX.
- Snapshot date: 2026-07-09.
- Ranking: descending SPY weight.
- Methodology: the S&P 500 is float-adjusted market-cap weighted, so index weight is used as the float-adjusted capitalization ranking proxy.
- Security count: 300; multiple share classes remain separate securities.

Refresh with:

```bash
cd backend
.venv/bin/python scripts/update_sp500_universe.py
```

The generated file contains names, tickers, ranks, weights, source URLs, and timestamps. It does not contain licensed index calculation data beyond the public fund holdings fields needed to construct the local watchlist.
