from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import threading
import time

from app.server import app, socketio

TUNNEL_RE = re.compile(r"https://[-a-zA-Z0-9]+\.trycloudflare\.com")


def stream_cloudflared(process: subprocess.Popen[str]) -> None:
    assert process.stdout is not None
    seen_url = None
    for line in process.stdout:
        text = line.rstrip()
        match = TUNNEL_RE.search(text)
        if match and match.group(0) != seen_url:
            seen_url = match.group(0)
            print("\nCloudflare tunnel:", seen_url, "\n", flush=True)
        print("[cloudflared]", text, flush=True)


def start_tunnel(port: int) -> subprocess.Popen[str] | None:
    executable = shutil.which("cloudflared")
    if not executable:
        print("cloudflared not found; running LAN-only. Install it to get a share URL.", flush=True)
        return None
    command = [executable, "tunnel", "--url", f"http://localhost:{port}"]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    threading.Thread(target=stream_cloudflared, args=(process,), daemon=True).start()
    return process


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Catan server and optional Cloudflare tunnel.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5050")))
    parser.add_argument("--no-tunnel", action="store_true", help="Run only the local Flask server.")
    args = parser.parse_args()

    tunnel = None if args.no_tunnel else start_tunnel(args.port)
    local_url = f"http://localhost:{args.port}"
    lan_url = f"http://{get_lan_hint()}:{args.port}" if get_lan_hint() else local_url
    print(f"Local server: {local_url}", flush=True)
    print(f"LAN hint:     {lan_url}", flush=True)
    if not args.no_tunnel:
        print("Waiting for Cloudflare to print the share URL...", flush=True)
    try:
        socketio.run(app, host=args.host, port=args.port, allow_unsafe_werkzeug=True)
    finally:
        if tunnel and tunnel.poll() is None:
            tunnel.terminate()
            time.sleep(0.5)
            if tunnel.poll() is None:
                tunnel.kill()
    return 0


def get_lan_hint() -> str | None:
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        address = sock.getsockname()[0]
        sock.close()
        return address
    except OSError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
