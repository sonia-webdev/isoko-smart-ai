# Running Isoko Smart AI week by week

## First time (loading your real prices)
Send your Esoko export (columns `observed_date, product, location, price, unit`; prices in kg):
```
curl -X POST https://isoko.yourdomain.rw/admin/upload -H "X-Admin-Token: YOUR_TOKEN" --data-binary @isoko_crop_data.csv
```
The answer lists how many rows were added and the data health. Or on the server: `python tools/refresh.py isoko_crop_data.csv`.

## Every week (about 10 minutes)
1. Export the newest prices from Esoko.
2. Upload them the same way. Duplicates, bad rows and anything not in kg are skipped; a backup is kept.
3. Read the answer: **reliability** (High / Medium / Low) and the **quiet markets** list. Ask Esoko, or your field agents, for
   fresh prices in those markets first.
4. Open `/health`. It must say `"stale": false` (newest price not older than 7 days). If it is stale, the app already warns
   farmers, but fix it the same day.
5. Once a month, or after a big data change, run `python tools/refresh.py --train` (a few minutes) to refresh the model check.

## What makes the advice trustworthy (reliability)
- **High:** at least 4 different days with a price in the last 14 days and the newest price at most 7 days old.
- **Medium:** at least 2 days with a price and the newest at most 14 days old.
- **Low:** anything else. Today almost everything is Low because markets report about once every one to three weeks.
To reach High, a market needs a price at least twice a week for the crop. This is a data collection task, not a software one.

## Feedback and real messages
- Farmers' "Was this advice useful?" answers are in `data/feedback.jsonl`. Read them weekly.
- To collect real SMS texts for tuning the message reader, set `ISOKO_LOG_MESSAGES=1`. Tell farmers first (docs/PRIVACY.md).
  Phone numbers are removed. The texts go to `data/messages_log.csv`; review them and add the good ones to the test sets.

## For analysts
`/api/prices.csv` (current prices, `?crop=Beans`) and `/api/monthly.csv` (month by month since May 2026).

## If something looks wrong
- Site down: `docker compose logs isoko`.
- Farmers get "old price" warnings: the data is old; upload fresh prices.
- Wrong advice for a market: check `/api/advice?crop=Beans&origin=Huye&qty=500` and the quiet-markets list; one old report can drive it.
