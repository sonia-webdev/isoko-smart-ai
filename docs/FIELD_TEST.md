# Field test plan (one week, 10 farmers, 3 officials)

**Goal:** learn if farmers understand the advice, trust it, and would act on it; find the messages they really type.

## Before
- Fresh prices loaded the same week. Check `/health`.
- Phones: ask farmers to use their own phone. Note smartphone or feature phone.
- Consent: read the short statement in PRIVACY.md. No names or numbers are written down.

## With each farmer (15 minutes)
1. Ask: "Where would you sell 300 kg of beans this week and why?" (write the answer).
2. Give them the app (Kinyarwanda) or the SMS number. Do not explain. Watch where they hesitate.
3. Ask them to find the advice for their own crop and market. Time it.
4. Ask: "What does 'Kwizerwa kw'amakuru: Hasi' mean to you?" (checks if the reliability message is understood).
5. Ask: "Would you travel to the market we suggested? What would stop you?"
6. Ask them to text three messages in their own words. Save them (no number) in `docs/farmer_messages_field.csv`.

## With officials (MINAGRI, district agronomists)
Ask them to find: the crop with the widest gap between markets; the markets with too little data; the monthly movement of rice.
Ask what number or report they would need that is missing.

## Measure
- Share of farmers who find the advice alone; share who understand the reliability label; share who would act.
- Share of their SMS texts the reader understands (run the new texts through `isoko_nlu` as in the notebook).
- Top 5 confusions. Fix those first.

## Record sheet
`docs/field_test_sheet.csv` has one row per participant.
