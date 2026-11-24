"""Isoko Smart AI - English and Kinyarwanda text (no Streamlit here, so it can be tested alone).

NOTE: the Kinyarwanda was first written by an AI model and has since been checked by a Kinyarwanda speaker (reported by the project team).
Have a Kinyarwanda speaker review it (see docs/kinyarwanda_review.csv) before real farmers use it.
Corrections go in data/kinyarwanda_corrections.csv (columns: key, kinyarwanda) and are applied
automatically, so nobody needs to edit code.
"""
from __future__ import annotations

import csv
import string

LANGS = {"en": "English", "rw": "Kinyarwanda"}
CURRENCY = {"en": "RWF", "rw": "FRW"}

CROPS = {
    "Beans": "Ibishyimbo", "Cassava": "Imyumbati", "Irish Potatoes": "Ibirayi", "Maize": "Ibigori",
    "Rice": "Umuceri", "Sweet Potatoes": "Ibijumba", "Tomatoes": "Inyanya",
}
MONTHS_RW = ["Mutarama", "Gashyantare", "Werurwe", "Mata", "Gicurasi", "Kamena",
             "Nyakanga", "Kanama", "Nzeri", "Ukwakira", "Ugushyingo", "Ukuboza"]

STR = {
    "en": {
        "language": "Language",
        "section": "Section",
        "page_sell": "Where to sell",
        "page_trends": "Price trends",
        "page_data": "Data and trust",
        "page_sms": "SMS demo",
        "page_season": "Seasonal patterns",
        "view_label": 'Who are you?',
        "view_home": '🏠 Home',
        "view_farmer": '🧑\u200d🌾 Farmer dashboard',
        "view_gov": '🏛️ Government dashboard (MINAGRI)',
        "page_overview": 'National overview',
        "page_markets": 'Market comparison',
        "home_tag": 'Know the market. Choose wisely. Earn more.',
        "home_lead": 'Isoko Smart AI shows a farmer which market pays the most for a crop after the cost of getting there, and gives government a clear view of how prices move across Rwanda. Every price comes from real farmgate reports by Esoko Rwanda.',
        "home_problem_title": 'The problem',
        "home_problem": 'Two markets a short ride apart can pay very different prices for the same beans or rice. Farmers rarely see those prices before they travel, and planners have no single, simple picture of where prices are low or moving fast.',
        "home_n_records": 'Price records',
        "home_n_markets": 'Markets',
        "home_n_crops": 'Crops',
        "home_n_latest": 'Latest price',
        "home_example_title": "A live example from today's data",
        "home_example_intro": 'A farmer at {origin} with {qty} kg of {product} asks where to sell:',
        "home_for_farmer_title": 'For farmers',
        "home_for_farmer": 'Pick your crop, how many kilos you have and where you are. You get one clear answer: where to sell, how much more you could earn after transport, and why. Works in English and Kinyarwanda, and by SMS on any phone.',
        "home_for_gov_title": 'For government (MINAGRI) and planners',
        "home_for_gov": "See every crop's price month by month, the gap between the cheapest and dearest markets, which markets report too little, and how far the data can be trusted. Download the tables for your own reports.",
        "home_go_farmer": 'Open the farmer dashboard',
        "home_go_gov": 'Open the government dashboard',
        "home_how_title": 'How it works',
        "home_step1": '1. Collect: real farmgate prices from Esoko Rwanda, from 1 May 2026, in RWF per kg.',
        "home_step2": '2. Calculate: price minus the cost of transport to each market, using real road distances where known.',
        "home_step3": '3. Explain: a plain answer, the reasons, and a warning when the data is thin or the answer is not safe.',
        "home_honest_title": 'Honest about AI',
        "home_honest": "The advice is a transparent calculation, so a farmer can always see why. Trained models are tested against simple rules and used only when they clearly win; today they do not, so they are not used. A language model only reads a farmer's message, it never chooses a market or writes a price.",
        "home_pick": 'Choose a dashboard in the menu on the left, or press a button above.',
        "gov_title": 'National overview',
        "gov_caption": 'What is happening to prices across Rwanda, from May 2026 onward. Source: Esoko Rwanda farmgate prices.',
        "gov_gap_title": 'Gap between dearer and cheaper markets, latest month',
        "gov_gap_help": 'A wide gap means farmers in some markets are paid much less for the same crop.',
        "gov_col_crop": 'Crop',
        "gov_col_month": 'Month',
        "gov_col_median": 'Median price (RWF/kg)',
        "gov_col_markets": 'Markets reporting',
        "gov_col_gap": 'Gap (%)',
        "gov_cov_title": 'Data coverage',
        "gov_cov_stale": '{n} of {total} markets have no price in the last 30 days.',
        "gov_cov_ok": 'All {total} markets reported in the last 30 days.',
        "mk_title": 'Market comparison',
        "mk_caption": 'Compare markets for one product over the last 30 days. Download the table for your own analysis.',
        "mk_col_market": 'Market',
        "mk_col_district": 'District',
        "mk_col_median": 'Median price (RWF/kg)',
        "mk_col_reports": 'Reports',
        "mk_col_last": 'Last price date',
        "mk_col_vs": 'Against national median (%)',
        "mk_none": 'No prices for this product in the last 30 days.',
        "mk_download": 'Download this table (CSV)',
        "mk_cov_table": 'Reports by market (all crops, since 1 May 2026)',
        "mk_col_crops": 'Crops',
        "mk_col_records": 'Records',
        "sell_title": "Where should I sell my harvest?",
        "crop": "Crop",
        "product": "Variety / product name",
        "qty": "Quantity (kg)",
        "origin": "Where are you now?",
        "head_sell": "Sell at {market}",
        "head_stay": "Selling at {market} is fine",
        "body_sell": ("After transport you could earn about {net} for {qty} kg, which is {uplift} ({pct}%) more "
                      "than selling at {base}. Price used: {price}/kg, last seen {date}."),
        "body_stay": ("No other market beats it by enough to cover the trip. Expected about {net} for {qty} kg "
                      "at {price}/kg."),
        "badge": "Data reliability: {level}",
        "level_High": "High", "level_Medium": "Medium", "level_Low": "Low",
        "warn_low": ("The price at {market} is old or rests on very few reports. "
                     "Call a trader there before you travel."),
        "stable_ok": "This advice stays the same even if transport costs are half, or double, what you entered.",
        "stable_warn": ("This advice depends on the transport cost you entered. If real costs are different, the "
                        "best choice changes. Get a real quote before you decide."),
        "sms_sell": "{crop} {qty}kg: SELL at {best}. About {net} RWF ({pct}% more than {base}). Price {price}/kg ({date}).",
        "sms_sell_tail": " Call a trader first.",
        "sms_stay": "{crop} {qty}kg: selling at {base} is fine. About {net} RWF at {price}/kg ({date}).",
        "sms_stay_tail": " No market beats it after transport.",
        "sms_old": " Old price!",
        "sms_price": "{crop} RWF/kg: highest {hi_market} {hi}; lowest {lo_market} {lo}; median {med} ({date}).",
        "sms_help": "Isoko: SELL <crop> <kg> <market>, e.g. SELL BEANS 500 NYABUGOGO. PRICE <crop>, e.g. PRICE MAIZE.",
        "sms_bad_crop": "Crop not found. Use: beans, cassava, potatoes, maize, rice, sweet potatoes or tomatoes.",
        "sms_bad_market": "Market not found. Send the name of the market where you are, e.g. NYABUGOGO.",
        "sms_bad_qty": "Send the weight in kg, e.g. SELL BEANS 500 NYABUGOGO.",
        "sms_no_price": "No recent price for {crop}. Ask a trader.",
        "why_missing": "No location known for this market, so it cannot be ranked.",
        "why_note_low": " Its price is old or rests on few reports.",
        "why_home_best": ("Your own market: no transport cost. No other market beats it by enough to cover the trip "
                          "(it must pay at least {gain}% more).{note}"),
        "why_best_rec": ("RECOMMENDED. After paying {transport} RWF for transport over {km} km you keep the most: {net} RWF, "
                         "which is {uplift} RWF ({pct}%) more than at {base}.{note}"),
        "why_best_not": ("Highest income after transport, but only {pct}% more than your own market ({base}). "
                         "That is not enough to justify the trip (it needs {gain}%).{note}"),
        "why_home": ("Your own market: no transport cost, you keep {net} RWF. {best} gives {diff} RWF more after "
                     "transport.{note}"),
        "why_more_price": ("Pays more per kg ({price} vs {best_price} RWF), but the {km} km trip costs {transport} RWF, "
                           "so you keep {gap} RWF less than at {best}.{note}"),
        "why_closer": ("Closer ({km} km), but pays less per kg ({price} vs {best_price} RWF). The lower price costs more "
                       "than the transport it saves: {gap} RWF less than {best}.{note}"),
        "why_less_price": ("Pays less per kg ({price} vs {best_price} RWF) and the {km} km trip costs {transport} RWF: "
                           "{gap} RWF less than {best}.{note}"),
        "why_same_price": "Same price as {best} but farther ({km} km), so transport leaves you {gap} RWF less.{note}",
        "col_why": "Why this market, or why not",
        "col_price": "Price (RWF/kg)", "col_distance": "Distance (km)", "col_distance_type": "Distance type",
        "col_transport": "Transport (RWF)", "col_trips": "Trips", "col_income": "Income after transport",
        "col_date": "Price date", "col_reliability": "Reliability", "col_data": "Data",
        "col_market": "location", "col_rank": "rank",
        "chart_income": "Estimated income after transport (RWF)",
        "tx_title": "Transport costs (you can change them)",
        "tx_how": "How should transport be costed?",
        "tx_simple": "Simple: RWF per kg per km", "tx_vehicle": "By vehicle (trips)",
        "tx_rate": "Transport cost, RWF per kg per km",
        "tx_rate_help": "Planning assumption. Replace with real local quotes.",
        "tx_vehicle_pick": "Vehicle", "tx_own_quote": "My own quote",
        "tx_capacity": "Load the vehicle carries (kg)", "tx_per_km": "Cost per km driven (RWF)",
        "tx_per_km_help": "Fuel, driver and wear. Ask a transporter.",
        "tx_round": "The vehicle must come back (pay both ways)",
        "tx_defaults": "Vehicle figures are planning defaults, not measured prices. Replace them with quotes from transporters on your route.",
        "tx_window": "Use prices from the last N days",
        "tx_safer": "Ignore markets with only one price report (safer)",
        "tx_safer_help": "One report can be a mistake or a lucky high price. Your own market is always kept.",
        "no_recent": "No recent prices for this product.",
        "no_distance": "No market with a known distance. Add coordinates to data/markets.csv.",
        "stab_title": "How sure is this advice? (transport cost 0.5x to 2x)",
        "stab_col_cost": "Transport cost vs what you entered", "stab_col_best": "Best market", "stab_col_worth": "Worth the trip?",
        "stab_none": "no ranked market", "yes": "yes", "no": "no",
    },
    "rw": {
        "language": "Ururimi",
        "section": "Igice",
        "page_sell": "Aho kugurisha",
        "page_trends": "Uko ibiciro bihinduka",
        "page_data": "Amakuru no kwizerwa",
        "page_sms": "Ubutumwa bugufi (SMS)",
        "page_season": "Uko ibiciro bihinduka mu mezi",
        "view_label": 'Uri nde?',
        "view_home": '🏠 Ahabanza',
        "view_farmer": "🧑\u200d🌾 Urubuga rw'umuhinzi",
        "view_gov": '🏛️ Urubuga rwa Leta (MINAGRI)',
        "page_overview": "Incamake y'igihugu",
        "page_markets": 'Kugereranya amasoko',
        "home_tag": 'Menya isoko. Hitamo neza. Ungukire.',
        "home_lead": 'Isoko Smart AI yereka umuhinzi isoko ryishyura byinshi igihingwa cye nyuma yo kwishyura ubwikorezi, ikanereka Leta uko ibiciro bihinduka mu Rwanda hose. Ibiciro byose bituruka ku makuru nyayo ya Esoko Rwanda.',
        "home_problem_title": 'Ikibazo',
        "home_problem": "Amasoko abiri ari hafi ashobora kwishyura ibiciro bitandukanye cyane ku bishyimbo cyangwa umuceri bimwe. Abahinzi ntibakunze kubona ibyo biciro mbere yo gutega, kandi abategura gahunda nta shusho imwe yoroshye bafite y'aho ibiciro biri hasi cyangwa bihinduka vuba.",
        "home_n_records": 'Ibiciro byanditswe',
        "home_n_markets": 'Amasoko',
        "home_n_crops": 'Ibihingwa',
        "home_n_latest": 'Igiciro cya vuba',
        "home_example_title": "Urugero rufatiye ku makuru y'uyu munsi",
        "home_example_intro": 'Umuhinzi uri i {origin} ufite ibiro {qty} bya {product} arabaza aho yagurishiriza:',
        "home_for_farmer_title": 'Ku bahinzi',
        "home_for_farmer": "Hitamo igihingwa, ibiro ufite n'aho uri. Ubona igisubizo kimwe gisobanutse: aho kugurisha, amafaranga yiyongera nyuma y'ubwikorezi, n'impamvu. Bikora mu Kinyarwanda no mu Cyongereza, no kuri SMS ku telefone iyo ari yo yose.",
        "home_for_gov_title": "Ku Gihugu (MINAGRI) n'abategura gahunda",
        "home_for_gov": "Reba ibiciro by'igihingwa cyose ukwezi ku kwezi, itandukaniro riri hagati y'amasoko ahendutse n'ahenze, amasoko atatanga amakuru ahagije, n'uko amakuru yizerwa. Manura imbonerahamwe ukoreshe muri raporo zawe.",
        "home_go_farmer": "Fungura urubuga rw'umuhinzi",
        "home_go_gov": 'Fungura urubuga rwa Leta',
        "home_how_title": 'Uko bikora',
        "home_step1": "1. Gukusanya: ibiciro nyabyo byo ku muhanda bya Esoko Rwanda, guhera ku itariki ya 1 Gicurasi 2026, mu mafaranga y'u Rwanda ku kilo.",
        "home_step2": "2. Kubara: igiciro gisigaye nyuma yo gukuramo ubwikorezi bugana ku isoko ryose, hakoreshejwe intera nyayo y'umuhanda aho izwi.",
        "home_step3": "3. Gusobanura: igisubizo cyoroshye, impamvu, n'umuburo iyo amakuru ari make cyangwa igisubizo kitizewe.",
        "home_honest_title": 'Ukuri ku bwenge buhangano (AI)',
        "home_honest": "Inama itangwa ni ukubara kugaragara, bityo umuhinzi ahora abona impamvu. Moderi zatojwe zipimwa ugereranyije n'amategeko yoroshye kandi zikoreshwa gusa iyo zitsinze neza; uyu munsi ntizitsinda, ntizikoreshwa. Moderi y'ururimi isoma ubutumwa bw'umuhinzi gusa, ntihitamo isoko cyangwa ngo yandike igiciro.",
        "home_pick": "Hitamo urubuga ku ruhande rw'ibumoso, cyangwa ukande akabuto hejuru.",
        "gov_title": "Incamake y'igihugu",
        "gov_caption": 'Uko ibiciro bimeze mu Rwanda hose, guhera muri Gicurasi 2026. Inkomoko: ibiciro bya Esoko Rwanda.',
        "gov_gap_title": "Itandukaniro ry'amasoko ahenze n'ahendutse, ukwezi kwa vuba",
        "gov_gap_help": 'Itandukaniro rinini bivuze ko abahinzi bo mu masoko amwe bishyurwa make cyane ku gihingwa kimwe.',
        "gov_col_crop": 'Igihingwa',
        "gov_col_month": 'Ukwezi',
        "gov_col_median": 'Igiciro rwagati (RWF/kg)',
        "gov_col_markets": 'Amasoko yatanze amakuru',
        "gov_col_gap": 'Itandukaniro (%)',
        "gov_cov_title": 'Amakuru aboneka',
        "gov_cov_stale": 'Amasoko {n} kuri {total} nta giciro afite mu minsi 30 ishize.',
        "gov_cov_ok": 'Amasoko yose {total} yatanze amakuru mu minsi 30 ishize.',
        "mk_title": 'Kugereranya amasoko',
        "mk_caption": 'Gereranya amasoko ku gicuruzwa kimwe mu minsi 30 ishize. Manura imbonerahamwe uyikoreshe mu isesengura ryawe.',
        "mk_col_market": 'Isoko',
        "mk_col_district": 'Akarere',
        "mk_col_median": 'Igiciro rwagati (RWF/kg)',
        "mk_col_reports": 'Inshuro cyanditswe',
        "mk_col_last": 'Itariki ya nyuma',
        "mk_col_vs": "Ugereranyije n'igiciro rwagati cy'igihugu (%)",
        "mk_none": "Nta biciro by'iki gicuruzwa mu minsi 30 ishize.",
        "mk_download": 'Manura iyi mbonerahamwe (CSV)',
        "mk_cov_table": 'Amakuru ku isoko (ibihingwa byose, kuva 1 Gicurasi 2026)',
        "mk_col_crops": 'Ibihingwa',
        "mk_col_records": 'Ibyanditswe',
        "sell_title": "Nagurisha he umusaruro wanjye?",
        "crop": "Igihingwa",
        "product": "Ubwoko / izina ry'igihingwa",
        "qty": "Ingano (kg)",
        "origin": "Ubu uri he?",
        "head_sell": "Gurishiriza i {market}",
        "head_stay": "Kugurishiriza i {market} ni byiza",
        "body_sell": ("Nyuma yo kwishyura ubwikorezi, wabona hafi {net} ku biro {qty} (kg). Ni {uplift} ({pct}%) "
                      "arenga ayo wabona uramutse ugurishirije i {base}. Igiciro cyakoreshejwe: {price}/kg, "
                      "cyabonetse ku itariki ya {date}."),
        "body_stay": ("Nta rindi soko ryakwinjiriza ahagije ngo yishyure urugendo. Wabona hafi {net} ku biro "
                      "{qty} (kg) ku giciro cya {price}/kg."),
        "badge": "Kwizerwa kw'amakuru: {level}",
        "level_High": "Hejuru", "level_Medium": "Hagati", "level_Low": "Hasi",
        "warn_low": ("Igiciro cy'i {market} ni icy'igihe gishize cyangwa gishingiye ku makuru make. "
                     "Hamagara umucuruzi waho mbere yo gukora urugendo."),
        "stable_ok": ("Iyi nama ntihinduka n'iyo ubwikorezi bwaba bubaye kimwe cya kabiri cyangwa bukikuba "
                      "kabiri by'ibyo wanditse."),
        "stable_warn": ("Iyi nama iterwa n'igiciro cy'ubwikorezi wanditse. Niba ibiciro nyakuri bitandukanye, "
                        "isoko ryiza ryahinduka. Baza igiciro nyacyo mbere yo gufata icyemezo."),
        "sms_sell": "{crop} {qty}kg: Gurishiriza i {best}. Hafi {net} FRW ({pct}% arenga i {base}). Igiciro {price}/kg ({date}).",
        "sms_sell_tail": " Hamagara umucuruzi mbere.",
        "sms_stay": "{crop} {qty}kg: Kugurishiriza i {base} ni byiza. Hafi {net} FRW ku {price}/kg ({date}).",
        "sms_stay_tail": " Nta rindi soko riruta nyuma y'ubwikorezi.",
        "sms_old": " Igiciro cya kera!",
        "sms_price": "{crop} FRW/kg: hejuru i {hi_market} {hi}; hasi i {lo_market} {lo}; hagati {med} ({date}).",
        "sms_help": ("Isoko: GURISHA <igihingwa> IBIRO <kg> <isoko>, urugero GURISHA IBISHYIMBO IBIRO 500 NYABUGOGO. "
                     "IGICIRO <igihingwa>, urugero IGICIRO IBIGORI."),
        "sms_bad_crop": "Igihingwa ntikibonetse. Koresha: ibishyimbo, imyumbati, ibirayi, ibigori, umuceri, ibijumba cyangwa inyanya.",
        "sms_bad_market": "Isoko ntiribonetse. Ohereza izina ry'isoko uriho, urugero NYABUGOGO.",
        "sms_bad_qty": "Ohereza ibiro, urugero GURISHA IBISHYIMBO IBIRO 500 NYABUGOGO.",
        "sms_no_price": "Nta giciro giheruka cya {crop}. Baza umucuruzi.",
        "why_missing": "Aho iri soko riherereye ntihazwi, bityo ntibishoboka kuriringanya n'andi.",
        "why_note_low": " Igiciro cyaryo ni icya kera cyangwa gishingiye ku makuru make.",
        "why_home_best": ("Isoko ryawe: nta kiguzi cy'ubwikorezi. Nta rindi soko riryuta ku buryo ryakwishyura urugendo "
                          "(ryagombye kwishyura nibura {gain}% arenga).{note}"),
        "why_best_rec": ("BYASHISHIJWE. Nyuma yo kwishyura {transport} FRW y'ubwikorezi ku ntera ya {km} km, ubona byinshi "
                         "kurusha ahandi: {net} FRW, ni {uplift} FRW ({pct}%) arenga ayo wabona i {base}.{note}"),
        "why_best_not": ("Ni ryo ryinjiza byinshi nyuma y'ubwikorezi, ariko ni {pct}% gusa arenga isoko ryawe ({base}). "
                         "Ntibihagije ngo bikwiye urugendo (hakenewe {gain}%).{note}"),
        "why_home": ("Isoko ryawe: nta kiguzi cy'ubwikorezi, ubona {net} FRW. I {best} wabona {diff} FRW arenga "
                     "nyuma y'ubwikorezi.{note}"),
        "why_more_price": ("Bishyura menshi ku kilo ({price} FRW, naho i {best} ni {best_price} FRW), ariko urugendo rwa "
                           "{km} km rutwara {transport} FRW, bityo ubona {gap} FRW munsi y'ayo wabona i {best}.{note}"),
        "why_closer": ("Riri hafi ({km} km), ariko bishyura make ku kilo ({price} FRW, naho i {best} ni {best_price} FRW). "
                       "Igiciro gito gitwara byinshi kurusha ubwikorezi bizigama: {gap} FRW munsi y'i {best}.{note}"),
        "why_less_price": ("Bishyura make ku kilo ({price} FRW, naho i {best} ni {best_price} FRW) kandi urugendo rwa {km} km "
                           "rutwara {transport} FRW: {gap} FRW munsi y'i {best}.{note}"),
        "why_same_price": "Igiciro kimwe n'i {best} ariko riri kure ({km} km), bityo ubwikorezi bugusigira {gap} FRW munsi.{note}",
        "col_why": "Impamvu iri soko, cyangwa impamvu atari ryo",
        "col_price": "Igiciro (FRW/kg)", "col_distance": "Intera (km)", "col_distance_type": "Uko intera yabonetse",
        "col_transport": "Ubwikorezi (FRW)", "col_trips": "Ingendo", "col_income": "Inyungu nyuma y'ubwikorezi",
        "col_date": "Itariki y'igiciro", "col_reliability": "Kwizerwa", "col_data": "Amakuru",
        "col_market": "Isoko", "col_rank": "Umwanya",
        "chart_income": "Inyungu ikekwa nyuma y'ubwikorezi (FRW)",
        "tx_title": "Ibiciro by'ubwikorezi (ushobora kubihindura)",
        "tx_how": "Ubwikorezi bubarwe gute?",
        "tx_simple": "Byoroshye: FRW ku kilo ku kilometero", "tx_vehicle": "Hakurikijwe ikinyabiziga (ingendo)",
        "tx_rate": "Igiciro cy'ubwikorezi, FRW ku kilo ku kilometero",
        "tx_rate_help": "Ni igereranyo. Gisimbuze ibiciro nyakuri byo mu gace kawe.",
        "tx_vehicle_pick": "Ikinyabiziga", "tx_own_quote": "Igiciro cyanjye bwite",
        "tx_capacity": "Ibiro ikinyabiziga gitwara (kg)", "tx_per_km": "Igiciro ku kilometero cyagenzwe (FRW)",
        "tx_per_km_help": "Lisansi, umushoferi n'ingaruka ku modoka. Baza umutwara ibintu.",
        "tx_round": "Ikinyabiziga kigomba kugaruka (wishyura inzira zombi)",
        "tx_defaults": ("Ibiciro by'ibinyabiziga ni ibigereranyo, si ibyapimwe. Bisimbuze ibiciro nyakuri bya "
                        "ababitwara ku nzira yawe."),
        "tx_window": "Koresha ibiciro by'iminsi N ishize",
        "tx_safer": "Ntiharebwe amasoko afite raporo y'igiciro imwe gusa (birushaho kuba byiza)",
        "tx_safer_help": "Raporo imwe ishobora kuba ikosa cyangwa igiciro cyo hejuru kidasanzwe. Isoko ryawe ntirivanwaho.",
        "no_recent": "Nta biciro bya vuba by'iki gihingwa.",
        "no_distance": "Nta soko rifite intera izwi. Ongera ahantu amasoko ari muri data/markets.csv.",
        "stab_title": "Iyi nama yizewe ite? (ubwikorezi bwikubye 0.5 kugeza kuri 2)",
        "stab_col_cost": "Ubwikorezi ugereranyije n'ibyo wanditse", "stab_col_best": "Isoko ryiza",
        "stab_col_worth": "Urugendo rurakwiye?",
        "stab_none": "nta soko ryashyizwe ku rutonde", "yes": "yego", "no": "oya",
    },
}


