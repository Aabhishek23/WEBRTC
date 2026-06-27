"""
Automation test: Simulates exactly what the GUI does when creating issues.
Tests: label existence check, label auto-creation, and issue creation with assignee.
"""

import subprocess
import json

REPO = ""   # will use gh's :owner/:repo auto-resolve
TEST_TITLE = "[AUTO-TEST] Label & Assignee Diagnostic Issue"
TEST_BODY = "This is an automated test issue. Safe to delete."
TEST_LABELS = ["backend", "Phase 1", "enhancement"]
TEST_ASSIGNEE = "@me"

PRESET_COLORS = ["89b4fa", "b4befe", "a6e3a1", "f38ba8", "f9e2af", "fab387", "cba6f7", "f5c2e7"]


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


print("=" * 60)
print("STEP 1: Check GitHub auth status")
r = run(["gh", "auth", "status"])
print(r.stdout or r.stderr)

print("=" * 60)
print("STEP 2: Fetch existing repo labels")
r = run(["gh", "api", "repos/:owner/:repo/labels", "--jq", ".[].name"])
if r.returncode != 0:
    print("[FAIL] Could not fetch labels:", r.stderr)
    existing_labels = set()
else:
    existing_labels = {l.strip() for l in r.stdout.splitlines() if l.strip()}
    print("[OK] Existing labels on GitHub:", existing_labels)

print("=" * 60)
print("STEP 3: Auto-create any missing test labels")
for label in TEST_LABELS:
    if label not in existing_labels:
        import random
        color = random.choice(PRESET_COLORS)
        print(f"  Creating missing label: '{label}' with color #{color}")
        r = run([
            "gh", "label", "create", label,
            "--color", color,
            "--description", f"Auto-created for test"
        ])
        if r.returncode == 0:
            print(f"  [OK] Created label: {label}")
            existing_labels.add(label)
        else:
            print(f"  [FAIL] Could not create label '{label}':", r.stderr.strip())
    else:
        print(f"  [SKIP] Label already exists: {label}")

print("=" * 60)
print("STEP 4: Create test issue with labels and assignee")
labels_str = ",".join(TEST_LABELS)
cmd = [
    "gh", "issue", "create",
    "--title", TEST_TITLE,
    "--body", TEST_BODY,
    "--label", labels_str,
    "--assignee", TEST_ASSIGNEE
]
print("Running command:", " ".join(cmd))
r = run(cmd)
if r.returncode == 0:
    print("[SUCCESS] Issue created:", r.stdout.strip())
else:
    print("[FAIL] Error creating issue:")
    print("  stdout:", r.stdout.strip())
    print("  stderr:", r.stderr.strip())

print("=" * 60)
print("DONE")
