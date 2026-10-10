#!/usr/bin/env python3
"""
Automated GitHub App setup via GitHub App Manifest flow.
Starts a local webserver, guides the user to approve app creation,
exchanges the callback code for App ID and Private Key,
and sets them directly into GitHub Actions Secrets.
"""

import http.server
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
import webbrowser

PORT = 3000
REPO = sys.argv[1] if len(sys.argv) > 1 else "grold/agy-github-automation"
APP_NAME = sys.argv[2] if len(sys.argv) > 2 else f"agy-bot-{REPO.split('/')[0]}"

MANIFEST = {
    "name": APP_NAME,
    "url": f"https://github.com/{REPO}",
    "hook_attributes": {
        "url": "https://example.com"
    },
    "redirect_url": f"http://localhost:{PORT}/callback",
    "public": False,
    "default_permissions": {
        "contents": "write",
        "issues": "write",
        "pull_requests": "write",
        "metadata": "read"
    },
    "default_events": []
}

class ManifestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Setup GitHub App for Antigravity</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #0d1117; color: #c9d1d9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 32px; max-width: 520px; width: 100%; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }}
        h1 {{ font-size: 20px; color: #58a6ff; margin-top: 0; }}
        p {{ font-size: 14px; line-height: 1.6; color: #8b949e; }}
        button {{ background: #238636; color: white; border: none; border-radius: 6px; padding: 12px 20px; font-size: 14px; font-weight: 600; cursor: pointer; width: 100%; margin-top: 16px; }}
        button:hover {{ background: #2ea043; }}
        code {{ background: #21262d; padding: 2px 6px; border-radius: 4px; color: #f0f6fc; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Register Antigravity Bot</h1>
        <p>This will register a dedicated GitHub App (<code>{APP_NAME}</code>) with automated permissions (Issues, Pull Requests, Contents) for <code>{REPO}</code>.</p>
        <form action="https://github.com/settings/apps/new" method="post">
            <input type="hidden" name="manifest" value='{json.dumps(MANIFEST)}' />
            <button type="submit">Create GitHub App on GitHub &rarr;</button>
        </form>
    </div>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))
        elif parsed.path == "/callback":
            params = urllib.parse.parse_qs(parsed.query)
            code = params.get("code", [""])[0]
            if not code:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing code in callback.")
                return

            print(f"\n[+] Received authorization code from GitHub: {code[:10]}...")
            print("[+] Exchanging code for App credentials...")

            req = urllib.request.Request(
                f"https://api.github.com/app-manifests/{code}/conversions",
                data=b"",
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "Antigravity-Setup"
                },
                method="POST"
            )

            try:
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode())
                
                app_id = str(data["id"])
                pem = data["pem"]
                slug = data["slug"]
                install_url = f"https://github.com/apps/{slug}/installations/new"

                print(f"[+] App ID: {app_id}")
                print(f"[+] App Slug: {slug}")
                print(f"[+] Storing secrets in repository '{REPO}'...")

                subprocess.run(["gh", "secret", "set", "APP_ID", "-R", REPO, "--body", app_id], check=True)
                subprocess.run(["gh", "secret", "set", "APP_PRIVATE_KEY", "-R", REPO, "--body", pem], check=True)

                print("[+] Successfully saved APP_ID and APP_PRIVATE_KEY to repository secrets!")
                print(f"\n>>> NEXT STEP: Install the App on '{REPO}' by visiting:")
                print(f"    {install_url}\n")

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                success_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>App Created Successfully!</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #0d1117; color: #c9d1d9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 32px; max-width: 520px; width: 100%; box-shadow: 0 8px 24px rgba(0,0,0,0.5); text-align: center; }}
        h1 {{ font-size: 22px; color: #3fb950; margin-top: 0; }}
        p {{ font-size: 14px; line-height: 1.6; color: #8b949e; text-align: left; }}
        a.btn {{ display: inline-block; background: #238636; color: white; text-decoration: none; border-radius: 6px; padding: 12px 24px; font-size: 14px; font-weight: 600; margin-top: 20px; }}
        a.btn:hover {{ background: #2ea043; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>&#10003; GitHub App Configured!</h1>
        <p>Your GitHub App (<code>{slug}</code>) was created and credentials (<code>APP_ID</code> and <code>APP_PRIVATE_KEY</code>) have been securely saved to <code>{REPO}</code>.</p>
        <p><strong>Final Step:</strong> Click the button below to install the App onto <code>{REPO}</code>.</p>
        <a class="btn" href="{install_url}">Install App on Repository &rarr;</a>
    </div>
</body>
</html>"""
                self.wfile.write(success_html.encode("utf-8"))

                # Schedule server shutdown
                def shutdown():
                    self.server.shutdown()
                import threading
                threading.Thread(target=shutdown).start()

            except Exception as e:
                print(f"[-] Error exchanging manifest code: {e}", file=sys.stderr)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {e}".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def main():
    server = http.server.HTTPServer(("127.0.0.1", PORT), ManifestHandler)
    url = f"http://localhost:{PORT}"
    print(f"=== GitHub App Manifest Setup Server Running ===")
    print(f"Repository: {REPO}")
    print(f"App Name:   {APP_NAME}")
    print(f"\nPlease open this link in your browser to create the App:")
    print(f"    {url}")
    print("==================================================")
    
    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
