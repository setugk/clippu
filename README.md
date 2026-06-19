# Clippery

Remember Pushbullet? You'd copy something on your phone and it would just appear on your laptop. It was magical.

Then they killed the free tier. Then the app stopped getting updates. Then you moved on — back to emailing yourself links, texting yourself snippets, opening Notion just to paste a URL.

Clippery is the fix. Open it on any device, paste your text, and it's instantly there on every other device with it open. No account. No subscription. No "sign in with Apple." Just a tiny server you run yourself.

![Clippery desktop](screenshots/clippery_selected.png)

<img src="screenshots/clippery_mobile.png" alt="Clippery mobile" width="320" />

## What it does

- Paste text on one device, copy it on another
- History of the last 25 clips, always visible
- Click any item to preview the full text
- Auto-syncs across all open tabs every 2 seconds — no refresh needed
- Works on desktop and mobile

## Stack

Single Python file. Flask backend, vanilla JS frontend — no build step, no bundler, no CDN dependencies. History stored as a JSON file on disk.

## Run it

```bash
docker compose up -d
```

That's it. Open `http://localhost:5050`.

```yaml
# docker-compose.yml
services:
  clipboard:
    build: .
    container_name: clipboard
    restart: unless-stopped
    ports:
      - "5050:5000"
    volumes:
      - ./data:/data
    environment:
      - CLIPPERY_USER=admin
      - CLIPPERY_PASS=changeme
```

## Authentication

Set `CLIPPERY_USER` and `CLIPPERY_PASS` in your `docker-compose.yml` to enable HTTP basic auth. The browser will prompt for credentials on first visit.

If neither variable is set, the app runs without auth — fine if you're behind Cloudflare Access or another reverse proxy that handles it.

## Remote access (optional)

If you want to access it from outside your home network, put it behind a [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) with a Zero Trust Access policy. That way you get your own `clippery.yourdomain.com` with email OTP authentication — no passwords to manage, no port forwarding.

## License

MIT
