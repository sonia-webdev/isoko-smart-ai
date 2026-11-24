# Putting Isoko Smart AI online

What you need: a small server (1 CPU, 1 GB memory is enough), a domain name, and about an hour.
Estimated cost: a basic VPS (a few US dollars a month) plus the domain. SMS messages cost extra (see "SMS" below).

## Option A: Docker (recommended)
1. Rent a Linux VPS (any provider) and install Docker.
2. Copy the project folder to it (`isoko/`).
3. Point your domain's DNS "A record" at the server's address.
4. In the project folder create a file called `.env`:
   ```
   DOMAIN=isoko.yourdomain.rw
   ISOKO_ADMIN_TOKEN=put-a-long-random-secret-here
   ```
5. Run `docker compose up -d`. Caddy gets the HTTPS certificate by itself.
6. Open `https://isoko.yourdomain.rw`. Check `https://isoko.yourdomain.rw/health`.
7. Load your real prices once (see OPERATIONS.md, "First time"). Until you do, the site uses the demonstration prices.

## Option B: no Docker
```
pip install -r requirements-server.txt
PORT=8080 ISOKO_ADMIN_TOKEN=... python server.py
```
Put it behind any HTTPS front (Caddy, nginx). To keep it running, use a systemd service:
```
[Service]
WorkingDirectory=/opt/isoko
Environment=PORT=8080
Environment=ISOKO_ADMIN_TOKEN=...
ExecStart=/usr/bin/python3 server.py
Restart=always
User=isoko
```

## The farmer's phone
Open the address in Chrome and choose "Add to Home screen". It then opens like an app and shows the last prices it saw if the
connection drops. This works only over HTTPS.

## SMS (needs an account, costs money, NOT done for you)
The server already understands SMS callbacks. To connect a real number you must:
1. Create an account with an SMS provider that serves Rwanda (for example Africa's Talking) and get a number or short code.
   Short codes and sender names need approval; ask the provider and the regulator (RURA) what is required.
2. In the provider's dashboard set the incoming-message callback to `https://isoko.yourdomain.rw/api/sms`.
   - Africa's Talking: also put `AT_USERNAME` and `AT_API_KEY` in `.env`; the server then sends the reply through their API.
   - Twilio style providers: use `https://isoko.yourdomain.rw/api/sms?format=twiml`.
3. Test with your own phone first and read the provider's pricing for replies.
Not tested against a live provider: the code is checked with a fake provider only.

USSD (menus on any feature phone, no data) is the other common way in Rwanda. It needs the mobile operators; it is not built.

## Backups
The things worth keeping are the Docker volumes `isoko_data` (prices, feedback) and `isoko_models`. Copy `data/isoko_crop_data.csv`
to a safe place every week.

## Updating the app
Copy the new project files and run `docker compose up -d --build`. The volumes keep your data.
