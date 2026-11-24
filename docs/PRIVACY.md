# Privacy: what Isoko stores

Isoko Smart AI is built to know as little about farmers as possible.

| Data | Kept? |
|---|---|
| Phone numbers | **No.** Used once to send a reply, never written to disk or logs. Numbers typed inside a comment or an SMS text are replaced by "[number]". |
| Name, location of the farmer, device | **No.** The server keeps no access log. |
| "Was this advice useful?" answer, crop, chosen market, language, short comment | Yes, in `data/feedback.jsonl`, with the time. Not linked to a person. |
| SMS texts | **Only if you switch it on** (`ISOKO_LOG_MESSAGES=1`), without phone numbers, to improve the message reader. |
| Language choice | On the farmer's own phone only. |

Message logging is **off** unless you switch it on. Before you do: tell farmers in plain Kinyarwanda that their texts (without their
phone number) may be read by the project team to improve the service, and agree with a lawyer how people can say no. The safe
alternative is to leave logging off and collect messages during field tests, with each farmer's consent.
Check Rwanda's law on personal data protection (Law No. 058/2021) and have a lawyer review this before a public launch.
This file is not legal advice.