def _fields(template: str) -> set:
    return {f for _, f, _, _ in string.Formatter().parse(template) if f}


def t(lang: str, key: str, **kw) -> str:
    """Text for `key` in `lang` (falls back to English if a Kinyarwanda string is missing)."""
    template = STR.get(lang, STR["en"]).get(key) or STR["en"][key]
    return template.format(**kw) if kw else template


def crop_name(lang: str, crop: str) -> str:
    return CROPS.get(crop, crop) if lang == "rw" else crop


def money(lang: str, x: float) -> str:
    return f"{x:,.0f} {CURRENCY.get(lang, 'RWF')}"


def fmt_date(lang: str, ts) -> str:
    return f"{ts.day:02d} {MONTHS_RW[ts.month - 1]}" if lang == "rw" else f"{ts:%d %b}"


def advice(lang: str, rec: dict, qty: float) -> dict:
    """The advice box: headline, body and reliability badge, from the recommendation made by isoko_core."""
    best, base = rec["best"], rec["baseline"]
    level = best["reliability"]
    badge = t(lang, "badge", level=t(lang, f"level_{level}"))
    if rec["worthwhile"]:
        return dict(kind="sell", level=level, badge=badge,
                    headline=t(lang, "head_sell", market=best["location"]),
                    body=t(lang, "body_sell", net=money(lang, best["net_return"]), qty=f"{qty:,.0f}",
                           uplift=money(lang, rec["uplift"]), pct=f"{rec['uplift_pct']:.0f}", base=base["location"],
                           price=money(lang, best["price"]), date=fmt_date(lang, best["last_date"])))
    return dict(kind="stay", level=level, badge=badge,
                headline=t(lang, "head_stay", market=base["location"]),
                body=t(lang, "body_stay", net=money(lang, base["net_return"]), qty=f"{qty:,.0f}",
                       price=money(lang, base["price"])))


