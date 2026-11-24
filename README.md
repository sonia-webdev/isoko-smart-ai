# Isoko Smart AI

Helps a farmer decide where to sell a crop: it compares farmgate prices between markets, subtracts the cost of
getting there, and says whether the trip is worth it. A forecast is shown only when it beat "same as last week"
in testing.

## Folder

| Path | What it is |
|---|---|
| `app.py` | The dashboard (Streamlit) |
| `isoko_core.py` | All logic: cleaning, distances, transport costs, ranking, forecast gate |
| `backtest.py` | Forecast model comparison used by the notebook |
| `isoko_i18n.py` | English and Kinyarwanda text (advice sentences, labels, SMS replies) |
| `isoko_sms.py` | SMS prototype: reads a text message, writes a reply of 160 characters or fewer |
| `data/isoko_crop_data.csv` | Your real prices (add it yourself; without it the app shows labelled demo data) |
| `data/markets.csv` | Market coordinates |
| `data/road_distances.csv` | Optional real road distances (see below) |
| `data/vehicles.json` | Optional vehicle costs from real quotes (see below) |
| `data/wfp_retail_rwa_2026.csv` | WFP retail prices (May to Aug 2026) used only as a benchmark |
| `data/kinyarwanda_corrections.csv` | Optional corrections from a Kinyarwanda speaker (see below) |
| `models/model_report.json` | Saved training and test results (made by `tools/train_models.py`) |
| `tools/` | Scripts for adding prices, road distances and transport quotes |
| `tests/` | Unit tests |

## Run it on your computer

```
pip install -r requirements.txt
streamlit run app.py
```

Run the tests: `python -m unittest discover -s tests -t .`

## Put it online permanently (no Colab)

One free option is Streamlit Community Cloud. Check its current terms; free apps may go to sleep when nobody
uses them and wake on the next visit.

1. Create a GitHub repository and upload this folder, so that `app.py` and `requirements.txt` are at the top level.
2. Decide about the real price file. In a **public** repository everyone can download it, so check that you may
   share the Esoko data, or use a **private** repository, or keep it out of git (see `.gitignore`). Without the
   file the app still runs and shows the demo data with a clear warning.
3. Go to share.streamlit.io, sign in with GitHub, choose "Create app", pick the repository and branch, and set the
   main file to `app.py`. Deploy. You get a permanent link.
4. To update prices later, run `python tools/add_prices.py new_prices.csv`, commit the changed CSV, and the app
   refreshes. (Hugging Face Spaces with the Streamlit option is a similar alternative.)

## Adding new prices

`python tools/add_prices.py new_prices.csv` needs the columns `observed_date, product, location, price, unit`.
It skips duplicates, bad rows and anything not in kg, keeps a backup (`.bak`) and lists products that are not one of
the project crops. `crop_category` is worked out from the product name (see `CROP_RULES` in `isoko_core.py`).

## Replacing the transport assumptions with real numbers

The dashboard has two ways to cost transport: a simple rate per kg per km, and a vehicle model (trips, cost per km,
round trip, market fees, road losses). The vehicle numbers in `isoko_core.VEHICLES` are **planning defaults, not
measurements**. To replace them:

1. Collect 5 or more quotes per vehicle type from transporters or cooperatives. Use `docs/transport_quotes_template.csv`.
2. Run `python tools/fit_transport.py your_quotes.csv`. It writes `data/vehicles.json` (median cost per km).
3. Restart the app. The page then says the figures come from real quotes.

The advice page also tests whether the best market changes if transport costs are half or double what was entered.

## Real road distances

Without extra data, distance is straight-line distance x 1.3. For real road distances, run
`python tools/build_road_distances.py` once with internet access (it uses the public OSRM demo server, so please
run it only once) and commit `data/road_distances.csv`.

## Markets without coordinates

Markets in the price data but not in `data/markets.csv` appear in the "Data and trust" page and are not ranked.
Add a row `location,lat,lon` for each. Spelling must match the price data (Butare is treated as Huye).

## Retail benchmark (WFP)

The "Data and trust" page and the notebook compare your Esoko **farmgate** medians with WFP **retail** medians, for the
same months. Retail is normally higher than farmgate, so this is a sanity check, not a like-for-like comparison.
It is **not** used for the market ranking or the forecasts.

* Source: WFP food prices for Rwanda, Humanitarian Data Exchange, licence CC BY-IGO (credit it in your report).
* The WFP file is monthly, per market, retail. It ended in August 2026 when it was downloaded.
* To refresh it: download the new CSV from the Humanitarian Data Exchange and run
  `python tools/prepare_wfp.py wfp_food_prices_rwa.csv`.
* Crops with no WFP price per kg in the period (for example tomatoes, sweet potatoes) are shown as "no WFP price", never filled in.

## Kinyarwanda

The sidebar has a language switch. The advice sentences, the main labels and the SMS replies are translated;
the transport settings, price trends and data pages are still English.

**The Kinyarwanda was first written by an AI and has since been checked by a Kinyarwanda speaker (reported by the project team).** Before real farmers use it:

1. Give `docs/kinyarwanda_review.csv` to a Kinyarwanda speaker (columns: key, english, kinyarwanda, correct_yes_no,
   kinyarwanda_corrected).
2. Copy their corrections into `data/kinyarwanda_corrections.csv` with the columns `key,kinyarwanda`.
   Keep the `{placeholders}` exactly as they are; a correction that loses one is refused.
3. Restart the app. No code needs to change.

