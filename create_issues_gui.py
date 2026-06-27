import os
import json
import subprocess
import threading
import sys
import webbrowser
import random
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Premium Color Palette (Dark Mode - Catppuccin Mocha inspired)
BG_COLOR = "#1e1e2e"         # Base background
CARD_COLOR = "#252538"       # Secondary card/frame background
TEXT_COLOR = "#cdd6f4"       # Primary text
MUTED_TEXT = "#a6adc8"       # Muted text
ACCENT_COLOR = "#89b4fa"     # Accent light blue
ACCENT_HOVER = "#b4befe"     # Hover accent
SUCCESS_COLOR = "#a6e3a1"    # Success green
ERROR_COLOR = "#f38ba8"      # Error red
BORDER_COLOR = "#313244"     # Subtly lighter border

DEFAULT_LABELS = [
    {"name": "bug", "color": "d73a4a", "description": "Something isn't working"},
    {"name": "duplicate", "color": "cfd3d7", "description": "This issue or pull request already exists"},
    {"name": "enhancement", "color": "a2eeef", "description": "New feature or request"},
    {"name": "good first issue", "color": "7057ff", "description": "Good for newcomers"},
    {"name": "help wanted", "color": "008672", "description": "Extra attention is needed"},
    {"name": "invalid", "color": "e4e669", "description": "This doesn't seem right"},
    {"name": "question", "color": "d876e3", "description": "Further information is requested"},
    {"name": "wontfix", "color": "ffffff", "description": "This will not be worked on"}
]

PRESET_COLORS = ["89b4fa", "b4befe", "a6e3a1", "f38ba8", "f9e2af", "fab387", "cba6f7", "f5c2e7"]

def get_contrast_color(hex_color):
    """Calculates black or white contrast color for a given hex background."""
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#000000" if luminance > 0.5 else "#ffffff"
    except Exception:
        return "#ffffff"

class GitHubIssueApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub Bulk Issue Creator")
        self.root.geometry("1150x700")
        self.root.configure(bg=BG_COLOR)
        
        self.root.minsize(1000, 600)

        # Set Custom Style
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        self.style.configure(".", background=BG_COLOR, foreground=TEXT_COLOR, fieldbackground=CARD_COLOR)
        self.style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=ACCENT_COLOR)
        self.style.configure("Sub.TLabel", font=("Segoe UI", 9, "italic"), foreground=MUTED_TEXT)
        
        self.style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=CARD_COLOR, foreground=TEXT_COLOR, padding=8, font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", BG_COLOR)], foreground=[("selected", ACCENT_COLOR)])

        self.style.configure("TButton", background=CARD_COLOR, foreground=TEXT_COLOR, bordercolor=BORDER_COLOR, font=("Segoe UI", 10), focuscolor=ACCENT_COLOR, padding=6)
        self.style.map("TButton",
            background=[("active", ACCENT_COLOR), ("pressed", ACCENT_HOVER)],
            foreground=[("active", BG_COLOR), ("pressed", BG_COLOR)]
        )

        self.style.configure("Accent.TButton", background=ACCENT_COLOR, foreground=BG_COLOR, font=("Segoe UI", 11, "bold"), padding=8)
        self.style.map("Accent.TButton",
            background=[("active", ACCENT_HOVER), ("pressed", ACCENT_COLOR)],
            foreground=[("active", BG_COLOR), ("pressed", BG_COLOR)]
        )

        self.style.configure("Treeview", 
            background=CARD_COLOR, 
            foreground=TEXT_COLOR, 
            fieldbackground=CARD_COLOR, 
            rowheight=25, 
            font=("Segoe UI", 9)
        )
        self.style.map("Treeview", background=[("selected", ACCENT_COLOR)], foreground=[("selected", BG_COLOR)])
        self.style.configure("Treeview.Heading", background=BORDER_COLOR, foreground=TEXT_COLOR, bordercolor=BORDER_COLOR, font=("Segoe UI", 10, "bold"))

        # State Variables
        self.issues_list = []
        self.json_file_path = "issues.json"
        self.is_authenticated = False
        
        self.collaborators = ["@me"]
        self.assignee_vars = {}
        
        self.available_labels_data = list(DEFAULT_LABELS)
        self.label_vars = {}
        
        self.remote_issues_data = {}
        self.global_click_bind_id = None

        # Draw Layout
        self.build_ui()
        
        # Initial Checks
        self.check_auth_async()
        self.fetch_collaborators_async()
        self.fetch_labels_async()
        # Do NOT auto-load — table starts empty

    def build_ui(self):
        # 1. TOP HEADER BANNER
        header_frame = tk.Frame(self.root, bg=BG_COLOR, padx=15, pady=10)
        header_frame.pack(fill=tk.X)
        
        title_lbl = ttk.Label(header_frame, text="GitHub Bulk Issue Creator", style="Header.TLabel")
        title_lbl.pack(side=tk.LEFT)
        
        self.auth_lbl = tk.Label(header_frame, text="Checking GitHub Auth Status...", bg=BG_COLOR, fg=MUTED_TEXT, font=("Segoe UI", 10, "bold"))
        self.auth_lbl.pack(side=tk.RIGHT, padx=10)

        sep = tk.Frame(self.root, height=1, bg=BORDER_COLOR)
        sep.pack(fill=tk.X, padx=15)

        # 2. TAB CONTROL SYSTEM
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        self.tab_local = tk.Frame(self.notebook, bg=BG_COLOR)
        self.notebook.add(self.tab_local, text=" Local Issue Drafts ")

        self.tab_remote = tk.Frame(self.notebook, bg=BG_COLOR)
        self.notebook.add(self.tab_remote, text=" GitHub Active Issues ")

        # --- TAB 1 CONTENT (LOCAL DRAFTS QUEUE) ---
        main_container = tk.Frame(self.tab_local, bg=BG_COLOR, pady=10)
        main_container.pack(fill=tk.BOTH, expand=True)

        # --- LEFT PANEL: ISSUE EDITOR FORM ---
        left_panel = tk.Frame(main_container, bg=BG_COLOR, width=330)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        form_title = ttk.Label(left_panel, text="Issue Details Editor", font=("Segoe UI", 12, "bold"))
        form_title.pack(anchor=tk.W, pady=(0, 10))

        # Title Field
        ttk.Label(left_panel, text="Issue Title:").pack(anchor=tk.W)
        self.title_entry = tk.Entry(left_panel, bg=CARD_COLOR, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief=tk.FLAT, font=("Segoe UI", 10))
        self.title_entry.pack(fill=tk.X, pady=(2, 6), ipady=4)

        # Body Field
        ttk.Label(left_panel, text="Description (Body):").pack(anchor=tk.W)
        self.body_text = tk.Text(left_panel, bg=CARD_COLOR, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief=tk.FLAT, font=("Segoe UI", 9), height=5)
        self.body_text.pack(fill=tk.X, pady=(2, 6))

        # Assignee Field (Multi-select Checkboxes)
        ttk.Label(left_panel, text="Assignee(s) (Select multiple):").pack(anchor=tk.W)
        self.assignee_container = tk.Frame(left_panel, bg=CARD_COLOR, bd=1, relief=tk.FLAT, height=85)
        self.assignee_container.pack(fill=tk.X, pady=(2, 6))
        self.assignee_container.pack_propagate(False)
        
        self.assignee_canvas = tk.Canvas(self.assignee_container, bg=CARD_COLOR, bd=0, highlightthickness=0)
        self.assignee_scrollbar = ttk.Scrollbar(self.assignee_container, orient="vertical", command=self.assignee_canvas.yview)
        self.assignee_scroll_frame = tk.Frame(self.assignee_canvas, bg=CARD_COLOR)
        
        self.assignee_scroll_frame.bind(
            "<Configure>",
            lambda e: self.assignee_canvas.configure(
                scrollregion=self.assignee_canvas.bbox("all")
            )
        )
        
        self.assignee_canvas.create_window((0, 0), window=self.assignee_scroll_frame, anchor="nw")
        self.assignee_canvas.configure(yscrollcommand=self.assignee_scrollbar.set)
        
        self.assignee_canvas.pack(side="left", fill="both", expand=True)
        self.assignee_scrollbar.pack(side="right", fill="y")
        
        self.rebuild_assignee_checkboxes()

        # Labels Header with Settings gear icon representation
        labels_header_frame = tk.Frame(left_panel, bg=BG_COLOR)
        labels_header_frame.pack(fill=tk.X, pady=(4, 2))
        ttk.Label(labels_header_frame, text="Labels").pack(side=tk.LEFT)
        
        # Trigger button that looks like GitHub settings gear/dropdown box
        self.labels_trigger_btn = tk.Button(
            labels_header_frame, 
            text="⚙️", 
            bg=BG_COLOR, 
            fg=MUTED_TEXT, 
            activebackground=BG_COLOR, 
            activeforeground=ACCENT_COLOR,
            relief=tk.FLAT, 
            font=("Segoe UI", 10, "bold"),
            bd=0,
            command=self.toggle_labels_popup
        )
        self.labels_trigger_btn.pack(side=tk.RIGHT)

        # Labels Container Box (Clickable, displays selected labels as badges/pills)
        self.labels_display_frame = tk.Frame(left_panel, bg=CARD_COLOR, bd=1, relief=tk.FLAT, height=65, padx=5, pady=5)
        self.labels_display_frame.pack(fill=tk.X, pady=(0, 6))
        self.labels_display_frame.pack_propagate(False)
        
        # Make the box itself open the dropdown too
        self.labels_display_frame.bind("<Button-1>", self.toggle_labels_popup)
        
        self.update_labels_pills()

        # Add custom label input
        custom_label_frame = tk.Frame(left_panel, bg=BG_COLOR)
        custom_label_frame.pack(fill=tk.X, pady=(2, 12))
        
        self.custom_label_entry = tk.Entry(custom_label_frame, bg=CARD_COLOR, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1, relief=tk.FLAT, font=("Segoe UI", 9))
        self.custom_label_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        self.custom_label_entry.insert(0, "Add custom label...")
        self.custom_label_entry.bind("<FocusIn>", lambda e: self.custom_label_entry.delete(0, tk.END) if self.custom_label_entry.get() == "Add custom label..." else None)
        self.custom_label_entry.bind("<FocusOut>", lambda e: self.custom_label_entry.insert(0, "Add custom label...") if self.custom_label_entry.get() == "" else None)
        
        add_lbl_btn = ttk.Button(custom_label_frame, text="+", width=3, command=self.add_custom_label)
        add_lbl_btn.pack(side=tk.RIGHT, padx=(3, 0))

        # Form Buttons
        btn_frame = tk.Frame(left_panel, bg=BG_COLOR)
        btn_frame.pack(fill=tk.X)
        
        self.add_new_btn = ttk.Button(btn_frame, text="🚀 Add as New Issue", style="Accent.TButton", command=self.add_new_issue)
        self.add_new_btn.pack(fill=tk.X, pady=(0, 5))
        
        row2_frame = tk.Frame(btn_frame, bg=BG_COLOR)
        row2_frame.pack(fill=tk.X)
        
        self.update_btn = ttk.Button(row2_frame, text="Update Selected", command=self.update_selected_issue)
        self.update_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        self.clear_btn = ttk.Button(row2_frame, text="Clear Form", command=self.clear_form)
        self.clear_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

        # --- RIGHT PANEL: TABLE LIST ---
        right_panel = tk.Frame(main_container, bg=BG_COLOR)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        list_header_frame = tk.Frame(right_panel, bg=BG_COLOR)
        list_header_frame.pack(fill=tk.X, pady=(0, 5))

        list_title = ttk.Label(list_header_frame, text="Issues Queue List", font=("Segoe UI", 12, "bold"))
        list_title.pack(side=tk.LEFT)
        
        self.file_status_lbl = ttk.Label(list_header_frame, text="File: none", style="Sub.TLabel")
        self.file_status_lbl.pack(side=tk.RIGHT, padx=5)

        # Table (Treeview)
        table_frame = tk.Frame(right_panel, bg=BG_COLOR)
        table_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        columns = ("Index", "Title", "Assignee", "Labels", "Status", "Issue URL")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended", yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.tree.heading("Index", text="#")
        self.tree.heading("Title", text="Issue Title")
        self.tree.heading("Assignee", text="Assignee(s)")
        self.tree.heading("Labels", text="Labels")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Issue URL", text="GitHub Link")

        self.tree.column("Index", width=40, anchor=tk.CENTER)
        self.tree.column("Title", width=250, anchor=tk.W)
        self.tree.column("Assignee", width=110, anchor=tk.W)
        self.tree.column("Labels", width=140, anchor=tk.W)
        self.tree.column("Status", width=90, anchor=tk.CENTER)
        self.tree.column("Issue URL", width=200, anchor=tk.W)
        
        self.tree.pack(fill=tk.BOTH, expand=True)

        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)

        self.tree.bind("<<TreeviewSelect>>", self.on_row_selected)

        # BOTTOM CONTROL PANEL for Tab 1
        bottom_frame = tk.Frame(self.tab_local, bg=BG_COLOR, pady=10)
        bottom_frame.pack(fill=tk.X)
        
        sep2 = tk.Frame(bottom_frame, height=1, bg=BORDER_COLOR)
        sep2.pack(fill=tk.X, pady=(0, 10))

        actions_frame = tk.Frame(bottom_frame, bg=BG_COLOR)
        actions_frame.pack(fill=tk.X)

        self.load_btn = ttk.Button(actions_frame, text="Load JSON File", command=self.open_file_dialog)
        self.load_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.save_btn = ttk.Button(actions_frame, text="Save JSON File", command=self.save_file_dialog)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.delete_btn = ttk.Button(actions_frame, text="Remove Selected", command=self.delete_selected_issues)
        self.delete_btn.pack(side=tk.LEFT, padx=5)

        self.create_all_btn = ttk.Button(actions_frame, text="🚀 Create Selected Issues on GitHub", style="Accent.TButton", command=self.start_creation_thread)
        self.create_all_btn.pack(side=tk.RIGHT, padx=(5, 0))


        # --- TAB 2 CONTENT (GITHUB EXPLORER) ---
        remote_container = tk.Frame(self.tab_remote, bg=BG_COLOR, padx=15, pady=15)
        remote_container.pack(fill=tk.BOTH, expand=True)

        remote_header = tk.Frame(remote_container, bg=BG_COLOR)
        remote_header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(remote_header, text="Active Repository Issues on GitHub", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        
        remote_table_frame = tk.Frame(remote_container, bg=BG_COLOR)
        remote_table_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar_remote_y = ttk.Scrollbar(remote_table_frame, orient=tk.VERTICAL)
        scrollbar_remote_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_remote_x = ttk.Scrollbar(remote_table_frame, orient=tk.HORIZONTAL)
        scrollbar_remote_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        remote_cols = ("Number", "Title", "Assignees", "Labels", "State")
        self.remote_tree = ttk.Treeview(
            remote_table_frame, 
            columns=remote_cols, 
            show="headings", 
            selectmode="browse",
            yscrollcommand=scrollbar_remote_y.set, 
            xscrollcommand=scrollbar_remote_x.set
        )
        
        self.remote_tree.heading("Number", text="Issue #")
        self.remote_tree.heading("Title", text="Issue Title")
        self.remote_tree.heading("Assignees", text="Assignee(s)")
        self.remote_tree.heading("Labels", text="Labels")
        self.remote_tree.heading("State", text="Status")
        
        self.remote_tree.column("Number", width=80, anchor=tk.CENTER)
        self.remote_tree.column("Title", width=380, anchor=tk.W)
        self.remote_tree.column("Assignees", width=180, anchor=tk.W)
        self.remote_tree.column("Labels", width=220, anchor=tk.W)
        self.remote_tree.column("State", width=95, anchor=tk.CENTER)
        
        self.remote_tree.pack(fill=tk.BOTH, expand=True)
        
        scrollbar_remote_y.config(command=self.remote_tree.yview)
        scrollbar_remote_x.config(command=self.remote_tree.xview)
        
        self.remote_tree.bind("<Double-1>", lambda e: self.open_remote_issue_in_browser())

        remote_bottom = tk.Frame(remote_container, bg=BG_COLOR, pady=10)
        remote_bottom.pack(fill=tk.X)
        
        sep_remote = tk.Frame(remote_bottom, height=1, bg=BORDER_COLOR)
        sep_remote.pack(fill=tk.X, pady=(0, 10))
        
        self.refresh_remote_btn = ttk.Button(remote_bottom, text="🔄 Refresh Active Issues", command=self.fetch_remote_issues_async)
        self.refresh_remote_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.open_browser_btn = ttk.Button(remote_bottom, text="🌐 Open Selected in Browser", command=self.open_remote_issue_in_browser)
        self.open_browser_btn.pack(side=tk.LEFT, padx=5)

    # --- INITIAL LOADERS & AUTHS ---

    def check_auth_async(self):
        """Runs authentication status check in a separate thread so GUI doesn't hang."""
        def run_check():
            try:
                subprocess.run(["gh", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.set_auth_status("❌ gh CLI not found in PATH", False)
                return

            try:
                result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
                if result.returncode == 0:
                    username = "Logged In"
                    for line in result.stderr.splitlines() + result.stdout.splitlines():
                        if "Logged in to github.com as" in line:
                            username = line.split("as")[-1].strip().split(" ")[0]
                            break
                    self.set_auth_status(f"✅ GitHub Connected ({username})", True)
                    self.fetch_remote_issues_async()
                else:
                    self.set_auth_status("❌ GitHub Not Authenticated ('gh auth login' required)", False)
            except Exception:
                self.set_auth_status("⚠️ Auth check failed", False)

        threading.Thread(target=run_check, daemon=True).start()

    def set_auth_status(self, text, is_ok):
        self.is_authenticated = is_ok
        color = SUCCESS_COLOR if is_ok else ERROR_COLOR
        self.auth_lbl.config(text=text, fg=color)

    # --- ASYNC API DATA FETCHING ---

    def fetch_collaborators_async(self):
        """Fetches collaborators from GitHub in a background thread."""
        def run_fetch():
            try:
                cmd = ["gh", "api", "repos/:owner/:repo/collaborators", "--jq", ".[].login"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                collabs = [c.strip() for c in result.stdout.splitlines() if c.strip()]
                if collabs:
                    new_collabs = ["@me"] + [c for c in collabs if c != "@me"]
                    self.root.after(0, self.update_collaborators_list, new_collabs)
            except Exception as e:
                print(f"Note: Could not fetch collaborators: {e}")

        threading.Thread(target=run_fetch, daemon=True).start()

    def update_collaborators_list(self, collab_list):
        self.collaborators = collab_list
        self.rebuild_assignee_checkboxes()

    def fetch_labels_async(self):
        """Fetches existing labels (including description and colors) from GitHub repository in a background thread."""
        def run_fetch():
            try:
                cmd = ["gh", "api", "repos/:owner/:repo/labels"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                labels_raw = json.loads(result.stdout)
                
                fetched_data = []
                for item in labels_raw:
                    fetched_data.append({
                        "name": item.get("name"),
                        "color": item.get("color"),
                        "description": item.get("description", "")
                    })
                
                if fetched_data:
                    self.root.after(0, self.update_labels_list, fetched_data)
            except Exception as e:
                print(f"Note: Could not fetch labels from repository: {e}")

        threading.Thread(target=run_fetch, daemon=True).start()

    def update_labels_list(self, label_data_list):
        # Merge fetched labels with defaults to avoid losing items
        seen_names = {l["name"] for l in label_data_list}
        merged_list = list(label_data_list)
        
        for default in DEFAULT_LABELS:
            if default["name"] not in seen_names:
                merged_list.append(default)
                
        # Sort alphabetically by label name
        self.available_labels_data = sorted(merged_list, key=lambda x: x["name"])
        self.update_labels_pills()

    def fetch_remote_issues_async(self):
        """Fetches active GitHub issues in a background thread."""
        self.refresh_remote_btn.config(state=tk.DISABLED)
        
        def run_fetch():
            try:
                cmd = ["gh", "issue", "list", "--limit", "100", "--json", "number,title,assignees,labels,state,url"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                issues = json.loads(result.stdout)
                self.root.after(0, self.update_remote_issues_table, issues)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Fetch Error", f"Could not fetch issues from GitHub:\n{e}"))
                self.root.after(0, lambda: self.refresh_remote_btn.config(state=tk.NORMAL))

        threading.Thread(target=run_fetch, daemon=True).start()

    def update_remote_issues_table(self, issues):
        self.refresh_remote_btn.config(state=tk.NORMAL)
        
        for row in self.remote_tree.get_children():
            self.remote_tree.delete(row)
            
        self.remote_issues_data = {}
        
        for issue in issues:
            num = issue.get("number")
            title = issue.get("title", "")
            state = issue.get("state", "")
            url = issue.get("url", "")
            
            self.remote_issues_data[num] = url
            
            assignees = ", ".join([a["login"] for a in issue.get("assignees", [])])
            labels = ", ".join([l["name"] for l in issue.get("labels", [])])
            
            self.remote_tree.insert("", tk.END, values=(
                f"#{num}",
                title,
                assignees or "Unassigned",
                labels or "None",
                state
            ))

    def open_remote_issue_in_browser(self):
        selected = self.remote_tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select an issue from the list.")
            return
            
        row_values = self.remote_tree.item(selected[0], "values")
        if not row_values:
            return
            
        try:
            num = int(row_values[0].replace("#", ""))
            url = self.remote_issues_data.get(num)
            if url:
                webbrowser.open(url)
            else:
                messagebox.showerror("Error", "Could not find URL for this issue.")
        except ValueError:
            pass

    # --- UI CHECKBOX BUILDERS ---

    def rebuild_assignee_checkboxes(self):
        for child in self.assignee_scroll_frame.winfo_children():
            child.destroy()
            
        current_checked = {name for name, var in self.assignee_vars.items() if var.get()}
        self.assignee_vars = {}
        
        seen = set()
        unique_collabs = []
        for c in self.collaborators:
            if c not in seen:
                seen.add(c)
                unique_collabs.append(c)
        self.collaborators = unique_collabs
        
        for username in self.collaborators:
            var = tk.BooleanVar()
            if username in current_checked:
                var.set(True)
            self.assignee_vars[username] = var
            
            cb = tk.Checkbutton(
                self.assignee_scroll_frame,
                text=username,
                variable=var,
                bg=CARD_COLOR,
                fg=TEXT_COLOR,
                activebackground=CARD_COLOR,
                activeforeground=TEXT_COLOR,
                anchor="w",
                padx=5,
                pady=1,
                font=("Segoe UI", 9)
            )
            cb.pack(fill="x", anchor="w", expand=True)
            
        self.root.update_idletasks()
        self.assignee_canvas.configure(scrollregion=self.assignee_canvas.bbox("all"))

    # --- DYNAMIC GITHUB-LIKE DROPDOWN CHECKLIST ---

    def toggle_labels_popup(self, event=None):
        # If already open, close it
        if hasattr(self, "labels_popup") and self.labels_popup.winfo_exists():
            self.labels_popup.destroy()
            return

        self.labels_popup = tk.Toplevel(self.root)
        self.labels_popup.overrideredirect(True)
        self.labels_popup.configure(bg=CARD_COLOR, bd=1, relief=tk.SOLID)

        # Position below the display frame
        self.root.update_idletasks()
        x = self.labels_display_frame.winfo_rootx()
        y = self.labels_display_frame.winfo_rooty() + self.labels_display_frame.winfo_height()
        width = max(self.labels_display_frame.winfo_width(), 280)

        self.labels_popup.geometry(f"{width}x310+{x}+{y}")
        self.labels_popup.lift()

        # 1. Header row with title + close button
        header_bar = tk.Frame(self.labels_popup, bg=CARD_COLOR, padx=8, pady=6)
        header_bar.pack(fill="x")

        tk.Label(header_bar, text="Apply labels to this issue",
                 bg=CARD_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 9, "bold")).pack(side="left")

        close_x = tk.Label(header_bar, text="×", bg=CARD_COLOR, fg=MUTED_TEXT,
                            font=("Segoe UI", 14, "bold"), cursor="hand2")
        close_x.pack(side="right")
        close_x.bind("<Button-1>", lambda e: self.labels_popup.destroy())

        # 2. Search bar
        search_frame = tk.Frame(self.labels_popup, bg=CARD_COLOR, padx=8, pady=4)
        search_frame.pack(fill="x")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.filter_labels_popup())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                bg=BG_COLOR, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
                                bd=1, relief=tk.SOLID, highlightthickness=0, font=("Segoe UI", 9))
        search_entry.pack(fill="x", ipady=3)
        search_entry.focus_set()

        # Separator
        tk.Frame(self.labels_popup, height=1, bg=BORDER_COLOR).pack(fill="x")

        # 3. Scrollable label list
        list_container = tk.Frame(self.labels_popup, bg=CARD_COLOR)
        list_container.pack(fill="both", expand=True)

        self.labels_canvas = tk.Canvas(list_container, bg=CARD_COLOR, bd=0, highlightthickness=0)
        self.labels_scrollbar = ttk.Scrollbar(list_container, orient="vertical",
                                              command=self.labels_canvas.yview)
        self.labels_scroll_frame = tk.Frame(self.labels_canvas, bg=CARD_COLOR)

        self.labels_scroll_frame.bind(
            "<Configure>",
            lambda e: self.labels_canvas.configure(scrollregion=self.labels_canvas.bbox("all"))
        )
        self.labels_canvas.create_window((0, 0), window=self.labels_scroll_frame, anchor="nw")
        self.labels_canvas.configure(yscrollcommand=self.labels_scrollbar.set)
        self.labels_canvas.pack(side="left", fill="both", expand=True)
        self.labels_scrollbar.pack(side="right", fill="y")

        # Mousewheel scrolling
        def on_mousewheel(e):
            self.labels_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        self.labels_canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Populate rows — ONLY Checkbutton handles toggle (no extra row bindings)
        self.label_widget_rows = {}
        for item in self.available_labels_data:
            name = item["name"]
            color_hex = item["color"]
            description = item.get("description", "")

            if name not in self.label_vars:
                self.label_vars[name] = tk.BooleanVar(value=False)
            var = self.label_vars[name]

            row_frame = tk.Frame(self.labels_scroll_frame, bg=CARD_COLOR, pady=2, cursor="hand2")
            row_frame.pack(fill="x", padx=4)
            self.label_widget_rows[name] = row_frame

            # Checkbutton — sole owner of the toggle
            cb = tk.Checkbutton(row_frame, variable=var,
                                bg=CARD_COLOR, activebackground=CARD_COLOR,
                                bd=0, highlightthickness=0,
                                command=self.update_labels_pills)
            cb.pack(side="left", padx=(4, 2))

            # Color dot
            dot = tk.Canvas(row_frame, width=12, height=12, bg=CARD_COLOR,
                            bd=0, highlightthickness=0)
            dot.create_oval(1, 1, 11, 11, fill=f"#{color_hex}", outline="")
            dot.pack(side="left", padx=4)

            # Name + description — clicking these fires the checkbutton invoke
            text_frame = tk.Frame(row_frame, bg=CARD_COLOR)
            text_frame.pack(side="left", fill="both", expand=True, padx=4)

            name_lbl = tk.Label(text_frame, text=name, bg=CARD_COLOR, fg=TEXT_COLOR,
                                font=("Segoe UI", 9, "bold"), anchor="w", cursor="hand2")
            name_lbl.pack(anchor="w")
            # Clicking name/description invokes the checkbox (safe, no double-fire)
            name_lbl.bind("<Button-1>", lambda e, c=cb: c.invoke())

            if description:
                desc_lbl = tk.Label(text_frame, text=description, bg=CARD_COLOR, fg=MUTED_TEXT,
                                    font=("Segoe UI", 8), anchor="w", cursor="hand2")
                desc_lbl.pack(anchor="w")
                desc_lbl.bind("<Button-1>", lambda e, c=cb: c.invoke())

            # Clicking the row background also invokes checkbox
            row_frame.bind("<Button-1>", lambda e, c=cb: c.invoke())
            dot.bind("<Button-1>", lambda e, c=cb: c.invoke())
            text_frame.bind("<Button-1>", lambda e, c=cb: c.invoke())

        # Close popup when clicking outside — use after() to avoid same-click close
        def check_outside(e):
            if not hasattr(self, "labels_popup") or not self.labels_popup.winfo_exists():
                return
            try:
                pw = self.labels_popup.winfo_rootx(), self.labels_popup.winfo_rooty(), \
                     self.labels_popup.winfo_width(), self.labels_popup.winfo_height()
                if not (pw[0] <= e.x_root <= pw[0]+pw[2] and pw[1] <= e.y_root <= pw[1]+pw[3]):
                    bx = self.labels_trigger_btn.winfo_rootx()
                    by = self.labels_trigger_btn.winfo_rooty()
                    bw = self.labels_trigger_btn.winfo_width()
                    bh = self.labels_trigger_btn.winfo_height()
                    if not (bx <= e.x_root <= bx+bw and by <= e.y_root <= by+bh):
                        self.labels_popup.destroy()
            except Exception:
                pass

        self.labels_popup.after(100, lambda: self.root.bind("<Button-1>", check_outside))
        self.labels_popup.bind("<Destroy>", lambda e: self._unbind_outside_click())

    def _unbind_outside_click(self):
        try:
            self.root.unbind("<Button-1>")
        except Exception:
            pass

    def destroy_labels_popup(self):
        if hasattr(self, "labels_popup") and self.labels_popup.winfo_exists():
            self.labels_popup.destroy()
        self._unbind_outside_click()
        self.global_click_bind_id = None

    def bind_global_click(self):
        pass  # no longer used

    def on_global_click(self, event):
        pass  # no longer used

    def filter_labels_popup(self):
        query = self.search_var.get().lower().strip()
        for name, row_frame in self.label_widget_rows.items():
            if query in name.lower():
                row_frame.pack(fill="x", anchor="w", expand=True)
            else:
                row_frame.pack_forget()

    def update_labels_pills(self):
        """Draws selected labels as beautiful colored pills/badges inside the labels_display_frame."""
        for child in self.labels_display_frame.winfo_children():
            child.destroy()
            
        selected_labels = [name for name, var in self.label_vars.items() if var.get()]
        
        if not selected_labels:
            lbl = tk.Label(self.labels_display_frame, text="None yet", bg=CARD_COLOR, fg=MUTED_TEXT, font=("Segoe UI", 9, "italic"))
            lbl.pack(anchor="w", padx=5, pady=15)
            # Rebind click event
            lbl.bind("<Button-1>", self.toggle_labels_popup)
            return

        # Container for horizontal display with wrap support
        row_frame = tk.Frame(self.labels_display_frame, bg=CARD_COLOR)
        row_frame.pack(fill="x", anchor="w")
        row_frame.bind("<Button-1>", self.toggle_labels_popup)
        
        char_count = 0
        for name in selected_labels:
            # Simple wrapping logic based on character lengths
            char_count += len(name) + 3
            if char_count > 25:
                row_frame = tk.Frame(self.labels_display_frame, bg=CARD_COLOR)
                row_frame.pack(fill="x", anchor="w")
                row_frame.bind("<Button-1>", self.toggle_labels_popup)
                char_count = len(name)
                
            color_hex = "cfd3d7"
            for item in self.available_labels_data:
                if item["name"] == name:
                    color_hex = item["color"]
                    break
                    
            bg_color = f"#{color_hex}"
            fg_color = get_contrast_color(color_hex)
            
            # Render pill
            pill = tk.Frame(row_frame, bg=bg_color, padx=6, pady=2)
            pill.pack(side="left", padx=3, pady=2)
            pill.bind("<Button-1>", self.toggle_labels_popup)
            
            pill_lbl = tk.Label(pill, text=name, bg=bg_color, fg=fg_color, font=("Segoe UI", 8, "bold"))
            pill_lbl.pack()
            pill_lbl.bind("<Button-1>", self.toggle_labels_popup)

    def add_custom_label(self):
        label = self.custom_label_entry.get().strip()
        if not label or label == "Add custom label...":
            return
            
        # Check if already exists in available labels database
        exists = False
        for item in self.available_labels_data:
            if item["name"] == label:
                exists = True
                break
                
        if not exists:
            # Assign a nice random Catppuccin color preset
            random_color = random.choice(PRESET_COLORS)
            self.available_labels_data.append({
                "name": label,
                "color": random_color,
                "description": "User created label"
            })
            self.available_labels_data.sort(key=lambda x: x["name"])
            
        if label not in self.label_vars:
            self.label_vars[label] = tk.BooleanVar()
        self.label_vars[label].set(True)
        
        self.update_labels_pills()
            
        self.custom_label_entry.delete(0, tk.END)
        self.custom_label_entry.insert(0, "Add custom label...")
        self.root.focus()

    # --- UI ACTIONS / FORM HANDLERS ---

    def load_initial_json(self):
        """Called on startup — table starts empty by default."""
        self.file_status_lbl.config(text="No file loaded — use 'Load JSON File' to import")

    def load_issues(self, file_path):
        self.json_file_path = file_path
        self.file_status_lbl.config(text=f"Loaded: {os.path.basename(file_path)}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.issues_list = []
                    for item in data:
                        raw_labels = item.get("labels", [])
                        if isinstance(raw_labels, str):
                            raw_labels = [l.strip() for l in raw_labels.split(",") if l.strip()]
                        
                        self.issues_list.append({
                            "title": item.get("title", ""),
                            "body": item.get("body", ""),
                            "assignee": item.get("assignee", ""),
                            "labels": raw_labels,
                            "status": "Pending",
                            "url": ""
                        })
                    self.refresh_table()
                else:
                    messagebox.showerror("Error", "JSON file root must be a list of issues.")
        except Exception as e:
            messagebox.showerror("Error Reading File", f"Could not load JSON file:\n{e}")

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for idx, issue in enumerate(self.issues_list, start=1):
            labels_str = ", ".join(issue["labels"]) if isinstance(issue["labels"], list) else str(issue["labels"])
            self.tree.insert("", tk.END, values=(
                idx,
                issue["title"],
                issue["assignee"] or "None",
                labels_str,
                issue["status"],
                issue["url"]
            ))

    def clear_form(self):
        self.title_entry.delete(0, tk.END)
        self.body_text.delete("1.0", tk.END)
        for var in self.assignee_vars.values():
            var.set(False)
        for var in self.label_vars.values():
            var.set(False)
        self.update_labels_pills()
        self.custom_label_entry.delete(0, tk.END)
        self.custom_label_entry.insert(0, "Add custom label...")
        self.tree.selection_remove(self.tree.selection())

    def on_row_selected(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        
        item_id = selected[0]
        row_values = self.tree.item(item_id, "values")
        if not row_values:
            return
            
        index = int(row_values[0]) - 1
        issue = self.issues_list[index]

        # Fill inputs
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, issue["title"])

        self.body_text.delete("1.0", tk.END)
        self.body_text.insert("1.0", issue["body"])

        # Select Assignees
        assignees_str = issue["assignee"] or ""
        selected_assignees = [a.strip() for a in assignees_str.split(",") if a.strip()]
        
        for var in self.assignee_vars.values():
            var.set(False)
            
        needs_rebuild_assignees = False
        for assignee in selected_assignees:
            if assignee in self.assignee_vars:
                self.assignee_vars[assignee].set(True)
            else:
                self.collaborators.append(assignee)
                needs_rebuild_assignees = True
                
        if needs_rebuild_assignees:
            self.rebuild_assignee_checkboxes()
            for assignee in selected_assignees:
                if assignee in self.assignee_vars:
                    self.assignee_vars[assignee].set(True)

        # Select Labels
        labels_list = issue.get("labels", [])
        if isinstance(labels_list, str):
            labels_list = [l.strip() for l in labels_list.split(",") if l.strip()]
            
        for var in self.label_vars.values():
            var.set(False)
            
        needs_rebuild_labels = False
        for lbl in labels_list:
            # Ensure label metadata object exists
            found = False
            for item in self.available_labels_data:
                if item["name"] == lbl:
                    found = True
                    break
            
            if not found:
                self.available_labels_data.append({
                    "name": lbl,
                    "color": random.choice(PRESET_COLORS),
                    "description": "Imported label"
                })
                needs_rebuild_labels = True

            if lbl not in self.label_vars:
                self.label_vars[lbl] = tk.BooleanVar()
            self.label_vars[lbl].set(True)
                
        if needs_rebuild_labels:
            self.available_labels_data.sort(key=lambda x: x["name"])
            
        self.update_labels_pills()

    def add_new_issue(self):
        title = self.title_entry.get().strip()
        body = self.body_text.get("1.0", tk.END).strip()
        
        if not title:
            messagebox.showwarning("Validation Error", "Issue Title is required!")
            return

        # Collect checked assignees
        assignees = [name for name, var in self.assignee_vars.items() if var.get()]
        assignee = ",".join(assignees)
        
        # Collect checked labels
        labels = [name for name, var in self.label_vars.items() if var.get()]

        # Always append a new draft
        self.issues_list.append({
            "title": title,
            "body": body,
            "assignee": assignee,
            "labels": labels,
            "status": "Pending",
            "url": ""
        })

        self.refresh_table()
        self.clear_form()

    def update_selected_issue(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select an issue from the list to update.")
            return
            
        title = self.title_entry.get().strip()
        body = self.body_text.get("1.0", tk.END).strip()
        
        if not title:
            messagebox.showwarning("Validation Error", "Issue Title is required!")
            return

        # Collect checked assignees
        assignees = [name for name, var in self.assignee_vars.items() if var.get()]
        assignee = ",".join(assignees)
        
        # Collect checked labels
        labels = [name for name, var in self.label_vars.items() if var.get()]

        item_id = selected[0]
        index = int(self.tree.item(item_id, "values")[0]) - 1
        
        self.issues_list[index]["title"] = title
        self.issues_list[index]["body"] = body
        self.issues_list[index]["assignee"] = assignee
        self.issues_list[index]["labels"] = labels

        self.refresh_table()
        self.clear_form()

    def delete_selected_issues(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select one or more rows from the list to remove.")
            return

        indices = sorted([int(self.tree.item(x, "values")[0]) - 1 for x in selected], reverse=True)
        for index in indices:
            self.issues_list.pop(index)

        self.refresh_table()
        self.clear_form()

    def open_file_dialog(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if file_path:
            self.load_issues(file_path)

    def save_file_dialog(self):
        file_path = filedialog.asksaveasfilename(
            defaulttextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=os.path.basename(self.json_file_path)
        )
        if file_path:
            try:
                out_data = []
                for issue in self.issues_list:
                    out_data.append({
                        "title": issue["title"],
                        "body": issue["body"],
                        "assignee": issue["assignee"],
                        "labels": issue["labels"]
                    })
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(out_data, f, indent=2, ensure_ascii=False)
                self.json_file_path = file_path
                self.file_status_lbl.config(text=f"Loaded: {os.path.basename(file_path)}")
                messagebox.showinfo("Success", f"Saved list to {file_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save JSON file:\n{e}")

    # --- BG THREAD: SUBPROCESS ISSUES INTEGRATION ---

    def start_creation_thread(self):
        selected = self.tree.selection()
        if not selected:
            response = messagebox.askyesno("Create Issues", "No specific items selected in the list. Do you want to process ALL pending issues?")
            if not response:
                return
            indices = list(range(len(self.issues_list)))
        else:
            indices = [int(self.tree.item(x, "values")[0]) - 1 for x in selected]

        if not self.is_authenticated:
            response = messagebox.askyesno("Auth Warning", "GitHub CLI is not verified as logged in. The commands might fail.\nDo you still want to proceed?")
            if not response:
                return

        self.create_all_btn.config(state=tk.DISABLED)
        self.load_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self.delete_btn.config(state=tk.DISABLED)
        self.add_new_btn.config(state=tk.DISABLED)
        self.update_btn.config(state=tk.DISABLED)

        thread = threading.Thread(target=self.process_issue_creation, args=(indices,), daemon=True)
        thread.start()

    def process_issue_creation(self, indices_to_create):
        # 1. Fetch existing labels on GitHub to verify what needs to be created
        existing_labels = set()
        try:
            cmd = ["gh", "api", "repos/:owner/:repo/labels", "--jq", ".[].name"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            existing_labels = {l.strip() for l in result.stdout.splitlines() if l.strip()}
        except Exception as e:
            # Fallback to defaults if API call fails
            existing_labels = {l["name"] for l in DEFAULT_LABELS}

        for idx in indices_to_create:
            issue = self.issues_list[idx]
            
            if "Created" in issue["status"]:
                continue

            self.update_row_status(idx, "Creating...", "")

            # 2. Check and auto-create missing labels on GitHub
            if issue["labels"]:
                for label in issue["labels"]:
                    if label not in existing_labels:
                        # Find color and description
                        color = random.choice(PRESET_COLORS)
                        desc = "Auto-created label"
                        for item in self.available_labels_data:
                            if item["name"] == label:
                                color = item["color"]
                                desc = item.get("description", "Auto-created label")
                                break
                        # Run gh label create
                        try:
                            subprocess.run([
                                "gh", "label", "create", label, 
                                "--color", color, 
                                "--description", desc
                            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                            existing_labels.add(label)
                        except Exception as e:
                            print(f"Note: Could not create missing label '{label}' on GitHub: {e}")

            # 3. Create the issue
            cmd = ["gh", "issue", "create", "--title", issue["title"], "--body", issue["body"]]
            
            # Add each assignee separately to allow partial failures
            valid_assignees = []
            if issue["assignee"]:
                for assignee in [a.strip() for a in issue["assignee"].split(",") if a.strip()]:
                    valid_assignees.append(assignee)
                    cmd.extend(["--assignee", assignee])
            
            if issue["labels"]:
                labels_str = ",".join(issue["labels"]) if isinstance(issue["labels"], list) else str(issue["labels"])
                cmd.extend(["--label", labels_str])

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                issue_url = result.stdout.strip()
                self.update_row_status(idx, "✅ Created", issue_url)
            except subprocess.CalledProcessError as e:
                err_msg = e.stderr.strip() or e.stdout.strip() or "CLI Error"
                # If assignee caused failure, retry without assignee
                if valid_assignees and ("assignee" in err_msg.lower() or "could not resolve" in err_msg.lower() or "invalid" in err_msg.lower()):
                    retry_cmd = ["gh", "issue", "create", "--title", issue["title"], "--body", issue["body"]]
                    if issue["labels"]:
                        labels_str = ",".join(issue["labels"]) if isinstance(issue["labels"], list) else str(issue["labels"])
                        retry_cmd.extend(["--label", labels_str])
                    try:
                        result = subprocess.run(retry_cmd, capture_output=True, text=True, check=True)
                        issue_url = result.stdout.strip()
                        self.update_row_status(idx, "⚠️ Created (no assignee)", issue_url)
                    except subprocess.CalledProcessError as e2:
                        err_msg2 = e2.stderr.strip() or e2.stdout.strip() or "CLI Error"
                        self.update_row_status(idx, "❌ Failed", f"Error: {err_msg2}")
                else:
                    self.update_row_status(idx, "❌ Failed", f"Error: {err_msg}")
            except Exception as e:
                self.update_row_status(idx, "❌ Failed", f"Exception: {str(e)}")

        self.root.after(0, self.cleanup_after_process)
        self.root.after(0, self.fetch_remote_issues_async)

    def update_row_status(self, index, status, url):
        self.issues_list[index]["status"] = status
        self.issues_list[index]["url"] = url
        self.root.after(0, self.refresh_table)

    def cleanup_after_process(self):
        self.create_all_btn.config(state=tk.NORMAL)
        self.load_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)
        self.delete_btn.config(state=tk.NORMAL)
        self.add_new_btn.config(state=tk.NORMAL)
        self.update_btn.config(state=tk.NORMAL)
        messagebox.showinfo("Processing Finished", "Finished processing selected issue creation jobs!")

if __name__ == "__main__":
    root = tk.Tk()
    app = GitHubIssueApp(root)
    root.mainloop()