def check_translations() -> list:
    """Problems that would crash the app: a missing key, or placeholders that differ between languages."""
    problems = []
    for key, en in STR["en"].items():
        rw = STR["rw"].get(key)
        if not rw:
            problems.append(f"{key}: missing Kinyarwanda")
        elif _fields(en) != _fields(rw):
            problems.append(f"{key}: placeholders differ {sorted(_fields(en))} vs {sorted(_fields(rw))}")
    problems += [f"{k}: Kinyarwanda key has no English" for k in STR["rw"] if k not in STR["en"]]
    return problems


def apply_corrections(path: str) -> list:
    """Apply reviewer corrections from a CSV (key, kinyarwanda). Returns the list of rows it refused."""
    import os
    refused = []
    if not path or not os.path.exists(path):
        return refused
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key, new = (row.get("key") or "").strip(), (row.get("kinyarwanda") or "").strip()
            if not key or not new:
                continue
            if key.startswith("crop:"):
                if key[5:] in CROPS:
                    CROPS[key[5:]] = new
                else:
                    refused.append(f"{key}: unknown crop")
            elif key not in STR["en"]:
                refused.append(f"{key}: unknown key")
            elif _fields(new) != _fields(STR["en"][key]):
                refused.append(f"{key}: keep the placeholders {sorted(_fields(STR['en'][key]))}")
            else:
                STR["rw"][key] = new
    return refused


def export_review_sheet(path: str) -> None:
    """Write the sheet a Kinyarwanda speaker fills in."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "english", "kinyarwanda", "correct_yes_no", "kinyarwanda_corrected"])
        for key, en in STR["en"].items():
            w.writerow([key, en, STR["rw"][key], "", ""])
        for crop, rw in CROPS.items():
            w.writerow([f"crop:{crop}", crop, rw, "", ""])


def _load_default_corrections():
    """Use data/kinyarwanda_corrections.csv (next to this file) automatically, so the app, the SMS code and the
    notebook all show the reviewer's wording without anyone editing code."""
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kinyarwanda_corrections.csv")
    return apply_corrections(path)


_load_default_corrections()
