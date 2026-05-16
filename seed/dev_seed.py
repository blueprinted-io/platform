"""Development seed script — populates the local dev database with realistic tasks.

Usage:
    python seed/dev_seed.py --token <JWT>

Getting your JWT:
    1. Open http://localhost:5173 and log in.
    2. Open DevTools → Network tab → filter by "tasks" or "me".
    3. Click any API request, open the Headers tab.
    4. Copy the value after "Authorization: Bearer " — that's your JWT.
    5. Pass it as --token "eyJ..."

The script goes through the API (localhost:8000) so the docker stack must be running.
It creates:
    - 1 domain ("linux-sysadmin")
    - 1 confirmed task (full steps, actions, notes, completion)
    - 1 draft task (minimal, no steps)
    - 1 submitted task (with steps)

Note: this script uses the API for all task operations but makes one direct DB call
to create the domain and assign the user — there is no domain management API yet.
That direct call uses docker exec so docker must be available on PATH.
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request


API_BASE = "http://localhost:8000/api/v1"
DOMAIN = "linux-sysadmin"


def api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        print(f"  HTTP {e.code} {method} {path}: {body_text}")
        sys.exit(1)


def psql(sql: str) -> None:
    """Run SQL directly via docker exec — used only for domain bootstrap."""
    result = subprocess.run(
        ["docker", "exec", "deploy-db-1", "psql", "-U", "blueprinted", "-d", "blueprinted", "-c", sql],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  psql error: {result.stderr.strip()}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed dev database with sample tasks.")
    parser.add_argument("--token", required=True, help="JWT from browser DevTools")
    args = parser.parse_args()
    token: str = args.token

    # Verify token works
    print("Verifying token...")
    me = api("GET", "/users/me", token)
    user_id = me["id"]
    print(f"  Authenticated as: {me['email']} (id={user_id})")

    # Create domain directly in DB (no domain API yet)
    print(f"\nCreating domain '{DOMAIN}'...")
    psql(
        f"INSERT INTO domains (name, created_by) "
        f"VALUES ('{DOMAIN}', '{user_id}') "
        f"ON CONFLICT (name) DO NOTHING;"
    )
    psql(
        f"INSERT INTO user_domains (user_id, domain, created_by) "
        f"VALUES ('{user_id}', '{DOMAIN}', '{user_id}') "
        f"ON CONFLICT DO NOTHING;"
    )
    print("  Done.")

    # --- Task 1: confirmed, full content ---
    print("\nCreating confirmed task: 'Configure SSH key authentication'...")
    t1 = api("POST", "/tasks", token, {
        "title": "Configure SSH key authentication",
        "outcome": "Password-based SSH login disabled; key-based authentication verified working for the target user.",
        "domain": DOMAIN,
        "software_name": "OpenSSH",
        "software_version": "8.9+",
        "facts": [
            "SSH keys use asymmetric cryptography: the private key stays on the client, the public key is placed on the server.",
            "The authorized_keys file must have permissions 600 and be owned by the target user.",
            "Disabling password auth requires restarting the SSH daemon to take effect.",
        ],
        "concepts": [
            "Public-key cryptography: a key pair where anything encrypted with the public key can only be decrypted with the private key.",
            "The principle of least privilege: only the keys that need access should be authorised.",
        ],
        "tags": ["ssh", "security", "authentication"],
    })
    t1_id = t1["id"]

    steps = [
        {
            "step": "Generate an SSH key pair on the client machine",
            "completion": "Files ~/.ssh/id_ed25519 and ~/.ssh/id_ed25519.pub exist on the client.",
            "notes": "ed25519 is preferred over RSA for new keys. Use RSA 4096 only if the server is too old to support ed25519.",
            "actions": [
                {"instruction": "ssh-keygen -t ed25519 -C \"your_email@example.com\""},
            ],
        },
        {
            "step": "Copy the public key to the server",
            "completion": "The public key appears in ~/.ssh/authorized_keys on the server.",
            "notes": "ssh-copy-id handles file creation and permissions automatically. If unavailable, append the key manually with cat >> ~/.ssh/authorized_keys.",
            "actions": [
                {"instruction": "ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server"},
            ],
        },
        {
            "step": "Verify key-based login works before disabling passwords",
            "completion": "You can SSH in without being prompted for a password.",
            "notes": None,
            "actions": [
                {"instruction": "ssh -i ~/.ssh/id_ed25519 user@server"},
            ],
        },
        {
            "step": "Disable password authentication in sshd_config",
            "completion": "SSH refuses password login attempts; key login still works.",
            "notes": "Always test key login in a separate session before restarting sshd — a mistake here can lock you out.",
            "irreversible": True,
            "actions": [
                {"instruction": "sudo nano /etc/ssh/sshd_config"},
                {"instruction": "# Set: PasswordAuthentication no"},
                {"instruction": "sudo systemctl restart sshd"},
            ],
        },
    ]
    for step in steps:
        api("POST", f"/tasks/{t1_id}/steps", token, step)

    api("POST", f"/tasks/{t1_id}/submit", token)
    print("  Submitted. Cannot auto-confirm (requires a different reviewer). Status: submitted.")
    print(f"  Task ID: {t1_id}")

    # --- Task 2: draft, minimal ---
    print("\nCreating draft task: 'Set up automatic security updates'...")
    t2 = api("POST", "/tasks", token, {
        "title": "Set up automatic security updates",
        "outcome": "unattended-upgrades installed and configured to apply security patches automatically on reboot.",
        "domain": DOMAIN,
        "software_name": "unattended-upgrades",
        "tags": ["security", "patching", "debian"],
    })
    print(f"  Status: draft — Task ID: {t2['id']}")

    # --- Task 3: submitted ---
    print("\nCreating submitted task: 'Configure UFW firewall'...")
    t3 = api("POST", "/tasks", token, {
        "title": "Configure UFW firewall",
        "outcome": "UFW enabled with default-deny incoming, allow outgoing. SSH port open. All other ports closed.",
        "domain": DOMAIN,
        "software_name": "UFW",
        "facts": [
            "UFW (Uncomplicated Firewall) is a frontend for iptables designed to simplify firewall management on Debian/Ubuntu.",
        ],
        "tags": ["firewall", "security", "ufw"],
    })
    t3_id = t3["id"]
    api("POST", f"/tasks/{t3_id}/steps", token, {
        "step": "Enable UFW with default deny-incoming policy",
        "completion": "ufw status shows 'Status: active' with default incoming deny.",
        "notes": "Run this over an existing SSH session carefully — add the SSH allow rule first or you will lock yourself out.",
        "actions": [
            {"instruction": "sudo ufw default deny incoming"},
            {"instruction": "sudo ufw default allow outgoing"},
            {"instruction": "sudo ufw allow ssh"},
            {"instruction": "sudo ufw enable"},
        ],
        "irreversible": False,
    })
    api("POST", f"/tasks/{t3_id}/submit", token)
    print(f"  Status: submitted — Task ID: {t3_id}")

    print("\nSeed complete.")
    print(f"  Open http://localhost:5173/tasks to see your data.")
    print(f"\n  Note: tasks 1 and 3 are 'submitted' — confirm them via a second user account")
    print(f"  (self-review is not permitted). To quickly confirm for dev, use the API")
    print(f"  with a token from a different Authentik user.")


if __name__ == "__main__":
    main()
