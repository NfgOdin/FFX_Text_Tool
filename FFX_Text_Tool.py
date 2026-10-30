import os
import sys
import csv
import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import struct
import webbrowser

APP_VERSION = "v1.2.0"
AUTHOR = "NfgOdin"
WEBSITE_URL = "https://nfgodin.github.io/"

# Add current folder to sys.path to load ffx_codec
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

try:
    from ffx_codec import FFXCodec, FILE_RECORD_SIZES
except ImportError:
    # Fallback to copy the record size dictionary locally if import fails
    FILE_RECORD_SIZES = {
        "item_txt.bin": 16, "arms_txt.bin": 16, "status_txt.bin": 16, "summon_txt.bin": 16,
        "config_txt.bin": 16, "menu_txt.bin": 16, "mmain_txt.bin": 16, "name_txt.bin": 16,
        "save_txt.bin": 16, "btlend_txt.bin": 16, "btl_txt.bin": 16, "build_txt.bin": 16,
        "help_txt.bin": 16, "item.bin": 92, "command.bin": 92, "monmagic1.bin": 92,
        "monmagic2.bin": 92, "important.bin": 20, "panel.bin": 16, "a_ability.bin": 16,
        "monster1.bin": 128, "monster2.bin": 128, "monster3.bin": 128,
        "ply_save.bin": 148, "w_name.bin": 72, "ply_rom.bin": 44, "sphere.bin": 16,
    }

CONFIG_FILE = os.path.join(script_dir, "ffx_text_tool_recent_files.json")

DAMAGE_FORMULAS = [
    (0x00, "None"),
    (0x01, "STR vs DEF"),
    (0x02, "STR ignore DEF"),
    (0x03, "MAG vs MDF"),
    (0x04, "MAG ignore MDF"),
    (0x05, "Ratio (Current/16)"),
    (0x06, "Fixed x50"),
    (0x07, "Healing"),
    (0x08, "Max/16"),
    (0x09, "Fixed x46~53"),
    (0x0D, "Ticks/16"),
    (0x0F, "Special MAG (ignore MDF)"),
    (0x10, "Fixed x User HP / 10"),
    (0x11, "Celestial HP-based"),
    (0x12, "Celestial MP-based"),
    (0x13, "Celestial Auron"),
    (0x15, "Fixed x Gil chosen / 10"),
    (0x16, "Fixed xKills"),
    (0x17, "Fixed x9999"),
]


class ToolTip:
    """Floating modern tooltip for in-game control tags and UI elements."""
    def __init__(self, root):
        self.root = root
        self.tip_window = None
        self.current_text = ""

    def show(self, text, x, y):
        if self.tip_window and self.current_text == text:
            return
        self.hide()
        self.current_text = text
        self.tip_window = tk.Toplevel(self.root)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x+14}+{y+16}")
        self.tip_window.attributes("-topmost", True)
        
        container = tk.Frame(self.tip_window, bg="#1a1e2b", highlightbackground="#3b82f6", highlightthickness=1, padx=9, pady=5)
        container.pack()
        
        lbl = tk.Label(
            container,
            text=text,
            bg="#1a1e2b",
            fg="#f3f4f6",
            font=("Segoe UI", 9),
            justify="left"
        )
        lbl.pack()

    def hide(self):
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None
            self.current_text = ""


