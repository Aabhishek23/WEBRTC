import os
import json
import subprocess
import sys
import argparse

def check_gh_installed():
    """Checks if GitHub CLI is installed and authenticated."""
    try:
        # Check if gh is installed
        subprocess.run(["gh", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: GitHub CLI ('gh') is not installed or not in your PATH.")
        print("Please install it from https://cli.github.com/ and try again.")
        return False

    try:
        # Check if authenticated
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Error: GitHub CLI is not authenticated.")
            print("Please run 'gh auth login' in your terminal to authenticate with GitHub.")
            return False
    except Exception as e:
        print(f"⚠️ Warning: Could not verify GitHub CLI auth status: {e}")
        print("We will try to proceed, but commands might fail if not authenticated.")
        
    return True

def create_github_issue(title, body, assignees=None, labels=None, milestone=None):
    """Creates a single GitHub issue using the gh CLI."""
    cmd = ["gh", "issue", "create", "--title", title, "--body", body]
    
    if assignees:
        # If it's a list or comma-separated string
        if isinstance(assignees, list):
            assignees = ",".join(assignees)
        cmd.extend(["--assignee", assignees])
        
    if labels:
        if isinstance(labels, list):
            labels = ",".join(labels)
        cmd.extend(["--label", labels])
        
    if milestone:
        cmd.extend(["--milestone", milestone])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # The output of gh issue create is the URL of the created issue
        issue_url = result.stdout.strip()
        return True, issue_url
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() or e.stdout.strip()
        return False, error_msg

def load_issues_from_json(file_path):
    """Loads issues from a JSON file."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return None

def interactive_mode():
    """Allows creating issues interactively one by one."""
    print("\n--- 📝 Interactive Issue Creator ---")
    issues = []
    while True:
        title = input("\nEnter Issue Title (or leave empty to finish): ").strip()
        if not title:
            break
            
        body = input("Enter Issue Description/Body: ").strip()
        assignee = input("Enter Assignee (e.g. @me, username, or leave empty): ").strip()
        labels_input = input("Enter Labels (comma-separated, e.g. bug,enhancement, or leave empty): ").strip()
        
        labels = [l.strip() for l in labels_input.split(",") if l.strip()] if labels_input else []
        
        issues.append({
            "title": title,
            "body": body,
            "assignee": assignee if assignee else None,
            "labels": labels
        })
        
        more = input("Add another issue? (y/n): ").strip().lower()
        if more != 'y':
            break
            
    return issues

def create_template_json(file_path):
    """Creates a sample issues.json file with pre-populated Phase 1 issues."""
    sample_issues = [
        {
            "title": "Phase 1 - Day 1 [Backend]: Setup Express App & Room Generator API",
            "body": "Setup basic Express app, configure environmental variables, and build a REST API (POST /api/rooms) returning a unique 9-digit hyphenated Room ID (XXX-XXX-XXX).",
            "assignee": "@me",
            "labels": ["backend", "enhancement", "Phase 1"]
        },
        {
            "title": "Phase 1 - Day 1 [Frontend]: React Boilerplate & Landing Page",
            "body": "Create frontend boilerplate with routing. Design the landing page containing a text input for Room ID, user nickname, and join/create buttons.",
            "assignee": "",
            "labels": ["frontend", "enhancement", "Phase 1"]
        },
        {
            "title": "Phase 1 - Day 2 [Backend]: Socket.IO Init & Room State Control",
            "body": "Initialize Socket.IO connection handlers. Write room state management to prevent more than two users from joining the same room (One-to-One boundary limit).",
            "assignee": "@me",
            "labels": ["backend", "enhancement", "Phase 1"]
        },
        {
            "title": "Phase 1 - Day 2 [Frontend]: Camera/Mic Selection & Local Stream",
            "body": "Add camera and microphone selection logic. Render the local camera track onto a <video> component with audio muted locally to prevent loop feedback.",
            "assignee": "",
            "labels": ["frontend", "enhancement", "Phase 1"]
        },
        {
            "title": "Phase 1 - Day 3 [Backend]: Socket Signaling Event Listeners",
            "body": "Complete signaling event listeners (offer, answer, ice-candidate) that target a specific peer socket to enable relaying.",
            "assignee": "@me",
            "labels": ["backend", "enhancement", "Phase 1"]
        },
        {
            "title": "Phase 1 - Day 3 [Frontend]: Socket Connection & Context Manager",
            "body": "Build the Socket manager in React using React contexts or custom hooks. Verify connection states, connect client sockets, and join the correct room room pool.",
            "assignee": "",
            "labels": ["frontend", "enhancement", "Phase 1"]
        },
        {
            "title": "Phase 1 - Day 4 [Integration]: Link Frontend Client Sockets with Backend",
            "body": "Integration Day 1: Link frontend client sockets to the backend. Verify logging on server when a user enters/leaves, and check user count limits.",
            "assignee": "@me",
            "labels": ["integration", "Phase 1"]
        },
        {
            "title": "Phase 1 - Day 5 [Frontend]: WebRTC RTCPeerConnection Lifecycle",
            "body": "Write the WebRTC core handshake: Instantiate RTCPeerConnection, attach media tracks, capture generated local ICE candidates, and trigger SDP offer generation upon receiving user-joined event.",
            "assignee": "",
            "labels": ["frontend", "enhancement", "Phase 1"]
        },
        {
            "title": "Phase 1 - Day 5 [Backend]: Real-time Logging & STUN configs",
            "body": "Assist with real-time logging, testing websocket packet integrity, and configuring fallback STUN servers on the signaling endpoints.",
            "assignee": "@me",
            "labels": ["backend", "Phase 1"]
        },
        {
            "title": "Phase 1 - Day 6 [Integration]: Complete WebRTC Handshake & Remote Stream Render",
            "body": "Integration Day 2: Verify the complete WebRTC handshake. Configure the remote stream component, bind incoming tracks to the remoteVideo HTML element, and test audio/video flow.",
            "assignee": "@me",
            "labels": ["integration", "Phase 1"]
        },
        {
            "title": "Phase 1 - Day 7 [Testing]: Local Loopback & NAT Traversal Tests",
            "body": "Perform local loopback tests, verify NAT traversal on different browser engines (Chrome vs Firefox/Safari), and package codebase for Phase 2.",
            "assignee": "@me",
            "labels": ["testing", "Phase 1"]
        }
    ]
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(sample_issues, f, indent=2, ensure_ascii=False)
        print(f"📄 Created template issue file: {file_path} with Phase 1 tasks!")
        return True
    except Exception as e:
        print(f"❌ Failed to create template file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Bulk GitHub Issue Creator using gh CLI")
    parser.path_args = parser.add_argument("-f", "--file", default="issues.json", help="Path to JSON file containing issues list")
    parser.add_argument("-i", "--interactive", action="store_true", help="Create issues one-by-one interactively")
    parser.add_argument("-t", "--template", action="store_true", help="Just generate the issues.json template and exit")
    
    args = parser.parse_args()

    # If user wants just template
    if args.template:
        create_template_json(args.file)
        sys.exit(0)

    # Check gh CLI installation and login status
    if not check_gh_installed():
        sys.exit(1)

    issues = []

    if args.interactive:
        issues = interactive_mode()
    else:
        # Check if file exists, if not create template
        if not os.path.exists(args.file):
            print(f"🔍 {args.file} not found.")
            create_template_json(args.file)
            print(f"💡 Edit {args.file} to add/modify your issues, then run: python create_issues.py")
            sys.exit(0)
            
        issues = load_issues_from_json(args.file)
        if not issues:
            print("❌ No issues found to create or failed to parse JSON.")
            sys.exit(1)

    if not issues:
        print("ℹ️ No issues to create. Exiting.")
        sys.exit(0)

    print(f"\n🚀 Starting creation of {len(issues)} issue(s) on GitHub...\n")
    
    success_count = 0
    fail_count = 0

    for idx, issue in enumerate(issues, start=1):
        title = issue.get("title")
        body = issue.get("body", "")
        assignee = issue.get("assignee")
        labels = issue.get("labels", [])
        milestone = issue.get("milestone")

        if not title:
            print(f"⚠️ Skipping item #{idx}: Missing 'title'")
            fail_count += 1
            continue

        print(f"Creating [{idx}/{len(issues)}]: \"{title}\"...")
        success, result = create_github_issue(title, body, assignee, labels, milestone)
        
        if success:
            print(f"  ✅ Success! Created: {result}")
            success_count += 1
        else:
            print(f"  ❌ Failed: {result}")
            fail_count += 1

    print("\n========================================")
    print(f"📊 Summary: {success_count} created successfully, {fail_count} failed.")
    print("========================================")

if __name__ == "__main__":
    main()