## SMS prototype

Any phone can use it, no smartphone or internet needed. Messages (English or Kinyarwanda):

| Message | Reply |
|---|---|
| `SELL BEANS 500 NYABUGOGO` / `GURISHA IBISHYIMBO 500 NYABUGOGO` | Where to sell 500 kg, with the expected income |
| `PRICE MAIZE` / `IGICIRO IBIGORI` | Highest, lowest and median price per kg |
| `HELP` / `UBUFASHA` | How to write a message |

Replies are one SMS (160 characters, basic SMS alphabet only) and use the same advice logic as the dashboard.

* Try it without any network: the "SMS demo" page in the app, or `python tools/sms_webhook.py --simulate`.
* `python tools/sms_webhook.py --port 8080` starts a small web server that answers `POST /sms` (field `text`).
* **A real SMS number is not included.** A provider such as Africa's Talking needs an account, a registered number
  or short code, and costs money. Read their documentation: some providers send the server's plain-text answer to the
  farmer, others need your server to call their send API. Use HTTPS, and do not store phone numbers.

## Known limits

* One data source (Esoko Rwanda, farmgate prices), updated only when you add data.
* Transport costs are only as good as the quotes behind them.
* Kinyarwanda needs native-speaker review (above). Voice, and a live SMS number, are future work.

## The dashboards

The app opens on a **Home** page that explains Isoko Smart AI (the problem, how it works, live key numbers, a worked example from
today's data, and what the AI does and does not do). The menu then has two dashboards:

- **Farmer dashboard:** Where to sell, Price trends, SMS demo (type a message in Kinyarwanda or English).
- **Government dashboard (MINAGRI):** National overview (plain-words price story, gap between dearer and cheaper markets, data
  coverage), Seasonal patterns (month-by-month 2026 prices per crop, CSV download), Market comparison (all markets for one product,
  and report counts per market, both downloadable) and Data and trust (retail benchmark, AI model check, limits).

The monthly page uses the Esoko file only (May 2026 onward), so it shows what happened this year, not a repeating seasonal pattern.
That needs several years of farmgate prices. WFP retail history is kept in `data/` for the benchmark only.

## Quick start on your own computer (new interface)

1. Unzip the project. Put your price file `isoko_crop_data.csv` in the project folder (or in `data/`).
2. Windows: double-click `start_isoko.bat`. Mac/Linux: run `./start_isoko.sh`. (Or: `python start.py`.)
3. Your browser opens `http://localhost:8080`: the new React interface with the landing page, farmer and government dashboards,
   and the transport options (simple or by vehicle).
Needs Python with `pandas` and `numpy` (`pip install pandas numpy`). `streamlit run app.py` starts the OLDER Streamlit interface,
which is kept only for comparison.

## Running it for real (server, API, guides)

`python server.py` serves the web interface and an API (advice, SMS callback, feedback, CSV exports, admin upload of new prices).
It needs only pandas. Read, in `docs/`: `DEPLOY.md` (put it online with Docker or a plain server, HTTPS, SMS provider),
`OPERATIONS.md` (the weekly routine and what makes data reliable), `PRIVACY.md`, `FIELD_TEST.md` (test with 10 farmers),
`FARMER_GUIDE.md` and `MINAGRI_BRIEF.md`. Weekly refresh: `python tools/refresh.py new_prices.csv`.
Not done, because it needs outside accounts: a live SMS number, a domain and hosting, USSD with the operators.

## The React + Tailwind interface (web/)

`web/index.html` is a second, more polished front end (React and Tailwind from a CDN): a landing page with illustrated crops,
a farmer dashboard and a government (MINAGRI) dashboard, with the language switch (English / Kinyarwanda) top right. It reads
`web/data.json`, made from the real Esoko file by `python tools/export_web_data.py`; the ranking maths is the same as `isoko_core.py`
(checked to give identical results). After adding prices, run `python tools/export_web_data.py` then `python tools/build_web.py`
(which joins `web/template.html` and `web/app.jsx` into `index.html`). Serve the `web/` folder with any static host, or open it
through `python -m http.server` inside `web/`. SMS and message reading stay in the Streamlit app.

## Trained models and the AI gate

`isoko_ml.py` trains two models (random forest and gradient boosting) to estimate a market's price in a week from the other
markets' average, the market's own history and premium, its location and the month. They are trained on the earlier 70% of weeks
and tested on the later 30% against simple rules. The result is shown in the notebook (section 6b) and in the app
(Data and trust, "AI model check"). A trained model is used for advice only if it beats the best simple rule by at least 10%
(`GATE_GAIN_PCT`). With a few months of sparse reports it does not; re-run after more weeks of data are added.

To train and test everything once and save the result, run `python tools/train_models.py` (notebook section 9b). It writes
`models/model_report.json`; the app reads it instead of retraining, and recomputes on its own if the data has changed.

## Free messages and a language model

`isoko_nlu.py` lets a language model read a farmer's free message (Kinyarwanda, English or mixed) and return four fields: intent, crop,
kilograms and market. The model never chooses the market and never writes a price. Its fields are checked against Isoko's own lists and the reply is
built by the same code as the dashboard; if the output fails the checks, the rule parser answers instead.
`docs/farmer_messages_testset.csv` (89 messages) scores the rule parser and the model. The Kinyarwanda rows were written by an AI model and need a native
speaker to correct them (`needs_native_review`). The model itself runs in Colab (notebook section 8c); it was not run in the build workspace.
