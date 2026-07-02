# Catan LAN

Private browser Catan-style game server for friends, with original placeholder art and Cloudflare tunnel sharing.

## Run

```bash
python -m pip install -r requirements.txt
python run.py
```

Open `http://localhost:5050`. If `cloudflared` is installed, `run.py` also prints a `https://*.trycloudflare.com` URL you can share.

Use LAN only:

```bash
python run.py --no-tunnel
```

## Assets

Placeholder PNGs live in `app/static/assets/`. Draw over any file, save it with the same name, then refresh/restart the server.

Regenerate missing placeholders without overwriting your drawings:

```bash
python scripts/generate_assets.py
```

Overwrite all placeholders:

```bash
python scripts/generate_assets.py --force
```

## Tests

```bash
pytest
```

Project rules, current feature status, button list, and asset inventory are in `Project.md`.