class FFXTextToolGUI:
    def __init__(self, parent, is_embedded=False):
        self.parent = parent
        self.is_embedded = is_embedded
        self.root = parent.winfo_toplevel() if is_embedded else parent
        
        # Modern Sleek Dark Palette
        self.bg_color = "#0e1117"
        self.card_color = "#161922"
        self.card_elevated = "#1f2432"
        self.accent_color = "#3b82f6"
        self.accent_hover = "#2563eb"
        self.text_color = "#f3f4f6"
        self.text_dim = "#9ca3af"
        self.border_color = "#282d3d"
        self.success_color = "#10b981"
        self.error_color = "#ef4444"
        self.preview_bg = "#070c18"
        self.preview_border = "#2563eb"
        
        # Tooltip Controller
        self.tag_tooltip = ToolTip(self.root)
        self.root.bind("<Button-1>", lambda e: self.tag_tooltip.hide(), add="+")
        
        if not is_embedded:
            self.root.title("FFX Text & Dialogue Editor")
            self.root.geometry("1180x760")
            self.root.minsize(960, 640)
            self.root.configure(bg=self.bg_color)
            
            ico_path = os.path.join(script_dir, "FFXTextTool.ico")
            if not os.path.exists(ico_path) and hasattr(sys, "_MEIPASS"):
                ico_path = os.path.join(sys._MEIPASS, "FFXTextTool.ico")
            if os.path.exists(ico_path):
                try:
                    self.root.iconbitmap(ico_path)
                except Exception:
                    pass
            
            # Apply TTK styles
            self.style = ttk.Style()
            self.style.theme_use("clam")
            
            self.style.configure(".", background=self.bg_color, foreground=self.text_color)
            self.style.configure("TFrame", background=self.bg_color)
            self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", 10))
            self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.accent_color)
            self.style.configure("SubHeader.TLabel", font=("Segoe UI", 10, "italic"), foreground=self.text_dim)
            self.style.configure("TEntry", fieldbackground=self.card_color, foreground=self.text_color, 
                                 bordercolor=self.border_color, lightcolor=self.border_color, darkcolor=self.border_color)
            self.style.configure("TCombobox", fieldbackground=self.card_color, background=self.card_color, 
                                 foreground=self.text_color, arrowcolor=self.accent_color, bordercolor=self.border_color)
            self.style.map("TCombobox",
                           fieldbackground=[("readonly", self.card_color), ("disabled", self.card_color)],
                           foreground=[("readonly", self.text_color), ("disabled", self.text_dim)],
                           background=[("readonly", self.card_color), ("disabled", self.card_color), ("active", self.border_color)],
                           arrowcolor=[("disabled", self.text_dim), ("!disabled", self.accent_color)],
                           bordercolor=[("focus", self.accent_color), ("!focus", self.border_color)])
            
            # Notebook tabs
            self.style.configure("TNotebook", background=self.bg_color, borderwidth=0)
            self.style.configure("TNotebook.Tab", background=self.card_color, foreground=self.text_dim, 
                                 padding=[15, 6], font=("Segoe UI", 9, "bold"), borderwidth=1, bordercolor=self.border_color)
            self.style.map("TNotebook.Tab", 
                           background=[("selected", self.accent_color), ("active", self.border_color), ("", self.card_color)],
                           foreground=[("selected", "#ffffff"), ("active", self.text_color), ("", self.text_dim)])
            
            # Scrollbar Styling
            self.style.configure("Vertical.TScrollbar", background=self.card_color, troughcolor=self.bg_color, 
                                 bordercolor=self.border_color, arrowcolor=self.accent_color,
                                 lightcolor=self.border_color, darkcolor=self.border_color)
            self.style.map("Vertical.TScrollbar",
                           background=[("active", self.accent_color), ("pressed", self.accent_color), ("", self.card_color)],
                           arrowcolor=[("active", "#ffffff"), ("", self.accent_color)])
            self.style.configure("Horizontal.TScrollbar", background=self.card_color, troughcolor=self.bg_color, 
                                 bordercolor=self.border_color, arrowcolor=self.accent_color,
                                 lightcolor=self.border_color, darkcolor=self.border_color)
            self.style.map("Horizontal.TScrollbar",
                           background=[("active", self.accent_color), ("pressed", self.accent_color), ("", self.card_color)],
                           arrowcolor=[("active", "#ffffff"), ("", self.accent_color)])

            # Treeview Styling
            self.style.configure("Treeview", background=self.card_color, fieldbackground=self.card_color, 
                                 foreground=self.text_color, borderwidth=1, bordercolor=self.border_color,
                                 font=("Segoe UI", 9), rowheight=26)
            self.style.configure("Treeview.Heading", background=self.card_elevated, foreground=self.accent_color,
                                 font=("Segoe UI", 9, "bold"), borderwidth=1, bordercolor=self.border_color)
            self.style.map("Treeview", 
                           background=[("selected", self.accent_color), ("!selected", self.card_color)],
                           foreground=[("selected", "#ffffff"), ("!selected", self.text_color)])

        # Active Data State
        self.codec = FFXCodec()
        self.records = []
        
        # Style the dropdown Listbox popup globally (white background, black text for high visibility on Windows)
        self.root.option_add("*TCombobox*Listbox.background", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.foreground", "#000000")
        self.root.option_add("*TCombobox*Listbox.selectBackground", self.accent_color)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))

        # Safeguard bind to force dropdown Listbox colors (white background, black text) on Windows
        def on_combobox_click(event):
            def configure_listbox(retries=0):
                try:
                    popdown = str(event.widget) + ".popdown"
                    listbox = popdown + ".f.l"
                    if event.widget.tk.call("winfo", "exists", listbox):
                        event.widget.tk.call(
                            listbox, "configure",
                            "-background", "#ffffff",
                            "-foreground", "#000000",
                            "-selectbackground", self.accent_color,
                            "-selectforeground", "#ffffff",
                            "-font", "{Segoe UI} 10"
                        )
                    elif retries < 10:
                        event.widget.after(20, lambda: configure_listbox(retries + 1))
                except Exception:
                    if retries < 10:
                        event.widget.after(20, lambda: configure_listbox(retries + 1))
            event.widget.after(5, configure_listbox)

        self.root.bind_class("TCombobox", "<ButtonPress-1>", on_combobox_click, add="+")
        self.root.bind_class("TCombobox", "<Down>", on_combobox_click, add="+")
        self.min_idx = 0
        self.max_idx = 0
        self.magic_part = b""
        self.active_file_path = None
        self.active_file_name = None
        
        # Load Config
        self.config = self.load_config()
        
        self.create_widgets()
        
        # Auto-detect game directory
        self.auto_detect_directory()

    def load_config(self):
        config = {"recent_files": []}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    loaded = json.load(f)
                    config.update(loaded)
            except Exception:
                pass
        return config

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def auto_detect_directory(self):
        # 1. Check saved config first
        config_path = self.config.get("master_path", "")
        if config_path and os.path.exists(config_path):
            self.ent_master_path.delete(0, tk.END)
            self.ent_master_path.insert(0, config_path)
            self.codec.ffx_master_path = config_path
            self.log(f"Loaded master folder from config: {config_path}")
            self.scan_localizations()
            return

        # 2. Fallback to auto-detect relative to script
        candidate_paths = [
            os.path.abspath(os.path.join(script_dir, "..", "VBF Browser", "Extracted", "ffx_ps2", "ffx", "master")),
            os.path.abspath(os.path.join(script_dir, "..", "VBF Browser", "extracted", "ffx_ps2", "ffx", "master")),
            os.path.abspath(os.path.join(script_dir, "..", "..", "Misc Tools", "FF10 Rando", "input", "ffx_ps2", "ffx", "master")),
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                self.ent_master_path.delete(0, tk.END)
                self.ent_master_path.insert(0, p)
                self.codec.ffx_master_path = p
                self.log(f"Auto-detected FFX extracted data folder: {p}")
                self.scan_localizations()
                return

    def log(self, text, tag=None):
        if self.is_embedded and hasattr(self.parent, "log"):
            # Redirect to unified toolbox log console
            self.parent.log(text, tag)
        else:
            # Standalone logger console print
            if hasattr(self, "txt_log") and self.txt_log:
                msg = str(text) + "\n"
                self.txt_log.insert(tk.END, msg, tag or "default")
                self.txt_log.see(tk.END)
            else:
                print(text)

    def clear_log(self):
        if self.is_embedded and hasattr(self.parent, "clear_log"):
            self.parent.clear_log()
        else:
            if hasattr(self, "txt_log") and self.txt_log:
                self.txt_log.delete("1.0", tk.END)

    def create_widgets(self):
        # Main Layout
        self.main_container = ttk.Frame(self.parent, padding=10)
        self.main_container.pack(fill="both", expand=True)
        
        # Grid layout: Top Bar, Middle Body, Bottom Console
        self.top_panel = ttk.LabelFrame(self.main_container, text=" FFX Game Directory Configuration ", padding=10)
        self.top_panel.pack(fill="x", side="top", pady=(0, 10))
        self.build_top_panel(self.top_panel)
        
        # Bottom Elements (packed first to guarantee footer & console are always pinned at the bottom and never clipped)
        if not self.is_embedded:
            # Footer underneath Process Logs (pinned at very bottom)
            self.footer_frame = ttk.Frame(self.main_container)
            self.footer_frame.pack(fill="x", side="bottom", pady=(4, 0))
            
            self.lbl_cheatsheet = tk.Label(
                self.footer_frame,
                text="📖 Tags Cheat Sheet",
                fg=self.accent_color,
                bg=self.bg_color,
                font=("Segoe UI", 9, "underline"),
                cursor="hand2"
            )
            self.lbl_cheatsheet.pack(side="right", padx=(5, 15))
            self.lbl_cheatsheet.bind("<Button-1>", lambda e: self.show_cheat_sheet_dialog())
            self.lbl_cheatsheet.bind("<Enter>", lambda e: self.lbl_cheatsheet.config(fg=self.accent_hover))
            self.lbl_cheatsheet.bind("<Leave>", lambda e: self.lbl_cheatsheet.config(fg=self.accent_color))

            self.lbl_about = tk.Label(
                self.footer_frame,
                text="About FFX Text Tool",
                fg=self.accent_color,
                bg=self.bg_color,
                font=("Segoe UI", 9, "underline"),
                cursor="hand2"
            )
            self.lbl_about.pack(side="right", padx=5)
            self.lbl_about.bind("<Button-1>", lambda e: self.show_about_dialog())
            self.lbl_about.bind("<Enter>", lambda e: self.lbl_about.config(fg=self.accent_hover))
            self.lbl_about.bind("<Leave>", lambda e: self.lbl_about.config(fg=self.accent_color))

            # Process Logs Console (pinned above footer, at the bottom)
            self.console_panel = ttk.LabelFrame(self.main_container, text=" Process Logs ", padding=5)
            self.console_panel.pack(fill="x", side="bottom", pady=(10, 0))
            
            self.txt_log = tk.Text(self.console_panel, bg="#0d0d0d", fg="#e5e7eb", font=("Consolas", 9), 
                                   height=5, wrap="word", relief="flat", highlightthickness=1, highlightbackground=self.border_color)
            self.txt_log.pack(fill="both", expand=True, side="left")
            
            # Tags
            self.txt_log.tag_config("success", foreground=self.success_color, font=("Consolas", 9, "bold"))
            self.txt_log.tag_config("error", foreground=self.error_color, font=("Consolas", 9, "bold"))
            self.txt_log.tag_config("info", foreground=self.accent_color, font=("Consolas", 9, "bold"))
            self.txt_log.tag_config("default", foreground="#e5e7eb")
            
            log_scroll = ttk.Scrollbar(self.console_panel, command=self.txt_log.yview)
            log_scroll.pack(fill="y", side="right")
            self.txt_log.config(yscrollcommand=log_scroll.set)

        # Middle Body split into Left Panel (Selection & Settings) and Right Panel (Treeview & Editors)
        self.body_paned = ttk.PanedWindow(self.main_container, orient="horizontal")
        self.body_paned.pack(fill="both", expand=True)
        
        self.left_panel = ttk.Frame(self.body_paned, width=320, padding=(0, 0, 10, 0))
        self.body_paned.add(self.left_panel, weight=1)
        self.build_left_panel(self.left_panel)
        
        self.right_panel = ttk.Frame(self.body_paned, padding=(10, 0, 0, 0))
        self.body_paned.add(self.right_panel, weight=4)
        self.build_right_panel(self.right_panel)

    def build_top_panel(self, frame):
        lbl = ttk.Label(frame, text="Master Folder:")
        lbl.grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        self.ent_master_path = ttk.Entry(frame, width=70)
        self.ent_master_path.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        frame.columnconfigure(1, weight=1)
        
        btn_browse = tk.Button(frame, text="Browse...", command=self.browse_master_folder, bg=self.card_color, 
                               fg=self.text_color, relief="flat", activebackground=self.border_color, activeforeground=self.text_color)
        btn_browse.grid(row=0, column=2, padx=(0, 10))
        self.bind_hover(btn_browse)
        
        btn_scan = tk.Button(frame, text="Scan Directory", command=self.scan_localizations, bg=self.accent_color, 
                              fg="white", font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.accent_hover, activeforeground="white")
        btn_scan.grid(row=0, column=3)
        self.bind_hover(btn_scan, is_primary=True)

    def build_left_panel(self, frame):
        # Group 1: Localization & Charset
        lbl_group = ttk.LabelFrame(frame, text=" Localization Settings ", padding=10)
        lbl_group.pack(fill="x", side="top", pady=(0, 15))
        
        ttk.Label(lbl_group, text="Localization Folder:").pack(anchor="w", pady=(0, 5))
        self.cmb_local = ttk.Combobox(lbl_group, state="readonly")
        self.cmb_local.pack(fill="x", pady=(0, 10))
        self.cmb_local.bind("<<ComboboxSelected>>", self.on_localization_changed)
        
        ttk.Label(lbl_group, text="Charset Table:").pack(anchor="w", pady=(0, 5))
        self.cmb_charset = ttk.Combobox(lbl_group, state="readonly", values=["us", "jp", "ch", "kr"])
        self.cmb_charset.pack(fill="x", pady=(0, 5))
        self.cmb_charset.set("us")
        
        # Group 2: Binary Text File
        lbl_file_group = ttk.LabelFrame(frame, text=" Select Data & File ", padding=10)
        lbl_file_group.pack(fill="both", expand=True, side="top")
        
        ttk.Label(lbl_file_group, text="Data Category:").pack(anchor="w", pady=(0, 5))
        self.cmb_category = ttk.Combobox(lbl_file_group, state="readonly", values=[
            "⚔️ Battle Kernel Tables (battle/kernel)",
            "🏟️ Monster Arena & Help (help)",
            "📜 Story & Cutscene Dialogue (event)",
            "🎙️ Battle Quotes & Voice (battle/btl)",
            "⚙️ Menu & System Text (menu/cloud)"
        ])
        self.cmb_category.pack(fill="x", pady=(0, 10))
        self.cmb_category.set("⚔️ Battle Kernel Tables (battle/kernel)")
        self.cmb_category.bind("<<ComboboxSelected>>", self.on_category_changed)

        ttk.Label(lbl_file_group, text="Select File:").pack(anchor="w", pady=(0, 5))
        self.cmb_bin_file = ttk.Combobox(lbl_file_group, state="readonly")
        self.cmb_bin_file.pack(fill="x", pady=(0, 15))
        self.cmb_bin_file.bind("<<ComboboxSelected>>", self.on_bin_file_selected)
        
        # Bulk Operations Buttons
        lbl_bulk = ttk.Label(lbl_file_group, text="Bulk Utilities:")
        lbl_bulk.pack(anchor="w", pady=(0, 5))
        
        btn_exp_csv = tk.Button(lbl_file_group, text="📥 Export CSV (Single/Batch)", command=self.export_csv, bg=self.card_color, 
                                 fg=self.text_color, font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color)
        btn_exp_csv.pack(fill="x", pady=4)
        self.bind_hover(btn_exp_csv)
        
        btn_imp_csv = tk.Button(lbl_file_group, text="📤 Import CSV (Single/Batch)", command=self.import_csv, bg=self.card_color, 
                                 fg=self.text_color, font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color)
        btn_imp_csv.pack(fill="x", pady=4)
        self.bind_hover(btn_imp_csv)

        btn_sr = tk.Button(lbl_file_group, text="🔍 Global Search & Replace", command=self.open_search_replace_dialog, bg=self.card_color, 
                                 fg=self.text_color, font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color)
        btn_sr.pack(fill="x", pady=4)
        self.bind_hover(btn_sr)
        
        # Repack & Save Button
        btn_save = tk.Button(lbl_file_group, text="💾 Repack & Save .bin File", command=self.save_bin_file, bg=self.accent_color, 
                              fg="white", font=("Segoe UI", 10, "bold"), relief="flat", activebackground=self.accent_hover, activeforeground="white")
        btn_save.pack(fill="x", pady=(20, 0))
        self.bind_hover(btn_save, is_primary=True)

    def build_right_panel(self, frame):
        # Top Row: Search Filtering
        self.right_paned = ttk.PanedWindow(frame, orient="horizontal")
        self.right_paned.pack(fill="both", expand=True)
        
        # Left Pane: list and search
        self.list_pane = ttk.Frame(self.right_paned, padding=(0, 0, 5, 0))
        self.right_paned.add(self.list_pane, weight=1)
        
        search_frame = ttk.Frame(self.list_pane)
        search_frame.pack(fill="x", side="top", pady=(0, 8))
        
        ttk.Label(search_frame, text="🔍", font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        self.ent_search = ttk.Entry(search_frame)
        self.ent_search.pack(fill="x", expand=True, side="left")
        self.ent_search.bind("<KeyRelease>", self.filter_treeview)
        self.ent_search.bind("<Escape>", lambda e: self.clear_search())

        self.btn_clear_search = tk.Button(
            search_frame, text="✕", command=self.clear_search,
            bg=self.card_color, fg=self.text_dim, font=("Segoe UI", 8, "bold"),
            relief="flat", activebackground=self.border_color, activeforeground=self.text_color,
            width=2, pady=1
        )
        self.btn_clear_search.pack(side="left", padx=(4, 6))
        self.bind_hover(self.btn_clear_search)
        
        self.lbl_search_count = ttk.Label(search_frame, text="0 entries", font=("Segoe UI", 8, "italic"), foreground=self.text_dim)
        self.lbl_search_count.pack(side="right")
        
        # Treeview list
        tree_frame = ttk.Frame(self.list_pane)
        tree_frame.pack(fill="both", expand=True, side="top")
        
        self.tree = ttk.Treeview(tree_frame, columns=("ID", "Name", "Description"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name / Preview")
        self.tree.heading("Description", text="Description / Info")
        
        self.tree.column("ID", width=55, anchor="center")
        self.tree.column("Name", width=140, anchor="w")
        self.tree.column("Description", width=240, anchor="w")
        
        self.tree.tag_configure("even", background=self.card_color)
        self.tree.tag_configure("odd", background="#11141c")
        
        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_row_selected)
        
        tree_scroll = ttk.Scrollbar(tree_frame, command=self.tree.yview)
        tree_scroll.pack(fill="y", side="right")
        self.tree.config(yscrollcommand=tree_scroll.set)
        
        # Right Pane: Editor Notebook
        self.editor_pane = ttk.Frame(self.right_paned, padding=(5, 0, 0, 0))
        self.right_paned.add(self.editor_pane, weight=2)
        
        self.editor_notebook = ttk.Notebook(self.editor_pane)
        self.editor_notebook.pack(fill="both", expand=True)
        
        # Tab 1: Dialogue Text
        self.text_tab = ttk.Frame(self.editor_notebook, padding=10)
        self.editor_notebook.add(self.text_tab, text=" Dialogue Text ")
        self.build_text_tab(self.text_tab)
        
        # Tab 2: Gameplay Stats
        self.stats_tab = ttk.Frame(self.editor_notebook, padding=10)
        self.editor_notebook.add(self.stats_tab, text=" Gameplay Stats ")
        self.build_stats_tab(self.stats_tab)

    def build_text_tab(self, frame):
        # 4. Bottom apply & length label (packed with side="bottom" first so it stays docked to bottom)
        bottom_row = ttk.Frame(frame)
        bottom_row.pack(fill="x", side="bottom", pady=(10, 0))
        
        self.lbl_len_warn = ttk.Label(bottom_row, text="Bytes used: Name: 0 | Desc: 0", font=("Segoe UI", 9, "italic"), foreground=self.text_dim)
        self.lbl_len_warn.pack(side="left")

        btn_tags = tk.Button(bottom_row, text="📖 Tags Cheat Sheet", command=self.show_cheat_sheet_dialog, bg=self.card_color, 
                             fg=self.text_color, font=("Segoe UI", 8, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=8, pady=3)
        btn_tags.pack(side="left", padx=(12, 0))
        self.bind_hover(btn_tags)
        
        btn_apply = tk.Button(bottom_row, text="Apply Dialogue Edits", command=self.apply_row_edits, bg=self.accent_color, 
                              fg="white", font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.accent_hover, activeforeground="white", padx=15, pady=4)
        btn_apply.pack(side="right")
        self.bind_hover(btn_apply, is_primary=True)

        # 1. Kernel Fields Frame (used for kernel tables and albhed)
        self.kernel_fields_frame = ttk.Frame(frame)
        self.kernel_fields_frame.columnconfigure(1, weight=1)
        
        # Name
        self.lbl_field_name = ttk.Label(self.kernel_fields_frame, text="Name:")
        self.lbl_field_name.grid(row=0, column=0, sticky="w", pady=5, padx=(0, 5))
        self.ent_name = ttk.Entry(self.kernel_fields_frame)
        self.ent_name.grid(row=0, column=1, sticky="ew", pady=5)
        self.ent_name.bind("<KeyRelease>", lambda e: (self.update_length_label(), self.update_live_preview()))
        
        # S. Name
        self.lbl_field_sname = ttk.Label(self.kernel_fields_frame, text="Simplified Name:")
        self.lbl_field_sname.grid(row=1, column=0, sticky="w", pady=5, padx=(0, 5))
        self.ent_sname = ttk.Entry(self.kernel_fields_frame)
        self.ent_sname.grid(row=1, column=1, sticky="ew", pady=5)
        self.ent_sname.bind("<KeyRelease>", lambda e: self.update_length_label())
        
        # Desc
        self.lbl_field_desc = ttk.Label(self.kernel_fields_frame, text="Description:")
        self.lbl_field_desc.grid(row=2, column=0, sticky="w", pady=5, padx=(0, 5))
        self.ent_desc = ttk.Entry(self.kernel_fields_frame)
        self.ent_desc.grid(row=2, column=1, sticky="ew", pady=5)
        self.ent_desc.bind("<KeyRelease>", lambda e: (self.update_length_label(), self.update_live_preview()))
        
        # S. Desc
        self.lbl_field_sdesc = ttk.Label(self.kernel_fields_frame, text="Simplified Description:")
        self.lbl_field_sdesc.grid(row=3, column=0, sticky="w", pady=5, padx=(0, 5))
        self.ent_sdesc = ttk.Entry(self.kernel_fields_frame)
        self.ent_sdesc.grid(row=3, column=1, sticky="ew", pady=5)
        self.ent_sdesc.bind("<KeyRelease>", lambda e: self.update_length_label())

        # Extra w_name rows for Wakka, Lulu, Rikku (shown dynamically for w_name.bin)
        self.lbl_field_wakka = ttk.Label(self.kernel_fields_frame, text="Wakka:")
        self.ent_wakka = ttk.Entry(self.kernel_fields_frame)
        self.ent_wakka.bind("<KeyRelease>", lambda e: self.update_length_label())

        self.lbl_field_lulu = ttk.Label(self.kernel_fields_frame, text="Lulu:")
        self.ent_lulu = ttk.Entry(self.kernel_fields_frame)
        self.ent_lulu.bind("<KeyRelease>", lambda e: self.update_length_label())

        self.lbl_field_rikku = ttk.Label(self.kernel_fields_frame, text="Rikku:")
        self.ent_rikku = ttk.Entry(self.kernel_fields_frame)
        self.ent_rikku.bind("<KeyRelease>", lambda e: self.update_length_label())

        # Pack kernel fields by default
        self.kernel_fields_frame.pack(fill="x", pady=(0, 8))

        # 2. Modern Multi-Line Dialogue Editor Frame (for cutscenes, battle quotes, and arena tutorial scripts)
        self.dialogue_editor_frame = ttk.Frame(frame)
        
        # Header + Shortcut hint
        header_row = ttk.Frame(self.dialogue_editor_frame)
        header_row.pack(fill="x", pady=(0, 4))
        ttk.Label(header_row, text="Dialogue / Text Message:", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Label(header_row, text="(Ctrl+Enter to Apply)", font=("Segoe UI", 8, "italic"), foreground=self.text_dim).pack(side="right")
        
        # Quick-Insert Tag Toolbar
        self.toolbar_frame = ttk.Frame(self.dialogue_editor_frame)
        self.toolbar_frame.pack(fill="x", pady=(0, 6))
        
        # Color dropdown button
        self.color_menu = self.make_color_menu()
        self.btn_pill_color = tk.Button(
            self.toolbar_frame, text="🟡 Color ▼", command=self.show_color_menu,
            bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"),
            relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=7, pady=2
        )
        self.btn_pill_color.pack(side="left", padx=(0, 4))
        self.bind_hover(self.btn_pill_color)
        
        # Speaker dropdown button
        self.speaker_menu = self.make_speaker_menu()
        self.btn_pill_speaker = tk.Button(
            self.toolbar_frame, text="👤 Speaker ▼", command=self.show_speaker_menu,
            bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"),
            relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=7, pady=2
        )
        self.btn_pill_speaker.pack(side="left", padx=(0, 4))
        self.bind_hover(self.btn_pill_speaker)
        
        # Pause pill
        btn_pill_pause = tk.Button(
            self.toolbar_frame, text="⏸️ Pause", command=lambda: self.insert_tag("{PAUSE}"),
            bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"),
            relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=7, pady=2
        )
        btn_pill_pause.pack(side="left", padx=(0, 4))
        self.bind_hover(btn_pill_pause)
        
        # Time pill
        btn_pill_time = tk.Button(
            self.toolbar_frame, text="⏱️ Time", command=lambda: self.insert_tag("{TIME:1E}"),
            bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"),
            relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=7, pady=2
        )
        btn_pill_time.pack(side="left", padx=(0, 4))
        self.bind_hover(btn_pill_time)
        
        # Choice pill
        btn_pill_choice = tk.Button(
            self.toolbar_frame, text="🔘 Choice", command=lambda: self.insert_tag("{CHOICE:00}"),
            bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"),
            relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=7, pady=2
        )
        btn_pill_choice.pack(side="left", padx=(0, 4))
        self.bind_hover(btn_pill_choice)
        
        # Newline pill
        btn_pill_newline = tk.Button(
            self.toolbar_frame, text="↩️ \\n", command=lambda: self.insert_tag("\n"),
            bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"),
            relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=7, pady=2
        )
        btn_pill_newline.pack(side="left", padx=(0, 4))
        self.bind_hover(btn_pill_newline)

        # Multi-Line Editor container
        txt_container = ttk.Frame(self.dialogue_editor_frame)
        txt_container.pack(fill="both", expand=True)
        
        self.txt_dialogue = tk.Text(
            txt_container, height=6, font=("Consolas", 10), wrap="word",
            bg="#131622", fg="#f3f4f6", insertbackground="#ffffff",
            relief="flat", highlightthickness=1, highlightbackground=self.border_color,
            padx=8, pady=6
        )
        dialogue_scroll = ttk.Scrollbar(txt_container, orient="vertical", command=self.txt_dialogue.yview)
        self.txt_dialogue.configure(yscrollcommand=dialogue_scroll.set)
        self.txt_dialogue.pack(side="left", fill="both", expand=True)
        dialogue_scroll.pack(side="right", fill="y")
        
        # Configure syntax tags on text editor
        self.txt_dialogue.tag_configure('tag_speaker', foreground='#38bdf8', font=('Consolas', 10, 'bold'))
        self.txt_dialogue.tag_configure('tag_color', foreground='#facc15', font=('Consolas', 10, 'bold'))
        self.txt_dialogue.tag_configure('tag_flow', foreground='#4ade80', font=('Consolas', 10, 'bold'))
        self.txt_dialogue.tag_configure('tag_choice', foreground='#fb923c', font=('Consolas', 10, 'bold'))
        self.txt_dialogue.tag_configure('tag_var', foreground='#f472b6', font=('Consolas', 10, 'bold'))
        self.txt_dialogue.tag_configure('tag_general', foreground='#94a3b8', font=('Consolas', 10, 'italic'))
        
        # Text Editor Binds
        self.txt_dialogue.bind("<KeyRelease>", self.on_dialogue_key_release)
        self.txt_dialogue.bind("<Control-Return>", lambda e: (self.apply_row_edits(), "break")[1])
        self.txt_dialogue.bind("<Control-s>", lambda e: (self.apply_row_edits(), "break")[1])
        self.txt_dialogue.bind("<Motion>", self.on_text_motion)
        self.txt_dialogue.bind("<Leave>", self.on_text_leave)

        # 3. In-Game Dialogue Box Live Preview Frame
        self.preview_frame = ttk.Frame(frame)
        self.preview_frame.pack(fill="both", expand=True, pady=(8, 0))
        
        lbl_prev_title = ttk.Label(self.preview_frame, text="🎮 In-Game Dialogue Box Preview", font=("Segoe UI", 9, "bold"), foreground=self.accent_color)
        lbl_prev_title.pack(anchor="w", pady=(0, 4))
        
        self.preview_box = tk.Frame(
            self.preview_frame, bg="#070c18", highlightbackground="#2563eb", highlightthickness=1, padx=10, pady=8
        )
        self.preview_box.pack(fill="both", expand=True)
        
        self.lbl_preview_speaker = tk.Label(
            self.preview_box, text="", bg="#070c18", fg="#38bdf8", font=("Segoe UI", 10, "bold"), anchor="w"
        )
        
        self.txt_preview_body = tk.Text(
            self.preview_box, bg="#070c18", fg="#ffffff", font=("Segoe UI", 10), height=4, wrap="word", relief="flat", state="disabled"
        )
        self.txt_preview_body.pack(fill="both", expand=True)
        
        self.txt_preview_body.tag_configure('prev_white', foreground='#ffffff')
        self.txt_preview_body.tag_configure('prev_yellow', foreground='#fde047', font=('Segoe UI', 10, 'bold'))
        self.txt_preview_body.tag_configure('prev_red', foreground='#f87171', font=('Segoe UI', 10, 'bold'))
        self.txt_preview_body.tag_configure('prev_blue', foreground='#60a5fa', font=('Segoe UI', 10, 'bold'))
        self.txt_preview_body.tag_configure('prev_grey', foreground='#9ca3af', font=('Segoe UI', 10, 'italic'))
        self.txt_preview_body.tag_configure('prev_pink', foreground='#f472b6')
        self.txt_preview_body.tag_configure('prev_ol_purple', foreground='#c084fc', font=('Segoe UI', 10, 'bold'))
        self.txt_preview_body.tag_configure('prev_ol_cyan', foreground='#38bdf8', font=('Segoe UI', 10, 'bold'))
        self.txt_preview_body.tag_configure('prev_choice', foreground='#fbbf24', font=('Segoe UI', 10, 'bold'))

    def make_color_menu(self):
        m = tk.Menu(self.root, tearoff=0, bg=self.card_color, fg=self.text_color, activebackground=self.accent_color, activeforeground="white")
        colors = [
            ("Yellow (Key Terms)", "{CLR:YELLOW}"),
            ("Red (Debuffs/Danger)", "{CLR:RED}"),
            ("Blue (Buffs/Tips)", "{CLR:BLUE}"),
            ("Grey (Inactive/Footnotes)", "{CLR:GREY}"),
            ("White (Standard)", "{CLR:WHITE}"),
            ("Pink (Special Prompts)", "{CLR:PINK}"),
            ("Outlined Purple", "{CLR:OL_PURPLE}"),
            ("Outlined Cyan", "{CLR:OL_CYAN}")
        ]
        for name, tag in colors:
            m.add_command(label=name, command=lambda t=tag: self.insert_tag(t))
        return m

    def make_speaker_menu(self):
        m = tk.Menu(self.root, tearoff=0, bg=self.card_color, fg=self.text_color, activebackground=self.accent_color, activeforeground="white")
        speakers = [
            ("Tidus", "{PC:00}\n"),
            ("Yuna", "{PC:01}\n"),
            ("Auron", "{PC:02}\n"),
            ("Kimahri", "{PC:03}\n"),
            ("Wakka", "{PC:04}\n"),
            ("Lulu", "{PC:05}\n"),
            ("Rikku", "{PC:06}\n"),
            ("Seymour", "{PC:07}\n"),
            ("Seymour (Macro)", "{MCR:s06l63}\n"),
            ("Tromell (Macro)", "{MCR:s06l40}\n")
        ]
        for name, tag in speakers:
            m.add_command(label=name, command=lambda t=tag: self.insert_tag(t))
        return m

    def show_color_menu(self, event=None):
        btn = self.btn_pill_color
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height()
        self.color_menu.tk_popup(x, y)

    def show_speaker_menu(self, event=None):
        btn = self.btn_pill_speaker
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height()
        self.speaker_menu.tk_popup(x, y)

    def insert_tag(self, tag):
        mode = getattr(self, 'active_mode', 'kernel')
        if mode in ("sps2", "msg") and hasattr(self, 'txt_dialogue'):
            self.txt_dialogue.insert(tk.INSERT, tag)
            self.txt_dialogue.focus_set()
            self.highlight_syntax()
            self.update_live_preview()
            self.update_length_label()
        else:
            focused = self.root.focus_get()
            if focused in (self.ent_name, self.ent_sname, self.ent_desc, self.ent_sdesc):
                focused.insert(tk.INSERT, tag)
            else:
                self.ent_desc.insert(tk.INSERT, tag)
                self.ent_desc.focus_set()
            self.update_length_label()
            self.update_live_preview()

    def on_dialogue_key_release(self, event=None):
        self.highlight_syntax()
        self.update_live_preview()
        self.update_length_label()

    def highlight_syntax(self):
        if not hasattr(self, 'txt_dialogue') or not self.txt_dialogue.winfo_exists():
            return
            
        for tag_name in ['tag_speaker', 'tag_color', 'tag_flow', 'tag_choice', 'tag_var', 'tag_general']:
            self.txt_dialogue.tag_remove(tag_name, "1.0", tk.END)

        content = self.txt_dialogue.get("1.0", tk.END)
        for m in re.finditer(r'\{[^}]+\}', content):
            tag_str = m.group(0)
            start_idx = f"1.0 + {m.start()} chars"
            end_idx = f"1.0 + {m.end()} chars"
            
            t = tag_str.strip('{}')
            if t.startswith(('PC:', 'MCR:', 'MACRO:')):
                self.txt_dialogue.tag_add('tag_speaker', start_idx, end_idx)
            elif t.startswith(('CLR:', 'COLOR:')):
                self.txt_dialogue.tag_add('tag_color', start_idx, end_idx)
            elif t in ('PAUSE', 'CHOICE-END') or t.startswith(('TIME:', 'SPACE:')):
                self.txt_dialogue.tag_add('tag_flow', start_idx, end_idx)
            elif t.startswith('CHOICE:'):
                self.txt_dialogue.tag_add('tag_choice', start_idx, end_idx)
            elif t.startswith(('VAR:', 'KEY:')):
                self.txt_dialogue.tag_add('tag_var', start_idx, end_idx)
            else:
                self.txt_dialogue.tag_add('tag_general', start_idx, end_idx)

    def on_text_motion(self, event):
        try:
            index = self.txt_dialogue.index(f"@{event.x},{event.y}")
            line_no, char_col = map(int, index.split('.'))
            line_text = self.txt_dialogue.get(f"{line_no}.0", f"{line_no}.end")
            
            hovered_tag = None
            for m in re.finditer(r'\{[^}]+\}', line_text):
                if m.start() <= char_col < m.end():
                    hovered_tag = m.group(0)
                    break
                    
            if hovered_tag:
                info = self.get_tag_tooltip_info(hovered_tag)
                root_x = self.txt_dialogue.winfo_rootx() + event.x
                root_y = self.txt_dialogue.winfo_rooty() + event.y
                self.tag_tooltip.show(info, root_x, root_y)
            else:
                self.tag_tooltip.hide()
        except Exception:
            self.tag_tooltip.hide()

    def on_text_leave(self, event=None):
        self.tag_tooltip.hide()

    def get_tag_tooltip_info(self, tag):
        t = tag.strip('{}')
        if t.startswith('PC:'):
            idx = t[3:].upper()
            pcs = {
                '00': 'Tidus', '01': 'Yuna', '02': 'Auron', '03': 'Kimahri',
                '04': 'Wakka', '05': 'Lulu', '06': 'Rikku', '07': 'Seymour',
                '08': 'Valefor', '09': 'Ifrit', '0A': 'Ixion', '0B': 'Shiva',
                '0C': 'Bahamut', '0D': 'Anima', '0E': 'Yojimbo',
                '0F': 'Cindy', '10': 'Sandy', '11': 'Mindy'
            }
            name = pcs.get(idx, f'Character #{idx}')
            return f"[Speaker: {name}]\nSets speaker nameplate when on line 1 of dialogue."
        elif t.startswith('MCR:') or t.startswith('MACRO:'):
            known = {
                's06l63': 'Seymour', 's06l40': 'Tromell', 's0Dl33': 'Spira',
                's06l20': 'Lord Jyscal', 's06l21': 'Grand Maester Mika', 's06l22': 'Maester Kinoc',
                's06l23': 'Maester Kelk', 's06l24': 'Maester Seymour', 's06l00': 'Sin',
                's06l01': 'Yu Yevon', 's06l02': 'Lady Yunalesca', 's06l03': 'Lord Zaon',
                's06l04': 'Lord Braska', 's06l05': 'Sir Jecht', 's06l06': 'Cid',
                's06l07': 'Brother', 's06l08': 'Dona', 's06l09': 'Barthello',
                's06l10': 'Isaaru', 's06l11': 'Maroda', 's06l12': 'Pacce',
                's06l13': 'Elma', 's06l14': 'Lucil', 's06l15': 'Clasko',
                's06l16': 'Luzzu', 's06l17': 'Gatta', 's06l18': 'Biran',
                's06l19': 'Yenke', 's06l30': "O'aka XXIII", 's06l31': 'Wantz',
                's06l32': 'Rin', 's06l33': 'Belgemine', 's06l34': 'Shelinda',
                's06l35': 'Maechen', 's06l36': 'Lady Ginnem', 's06l37': 'Chocobo Knight',
                's06l38': 'Crusader', 's06l39': 'Priest', 's06l41': 'Guado',
                's06l42': 'Al Bhed', 's06l43': 'Hypello', 's06l44': 'Ronso'
            }
            val = t.split(':', 1)[1]
            k_name = known.get(val)
            desc = f" ({k_name})" if k_name else ""
            return f"[Macro Reference: {val}{desc}]\nDynamic character, NPC, or location name lookup."
        elif t.startswith('CLR:') or t.startswith('COLOR:'):
            c = t.split(':', 1)[1].upper()
            col_desc = {
                'WHITE': 'Standard White (Default dialogue color)',
                'YELLOW': 'Highlight Yellow (Key terms, abilities, items)',
                'GREY': 'Disabled Grey (Inactive choices or footnotes)',
                'BLUE': 'Beneficial Blue (Buffs, positive stats, tips)',
                'RED': 'Danger Red (Debuffs, boss attacks, warnings)',
                'PINK': 'Special Pink (Unique prompts / events)',
                'OL_PURPLE': 'Outlined Purple (Special styling)',
                'OL_CYAN': 'Outlined Cyan (Header styling)'
            }.get(c, c)
            return f"[Text Color: {c}]\n{col_desc}"
        elif t == 'PAUSE':
            return "[Player Input Pause]\nHalts text scrolling until the player presses confirm."
        elif t.startswith('TIME:'):
            frames = t.split(':', 1)[1]
            return f"[Timed Delay: {frames} frames]\nPauses dialogue flow to sync with speech or gestures."
        elif t.startswith('SPACE:'):
            pixels = t.split(':', 1)[1]
            return f"[Horizontal Spacing: {pixels}px]\nInserts horizontal whitespace for indenting or tables."
        elif t.startswith('CHOICE:'):
            c = t.split(':', 1)[1]
            return f"[Choice Option #{c}]\nMarks a selectable dialogue option."
        elif t == 'CHOICE-END':
            return "[End Choice Box]\nCloses the selectable dialogue choices prompt."
        elif t.startswith('VAR:'):
            v = t.split(':', 1)[1]
            return f"[Live Game Variable #{v}]\nDynamically injects in-game numbers (Gil, timer, score)."
        elif t.startswith('KEY:'):
            k = t.split(':', 1)[1]
            return f"[Key Item #{k}]\nDynamically displays localized key item name."
        elif t.startswith('CTRL:'):
            ctrl = t.split(':', 1)[1]
            return f"[Screen Control Byte: 0x{ctrl}]\nSPS2 layout / presentation control code."
        elif t in ('\\n', 'n'):
            return "[Line Break]\nAdvances text to the next row in the text box."
        return f"[Engine Tag: {tag}]"

    def update_live_preview(self):
        if not hasattr(self, 'txt_preview_body'):
            return
            
        mode = getattr(self, 'active_mode', 'kernel')
        if mode in ('sps2', 'msg') and hasattr(self, 'txt_dialogue'):
            raw_text = self.txt_dialogue.get("1.0", "end-1c")
        elif mode == 'kernel':
            raw_text = self.ent_desc.get()
            if not raw_text and hasattr(self, 'ent_name'):
                raw_text = self.ent_name.get()
        else:
            raw_text = self.ent_name.get()
            
        pc_names = {
            '00': 'Tidus', '01': 'Yuna', '02': 'Auron', '03': 'Kimahri',
            '04': 'Wakka', '05': 'Lulu', '06': 'Rikku', '07': 'Seymour',
            '08': 'Valefor', '09': 'Ifrit', '0A': 'Ixion', '0B': 'Shiva',
            '0C': 'Bahamut', '0D': 'Anima', '0E': 'Yojimbo',
            '0F': 'Cindy', '10': 'Sandy', '11': 'Mindy'
        }
        
        macro_names = {
            's06l63': 'Seymour', 's06l40': 'Tromell', 's0Dl33': 'Spira',
            's06l20': 'Lord Jyscal', 's06l21': 'Grand Maester Mika', 's06l22': 'Maester Kinoc',
            's06l23': 'Maester Kelk', 's06l24': 'Maester Seymour', 's06l00': 'Sin',
            's06l01': 'Yu Yevon', 's06l02': 'Lady Yunalesca', 's06l03': 'Lord Zaon',
            's06l04': 'Lord Braska', 's06l05': 'Sir Jecht', 's06l06': 'Cid',
            's06l07': 'Brother', 's06l08': 'Dona', 's06l09': 'Barthello',
            's06l10': 'Isaaru', 's06l11': 'Maroda', 's06l12': 'Pacce',
            's06l13': 'Elma', 's06l14': 'Lucil', 's06l15': 'Clasko',
            's06l16': 'Luzzu', 's06l17': 'Gatta', 's06l18': 'Biran',
            's06l19': 'Yenke', 's06l30': "O'aka XXIII", 's06l31': 'Wantz',
            's06l32': 'Rin', 's06l33': 'Belgemine', 's06l34': 'Shelinda',
            's06l35': 'Maechen', 's06l36': 'Lady Ginnem', 's06l37': 'Chocobo Knight',
            's06l38': 'Crusader', 's06l39': 'Priest', 's06l41': 'Guado',
            's06l42': 'Al Bhed', 's06l43': 'Hypello', 's06l44': 'Ronso'
        }
        
        # 1. Normalize line breaks from CSV {\n} placeholders
        text = raw_text.replace("{\\n}", "\n").replace("{/n}", "\n").replace("{n}", "\n")
        
        # 2. Detect speaker from line 1
        lines = text.split('\n')
        speaker = ""
        body_lines = lines
        
        if lines:
            m_spk = re.match(r'^\s*\{(PC:([0-9a-fA-F]+)|(?:MCR|MACRO):([a-zA-Z0-9]+))\}\s*(.*)$', lines[0])
            if m_spk:
                pc_id = m_spk.group(2)
                mcr_id = m_spk.group(3)
                remainder = m_spk.group(4)
                
                if pc_id:
                    speaker = pc_names.get(pc_id.upper(), f"Character #{pc_id}")
                elif mcr_id:
                    speaker = macro_names.get(mcr_id, mcr_id)
                    
                if remainder:
                    body_lines = [remainder] + lines[1:]
                else:
                    body_lines = lines[1:]
            elif mode == 'kernel' and hasattr(self, 'ent_name') and self.ent_name.get():
                speaker = self.ent_name.get()
                
        if speaker:
            self.lbl_preview_speaker.config(text=f"[ {speaker.upper()} ]")
            self.lbl_preview_speaker.pack(anchor="w", pady=(0, 4))
        else:
            self.lbl_preview_speaker.pack_forget()
            
        body = '\n'.join(body_lines)
        
        # 3. Resolve inline character and macro tags into actual names
        body = re.sub(r'\{PC:([0-9a-fA-F]+)\}', lambda m: pc_names.get(m.group(1).upper(), f"Character #{m.group(1)}"), body)
        body = re.sub(r'\{(?:MCR|MACRO):([a-zA-Z0-9]+)\}', lambda m: macro_names.get(m.group(1), "[NPC]"), body)
        
        # 4. Resolve choices into in-game interactive selection prompt (with cursor pointer)
        body = re.sub(r'\{CHOICE:\d+\}\s*', '  ▶  ', body)
        body = re.sub(r'\{CHOICE-END\}', '', body)
        
        # 5. Resolve variables and key items into clean in-game representations
        body = re.sub(r'\{VAR:\d+\}', '[1,000]', body)
        body = re.sub(r'\{KEY:\d+\}', '[Key Item]', body)
        
        # 6. Resolve spacing and indentation
        def _resolve_space(match):
            try:
                px = int(match.group(1), 16)
                num_spaces = max(1, px // 8)
                return ' ' * num_spaces
            except Exception:
                return ' '
        body = re.sub(r'\{SPACE:([0-9a-fA-F]+)\}', _resolve_space, body)
        
        # 7. Strip out all invisible bytecode and flow control tags
        body = re.sub(r'\{(?:PAUSE|TIME:[^}]+|CTRL:[^}]+|CMD:[^}]+|UNK[A-Z0-9]*:[^}]+)\}', '', body)
        
        # 8. Strip any remaining unexpected or unmapped {TAG} codes so NO curly brackets leak into the preview
        body = re.sub(r'\{[^}]+\}', lambda m: m.group(0) if m.group(0).startswith('{CLR:') else '', body)
        
        # 9. Clean up excess whitespace and empty presentation lines
        body = '\n'.join(line.rstrip() for line in body.splitlines()).strip('\r\n')
        
        # 10. Render formatted colored text into preview Text widget
        self.txt_preview_body.config(state="normal")
        self.txt_preview_body.delete("1.0", tk.END)
        
        parts = re.split(r'(\{CLR:[^}]+\})', body)
        cur_tag = "prev_white"
        cmap = {
            'WHITE': 'prev_white',
            'YELLOW': 'prev_yellow',
            'RED': 'prev_red',
            'BLUE': 'prev_blue',
            'GREY': 'prev_grey',
            'PINK': 'prev_pink',
            'OL_PURPLE': 'prev_ol_purple',
            'OL_CYAN': 'prev_ol_cyan'
        }
        
        for part in parts:
            if part.startswith('{CLR:'):
                cname = part[5:-1].upper()
                cur_tag = cmap.get(cname, 'prev_white')
            else:
                if part:
                    if '  ▶  ' in part:
                        subparts = part.split('  ▶  ')
                        for i, sp in enumerate(subparts):
                            if i > 0:
                                self.txt_preview_body.insert(tk.END, "  ▶  ", "prev_choice")
                            if sp:
                                self.txt_preview_body.insert(tk.END, sp, cur_tag)
                    else:
                        self.txt_preview_body.insert(tk.END, part, cur_tag)
                        
        self.txt_preview_body.config(state="disabled")

    def clear_search(self):
        self.ent_search.delete(0, tk.END)
        self.filter_treeview()
        self.ent_search.focus_set()

    def build_stats_tab(self, frame):
        self.stats_canvas = tk.Canvas(frame, borderwidth=0, highlightthickness=0, bg=self.bg_color)
        self.stats_scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.stats_canvas.yview)
        self.stats_scroll_frame = ttk.Frame(self.stats_canvas)
        
        self.stats_scroll_frame.bind(
            "<Configure>",
            lambda e: self.stats_canvas.configure(scrollregion=self.stats_canvas.bbox("all"))
        )
        
        self.stats_canvas.create_window((0, 0), window=self.stats_scroll_frame, anchor="nw")
        self.stats_canvas.configure(yscrollcommand=self.stats_scrollbar.set)
        
        self.stats_canvas.pack(side="left", fill="both", expand=True)
        self.stats_scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event):
            self.stats_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.stats_scroll_frame.bind("<Enter>", lambda e: self.stats_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.stats_scroll_frame.bind("<Leave>", lambda e: self.stats_canvas.unbind_all("<MouseWheel>"))

        self.build_stats_fields(self.stats_scroll_frame)

    def build_stats_fields(self, frame):
        self.stat_vars = {}
        
        # No stats label
        self.stats_none_label = ttk.Label(frame, text="No gameplay stats available for this file type.", font=("Segoe UI", 10, "italic"), foreground=self.text_dim)
        self.stats_none_label.pack(pady=20, padx=10)
        
        # Key Item Group
        self.grp_key_item = ttk.LabelFrame(frame, text=" Key Item Configuration ", padding=10)
        
        self.stat_vars["primer"] = tk.IntVar()
        ttk.Checkbutton(self.grp_key_item, text="Is Al Bhed Primer", variable=self.stat_vars["primer"]).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
        
        ttk.Label(self.grp_key_item, text="Ordering Index:").grid(row=1, column=0, sticky="w", pady=5)
        self.stat_vars["ordering"] = tk.StringVar(value="0")
        tk.Spinbox(self.grp_key_item, from_=0, to=255, textvariable=self.stat_vars["ordering"], width=10, bg=self.card_color, fg=self.text_color, buttonbackground=self.card_color).grid(row=1, column=1, sticky="w", pady=5, padx=5)
        
        ttk.Label(self.grp_key_item, text="Unknown Byte 12:").grid(row=2, column=0, sticky="w", pady=5)
        self.stat_vars["unk12"] = tk.StringVar(value="0")
        tk.Spinbox(self.grp_key_item, from_=0, to=255, textvariable=self.stat_vars["unk12"], width=10, bg=self.card_color, fg=self.text_color, buttonbackground=self.card_color).grid(row=2, column=1, sticky="w", pady=5, padx=5)
        
        # Ability / Item Group
        self.grp_ability = ttk.LabelFrame(frame, text=" Ability / Item Stats ", padding=10)
        
        ttk.Label(self.grp_ability, text="MP Cost:").grid(row=0, column=0, sticky="w", pady=5)
        self.stat_vars["mp_cost"] = tk.StringVar(value="0")
        tk.Spinbox(self.grp_ability, from_=0, to=255, textvariable=self.stat_vars["mp_cost"], width=8, bg=self.card_color, fg=self.text_color).grid(row=0, column=1, sticky="w", pady=5, padx=5)
        
        ttk.Label(self.grp_ability, text="OD Cost:").grid(row=0, column=2, sticky="w", pady=5, padx=(10, 0))
        self.stat_vars["od_cost"] = tk.StringVar(value="0")
        tk.Spinbox(self.grp_ability, from_=0, to=255, textvariable=self.stat_vars["od_cost"], width=8, bg=self.card_color, fg=self.text_color).grid(row=0, column=3, sticky="w", pady=5, padx=5)
        
        ttk.Label(self.grp_ability, text="Power:").grid(row=1, column=0, sticky="w", pady=5)
        self.stat_vars["power"] = tk.StringVar(value="0")
        tk.Spinbox(self.grp_ability, from_=0, to=255, textvariable=self.stat_vars["power"], width=8, bg=self.card_color, fg=self.text_color).grid(row=1, column=1, sticky="w", pady=5, padx=5)
        
        ttk.Label(self.grp_ability, text="Accuracy:").grid(row=1, column=2, sticky="w", pady=5, padx=(10, 0))
        self.stat_vars["accuracy"] = tk.StringVar(value="0")
        tk.Spinbox(self.grp_ability, from_=0, to=255, textvariable=self.stat_vars["accuracy"], width=8, bg=self.card_color, fg=self.text_color).grid(row=1, column=3, sticky="w", pady=5, padx=5)
        
        ttk.Label(self.grp_ability, text="Hit Count:").grid(row=2, column=0, sticky="w", pady=5)
        self.stat_vars["hit_count"] = tk.StringVar(value="1")
        tk.Spinbox(self.grp_ability, from_=0, to=255, textvariable=self.stat_vars["hit_count"], width=8, bg=self.card_color, fg=self.text_color).grid(row=2, column=1, sticky="w", pady=5, padx=5)
        
        ttk.Label(self.grp_ability, text="Formula:").grid(row=2, column=2, sticky="w", pady=5, padx=(10, 0))
        self.stat_vars["formula"] = tk.StringVar()
        self.cmb_formula = ttk.Combobox(self.grp_ability, textvariable=self.stat_vars["formula"], state="readonly", width=15)
        self.cmb_formula["values"] = [f"{name} ({hex(code)})" for code, name in DAMAGE_FORMULAS]
        self.cmb_formula.grid(row=2, column=3, sticky="w", pady=5, padx=5)
        
        # Elements Group
        self.grp_elements = ttk.LabelFrame(frame, text=" Elements ", padding=10)
        self.stat_vars["elem_fire"] = tk.IntVar()
        self.stat_vars["elem_ice"] = tk.IntVar()
        self.stat_vars["elem_thunder"] = tk.IntVar()
        self.stat_vars["elem_water"] = tk.IntVar()
        self.stat_vars["elem_holy"] = tk.IntVar()
        
        ttk.Checkbutton(self.grp_elements, text="Fire", variable=self.stat_vars["elem_fire"]).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Checkbutton(self.grp_elements, text="Ice", variable=self.stat_vars["elem_ice"]).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Checkbutton(self.grp_elements, text="Thunder", variable=self.stat_vars["elem_thunder"]).grid(row=0, column=2, sticky="w", padx=5)
        ttk.Checkbutton(self.grp_elements, text="Water", variable=self.stat_vars["elem_water"]).grid(row=0, column=3, sticky="w", padx=5)
        ttk.Checkbutton(self.grp_elements, text="Holy", variable=self.stat_vars["elem_holy"]).grid(row=0, column=4, sticky="w", padx=5)
        
        # Targeting Group
        self.grp_targeting = ttk.LabelFrame(frame, text=" Targeting ", padding=10)
        self.stat_vars["tgt_enabled"] = tk.IntVar()
        self.stat_vars["tgt_enemies"] = tk.IntVar()
        self.stat_vars["tgt_multi"] = tk.IntVar()
        self.stat_vars["tgt_self"] = tk.IntVar()
        self.stat_vars["tgt_either"] = tk.IntVar()
        self.stat_vars["tgt_dead"] = tk.IntVar()
        self.stat_vars["tgt_ranged"] = tk.IntVar()
        
        ttk.Checkbutton(self.grp_targeting, text="Enabled", variable=self.stat_vars["tgt_enabled"]).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Checkbutton(self.grp_targeting, text="Enemies", variable=self.stat_vars["tgt_enemies"]).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Checkbutton(self.grp_targeting, text="Multi-target", variable=self.stat_vars["tgt_multi"]).grid(row=0, column=2, sticky="w", padx=5)
        ttk.Checkbutton(self.grp_targeting, text="Self Only", variable=self.stat_vars["tgt_self"]).grid(row=0, column=3, sticky="w", padx=5)
        ttk.Checkbutton(self.grp_targeting, text="Either Team", variable=self.stat_vars["tgt_either"]).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Checkbutton(self.grp_targeting, text="Dead Only", variable=self.stat_vars["tgt_dead"]).grid(row=1, column=1, sticky="w", padx=5, pady=5)
        ttk.Checkbutton(self.grp_targeting, text="Ranged", variable=self.stat_vars["tgt_ranged"]).grid(row=1, column=2, sticky="w", padx=5, pady=5)
        
        # Status Group
        self.grp_status = ttk.LabelFrame(frame, text=" Status Infliction Chances (0-255) ", padding=10)
        status_list = [
            ("Death", "st_death"), ("Zombie", "st_zombie"), ("Petrify", "st_petrify"), 
            ("Poison", "st_poison"), ("Confuse", "st_confuse"), ("Berserk", "st_berserk"), 
            ("Provoke", "st_provoke"), ("Threaten", "st_threaten"), ("Sleep", "st_sleep"), 
            ("Silence", "st_silence"), ("Darkness", "st_darkness"), ("Slow", "st_slow"), 
            ("Haste", "st_haste")
        ]
        for idx, (lbl, key) in enumerate(status_list):
            r = idx // 3
            c = (idx % 3) * 2
            ttk.Label(self.grp_status, text=f"{lbl}:").grid(row=r, column=c, sticky="w", pady=5, padx=(5 if c > 0 else 0, 0))
            self.stat_vars[key] = tk.StringVar(value="0")
            tk.Spinbox(self.grp_status, from_=0, to=255, textvariable=self.stat_vars[key], width=5, bg=self.card_color, fg=self.text_color).grid(row=r, column=c+1, sticky="w", pady=5, padx=5)
            
        # Unified Apply Button for Stats
        self.btn_apply_stats = tk.Button(frame, text="Apply Stats Changes", command=self.apply_stats_edits, bg=self.accent_color,
                                         fg="white", font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.accent_hover, activeforeground="white", padx=15, pady=4)

    def show_stats_group(self, file_name):
        self.stats_none_label.pack_forget()
        self.grp_key_item.pack_forget()
        self.grp_ability.pack_forget()
        self.grp_elements.pack_forget()
        self.grp_targeting.pack_forget()
        self.grp_status.pack_forget()
        self.btn_apply_stats.pack_forget()
        
        if file_name == "important.bin":
            self.grp_key_item.pack(fill="x", pady=5, padx=5)
            self.btn_apply_stats.pack(pady=10, padx=5, anchor="e")
        elif file_name in ["item.bin", "command.bin", "monmagic1.bin", "monmagic2.bin"]:
            self.grp_ability.pack(fill="x", pady=5, padx=5)
            self.grp_elements.pack(fill="x", pady=5, padx=5)
            self.grp_targeting.pack(fill="x", pady=5, padx=5)
            self.grp_status.pack(fill="x", pady=5, padx=5)
            self.btn_apply_stats.pack(pady=10, padx=5, anchor="e")
        else:
            self.stats_none_label.pack(pady=20, padx=10)

    def apply_stats_edits(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "No entry selected.")
            return
            
        entry_id = int(sel[0])
        record = next((r for r in self.records if r['id'] == entry_id), None)
        if not record:
            return
            
        file_name = self.active_file_name
        extra_bytes = bytearray(record.get('extra_bytes', b''))
        
        if file_name == "important.bin" and len(extra_bytes) >= 4:
            extra_bytes[0] = 1 if self.stat_vars["primer"].get() else 0
            extra_bytes[2] = max(0, min(255, int(self.stat_vars["unk12"].get() or 0)))
            extra_bytes[3] = max(0, min(255, int(self.stat_vars["ordering"].get() or 0)))
            record['extra_bytes'] = bytes(extra_bytes)
            self.log(f"Applied stats edits in-memory to Key Item ID {entry_id}.")
            
        elif file_name in ["item.bin", "command.bin", "monmagic1.bin", "monmagic2.bin"] and len(extra_bytes) >= 76:
            def set_b(offset, val):
                extra_bytes[offset - 0x10] = max(0, min(255, int(val)))
                
            set_b(0x25, self.stat_vars["mp_cost"].get() or 0)
            set_b(0x26, self.stat_vars["od_cost"].get() or 0)
            set_b(0x2A, self.stat_vars["power"].get() or 0)
            set_b(0x29, self.stat_vars["accuracy"].get() or 0)
            set_b(0x2B, self.stat_vars["hit_count"].get() or 0)
            
            f_str = self.cmb_formula.get()
            f_code = 0
            for code, name in DAMAGE_FORMULAS:
                if f"{name} ({hex(code)})" == f_str:
                    f_code = code
                    break
            set_b(0x28, f_code)
            
            elem = 0
            if self.stat_vars["elem_fire"].get(): elem |= 0x01
            if self.stat_vars["elem_ice"].get(): elem |= 0x02
            if self.stat_vars["elem_thunder"].get(): elem |= 0x04
            if self.stat_vars["elem_water"].get(): elem |= 0x08
            if self.stat_vars["elem_holy"].get(): elem |= 0x10
            set_b(0x2D, elem)
            
            tgt = 0
            if self.stat_vars["tgt_enabled"].get(): tgt |= 0x01
            if self.stat_vars["tgt_enemies"].get(): tgt |= 0x02
            if self.stat_vars["tgt_multi"].get(): tgt |= 0x04
            if self.stat_vars["tgt_self"].get(): tgt |= 0x08
            if self.stat_vars["tgt_either"].get(): tgt |= 0x20
            if self.stat_vars["tgt_dead"].get(): tgt |= 0x40
            if self.stat_vars["tgt_ranged"].get(): tgt |= 0x80
            set_b(0x1A, tgt)
            
            set_b(0x2E, self.stat_vars["st_death"].get() or 0)
            set_b(0x2F, self.stat_vars["st_zombie"].get() or 0)
            set_b(0x30, self.stat_vars["st_petrify"].get() or 0)
            set_b(0x31, self.stat_vars["st_poison"].get() or 0)
            set_b(0x36, self.stat_vars["st_confuse"].get() or 0)
            set_b(0x37, self.stat_vars["st_berserk"].get() or 0)
            set_b(0x38, self.stat_vars["st_provoke"].get() or 0)
            set_b(0x39, self.stat_vars["st_threaten"].get() or 0)
            set_b(0x3A, self.stat_vars["st_sleep"].get() or 0)
            set_b(0x3B, self.stat_vars["st_silence"].get() or 0)
            set_b(0x3C, self.stat_vars["st_darkness"].get() or 0)
            set_b(0x46, self.stat_vars["st_slow"].get() or 0)
            set_b(0x45, self.stat_vars["st_haste"].get() or 0)
            
            record['extra_bytes'] = bytes(extra_bytes)
            self.log(f"Applied stats edits in-memory to Ability/Item ID {entry_id}.")


    def browse_master_folder(self):
        folder = filedialog.askdirectory(title="Select Extracted FFX Master Folder")
        if folder:
            path = os.path.abspath(folder)
            self.config["master_path"] = path
            self.save_config()
            if hasattr(self, "parent") and self.parent and hasattr(self.parent, "update_global_master_path"):
                self.parent.update_global_master_path(path)
            else:
                self.ent_master_path.delete(0, tk.END)
                self.ent_master_path.insert(0, path)
                self.codec.ffx_master_path = path
                self.log(f"Set FFX Master folder: {path}")
                self.scan_localizations()

    def scan_localizations(self):
        path = self.ent_master_path.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Invalid master folder path. Make sure it exists.")
            return
            
        self.codec.ffx_master_path = path
        # Look for localization folders
        locs = []
        for name in os.listdir(path):
            d = os.path.join(path, name)
            if os.path.isdir(d):
                kernel_path = os.path.join(d, "battle", "kernel")
                if os.path.exists(kernel_path):
                    locs.append(name)
                    
        if not locs:
            # Maybe the path entered was already the localization subfolder (e.g. jppc)
            parent_dir = os.path.dirname(path)
            kernel_dir = os.path.join(path, "battle", "kernel")
            if os.path.exists(kernel_dir):
                loc_name = os.path.basename(path)
                self.ent_master_path.delete(0, tk.END)
                self.ent_master_path.insert(0, parent_dir)
                self.codec.ffx_master_path = parent_dir
                locs = [loc_name]
                
        if locs:
            # Sort localizations (prefer uspc / new_uspc first for default)
            preferred = ["new_uspc", "uspc", "jppc", "new_jppc"]
            locs = sorted(locs, key=lambda x: preferred.index(x) if x in preferred else 99)
            self.cmb_local.config(values=locs)
            self.cmb_local.set(locs[0])
            self.log(f"Found {len(locs)} localizations: {', '.join(locs)}")
            self.on_localization_changed()
        else:
            self.cmb_local.config(values=[])
            self.cmb_local.set("")
            self.cmb_bin_file.config(values=[])
            self.cmb_bin_file.set("")
            messagebox.showwarning("Warning", "Could not find any 'battle/kernel' subfolders inside the master folder.")

    def on_localization_changed(self, event=None):
        loc = self.cmb_local.get()
        if not loc:
            return
            
        # Auto-detect charset mapping
        if "jp" in loc.lower():
            self.cmb_charset.set("jp")
        elif "ch" in loc.lower() or "cn" in loc.lower():
            self.cmb_charset.set("ch")
        elif "kr" in loc.lower():
            self.cmb_charset.set("kr")
        else:
            self.cmb_charset.set("us")
            
        self.log(f"Switched localization to '{loc}'. Auto-set charset to '{self.cmb_charset.get()}'.")
        self.populate_category_files()

    def on_category_changed(self, event=None):
        self.populate_category_files()

    def populate_category_files(self):
        loc = self.cmb_local.get()
        if not loc or not self.codec.ffx_master_path:
            return
            
        category = self.cmb_category.get()
        loc_dir = os.path.join(self.codec.ffx_master_path, loc)
        self.file_map = {}
        
        if "Kernel" in category:
            kernel_path = os.path.join(loc_dir, "battle", "kernel")
            if os.path.exists(kernel_path):
                for name in os.listdir(kernel_path):
                    if name.endswith(".bin") and name in FILE_RECORD_SIZES:
                        self.file_map[name] = os.path.join(kernel_path, name)
        elif "Arena" in category or "Help" in category:
            help_path = os.path.join(loc_dir, "help")
            if os.path.exists(help_path):
                for root, dirs, files in os.walk(help_path):
                    for f in files:
                        if f.endswith(".sps2"):
                            rel = os.path.relpath(os.path.join(root, f), help_path).replace("\\", "/")
                            self.file_map[rel] = os.path.join(root, f)
        elif "Story" in category or "Cutscene" in category:
            evt_path = os.path.join(loc_dir, "event", "obj_ps3")
            if not os.path.exists(evt_path):
                evt_path = os.path.join(loc_dir, "event", "obj_psv")
            if not os.path.exists(evt_path):
                evt_path = os.path.join(loc_dir, "event")
            if os.path.exists(evt_path):
                for root, dirs, files in os.walk(evt_path):
                    for f in files:
                        if f.endswith(".bin"):
                            rel = os.path.relpath(os.path.join(root, f), evt_path).replace("\\", "/")
                            self.file_map[rel] = os.path.join(root, f)
        elif "Battle Quotes" in category or "Voice" in category or "btl" in category:
            btl_path = os.path.join(loc_dir, "battle", "btl")
            if os.path.exists(btl_path):
                for root, dirs, files in os.walk(btl_path):
                    for f in files:
                        if f.endswith(".bin"):
                            rel = os.path.relpath(os.path.join(root, f), btl_path).replace("\\", "/")
                            self.file_map[rel] = os.path.join(root, f)
        elif "Menu" in category or "System" in category:
            menu_path = os.path.join(loc_dir, "menu")
            if os.path.exists(menu_path):
                for name in os.listdir(menu_path):
                    if name.endswith(".bin") and not name.startswith("ffxsjis"):
                        self.file_map[f"menu/{name}"] = os.path.join(menu_path, name)
            cloud_path = os.path.join(loc_dir, "cloudsave")
            if os.path.exists(cloud_path):
                for name in os.listdir(cloud_path):
                    if name.endswith(".bin"):
                        self.file_map[f"cloudsave/{name}"] = os.path.join(cloud_path, name)

        sorted_files = sorted(self.file_map.keys())
        self.cmb_bin_file.config(values=sorted_files)
        if sorted_files:
            default_f = sorted_files[0]
            for pref in ["mon_boku/mon_boku.sps2", "mon_boku.sps2", "item_txt.bin", "menu/menumain.bin"]:
                if pref in sorted_files:
                    default_f = pref
                    break
            self.cmb_bin_file.set(default_f)
            self.on_bin_file_selected()
        else:
            self.cmb_bin_file.set("")
            self.clear_table()

    def clear_table(self):
        self.records = []
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.clear_editor_fields()

    def clear_editor_fields(self):
        self.ent_name.delete(0, tk.END)
        self.ent_sname.delete(0, tk.END)
        self.ent_desc.delete(0, tk.END)
        self.ent_sdesc.delete(0, tk.END)
        if hasattr(self, 'txt_dialogue'):
            self.txt_dialogue.delete("1.0", tk.END)
        if hasattr(self, 'ent_wakka'):
            self.ent_wakka.delete(0, tk.END)
            self.ent_lulu.delete(0, tk.END)
            self.ent_rikku.delete(0, tk.END)
        self.update_live_preview()
        self.lbl_len_warn.config(text="Bytes used: Name: 0 | Desc: 0", foreground=self.text_dim)

    def on_bin_file_selected(self, event=None):
        loc = self.cmb_local.get()
        selected_key = self.cmb_bin_file.get()
        if not loc or not selected_key:
            return
            
        filepath = getattr(self, 'file_map', {}).get(selected_key)
        if not filepath or not os.path.exists(filepath):
            filepath = os.path.join(self.codec.ffx_master_path, loc, "battle", "kernel", selected_key)
            if not os.path.exists(filepath):
                messagebox.showerror("Error", f"File not found: {filepath}")
                return
            
        self.active_file_path = filepath
        self.active_file_name = os.path.basename(filepath)
        
        # Check file mode
        norm_path = filepath.replace("\\", "/").lower()
        if norm_path.endswith(".sps2"):
            self.active_mode = "sps2"
        elif "albheddic" in self.active_file_name.lower():
            self.active_mode = "albhed"
        elif "battle/kernel" in norm_path or self.active_file_name in FILE_RECORD_SIZES:
            self.active_mode = "kernel"
        else:
            self.active_mode = "msg"
            
        # Adjust UI layout based on active_mode
        if self.active_mode == "kernel":
            if hasattr(self, 'dialogue_editor_frame'):
                self.dialogue_editor_frame.pack_forget()
            if hasattr(self, 'kernel_fields_frame'):
                self.kernel_fields_frame.pack(fill="x", pady=(0, 8))
            if hasattr(self, 'preview_frame'):
                self.preview_frame.pack(fill="both", expand=True)

            self.lbl_field_sname.grid(row=1, column=0, sticky="w", pady=5, padx=(0, 5))
            self.ent_sname.grid(row=1, column=1, sticky="ew", pady=5)
            self.lbl_field_desc.grid(row=2, column=0, sticky="w", pady=5, padx=(0, 5))
            self.ent_desc.grid(row=2, column=1, sticky="ew", pady=5)
            self.lbl_field_sdesc.grid(row=3, column=0, sticky="w", pady=5, padx=(0, 5))
            self.ent_sdesc.grid(row=3, column=1, sticky="ew", pady=5)
            
            if self.active_file_name == "w_name.bin":
                self.lbl_field_name.config(text="Tidus:")
                self.lbl_field_sname.config(text="Yuna:")
                self.lbl_field_desc.config(text="Auron:")
                self.lbl_field_sdesc.config(text="Kimahri:")
                self.lbl_field_wakka.grid(row=4, column=0, sticky="w", pady=5, padx=(0, 5))
                self.ent_wakka.grid(row=4, column=1, sticky="ew", pady=5)
                self.lbl_field_lulu.grid(row=5, column=0, sticky="w", pady=5, padx=(0, 5))
                self.ent_lulu.grid(row=5, column=1, sticky="ew", pady=5)
                self.lbl_field_rikku.grid(row=6, column=0, sticky="w", pady=5, padx=(0, 5))
                self.ent_rikku.grid(row=6, column=1, sticky="ew", pady=5)
            elif self.active_file_name == "ply_save.bin":
                self.lbl_field_name.config(text="Character Name:")
                self.lbl_field_sname.config(text="(Unused):")
                self.lbl_field_desc.config(text="(Unused):")
                self.lbl_field_sdesc.config(text="(Unused):")
                if hasattr(self, 'ent_wakka'):
                    self.lbl_field_wakka.grid_forget()
                    self.ent_wakka.grid_forget()
                    self.lbl_field_lulu.grid_forget()
                    self.ent_lulu.grid_forget()
                    self.lbl_field_rikku.grid_forget()
                    self.ent_rikku.grid_forget()
            else:
                self.lbl_field_name.config(text="Name:")
                self.lbl_field_sname.config(text="Simplified Name:")
                self.lbl_field_desc.config(text="Description:")
                self.lbl_field_sdesc.config(text="Simplified Description:")
                if hasattr(self, 'ent_wakka'):
                    self.lbl_field_wakka.grid_forget()
                    self.ent_wakka.grid_forget()
                    self.lbl_field_lulu.grid_forget()
                    self.ent_lulu.grid_forget()
                    self.lbl_field_rikku.grid_forget()
                    self.ent_rikku.grid_forget()
        elif self.active_mode == "albhed":
            if hasattr(self, 'dialogue_editor_frame'):
                self.dialogue_editor_frame.pack_forget()
            if hasattr(self, 'preview_frame'):
                self.preview_frame.pack_forget()
            if hasattr(self, 'kernel_fields_frame'):
                self.kernel_fields_frame.pack(fill="x", pady=(0, 8))

            self.lbl_field_name.config(text="Letter Translation (e.g. A -> Y):")
            self.lbl_field_sname.grid_remove()
            self.ent_sname.grid_remove()
            self.lbl_field_desc.grid_remove()
            self.ent_desc.grid_remove()
            self.lbl_field_sdesc.grid_remove()
            self.ent_sdesc.grid_remove()
            if hasattr(self, 'ent_wakka'):
                self.lbl_field_wakka.grid_forget()
                self.ent_wakka.grid_forget()
                self.lbl_field_lulu.grid_forget()
                self.ent_lulu.grid_forget()
                self.lbl_field_rikku.grid_forget()
                self.ent_rikku.grid_forget()
        else: # sps2 or msg
            if hasattr(self, 'kernel_fields_frame'):
                self.kernel_fields_frame.pack_forget()
            if hasattr(self, 'dialogue_editor_frame'):
                self.dialogue_editor_frame.pack(fill="both", expand=True, pady=(0, 8))
            if hasattr(self, 'preview_frame'):
                self.preview_frame.pack(fill="both", expand=True)

        record_len = FILE_RECORD_SIZES.get(self.active_file_name, 16)
        charset = self.cmb_charset.get()
        
        self.log(f"Reading file '{self.active_file_name}' (Mode: {self.active_mode})...")
        try:
            records, min_idx, max_idx, magic_part, mode = self.codec.load_any_ffx_file(filepath, record_len, charset)
            self.records = records
            self.min_idx = min_idx
            self.max_idx = max_idx
            self.magic_part = magic_part
            self.active_mode = mode
            self.log(f"Successfully loaded {len(records)} entries (IDs {min_idx} to {max_idx}).", "success")
            
            # Update Dashboard Recent Files Config
            self.add_recent_file(filepath)
            
            self.filter_treeview()
        except Exception as e:
            self.log(f"Failed to read file: {e}", "error")
            messagebox.showerror("Read Error", f"Failed to parse binary file:\n{str(e)}")
            self.clear_table()

    def add_recent_file(self, path):
        recent = self.config.get("recent_files", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.config["recent_files"] = recent[:10]
        self.save_config()

    def load_from_absolute_path(self, filepath):
        filepath = os.path.abspath(filepath)
        if not os.path.exists(filepath):
            return
            
        norm_path = filepath.replace("\\", "/")
        parts = norm_path.split("/")
        
        try:
            if "battle" in parts and "kernel" in parts:
                b_idx = parts.index("battle")
                if parts[b_idx + 1] == "kernel":
                    loc = parts[b_idx - 1]
                    master_path = "/".join(parts[:b_idx - 1])
                    filename = parts[-1]
                    
                    self.ent_master_path.delete(0, tk.END)
                    self.ent_master_path.insert(0, os.path.abspath(master_path))
                    self.codec.ffx_master_path = os.path.abspath(master_path)
                    
                    # Scan localizations
                    self.scan_localizations()
                    
                    self.cmb_local.set(loc)
                    self.on_localization_changed()
                    
                    self.cmb_bin_file.set(filename)
                    self.on_bin_file_selected()
                    
                    self.log(f"Successfully loaded file: {filename}")
        except Exception as e:
            self.log(f"Error loading file: {e}", "error")

    def filter_treeview(self, event=None):
        query = self.ent_search.get().strip().lower()
        
        # Clear Treeview
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        mode = getattr(self, 'active_mode', 'kernel')
        total_records = len(self.records)
        visible_count = 0
            
        for r in self.records:
            name = r.get('name', '')
            sname = r.get('sname', '')
            desc = r.get('desc', '')
            sdesc = r.get('sdesc', '')
            wakka = r.get('w_wakka', '')
            lulu = r.get('w_lulu', '')
            rikku = r.get('w_rikku', '')
            
            if mode == "albhed":
                display_desc = desc
                match = (not query or query in str(r['id']) or query in name.lower() or query in desc.lower())
            elif mode != "kernel":
                display_desc = f"Ptr: 0x{r.get('ptr', 0):X}" if 'ptr' in r else ""
                match = (not query or query in str(r['id']) or query in name.lower())
            else:
                display_desc = desc if desc and desc != "-" else (sname if sname else sdesc)
                match = (not query or query in str(r['id']) or
                         query in name.lower() or query in desc.lower() or
                         query in sname.lower() or query in sdesc.lower() or
                         query in wakka.lower() or query in lulu.lower() or query in rikku.lower())
                         
            if match:
                name_clean = name.replace("\r\n", " ").replace("\n", " ")
                desc_clean = display_desc.replace("\r\n", " ").replace("\n", " ")
                row_tag = "even" if visible_count % 2 == 0 else "odd"
                self.tree.insert("", tk.END, iid=r['id'], values=(r['id'], name_clean, desc_clean), tags=(row_tag,))
                visible_count += 1
                
        if hasattr(self, 'lbl_search_count'):
            if query:
                self.lbl_search_count.config(text=f"{visible_count} of {total_records} matches")
            else:
                self.lbl_search_count.config(text=f"{total_records} entries")

    def on_tree_row_selected(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        entry_id = int(sel[0])
        # Find record in memory
        record = next((r for r in self.records if r['id'] == entry_id), None)
        if not record:
            return
            
        self.clear_editor_fields()
        mode = getattr(self, 'active_mode', 'kernel')
        name_val = record.get('name', '')
        self.ent_name.insert(0, name_val)
        if hasattr(self, 'txt_dialogue'):
            self.txt_dialogue.insert("1.0", name_val)
            self.highlight_syntax()
            
        self.ent_sname.insert(0, record.get('sname', ''))
        self.ent_desc.insert(0, record.get('desc', ''))
        self.ent_sdesc.insert(0, record.get('sdesc', ''))
        if mode == 'kernel' and self.active_file_name == "w_name.bin" and hasattr(self, 'ent_wakka'):
            self.ent_wakka.insert(0, record.get('w_wakka', ''))
            self.ent_lulu.insert(0, record.get('w_lulu', ''))
            self.ent_rikku.insert(0, record.get('w_rikku', ''))
        
        self.update_length_label()
        self.update_live_preview()

        # Populate Stats tab if applicable
        file_name = self.active_file_name
        extra_bytes = record.get('extra_bytes', b'')
        
        self.show_stats_group(file_name)
        
        if file_name == "important.bin" and len(extra_bytes) >= 4:
            self.stat_vars["primer"].set(1 if extra_bytes[0] > 0 else 0)
            self.stat_vars["unk12"].set(str(extra_bytes[2]))
            self.stat_vars["ordering"].set(str(extra_bytes[3]))
            
        elif file_name in ["item.bin", "command.bin", "monmagic1.bin", "monmagic2.bin"] and len(extra_bytes) >= 76:
            def get_b(offset):
                return extra_bytes[offset - 0x10]
                
            self.stat_vars["mp_cost"].set(str(get_b(0x25)))
            self.stat_vars["od_cost"].set(str(get_b(0x26)))
            self.stat_vars["power"].set(str(get_b(0x2A)))
            self.stat_vars["accuracy"].set(str(get_b(0x29)))
            self.stat_vars["hit_count"].set(str(get_b(0x2B)))
            
            formula_val = get_b(0x28)
            formula_str = "None (0x0)"
            for code, name in DAMAGE_FORMULAS:
                if code == formula_val:
                    formula_str = f"{name} ({hex(code)})"
                    break
            self.cmb_formula.set(formula_str)
            
            elem = get_b(0x2D)
            self.stat_vars["elem_fire"].set(1 if elem & 0x01 else 0)
            self.stat_vars["elem_ice"].set(1 if elem & 0x02 else 0)
            self.stat_vars["elem_thunder"].set(1 if elem & 0x04 else 0)
            self.stat_vars["elem_water"].set(1 if elem & 0x08 else 0)
            self.stat_vars["elem_holy"].set(1 if elem & 0x10 else 0)
            
            tgt = get_b(0x1A)
            self.stat_vars["tgt_enabled"].set(1 if tgt & 0x01 else 0)
            self.stat_vars["tgt_enemies"].set(1 if tgt & 0x02 else 0)
            self.stat_vars["tgt_multi"].set(1 if tgt & 0x04 else 0)
            self.stat_vars["tgt_self"].set(1 if tgt & 0x08 else 0)
            self.stat_vars["tgt_either"].set(1 if tgt & 0x20 else 0)
            self.stat_vars["tgt_dead"].set(1 if tgt & 0x40 else 0)
            self.stat_vars["tgt_ranged"].set(1 if tgt & 0x80 else 0)
            
            self.stat_vars["st_death"].set(str(get_b(0x2E)))
            self.stat_vars["st_zombie"].set(str(get_b(0x2F)))
            self.stat_vars["st_petrify"].set(str(get_b(0x30)))
            self.stat_vars["st_poison"].set(str(get_b(0x31)))
            self.stat_vars["st_confuse"].set(str(get_b(0x36)))
            self.stat_vars["st_berserk"].set(str(get_b(0x37)))
            self.stat_vars["st_provoke"].set(str(get_b(0x38)))
            self.stat_vars["st_threaten"].set(str(get_b(0x39)))
            self.stat_vars["st_sleep"].set(str(get_b(0x3A)))
            self.stat_vars["st_silence"].set(str(get_b(0x3B)))
            self.stat_vars["st_darkness"].set(str(get_b(0x3C)))
            self.stat_vars["st_slow"].set(str(get_b(0x46)))
            self.stat_vars["st_haste"].set(str(get_b(0x45)))

    def update_length_label(self):
        charset = self.cmb_charset.get()
        mode = getattr(self, 'active_mode', 'kernel')
        
        if mode in ("sps2", "msg") and hasattr(self, 'txt_dialogue'):
            cur_text = self.txt_dialogue.get("1.0", "end-1c")
            name_bytes = len(self.codec.encode_ffx_string(cur_text, charset))
            msg = f"Current message: {name_bytes} bytes"
            self.lbl_len_warn.config(text=msg, foreground=self.text_dim)
            return
        elif mode != "kernel":
            name_bytes = len(self.codec.encode_ffx_string(self.ent_name.get(), charset))
            msg = f"Current message: {name_bytes} bytes"
            self.lbl_len_warn.config(text=msg, foreground=self.text_dim)
            return

        name_bytes = len(self.codec.encode_ffx_string(self.ent_name.get(), charset))
        sname_bytes = len(self.codec.encode_ffx_string(self.ent_sname.get(), charset))
        desc_bytes = len(self.codec.encode_ffx_string(self.ent_desc.get(), charset))
        sdesc_bytes = len(self.codec.encode_ffx_string(self.ent_sdesc.get(), charset))
        
        total_rec_bytes = name_bytes + sname_bytes + desc_bytes + sdesc_bytes + 4
        if self.active_file_name == "w_name.bin" and hasattr(self, 'ent_wakka'):
            total_rec_bytes += len(self.codec.encode_ffx_string(self.ent_wakka.get(), charset)) + 1
            total_rec_bytes += len(self.codec.encode_ffx_string(self.ent_lulu.get(), charset)) + 1
            total_rec_bytes += len(self.codec.encode_ffx_string(self.ent_rikku.get(), charset)) + 1
        
        # Calculate current total pool size in memory
        unique_strings = set()
        for r in self.records:
            sel = self.tree.selection()
            is_current = sel and (int(sel[0]) == r['id'])
            if is_current:
                unique_strings.update([self.ent_name.get(), self.ent_sname.get(), self.ent_desc.get(), self.ent_sdesc.get()])
                if self.active_file_name == "w_name.bin" and hasattr(self, 'ent_wakka'):
                    unique_strings.update([self.ent_wakka.get(), self.ent_lulu.get(), self.ent_rikku.get()])
            else:
                unique_strings.update([r['name'], r.get('sname', ''), r.get('desc', ''), r.get('sdesc', '')])
                if self.active_file_name == "w_name.bin":
                    unique_strings.update([r.get('w_wakka', ''), r.get('w_lulu', ''), r.get('w_rikku', '')])
        
        total_pool_size = sum(len(self.codec.encode_ffx_string(s, charset)) + 1 for s in unique_strings)
        
        msg = f"Current entry: {total_rec_bytes} bytes | Total Pool: {total_pool_size} / 65535 bytes"
        self.lbl_len_warn.config(text=msg)
        
        if total_pool_size > 65535 or total_rec_bytes > 800:
            self.lbl_len_warn.config(foreground=self.error_color)
        elif total_pool_size > 60000:
            self.lbl_len_warn.config(foreground="orange")
        else:
            self.lbl_len_warn.config(foreground=self.text_dim)

    def apply_row_edits(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "No entry selected. Double-click or select an entry in the table first.")
            return
            
        entry_id = int(sel[0])
        record = next((r for r in self.records if r['id'] == entry_id), None)
        if not record:
            return
            
        mode = getattr(self, 'active_mode', 'kernel')
        charset = self.cmb_charset.get()
        
        if mode in ("sps2", "msg") and hasattr(self, 'txt_dialogue'):
            text_val = self.txt_dialogue.get("1.0", "end-1c")
            record['name'] = text_val
            name_clean = text_val.replace("\r\n", " ").replace("\n", " ")
            desc_clean = f"Ptr: 0x{record.get('ptr', 0):X}" if 'ptr' in record else ""
        elif mode == "albhed":
            record['name'] = self.ent_name.get()
            name_clean = record['name'].replace("\r\n", " ").replace("\n", " ")
            desc_clean = record.get('desc', '')
        else:
            name_bytes = len(self.codec.encode_ffx_string(self.ent_name.get(), charset))
            sname_bytes = len(self.codec.encode_ffx_string(self.ent_sname.get(), charset))
            desc_bytes = len(self.codec.encode_ffx_string(self.ent_desc.get(), charset))
            sdesc_bytes = len(self.codec.encode_ffx_string(self.ent_sdesc.get(), charset))
            total_rec_bytes = name_bytes + sname_bytes + desc_bytes + sdesc_bytes + 4
            if self.active_file_name == "w_name.bin" and hasattr(self, 'ent_wakka'):
                total_rec_bytes += len(self.codec.encode_ffx_string(self.ent_wakka.get(), charset)) + 1
                total_rec_bytes += len(self.codec.encode_ffx_string(self.ent_lulu.get(), charset)) + 1
                total_rec_bytes += len(self.codec.encode_ffx_string(self.ent_rikku.get(), charset)) + 1
            
            if total_rec_bytes > 1000:
                ans = messagebox.askyesno("Length Warning", 
                    f"This entry is extremely long ({total_rec_bytes} bytes).\n"
                    "In-game text buffers might overflow, causing text cutoff or crashes.\n\n"
                    "Do you want to apply it anyway?")
                if not ans:
                    return

            record['name'] = self.ent_name.get()
            record['sname'] = self.ent_sname.get()
            record['desc'] = self.ent_desc.get()
            record['sdesc'] = self.ent_sdesc.get()
            if self.active_file_name == "w_name.bin" and hasattr(self, 'ent_wakka'):
                record['w_wakka'] = self.ent_wakka.get()
                record['w_lulu'] = self.ent_lulu.get()
                record['w_rikku'] = self.ent_rikku.get()
            
            name_clean = record['name'].replace("\r\n", " ").replace("\n", " ")
            desc_clean = record['desc'].replace("\r\n", " ").replace("\n", " ")
        
        # Update tree row display
        self.tree.item(entry_id, values=(record['id'], name_clean, desc_clean))
        self.log(f"Applied modifications in-memory to entry ID {entry_id}.")
        self.update_length_label()
        self.update_live_preview()

    def export_csv(self):
        if not self.records:
            messagebox.showwarning("Warning", "No active table loaded. Load a file first.")
            return
            
        def clean_csv_cell(val):
            # Replace actual newlines with {\n} so each record stays strictly on a single row
            return str(val).replace("\r\n", "{\\n}").replace("\n", "{\\n}").replace("\r", "{\\n}")

        mode = getattr(self, 'active_mode', 'kernel')
        num_files_in_cat = len(getattr(self, 'file_map', {}))

        # Ask user for Single vs Batch mode
        ans = messagebox.askyesnocancel("Export CSV Mode",
            f"Do you want to export ALL files in the current category in one batch?\n\n"
            f"Select 'Yes' to batch export all {num_files_in_cat} files in this category to CSV.\n"
            "Select 'No' to export only the currently active file to a single CSV file.")
            
        if ans is None:
            return
            
        if ans is True:
            # Batch mode
            target_dir = filedialog.askdirectory(title="Select Target Folder for Batch CSV Export")
            if not target_dir:
                return
                
            charset = self.cmb_charset.get()
            exported = []
            
            for key, fpath in getattr(self, 'file_map', {}).items():
                safe_name = key.replace("/", "_").replace("\\", "_")
                csv_path = os.path.join(target_dir, f"{os.path.splitext(safe_name)[0]}.csv")
                try:
                    recs, min_id, max_id, magic, fmode = self.codec.load_any_ffx_file(fpath, 16, charset)
                    with open(csv_path, "w", encoding="utf-8", newline="") as f:
                        writer = csv.writer(f)
                        if fmode == "kernel":
                            if os.path.basename(fpath) == "w_name.bin":
                                writer.writerow(["ID", "Name", "SimplifiedName", "Description", "SimplifiedDescription", "Wakka", "Lulu", "Rikku"])
                                for r in recs:
                                    writer.writerow([
                                        r['id'],
                                        clean_csv_cell(r['name']),
                                        clean_csv_cell(r['sname']),
                                        clean_csv_cell(r['desc']),
                                        clean_csv_cell(r['sdesc']),
                                        clean_csv_cell(r.get('w_wakka', '')),
                                        clean_csv_cell(r.get('w_lulu', '')),
                                        clean_csv_cell(r.get('w_rikku', ''))
                                    ])
                            else:
                                writer.writerow(["ID", "Name", "SimplifiedName", "Description", "SimplifiedDescription"])
                                for r in recs:
                                    writer.writerow([
                                        r['id'],
                                        clean_csv_cell(r['name']),
                                        clean_csv_cell(r['sname']),
                                        clean_csv_cell(r['desc']),
                                        clean_csv_cell(r['sdesc'])
                                    ])
                        else:
                            writer.writerow(["ID", "Text"])
                            for r in recs:
                                writer.writerow([r['id'], clean_csv_cell(r['name'])])
                    exported.append(key)
                except Exception as e:
                    self.log(f"Failed to batch export '{key}': {e}", "error")
            
            if exported:
                self.log(f"Successfully batch exported {len(exported)} files to CSV in: {target_dir}", "success")
                messagebox.showinfo("Export Successful", f"Batch export completed successfully!\n\nExported {len(exported)} files.")
            else:
                messagebox.showerror("Export Error", "No files were successfully exported.")
        else:
            # Single file mode
            base_safe = self.active_file_name.replace('.bin', '').replace('.sps2', '')
            save_path = filedialog.asksaveasfilename(
                title="Export Table to CSV",
                filetypes=[("CSV Files", "*.csv")],
                defaultextension=".csv",
                initialfile=f"{base_safe}_export.csv"
            )
            if not save_path:
                return
                
            self.log(f"Exporting entries to CSV: {save_path}...")
            try:
                with open(save_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    if mode == "kernel":
                        if self.active_file_name == "w_name.bin":
                            writer.writerow(["ID", "Name", "SimplifiedName", "Description", "SimplifiedDescription", "Wakka", "Lulu", "Rikku"])
                            for r in self.records:
                                writer.writerow([
                                    r['id'],
                                    clean_csv_cell(r['name']),
                                    clean_csv_cell(r['sname']),
                                    clean_csv_cell(r['desc']),
                                    clean_csv_cell(r['sdesc']),
                                    clean_csv_cell(r.get('w_wakka', '')),
                                    clean_csv_cell(r.get('w_lulu', '')),
                                    clean_csv_cell(r.get('w_rikku', ''))
                                ])
                        else:
                            writer.writerow(["ID", "Name", "SimplifiedName", "Description", "SimplifiedDescription"])
                            for r in self.records:
                                writer.writerow([
                                    r['id'],
                                    clean_csv_cell(r['name']),
                                    clean_csv_cell(r['sname']),
                                    clean_csv_cell(r['desc']),
                                    clean_csv_cell(r['sdesc'])
                                ])
                    else:
                        writer.writerow(["ID", "Text"])
                        for r in self.records:
                            writer.writerow([r['id'], clean_csv_cell(r['name'])])
                self.log(f"Successfully exported {len(self.records)} rows to CSV.", "success")
                messagebox.showinfo("Export Successful", f"Successfully exported all records to:\n{save_path}")
            except Exception as e:
                self.log(f"CSV Export failed: {e}", "error")
                messagebox.showerror("Export Error", f"Failed to save CSV file:\n{str(e)}")

    def import_csv(self):
        if not self.records:
            messagebox.showwarning("Warning", "Load the target table file in the editor first.")
            return
            
        def restore_csv_cell(val):
            # Convert {\n} placeholders back into FFX line breaks
            if not val:
                return ""
            return val.replace("{\\n}", "\n").replace("{/n}", "\n").replace("{n}", "\n")

        mode = getattr(self, 'active_mode', 'kernel')
        num_files_in_cat = len(getattr(self, 'file_map', {}))

        # Ask user for Single vs Batch mode
        ans = messagebox.askyesnocancel("Import CSV Mode",
            f"Do you want to batch import CSV translation files for this category?\n\n"
            f"Select 'Yes' to batch import and update all matching files ({num_files_in_cat} files in this category).\n"
            "Select 'No' to import into the currently active table from a single CSV file.")
            
        if ans is None:
            return
            
        if ans is True:
            # Batch import mode
            source_dir = filedialog.askdirectory(title="Select Folder containing CSV Files")
            if not source_dir:
                return
                
            charset = self.cmb_charset.get()
            imported = []
            
            for key, fpath in getattr(self, 'file_map', {}).items():
                safe_name = key.replace("/", "_").replace("\\", "_")
                base_cand = os.path.splitext(safe_name)[0]
                csv_cand1 = os.path.join(source_dir, f"{base_cand}.csv")
                csv_cand2 = os.path.join(source_dir, f"{base_cand}_export.csv")
                csv_path = csv_cand1 if os.path.exists(csv_cand1) else (csv_cand2 if os.path.exists(csv_cand2) else None)
                
                if csv_path:
                    try:
                        recs, min_id, max_id, magic, fmode = self.codec.load_any_ffx_file(fpath, 16, charset)
                        imported_count = 0
                        with open(csv_path, "r", encoding="utf-8") as f:
                            reader = csv.reader(f)
                            header = next(reader, None)
                            if not header: continue
                            for row in reader:
                                if not row: continue
                                try:
                                    rid = int(row[0])
                                    record = next((r for r in recs if r['id'] == rid), None)
                                    if record:
                                        if len(row) > 1:
                                            if fmode == "kernel":
                                                record['name'] = restore_csv_cell(row[1])
                                                if len(row) > 2: record['sname'] = restore_csv_cell(row[2])
                                                if len(row) > 3: record['desc'] = restore_csv_cell(row[3])
                                                if len(row) > 4: record['sdesc'] = restore_csv_cell(row[4])
                                                if len(row) >= 8 and os.path.basename(fpath) == "w_name.bin":
                                                    record['w_wakka'] = restore_csv_cell(row[5])
                                                    record['w_lulu'] = restore_csv_cell(row[6])
                                                    record['w_rikku'] = restore_csv_cell(row[7])
                                            else:
                                                record['name'] = restore_csv_cell(row[1])
                                            imported_count += 1
                                except ValueError:
                                    continue
                                    
                        if imported_count > 0:
                            bak_path = fpath + ".bak"
                            if not os.path.exists(bak_path):
                                import shutil
                                shutil.copy2(fpath, bak_path)
                            self.codec.save_any_ffx_file(fpath, recs, min_id, max_id, magic, charset)
                            imported.append((key, imported_count))
                    except Exception as e:
                        self.log(f"Failed to batch import '{key}': {e}", "error")
            
            if imported:
                summary_msg = "\n".join(f"- {name}: {count} rows" for name, count in imported[:15])
                if len(imported) > 15:
                    summary_msg += f"\n...and {len(imported) - 15} more files."
                self.log(f"Successfully batch imported updates for {len(imported)} files from: {source_dir}", "success")
                self.on_bin_file_selected()
                messagebox.showinfo("Import Successful", f"Batch import completed successfully!\n\nImported updates:\n{summary_msg}")
            else:
                messagebox.showerror("Import Error", "No matching CSV files were found or imported.")
                
        else:
            # Single file mode
            open_path = filedialog.askopenfilename(
                title="Import Table from CSV",
                filetypes=[("CSV Files", "*.csv")]
            )
            if not open_path:
                return
                
            self.log(f"Importing entries from CSV: {open_path}...")
            try:
                imported_count = 0
                with open(open_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if not header:
                        raise ValueError("CSV file is empty.")
                        
                    for row in reader:
                        if not row: continue
                        try:
                            rid = int(row[0])
                            record = next((r for r in self.records if r['id'] == rid), None)
                            if record:
                                if len(row) > 1:
                                    if mode == "kernel":
                                        record['name'] = restore_csv_cell(row[1])
                                        if len(row) > 2: record['sname'] = restore_csv_cell(row[2])
                                        if len(row) > 3: record['desc'] = restore_csv_cell(row[3])
                                        if len(row) > 4: record['sdesc'] = restore_csv_cell(row[4])
                                        if len(row) >= 8 and self.active_file_name == "w_name.bin":
                                            record['w_wakka'] = restore_csv_cell(row[5])
                                            record['w_lulu'] = restore_csv_cell(row[6])
                                            record['w_rikku'] = restore_csv_cell(row[7])
                                    else:
                                        record['name'] = restore_csv_cell(row[1])
                                    imported_count += 1
                        except ValueError:
                            continue
                            
                self.log(f"Successfully imported {imported_count} updates from CSV. Refreshing table view...", "success")
                self.filter_treeview()
                self.clear_editor_fields()
                messagebox.showinfo("Import Successful", f"Successfully imported {imported_count} translations from CSV.\n\nClick 'Repack & Save' to write changes to disk.")
            except Exception as e:
                self.log(f"CSV Import failed: {e}", "error")
                messagebox.showerror("Import Error", f"Failed to load CSV file:\n{str(e)}")

    def open_search_replace_dialog(self):
        if not self.records:
            messagebox.showwarning("Warning", "Load the target table file in the editor first.")
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Global Search & Replace")
        dialog.geometry("450x250")
        dialog.resizable(False, False)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.columnconfigure(1, weight=1)
        
        ttk.Label(dialog, text="Find Text:").grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        ent_find = ttk.Entry(dialog, width=40)
        ent_find.grid(row=0, column=1, sticky="ew", padx=15, pady=(15, 5))
        
        ttk.Label(dialog, text="Replace With:").grid(row=1, column=0, sticky="w", padx=15, pady=5)
        ent_replace = ttk.Entry(dialog, width=40)
        ent_replace.grid(row=1, column=1, sticky="ew", padx=15, pady=5)
        
        ttk.Label(dialog, text="Scope:").grid(row=2, column=0, sticky="w", padx=15, pady=5)
        cmb_scope = ttk.Combobox(dialog, state="readonly", values=["Current File only", "Current Category files", "All Files in Localization"])
        cmb_scope.grid(row=2, column=1, sticky="w", padx=15, pady=5)
        cmb_scope.set("Current File only")
        
        var_case = tk.BooleanVar(value=False)
        chk_case = ttk.Checkbutton(dialog, text="Case Sensitive", variable=var_case)
        chk_case.grid(row=3, column=1, sticky="w", padx=15, pady=5)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=15, pady=15)
        
        def run_replace():
            find_txt = ent_find.get()
            replace_txt = ent_replace.get()
            scope = cmb_scope.get()
            case_sens = var_case.get()
            
            if not find_txt:
                messagebox.showwarning("Warning", "Please enter text to find.")
                return
                
            if scope == "Current File only":
                count = 0
                if self.active_mode == 'kernel':
                    fields = ['name', 'sname', 'desc', 'sdesc']
                    if self.active_file_name == "w_name.bin":
                        fields.extend(['w_wakka', 'w_lulu', 'w_rikku'])
                else:
                    fields = ['name']

                for r in self.records:
                    for field in fields:
                        orig = r.get(field, "")
                        if not orig:
                            continue
                        if not case_sens:
                            import re
                            pattern = re.compile(re.escape(find_txt), re.IGNORECASE)
                            new_val, sub_count = pattern.subn(replace_txt, orig)
                        else:
                            new_val = orig.replace(find_txt, replace_txt)
                            sub_count = orig.count(find_txt)
                        if sub_count > 0:
                            r[field] = new_val
                            count += sub_count
                if count > 0:
                    self.log(f"Search & Replace: Replaced {count} occurrences of '{find_txt}' with '{replace_txt}' in current file memory.", "success")
                    self.filter_treeview()
                    self.clear_editor_fields()
                    messagebox.showinfo("Success", f"Replaced {count} occurrences in the current file.\n\nNote: Changes are in-memory. Click 'Repack & Save' to write them to disk.")
                    dialog.destroy()
                else:
                    messagebox.showinfo("Search & Replace", "No occurrences found.")
            elif scope == "Current Category files":
                cat_name = self.cmb_category.get()
                ans = messagebox.askyesno("Confirm Category Action",
                    f"This will read, modify, and save all {len(self.file_map)} files in the active category: '{cat_name}'.\n"
                    "Automatic backup files (.bak) will be created for any modified files.\n\n"
                    "Are you sure you want to perform this category-wide replacement?")
                if not ans:
                    return

                charset = self.cmb_charset.get()
                modified_files = []
                total_replaced = 0

                for fname, fpath in self.file_map.items():
                    try:
                        recs, min_id, max_id, magic, mode = self.codec.load_any_ffx_file(fpath, 16, charset)
                        file_mod = False
                        file_replaced = 0
                        fields = ['name', 'sname', 'desc', 'sdesc'] if mode == 'kernel' else ['name']
                        if fname == "w_name.bin":
                            fields.extend(['w_wakka', 'w_lulu', 'w_rikku'])

                        for r in recs:
                            for field in fields:
                                orig = r.get(field, "")
                                if not orig:
                                    continue
                                if not case_sens:
                                    import re
                                    pattern = re.compile(re.escape(find_txt), re.IGNORECASE)
                                    new_val, sub_count = pattern.subn(replace_txt, orig)
                                else:
                                    new_val = orig.replace(find_txt, replace_txt)
                                    sub_count = orig.count(find_txt)
                                if sub_count > 0:
                                    r[field] = new_val
                                    file_replaced += sub_count
                                    file_mod = True
                        if file_mod:
                            bak_path = fpath + ".bak"
                            if not os.path.exists(bak_path):
                                import shutil
                                shutil.copy2(fpath, bak_path)
                            self.codec.save_any_ffx_file(fpath, recs, min_id, max_id, magic, charset)
                            modified_files.append(fname)
                            total_replaced += file_replaced
                    except Exception as e:
                        self.log(f"Failed to process '{fname}' for replacement: {e}", "error")

                if total_replaced > 0:
                    self.log(f"Category Search & Replace: Replaced {total_replaced} occurrences across files: {', '.join(modified_files)}", "success")
                    self.on_bin_file_selected()
                    messagebox.showinfo("Success", f"Replaced {total_replaced} occurrences across {len(modified_files)} files in category '{cat_name}':\n\n" + "\n".join(modified_files[:15]) + ("\n..." if len(modified_files) > 15 else ""))
                    dialog.destroy()
                else:
                    messagebox.showinfo("Search & Replace", f"No occurrences found in category '{cat_name}'.")
            else:
                loc = self.cmb_local.get()
                loc_dir = os.path.join(self.codec.ffx_master_path, loc)
                all_files = []
                
                # Gather files across all categories
                kernel_dir = os.path.join(loc_dir, "battle", "kernel")
                if os.path.exists(kernel_dir):
                    for f in os.listdir(kernel_dir):
                        if f.endswith(".bin") and f in FILE_RECORD_SIZES:
                            all_files.append((f"kernel/{f}", os.path.join(kernel_dir, f)))
                help_dir = os.path.join(loc_dir, "help")
                if os.path.exists(help_dir):
                    for root, dirs, files in os.walk(help_dir):
                        for f in files:
                            if f.endswith(".sps2"):
                                all_files.append((f"help/{f}", os.path.join(root, f)))
                evt_dir = os.path.join(loc_dir, "event", "obj_ps3")
                if not os.path.exists(evt_dir):
                    evt_dir = os.path.join(loc_dir, "event", "obj_psv")
                if not os.path.exists(evt_dir):
                    evt_dir = os.path.join(loc_dir, "event")
                if os.path.exists(evt_dir):
                    for root, dirs, files in os.walk(evt_dir):
                        for f in files:
                            if f.endswith(".bin"):
                                all_files.append((f"event/{f}", os.path.join(root, f)))
                btl_dir = os.path.join(loc_dir, "battle", "btl")
                if os.path.exists(btl_dir):
                    for root, dirs, files in os.walk(btl_dir):
                        for f in files:
                            if f.endswith(".bin"):
                                all_files.append((f"btl/{f}", os.path.join(root, f)))
                menu_dir = os.path.join(loc_dir, "menu")
                if os.path.exists(menu_dir):
                    for f in os.listdir(menu_dir):
                        if f.endswith(".bin") and not f.startswith("ffxsjis"):
                            all_files.append((f"menu/{f}", os.path.join(menu_dir, f)))
                cloud_dir = os.path.join(loc_dir, "cloudsave")
                if os.path.exists(cloud_dir):
                    for f in os.listdir(cloud_dir):
                        if f.endswith(".bin"):
                            all_files.append((f"cloud/{f}", os.path.join(cloud_dir, f)))

                ans = messagebox.askyesno("Confirm Global Action",
                    f"This will scan, modify, and save across all {len(all_files)} supported files in '{loc}'.\n"
                    "Automatic backup files (.bak) will be created for any modified files.\n\n"
                    "Are you sure you want to perform this global replacement?")
                if not ans:
                    return

                charset = self.cmb_charset.get()
                modified_files = []
                total_replaced = 0

                for disp_name, fpath in all_files:
                    try:
                        recs, min_id, max_id, magic, mode = self.codec.load_any_ffx_file(fpath, 16, charset)
                        file_mod = False
                        file_replaced = 0
                        fields = ['name', 'sname', 'desc', 'sdesc'] if mode == 'kernel' else ['name']
                        if "w_name.bin" in fpath.lower():
                            fields.extend(['w_wakka', 'w_lulu', 'w_rikku'])

                        for r in recs:
                            for field in fields:
                                orig = r.get(field, "")
                                if not orig:
                                    continue
                                if not case_sens:
                                    import re
                                    pattern = re.compile(re.escape(find_txt), re.IGNORECASE)
                                    new_val, sub_count = pattern.subn(replace_txt, orig)
                                else:
                                    new_val = orig.replace(find_txt, replace_txt)
                                    sub_count = orig.count(find_txt)
                                if sub_count > 0:
                                    r[field] = new_val
                                    file_replaced += sub_count
                                    file_mod = True
                        if file_mod:
                            bak_path = fpath + ".bak"
                            if not os.path.exists(bak_path):
                                import shutil
                                shutil.copy2(fpath, bak_path)
                            self.codec.save_any_ffx_file(fpath, recs, min_id, max_id, magic, charset)
                            modified_files.append(disp_name)
                            total_replaced += file_replaced
                    except Exception as e:
                        self.log(f"Failed to process '{disp_name}' for replacement: {e}", "error")

                if total_replaced > 0:
                    self.log(f"Global Search & Replace: Replaced {total_replaced} occurrences across files: {', '.join(modified_files)}", "success")
                    self.on_bin_file_selected()
                    messagebox.showinfo("Success", f"Replaced {total_replaced} occurrences across {len(modified_files)} files:\n\n" + "\n".join(modified_files[:20]) + ("\n..." if len(modified_files) > 20 else ""))
                    dialog.destroy()
                else:
                    messagebox.showinfo("Search & Replace", "No occurrences found in any files.")
        
        btn_run = tk.Button(btn_frame, text="Run Replace", command=run_replace, bg=self.accent_color, fg="white",
                             font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.accent_hover, activeforeground="white", padx=15, pady=4)
        btn_run.pack(side="right")
        self.bind_hover(btn_run, is_primary=True)
        
        btn_cancel = tk.Button(btn_frame, text="Cancel", command=dialog.destroy, bg=self.card_color, fg=self.text_color,
                               font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=15, pady=4)
        btn_cancel.pack(side="left")
        self.bind_hover(btn_cancel)

    def save_bin_file(self):
        if not self.records or not self.active_file_path:
            messagebox.showwarning("Warning", "No active file loaded to save.")
            return
            
        # Double check if any editing is unsaved in entry boxes
        sel = self.tree.selection()
        if sel:
            entry_id = int(sel[0])
            record = next((r for r in self.records if r['id'] == entry_id), None)
            if record:
                if self.active_mode == 'kernel':
                    has_unapplied = (
                        record['name'] != self.ent_name.get() or 
                        record['sname'] != self.ent_sname.get() or 
                        record['desc'] != self.ent_desc.get() or 
                        record['sdesc'] != self.ent_sdesc.get()
                    )
                    if self.active_file_name == "w_name.bin" and hasattr(self, 'ent_wakka'):
                        if (record.get('w_wakka', '') != self.ent_wakka.get() or
                            record.get('w_lulu', '') != self.ent_lulu.get() or
                            record.get('w_rikku', '') != self.ent_rikku.get()):
                            has_unapplied = True
                elif self.active_mode in ('sps2', 'msg') and hasattr(self, 'txt_dialogue'):
                    has_unapplied = (record.get('name', '') != self.txt_dialogue.get("1.0", "end-1c"))
                else:
                    has_unapplied = (record.get('name', '') != self.ent_name.get())

                if has_unapplied:
                    ans = messagebox.askyesnocancel("Unapplied Edits", 
                        f"Entry ID {entry_id} has modifications in the editor boxes that haven't been applied to the table.\n\n"
                        "Do you want to apply these modifications before saving?")
                    if ans is True:
                        self.apply_row_edits()
                    elif ans is None:
                        return
                        
        charset = self.cmb_charset.get()
        
        # Verify safeguard on total pool size for 16-bit offset kernel tables
        if self.active_mode == 'kernel':
            unique_strings = set()
            for r in self.records:
                unique_strings.update([r['name'], r['sname'], r['desc'], r['sdesc']])
                if self.active_file_name == "w_name.bin":
                    unique_strings.update([r.get('w_wakka', ''), r.get('w_lulu', ''), r.get('w_rikku', '')])
            total_pool_size = sum(len(self.codec.encode_ffx_string(s, charset)) + 1 for s in unique_strings)
            
            if total_pool_size > 65535:
                messagebox.showerror("Save Blocked", 
                    f"The total unique string pool size is {total_pool_size} bytes, which exceeds the 16-bit offset limit of 65,535 bytes.\n\n"
                    "Saving now would corrupt the binary file and crash the game.\n"
                    "Please shorten your dialogue edits before saving.")
                return

        self.log(f"Repacking file to {self.active_file_path} (Mode: {self.active_mode}, Charset: {charset})...")
        
        try:
            bak_path = self.active_file_path + ".bak"
            if not os.path.exists(bak_path):
                import shutil
                shutil.copy2(self.active_file_path, bak_path)
                self.log(f"Created a backup copy of the original file at {bak_path}")
                
            written_size = self.codec.save_any_ffx_file(
                self.active_file_path,
                self.records,
                self.min_idx,
                self.max_idx,
                self.magic_part,
                charset
            )
            
            self.log(f"Repack complete! Successfully saved {written_size} bytes to '{self.active_file_name}'.", "success")
            messagebox.showinfo("Save Successful", f"File repacked successfully!\n\nFile: {self.active_file_name}\nBytes: {written_size}")
        except Exception as e:
            self.log(f"Repack failed: {e}", "error")
            messagebox.showerror("Save Error", f"Failed to repack and save file:\n{str(e)}")

    def bind_hover(self, btn, is_primary=False):
        if is_primary:
            btn.bind("<Enter>", lambda e: btn.config(bg=self.accent_hover))
            btn.bind("<Leave>", lambda e: btn.config(bg=self.accent_color))
        else:
            btn.bind("<Enter>", lambda e: btn.config(bg=self.border_color))
            btn.bind("<Leave>", lambda e: btn.config(bg=self.card_color))

    def show_cheat_sheet_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("FFX In-Game Control Tags Cheat Sheet")
        dialog.geometry("680x560")
        dialog.minsize(580, 420)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)

        # Center relative to main window
        dialog.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        dx = rx + max(0, (rw - 680) // 2)
        dy = ry + max(0, (rh - 560) // 2)
        dialog.geometry(f"+{dx}+{dy}")

        header = ttk.Frame(dialog, padding=(18, 14, 18, 6))
        header.pack(fill="x")
        tk.Label(header, text="FFX In-Game Control Tags Cheat Sheet", font=("Segoe UI", 13, "bold"), fg=self.accent_color, bg=self.bg_color).pack(anchor="w")
        tk.Label(header, text="These tags represent special engine bytecodes (colors, pauses, speakers, variables, and line feeds).", font=("Segoe UI", 9), fg=self.text_dim, bg=self.bg_color).pack(anchor="w", pady=(3, 0))

        content_frame = ttk.Frame(dialog, padding=(18, 6, 18, 10))
        content_frame.pack(fill="both", expand=True)

        txt = tk.Text(content_frame, bg="#131418", fg="#e5e7eb", font=("Segoe UI", 9), wrap="word", relief="flat", highlightthickness=1, highlightbackground=self.border_color, padx=12, pady=12)
        scroll = ttk.Scrollbar(content_frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=scroll.set)
        txt.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        txt.tag_config("sec_title", font=("Segoe UI", 10, "bold"), foreground=self.accent_color)
        txt.tag_config("tag_name", font=("Consolas", 10, "bold"), foreground="#6ee7b7")
        txt.tag_config("tag_sub", font=("Segoe UI", 9, "bold"), foreground="#f3f4f6")
        txt.tag_config("tag_desc", font=("Segoe UI", 9), foreground="#d1d5db")
        txt.tag_config("tag_ex", font=("Consolas", 9), foreground="#93c5fd")

        sections = [
            ("Formatting & Flow Control", [
                (r"\n or {\n}", "Line Break", "Advances text to the next row in the text box. In CSV files, line feeds are exported as {\\n} to prevent breaking spreadsheet rows.", r"Welcome!\nHow can I help you?"),
                ("{PAUSE}", "Player Input Pause", "Freezes text display until the player presses the confirm button or voiceover finishes.", r"Wait...{PAUSE}\nDid you hear that?"),
                ("{SPACE:XX}", "Horizontal Spacing (Pixels)", "Adds horizontal space in pixels (hex 00-FF). Useful for alignment, indenting, and tabulating.", r"{SPACE:0A}Option A"),
                ("{TIME:XX}", "Timed Delay (Frames)", "Waits XX frames before continuing text. Used in cutscenes to sync text with voice acting and gestures.", r"{TIME:1E}Now!")
            ]),
            ("Text Colors ({CLR:...})", [
                ("{CLR:WHITE}", "Default White", "Standard dialogue text color (byte 0x41).", "{CLR:WHITE}Standard message text"),
                ("{CLR:YELLOW}", "Highlight Yellow", "Used for key terms, location names, and items (byte 0x43).", "{CLR:YELLOW}Overdrive{CLR:WHITE}"),
                ("{CLR:GREY}", "Disabled / Subdued", "Used for inactive commands, footnotes, and disabled choices (byte 0x52).", "{CLR:GREY}(Inactive)"),
                ("{CLR:BLUE}", "Beneficial Blue", "Used for positive status effects, support magic, and helpful tips (byte 0x88).", "{CLR:BLUE}Haste{CLR:WHITE}"),
                ("{CLR:RED}", "Danger Red", "Used for debuffs, warnings, and boss attacks (byte 0x94).", "{CLR:RED}Doom{CLR:WHITE}"),
                ("{CLR:PINK}", "Pink / Special", "Used for special emphasis and rare prompts (byte 0x97).", "{CLR:PINK}Special Event{CLR:WHITE}"),
                ("{CLR:OL_PURPLE}", "Outlined Purple", "Outlined purple styling (byte 0xA1).", "{CLR:OL_PURPLE}Title"),
                ("{CLR:OL_CYAN}", "Outlined Cyan", "Outlined cyan styling (byte 0xB1).", "{CLR:OL_CYAN}Notice")
            ]),
            ("Speakers, Characters & Names", [
                ("{PC:XX}", "Playable Character", "00=Tidus, 01=Yuna, 02=Auron, 03=Kimahri, 04=Wakka, 05=Lulu, 06=Rikku, 07=Seymour. In cutscenes, placing this on line 1 sets the speaker nameplate.", "{PC:00}\nI am with you!"),
                ("{MCR:sXXlYY}", "Macro String Reference", "Fetches dynamic character, NPC, or location names from engine text bank XX, line YY. E.g. {MCR:s06l63}=Seymour, {MCR:s06l40}=Tromell, {MCR:s0Dl33}=Spira.", "{MCR:s06l63}\nThat is enough, {MCR:s06l40}."),
                ("{VAR:XX}", "Numeric Game Variable", "Live in-game numeric values (Gil, sphere level, timer, score, countdown).", "Obtained: {VAR:01} Gil"),
                ("{KEY:XX}", "Key Item Name", "Dynamically displays the name of Key Item index XX from inventory tables.", "Received {KEY:04}!")
            ]),
            ("Interactive Choices & Menus", [
                ("{CHOICE:XX}", "Choice Option", "Defines selectable choices in dialogue prompts. XX is option index (00, 01, etc.).", "{CHOICE:00} Yes\n{CHOICE:01} No{CHOICE-END}"),
                ("{CHOICE-END}", "End Choice Box", "Terminates the list of selectable options in a choice prompt.", "{CHOICE:00} Fight\n{CHOICE:01} Flee{CHOICE-END}")
            ]),
            ("Presentation & Internal Packets", [
                ("{CTRL:XX}", "Screen Presentation", "UI control byte used in .sps2 tutorial and Monster Arena screens (e.g. {CTRL:F0}).", " {CTRL:F0}"),
                ("{CMD:XX:YY}", "Raw Engine Bytecode", "Preserves unmapped 2-byte bytecode commands without data corruption.", "{CMD:28:01}")
            ])
        ]

        for sec_title, items in sections:
            txt.insert("end", f"■ {sec_title}\n\n", "sec_title")
            for tag, name, desc, example in items:
                txt.insert("end", f"  • {tag}", "tag_name")
                txt.insert("end", f"  —  {name}\n", "tag_sub")
                txt.insert("end", f"     {desc}\n", "tag_desc")
                txt.insert("end", f"     Example: {example}\n\n", "tag_ex")

        txt.configure(state="disabled")

        btn_close = tk.Button(dialog, text="Close", command=dialog.destroy, bg=self.card_color, fg=self.text_color,
                              font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=16, pady=4)
        btn_close.pack(pady=(0, 12))
        self.bind_hover(btn_close)

    def show_about_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("About FFX Text Tool")
        dialog.geometry("450x300")
        dialog.resizable(False, False)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog relative to main window
        dialog.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        dx = rx + max(0, (rw - 450) // 2)
        dy = ry + max(0, (rh - 300) // 2)
        dialog.geometry(f"+{dx}+{dy}")

        card = ttk.Frame(dialog, padding=20)
        card.pack(fill="both", expand=True, padx=15, pady=15)

        lbl_title = tk.Label(
            card,
            text="FFX Text & Dialogue Editor",
            font=("Segoe UI", 14, "bold"),
            fg=self.accent_color,
            bg=self.bg_color
        )
        lbl_title.pack(pady=(0, 6))

        lbl_ver = tk.Label(
            card,
            text=f"Version: {APP_VERSION}",
            font=("Segoe UI", 10, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        lbl_ver.pack(pady=(0, 4))

        lbl_author = tk.Label(
            card,
            text=f"Tool Creator: {AUTHOR}",
            font=("Segoe UI", 10),
            fg=self.text_dim,
            bg=self.bg_color
        )
        lbl_author.pack(pady=(0, 12))

        lbl_web_desc = tk.Label(
            card,
            text="Visit Website:",
            font=("Segoe UI", 9),
            fg=self.text_dim,
            bg=self.bg_color
        )
        lbl_web_desc.pack(pady=(0, 2))

        lbl_link = tk.Label(
            card,
            text=WEBSITE_URL,
            font=("Segoe UI", 10, "underline"),
            fg=self.accent_color,
            bg=self.bg_color,
            cursor="hand2"
        )
        lbl_link.pack(pady=(0, 20))
        lbl_link.bind("<Button-1>", lambda e: webbrowser.open_new(WEBSITE_URL))
        lbl_link.bind("<Enter>", lambda e: lbl_link.config(fg=self.accent_hover))
        lbl_link.bind("<Leave>", lambda e: lbl_link.config(fg=self.accent_color))

        btn_close = tk.Button(
            card,
            text="Close",
            command=dialog.destroy,
            bg=self.card_color,
            fg=self.text_color,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            activebackground=self.border_color,
            activeforeground=self.text_color,
            padx=20,
            pady=4
        )
        btn_close.pack(side="bottom")
        self.bind_hover(btn_close)

def main():
    root = tk.Tk()
    # Apply dark mode window border coloring on modern Windows if possible
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
        
    app = FFXTextToolGUI(root, is_embedded=False)
    root.mainloop()

if __name__ == "__main__":
    main()
