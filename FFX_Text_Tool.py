import os
import sys
import csv
import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import struct
import shutil
import webbrowser

APP_VERSION = "v2.0.0"
AUTHOR = "NfgOdin"
WEBSITE_URL = "https://nfgodin.github.io/"

def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

# Add current folder to sys.path to load ffx_codec and canonical_lore
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
        # FFX-2 Extended Tables
        "acc.bin": 16, "accessory.bin": 16, "dress.bin": 16, "monmagic.bin": 92,
    }

try:
    from canonical_lore import CANONICAL_LORE_GLOSSARY
except ImportError:
    CANONICAL_LORE_GLOSSARY = []

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
        self.speaker_bg = "#0e1e3e"
        self.speaker_fg = "#38bdf8"
        
        # Translation Memory & Interactive Choice States (Pillars 3 & 5)
        self.translation_memory = {}
        self.active_tm_suggestion = None
        self.active_choice_idx = 0
        self.total_choices = 0
        self.is_dirty = False
        self.current_entry_id = None
        
        # Tooltip Controller
        self.tag_tooltip = ToolTip(self.root)
        self.root.bind("<Button-1>", lambda e: self.tag_tooltip.hide(), add="+")
        
        if not is_embedded:
            self.root.title("FFX Text & Dialogue Editor")
            self.root.geometry("1180x760")
            self.root.minsize(960, 640)
            self.root.configure(bg=self.bg_color)
            self.root.protocol("WM_DELETE_WINDOW", self.on_window_closing)
            
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
        self.macro_db = {}
        
        # Load Config
        self.config = self.load_config()
        self.active_game = self.config.get("active_game", "Final Fantasy X")
        if not is_embedded:
            self.root.title(f"{self.active_game} - Text & Localization Studio {APP_VERSION}")
            
        # Prompt blink & audit state
        self._blink_state = False
        self._prompt_after_id = None
        self._has_pause_prompt = False
        self.current_audit_issues = []
        self.batch_rules = []

        self.create_widgets()
        self.apply_theme(self.active_game)

        if not is_embedded:
            self.build_menu_bar()
            self.setup_global_shortcuts()
            
        self._start_prompt_blink()
        
        # Auto-detect game directory
        self.auto_detect_directory()
        
        # Load macro dictionary
        self.load_macro_dictionary()

    def apply_theme(self, game_target=None):
        """
        Universal FFX & FFX-2 Engine Switcher Palette (Pillar 1).
        Adapts UI accents, dialogue borders, and theme elements:
        - Final Fantasy X: Sin Blue (#3b82f6)
        - Final Fantasy X-2: Celsius Purple (#a855f7)
        """
        if game_target is None:
            game_target = getattr(self, 'active_game', "Final Fantasy X")
        
        is_x2 = ("X-2" in game_target)
        if is_x2:
            self.accent_color = "#a855f7"      # Celsius Purple
            self.accent_hover = "#9333ea"
            self.preview_border = "#9333ea"
            self.preview_bg = "#12091e"
            self.speaker_bg = "#280e3e"
            self.speaker_fg = "#c084fc"
        else:
            self.accent_color = "#3b82f6"      # Sin Blue
            self.accent_hover = "#2563eb"
            self.preview_border = "#2563eb"
            self.preview_bg = "#070c18"
            self.speaker_bg = "#0e1e3e"
            self.speaker_fg = "#38bdf8"
            
        if hasattr(self, 'style'):
            self.style.configure("Header.TLabel", foreground=self.accent_color)
            self.style.configure("TCombobox", arrowcolor=self.accent_color)
            self.style.map("TCombobox",
                           arrowcolor=[("disabled", self.text_dim), ("!disabled", self.accent_color)],
                           bordercolor=[("focus", self.accent_color), ("!focus", self.border_color)])
            self.style.map("TNotebook.Tab", 
                           background=[("selected", self.accent_color), ("active", self.border_color), ("", self.card_color)])
            self.style.configure("Treeview.Heading", foreground=self.accent_color)
            self.style.map("Treeview", 
                           background=[("selected", self.accent_color), ("!selected", self.card_color)])
            self.style.configure("Vertical.TScrollbar", arrowcolor=self.accent_color)
            self.style.map("Vertical.TScrollbar",
                           background=[("active", self.accent_color), ("pressed", self.accent_color), ("", self.card_color)],
                           arrowcolor=[("active", "#ffffff"), ("", self.accent_color)])
            self.style.configure("Horizontal.TScrollbar", arrowcolor=self.accent_color)
            self.style.map("Horizontal.TScrollbar",
                           background=[("active", self.accent_color), ("pressed", self.accent_color), ("", self.card_color)],
                           arrowcolor=[("active", "#ffffff"), ("", self.accent_color)])
                           
        if hasattr(self, 'preview_box'):
            self.preview_box.config(bg=self.preview_bg, highlightbackground=self.preview_border)
        if hasattr(self, 'lbl_preview_speaker'):
            self.lbl_preview_speaker.config(bg=self.speaker_bg, fg=self.speaker_fg)
        if hasattr(self, 'txt_preview_body'):
            self.txt_preview_body.config(bg=self.preview_bg)
        if hasattr(self, 'lbl_prev_title'):
            self.lbl_prev_title.config(foreground=self.accent_color)
        if hasattr(self, 'btn_apply_dialogue'):
            self.btn_apply_dialogue.config(bg=self.accent_color, activebackground=self.accent_hover)
        if hasattr(self, 'btn_repack_save'):
            self.btn_repack_save.config(bg=self.accent_color, activebackground=self.accent_hover)
        if hasattr(self, 'btn_apply_tm'):
            self.btn_apply_tm.config(bg=self.accent_color, activebackground=self.accent_hover)
        if hasattr(self, 'txt_log') and self.txt_log:
            self.txt_log.tag_config("info", foreground=self.accent_color)
            
        for foot_attr in ('lbl_cheatsheet', 'lbl_macrodic', 'lbl_lore', 'lbl_qa_audit_foot', 'lbl_dash_foot', 'lbl_about'):
            if hasattr(self, foot_attr):
                getattr(self, foot_attr).config(fg=self.accent_color)

    def index_translation_memory(self):
        """
        Populates Translation Memory from canonical lore glossary and loaded records (Pillar 3).
        """
        loc_name = self.cmb_local.get() if hasattr(self, 'cmb_local') else "new_uspc"
        lang_map = {
            "new_itpc": "it",
            "new_depc": "de",
            "new_frpc": "fr",
            "new_espc": "es",
            "jppc": "jp"
        }
        target_lang = lang_map.get(loc_name.lower())
        
        # 1. Index Canonical Lore terms
        for term in CANONICAL_LORE_GLOSSARY:
            en_val = term.get("en", "").strip()
            jp_val = term.get("jp", "").strip()
            if target_lang:
                tgt_val = term.get(target_lang, "").strip()
                if en_val and tgt_val and en_val != tgt_val:
                    self.translation_memory[en_val] = tgt_val
                if jp_val and tgt_val and jp_val != tgt_val:
                    self.translation_memory[jp_val] = tgt_val
            else:
                # If in new_uspc or base English locale, provide JP -> EN and multilingual lore associations
                if jp_val and en_val and jp_val != en_val:
                    self.translation_memory[jp_val] = en_val
                for other_lang in ("it", "de", "fr", "es"):
                    ov = term.get(other_lang, "").strip()
                    if en_val and ov and en_val != ov:
                        self.translation_memory[en_val] = ov
                
        # 2. Index active file translations vs reference
        if self.records and self.active_file_path:
            ref_recs = self.get_reference_records_for_file(self.active_file_path, "new_uspc")
            ref_dict = {r['id']: r for r in ref_recs}
            for r in self.records:
                orig = ref_dict.get(r['id'])
                if orig:
                    r_name = r.get('name', '').strip()
                    o_name = orig.get('name', '').strip()
                    if r_name and o_name and r_name != o_name:
                        self.translation_memory[o_name] = r_name
                    r_desc = r.get('desc', '').strip()
                    o_desc = orig.get('desc', '').strip()
                    if r_desc and o_desc and r_desc != o_desc and r_desc != '-':
                        self.translation_memory[o_desc] = r_desc

    def check_translation_memory(self):
        """
        Checks if current entry has an exact or high-confidence match in TM (Pillar 3).
        """
        if not hasattr(self, 'frame_tm_suggestion'):
            return
            
        sel = self.tree.selection()
        if not sel or not self.records:
            self.frame_tm_suggestion.pack_forget()
            self.active_tm_suggestion = None
            return

        try:
            entry_id = int(sel[0])
            active_rec = next((r for r in self.records if r['id'] == entry_id), None)
        except ValueError:
            active_rec = next((r for r in self.records if str(r['id']) == sel[0]), None)
            entry_id = sel[0]

        if not active_rec:
            self.frame_tm_suggestion.pack_forget()
            self.active_tm_suggestion = None
            return

        ref_recs = self.get_reference_records_for_file(self.active_file_path, "new_uspc") if self.active_file_path else []
        ref_rec = next((r for r in ref_recs if r['id'] == entry_id), None) if ref_recs else None
        
        ref_text = ref_rec.get('name', '').strip() if ref_rec else ''
        cur_text = active_rec.get('name', '').strip()
        
        match = None
        if ref_text:
            match = self.translation_memory.get(ref_text)
            
        if match and match != cur_text and match != ref_text:
            disp_match = match.replace("\n", " ").replace("\r", "")
            if len(disp_match) > 42:
                disp_match = disp_match[:39] + "..."
            self.lbl_tm_text.config(text=f'💡 TM Match: "{disp_match}"')
            self.active_tm_suggestion = match
            if hasattr(self, 'txt_dialogue') and self.txt_dialogue.winfo_exists():
                self.frame_tm_suggestion.pack(fill="x", pady=(0, 4), before=self.txt_dialogue.master)
            else:
                self.frame_tm_suggestion.pack(fill="x", pady=(0, 4))
        else:
            self.frame_tm_suggestion.pack_forget()
            self.active_tm_suggestion = None

    def apply_translation_memory(self):
        """Applies active Translation Memory match to the editor (Pillar 3)."""
        if not getattr(self, 'active_tm_suggestion', None):
            return
        suggestion = self.active_tm_suggestion
        mode = getattr(self, 'active_mode', 'kernel')
        if mode in ('sps2', 'msg') and hasattr(self, 'txt_dialogue'):
            self.txt_dialogue.delete("1.0", tk.END)
            self.txt_dialogue.insert("1.0", suggestion)
            self.highlight_syntax()
            self.update_live_preview()
            self.update_length_label()
        elif hasattr(self, 'ent_name'):
            self.ent_name.delete(0, tk.END)
            self.ent_name.insert(0, suggestion)
            self.update_live_preview()
            self.update_length_label()
        self.frame_tm_suggestion.pack_forget()
        self.active_tm_suggestion = None
        self.log(f"Applied Translation Memory match to active entry.", "success")

    def load_macro_dictionary(self):
        """
        Loads the in-game macro dictionary (~1,556 entries) for characters,
        blitzball players, techniques, field locations, and world regions.
        Attempts to load localized macrodic.dcp first; falls back to default_macros.json.
        """
        loc = self.cmb_local.get() if hasattr(self, 'cmb_local') else "new_uspc"
        charset = self.cmb_charset.get() if hasattr(self, 'cmb_charset') else "us"
        if not loc:
            loc = "new_uspc"
        if not charset:
            charset = "us"

        loaded = False
        if hasattr(self, 'codec') and self.codec and self.codec.ffx_master_path:
            loc_dir = os.path.join(self.codec.ffx_master_path, loc)
            search_candidates = [
                os.path.join(loc_dir, "menu", "macrodic.dcp"),
                os.path.join(self.codec.ffx_master_path, "new_uspc", "menu", "macrodic.dcp"),
                os.path.join(self.codec.ffx_master_path, "jppc", "menu", "macrodic.dcp"),
            ]
            for cand in search_candidates:
                if os.path.exists(cand):
                    macros = self.codec.read_macrodic_dcp(cand, charset)
                    if macros:
                        self.macro_db = macros
                        loaded = True
                        break

        if not loaded:
            json_path = get_resource_path("default_macros.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        self.macro_db = json.load(f)
                    loaded = True
                except Exception:
                    pass

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

        # 2. Fallback to auto-detect relative to script or Steam
        game_sub = "ffx2" if "Final Fantasy X-2" in getattr(self, 'active_game', '') else "ffx"
        alt_sub = "ffx" if game_sub == "ffx2" else "ffx2"

        candidate_paths = [
            os.path.abspath(os.path.join(script_dir, "..", "VBF Browser", "Extracted", "ffx_ps2", game_sub, "master")),
            os.path.abspath(os.path.join(script_dir, "..", "VBF Browser", "extracted", "ffx_ps2", game_sub, "master")),
            os.path.abspath(os.path.join(script_dir, "..", "..", "Misc Tools", "FF10 Rando", "input", "ffx_ps2", game_sub, "master")),
            os.path.abspath(os.path.join(script_dir, "..", "VBF Browser", "Extracted", "ffx_ps2", alt_sub, "master")),
            os.path.abspath(os.path.join(script_dir, "..", "VBF Browser", "extracted", "ffx_ps2", alt_sub, "master")),
            os.path.abspath(os.path.join(script_dir, "..", "..", "Misc Tools", "FF10 Rando", "input", "ffx_ps2", alt_sub, "master")),
            os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY FFX&FFX-2 HD Remaster\ffx_ps2", game_sub, "master"),
            os.path.join(r"C:\Program Files\Steam\steamapps\common\FINAL FANTASY FFX&FFX-2 HD Remaster\ffx_ps2", game_sub, "master"),
            os.path.join(r"D:\Steam\steamapps\common\FINAL FANTASY FFX&FFX-2 HD Remaster\ffx_ps2", game_sub, "master"),
            os.path.join(r"D:\SteamLibrary\steamapps\common\FINAL FANTASY FFX&FFX-2 HD Remaster\ffx_ps2", game_sub, "master"),
            os.path.join(r"E:\Steam\steamapps\common\FINAL FANTASY FFX&FFX-2 HD Remaster\ffx_ps2", game_sub, "master"),
            os.path.join(r"E:\SteamLibrary\steamapps\common\FINAL FANTASY FFX&FFX-2 HD Remaster\ffx_ps2", game_sub, "master"),
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                self.ent_master_path.delete(0, tk.END)
                self.ent_master_path.insert(0, p)
                self.codec.ffx_master_path = p
                self.log(f"Auto-detected {getattr(self, 'active_game', 'FFX')} extracted data folder: {p}")
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
        self.top_panel = ttk.LabelFrame(self.main_container, text=" FFX & FFX-2 Game Directory Configuration ", padding=10)
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

            self.lbl_macrodic = tk.Label(
                self.footer_frame,
                text="🔍 Macro Dictionary",
                fg=self.accent_color,
                bg=self.bg_color,
                font=("Segoe UI", 9, "underline"),
                cursor="hand2"
            )
            self.lbl_macrodic.pack(side="right", padx=5)
            self.lbl_macrodic.bind("<Button-1>", lambda e: self.show_macro_dictionary_dialog())
            self.lbl_macrodic.bind("<Enter>", lambda e: self.lbl_macrodic.config(fg=self.accent_hover))
            self.lbl_macrodic.bind("<Leave>", lambda e: self.lbl_macrodic.config(fg=self.accent_color))

            self.lbl_lore = tk.Label(
                self.footer_frame,
                text="📚 Lore Glossary",
                fg=self.accent_color,
                bg=self.bg_color,
                font=("Segoe UI", 9, "underline"),
                cursor="hand2"
            )
            self.lbl_lore.pack(side="right", padx=5)
            self.lbl_lore.bind("<Button-1>", lambda e: self.show_canonical_lore_dialog())
            self.lbl_lore.bind("<Enter>", lambda e: self.lbl_lore.config(fg=self.accent_hover))
            self.lbl_lore.bind("<Leave>", lambda e: self.lbl_lore.config(fg=self.accent_color))

            self.lbl_qa_audit_foot = tk.Label(
                self.footer_frame,
                text="🛡️ QA Auditor",
                fg="#38bdf8",
                bg=self.bg_color,
                font=("Segoe UI", 9, "underline"),
                cursor="hand2"
            )
            self.lbl_qa_audit_foot.pack(side="right", padx=5)
            self.lbl_qa_audit_foot.bind("<Button-1>", lambda e: self.open_qa_auditor_dialog())
            self.lbl_qa_audit_foot.bind("<Enter>", lambda e: self.lbl_qa_audit_foot.config(fg="#7dd3fc"))
            self.lbl_qa_audit_foot.bind("<Leave>", lambda e: self.lbl_qa_audit_foot.config(fg="#38bdf8"))

            self.lbl_dash_foot = tk.Label(
                self.footer_frame,
                text="📊 Progress Dashboard",
                fg=self.accent_color,
                bg=self.bg_color,
                font=("Segoe UI", 9, "underline"),
                cursor="hand2"
            )
            self.lbl_dash_foot.pack(side="right", padx=5)
            self.lbl_dash_foot.bind("<Button-1>", lambda e: self.open_project_dashboard_dialog())
            self.lbl_dash_foot.bind("<Enter>", lambda e: self.lbl_dash_foot.config(fg=self.accent_hover))
            self.lbl_dash_foot.bind("<Leave>", lambda e: self.lbl_dash_foot.config(fg=self.accent_color))

            self.lbl_about = tk.Label(
                self.footer_frame,
                text="About Studio",
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
        # 1-Click Game Switcher (Pillar 1)
        lbl_game = ttk.Label(frame, text="Active Game:", font=("Segoe UI", 9, "bold"))
        lbl_game.grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
        
        self.cmb_game_target = ttk.Combobox(
            frame, values=["Final Fantasy X", "Final Fantasy X-2"], state="readonly", width=18, font=("Segoe UI", 9, "bold")
        )
        self.cmb_game_target.set(getattr(self, 'active_game', "Final Fantasy X"))
        self.cmb_game_target.grid(row=0, column=1, sticky="w", padx=(0, 15), pady=2)
        self.cmb_game_target.bind("<<ComboboxSelected>>", self.on_game_target_changed)
        
        lbl_m = ttk.Label(frame, text="Master Folder:")
        lbl_m.grid(row=0, column=2, sticky="w", padx=(0, 8), pady=2)
        
        self.ent_master_path = ttk.Entry(frame, width=50)
        self.ent_master_path.grid(row=0, column=3, sticky="ew", padx=(0, 8), pady=2)
        frame.columnconfigure(3, weight=1)
        
        btn_browse = tk.Button(frame, text="Browse...", command=self.browse_master_folder, bg=self.card_color, 
                               fg=self.text_color, relief="flat", activebackground=self.border_color, activeforeground=self.text_color)
        btn_browse.grid(row=0, column=4, padx=(0, 8), pady=2)
        self.bind_hover(btn_browse)
        
        btn_scan = tk.Button(frame, text="Scan Directory", command=self.scan_localizations, bg=self.accent_color, 
                              fg="white", font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.accent_hover, activeforeground="white")
        btn_scan.grid(row=0, column=5, pady=2)
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
        self.cmb_bin_file.pack(fill="x", pady=(0, 12))
        self.cmb_bin_file.bind("<<ComboboxSelected>>", self.on_bin_file_selected)
        
        # Bulk Operations Buttons
        lbl_bulk = ttk.Label(lbl_file_group, text="Bulk Utilities:")
        lbl_bulk.pack(anchor="w", pady=(0, 4))
        
        btn_exp_csv = tk.Button(lbl_file_group, text="📥 Export CSV (Single/Batch)", command=self.export_csv, bg=self.card_color, 
                                 fg=self.text_color, font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color)
        btn_exp_csv.pack(fill="x", pady=2)
        self.bind_hover(btn_exp_csv)
        
        btn_imp_csv = tk.Button(lbl_file_group, text="📤 Import CSV (Single/Batch)", command=self.import_csv, bg=self.card_color, 
                                 fg=self.text_color, font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color)
        btn_imp_csv.pack(fill="x", pady=2)
        self.bind_hover(btn_imp_csv)

        btn_sr = tk.Button(lbl_file_group, text="🔍 Global Search & Replace", command=self.open_search_replace_dialog, bg=self.card_color, 
                                 fg=self.text_color, font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color)
        btn_sr.pack(fill="x", pady=2)
        self.bind_hover(btn_sr)

        btn_batch_rules = tk.Button(lbl_file_group, text="⚡ Batch Rulesets", command=self.open_batch_ruleset_dialog, bg=self.card_color, 
                                 fg=self.text_color, font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color)
        btn_batch_rules.pack(fill="x", pady=2)
        self.bind_hover(btn_batch_rules)

        btn_qa_audit = tk.Button(lbl_file_group, text="🛡️ QA Syntax & Crash Auditor", command=self.open_qa_auditor_dialog, bg=self.card_color, 
                                 fg="#38bdf8", font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground="#38bdf8")
        btn_qa_audit.pack(fill="x", pady=2)
        self.bind_hover(btn_qa_audit)

        btn_dash = tk.Button(lbl_file_group, text="📊 Translation Dashboard", command=self.open_project_dashboard_dialog, bg=self.card_color, 
                                 fg=self.text_color, font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color)
        btn_dash.pack(fill="x", pady=2)
        self.bind_hover(btn_dash)

        btn_pkg_mod = tk.Button(lbl_file_group, text="📦 Package Mod (SpiraMM / Nexus)", command=self.open_mod_packager_dialog, bg=self.card_color, 
                                 fg=self.text_color, font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color)
        btn_pkg_mod.pack(fill="x", pady=2)
        self.bind_hover(btn_pkg_mod)
        
        # Repack & Save Button
        self.btn_repack_save = tk.Button(lbl_file_group, text="💾 Repack & Save .bin File", command=self.save_bin_file, bg=self.accent_color, 
                              fg="white", font=("Segoe UI", 10, "bold"), relief="flat", activebackground=self.accent_hover, activeforeground="white")
        self.btn_repack_save.pack(fill="x", pady=(12, 0))
        self.bind_hover(self.btn_repack_save, is_primary=True)

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
        self.ent_search.bind("<Return>", lambda e: self.find_next_match())
        self.ent_search.bind("<Shift-Return>", lambda e: self.find_prev_match())
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
        
        self.lbl_len_warn = tk.Label(bottom_row, text="Bytes used: Name: 0 | Desc: 0", font=("Segoe UI", 9, "bold"), fg=self.text_dim, bg=self.bg_color)
        self.lbl_len_warn.pack(side="left")

        btn_tags = tk.Button(bottom_row, text="📖 Tags Cheat Sheet", command=self.show_cheat_sheet_dialog, bg=self.card_color, 
                             fg=self.text_color, font=("Segoe UI", 8, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=8, pady=3)
        btn_tags.pack(side="left", padx=(12, 0))
        self.bind_hover(btn_tags)

        btn_macro_dic = tk.Button(bottom_row, text="🔍 Macro Dictionary", command=self.show_macro_dictionary_dialog, bg=self.card_color, 
                                  fg=self.text_color, font=("Segoe UI", 8, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=8, pady=3)
        btn_macro_dic.pack(side="left", padx=(6, 0))
        self.bind_hover(btn_macro_dic)
        
        self.btn_apply_dialogue = tk.Button(bottom_row, text="Apply Dialogue Edits", command=self.apply_row_edits, bg=self.accent_color, 
                              fg="white", font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.accent_hover, activeforeground="white", padx=15, pady=4)
        self.btn_apply_dialogue.pack(side="right")
        self.bind_hover(self.btn_apply_dialogue, is_primary=True)

        # 0. Reference Pane (Dual-Locale Reference Viewer)
        self.ref_frame = ttk.LabelFrame(frame, text=" 📖 Dual-Locale Reference Viewer ", padding=6)
        ref_header = ttk.Frame(self.ref_frame)
        ref_header.pack(fill="x", pady=(0, 2))
        
        self.var_show_ref = tk.BooleanVar(value=False)
        self.chk_show_ref = ttk.Checkbutton(ref_header, text="Enable Reference Split-View", variable=self.var_show_ref, command=self.toggle_reference_view)
        self.chk_show_ref.pack(side="left")
        
        self.lbl_ref_loc = ttk.Label(ref_header, text="Compare with:")
        self.cmb_ref_local = ttk.Combobox(ref_header, state="readonly", width=12, values=self.localizations if hasattr(self, 'localizations') and self.localizations else ["new_uspc", "new_itpc", "new_depc", "new_fpc", "new_espc", "jppc"])
        self.cmb_ref_local.set("new_uspc")
        self.cmb_ref_local.bind("<<ComboboxSelected>>", self.on_ref_locale_changed)
        
        self.btn_copy_ref = tk.Button(ref_header, text="📋 Copy Reference to Editor", command=self.copy_ref_to_editor,
                                      bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"),
                                      relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=6, pady=2)
        self.bind_hover(self.btn_copy_ref)

        self.btn_diff_ref = tk.Button(ref_header, text="🔍 Visual Diff", command=self.open_visual_diff_dialog,
                                      bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"),
                                      relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=6, pady=2)
        self.bind_hover(self.btn_diff_ref)
        
        self.ref_content_frame = ttk.Frame(self.ref_frame)
        self.txt_ref_display = scrolledtext.ScrolledText(self.ref_content_frame, height=3, bg="#11141c", fg="#38bdf8", font=("Consolas", 9), relief="flat", wrap="word", state="disabled")
        self.txt_ref_display.pack(fill="x", expand=False)
        self.ref_frame.pack(fill="x", pady=(0, 8))

        # 1. Kernel Fields Frame (used for kernel tables and albhed)
        self.kernel_fields_frame = ttk.Frame(frame)
        self.kernel_fields_frame.columnconfigure(1, weight=1)
        
        # Name
        self.lbl_field_name = ttk.Label(self.kernel_fields_frame, text="Name:")
        self.lbl_field_name.grid(row=0, column=0, sticky="w", pady=5, padx=(0, 5))
        self.ent_name = ttk.Entry(self.kernel_fields_frame)
        self.ent_name.grid(row=0, column=1, sticky="ew", pady=5)
        self.ent_name.bind("<KeyRelease>", lambda e: (self.update_length_label(), self.update_live_preview()))
        self.ent_name.bind("<FocusIn>", lambda e: self.update_live_preview())
        
        # S. Name
        self.lbl_field_sname = ttk.Label(self.kernel_fields_frame, text="Simplified Name:")
        self.lbl_field_sname.grid(row=1, column=0, sticky="w", pady=5, padx=(0, 5))
        self.ent_sname = ttk.Entry(self.kernel_fields_frame)
        self.ent_sname.grid(row=1, column=1, sticky="ew", pady=5)
        self.ent_sname.bind("<KeyRelease>", lambda e: (self.update_length_label(), self.update_live_preview()))
        self.ent_sname.bind("<FocusIn>", lambda e: self.update_live_preview())
        
        # Desc
        self.lbl_field_desc = ttk.Label(self.kernel_fields_frame, text="Description:")
        self.lbl_field_desc.grid(row=2, column=0, sticky="w", pady=5, padx=(0, 5))
        self.ent_desc = ttk.Entry(self.kernel_fields_frame)
        self.ent_desc.grid(row=2, column=1, sticky="ew", pady=5)
        self.ent_desc.bind("<KeyRelease>", lambda e: (self.update_length_label(), self.update_live_preview()))
        self.ent_desc.bind("<FocusIn>", lambda e: self.update_live_preview())
        
        # S. Desc
        self.lbl_field_sdesc = ttk.Label(self.kernel_fields_frame, text="Simplified Description:")
        self.lbl_field_sdesc.grid(row=3, column=0, sticky="w", pady=5, padx=(0, 5))
        self.ent_sdesc = ttk.Entry(self.kernel_fields_frame)
        self.ent_sdesc.grid(row=3, column=1, sticky="ew", pady=5)
        self.ent_sdesc.bind("<KeyRelease>", lambda e: (self.update_length_label(), self.update_live_preview()))
        self.ent_sdesc.bind("<FocusIn>", lambda e: self.update_live_preview())

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

        # Setup Undo/Redo and Right-Click Context Menu for all kernel entries
        for ent in (self.ent_name, self.ent_sname, self.ent_desc, self.ent_sdesc, self.ent_wakka, self.ent_lulu, self.ent_rikku):
            self.setup_entry_undo(ent)
            self.setup_context_menu(ent)

        # Pack kernel fields by default
        self.kernel_fields_frame.pack(fill="x", pady=(0, 8))

        # 2. Modern Multi-Line Dialogue Editor Frame (for cutscenes, battle quotes, and arena tutorial scripts)
        self.dialogue_editor_frame = ttk.Frame(frame)
        
        # Header + Shortcut hint
        header_row = ttk.Frame(self.dialogue_editor_frame)
        header_row.pack(fill="x", pady=(0, 4))
        ttk.Label(header_row, text="Dialogue / Text Message:", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Label(header_row, text="(Ctrl+Enter to Apply)", font=("Segoe UI", 8, "italic"), foreground=self.text_dim).pack(side="right")
        self.lbl_timing_estimate = tk.Label(header_row, text="", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg=self.bg_color)
        self.lbl_timing_estimate.pack(side="right", padx=(0, 10))
        
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

        # Macro Dictionary pill
        btn_pill_macro = tk.Button(
            self.toolbar_frame, text="🔍 Macro Dic", command=self.show_macro_dictionary_dialog,
            bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"),
            relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=7, pady=2
        )
        btn_pill_macro.pack(side="left", padx=(0, 4))
        self.bind_hover(btn_pill_macro)

        # Translation Memory Suggestion Strip (Pillar 3)
        self.frame_tm_suggestion = tk.Frame(self.dialogue_editor_frame, bg="#1a1e2b", padx=8, pady=4, highlightthickness=1, highlightbackground=self.border_color)
        self.lbl_tm_text = tk.Label(self.frame_tm_suggestion, text="", font=("Segoe UI", 9, "italic"), fg="#38bdf8", bg="#1a1e2b")
        self.lbl_tm_text.pack(side="left", padx=(0, 8))
        self.btn_apply_tm = tk.Button(self.frame_tm_suggestion, text="⚡ Apply TM (Ctrl+T)", command=self.apply_translation_memory,
                                      bg=self.accent_color, fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=1)
        self.btn_apply_tm.pack(side="right")
        self.bind_hover(self.btn_apply_tm, is_primary=True)

        # Multi-Line Editor container
        txt_container = ttk.Frame(self.dialogue_editor_frame)
        txt_container.pack(fill="both", expand=True)
        
        self.txt_dialogue = tk.Text(
            txt_container, height=6, font=("Consolas", 10), wrap="word",
            bg="#131622", fg="#f3f4f6", insertbackground="#ffffff",
            relief="flat", highlightthickness=1, highlightbackground=self.border_color,
            padx=8, pady=6,
            undo=True, autoseparators=True, maxundo=100
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
        self.txt_dialogue.bind("<Control-t>", lambda e: (self.apply_translation_memory(), "break")[1])
        self.txt_dialogue.bind("<Control-T>", lambda e: (self.apply_translation_memory(), "break")[1])
        self.txt_dialogue.bind("<Control-z>", self.dialogue_undo)
        self.txt_dialogue.bind("<Control-y>", self.dialogue_redo)
        self.txt_dialogue.bind("<Control-Z>", self.dialogue_redo)
        self.txt_dialogue.bind("<Motion>", self.on_text_motion)
        self.txt_dialogue.bind("<Leave>", self.on_text_leave)
        self.setup_context_menu(self.txt_dialogue)

        # 3. In-Game Dialogue Box Live Preview Frame
        self.preview_frame = ttk.Frame(frame)
        self.preview_frame.pack(fill="both", expand=True, pady=(8, 0))
        
        prev_header = ttk.Frame(self.preview_frame)
        prev_header.pack(fill="x", pady=(0, 4))
        
        self.lbl_prev_title = ttk.Label(prev_header, text="🎮 In-Game Dialogue Box Preview", font=("Segoe UI", 9, "bold"), foreground=self.accent_color)
        self.lbl_prev_title.pack(side="left")

        self.lbl_preview_layout_warn = tk.Label(prev_header, text="", font=("Segoe UI", 8, "bold"), fg="#4ade80", bg=self.bg_color)
        self.lbl_preview_layout_warn.pack(side="left", padx=(10, 0))

        # Interactive Choice Branching Simulator Controls (Pillar 5)
        self.frame_choice_ctrls = tk.Frame(prev_header, bg=self.bg_color)
        self.lbl_choice_stat = tk.Label(self.frame_choice_ctrls, text="", font=("Segoe UI", 8, "bold"), fg="#fbbf24", bg=self.bg_color)
        self.lbl_choice_stat.pack(side="left", padx=(0, 4))
        btn_prev_choice = tk.Button(self.frame_choice_ctrls, text="▲", command=self.prev_choice_option, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"), relief="flat", width=2, pady=0)
        btn_prev_choice.pack(side="left", padx=1)
        self.bind_hover(btn_prev_choice)
        btn_next_choice = tk.Button(self.frame_choice_ctrls, text="▼", command=self.next_choice_option, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"), relief="flat", width=2, pady=0)
        btn_next_choice.pack(side="left", padx=1)
        self.bind_hover(btn_next_choice)
        
        self.frame_prev_field = ttk.Frame(prev_header)
        self.frame_prev_field.pack(side="right")
        
        lbl_field = ttk.Label(self.frame_prev_field, text="Preview Field:", font=("Segoe UI", 8), foreground="#94a3b8")
        lbl_field.pack(side="left", padx=(0, 4))
        
        self.cmb_prev_field = ttk.Combobox(
            self.frame_prev_field,
            values=["Auto (Active Field)", "Simplified Desc (Scan)", "Description (Sensor)", "Name", "Simplified Name"],
            state="readonly",
            width=20,
            font=("Segoe UI", 8)
        )
        self.cmb_prev_field.set("Auto (Active Field)")
        self.cmb_prev_field.pack(side="left")
        self.cmb_prev_field.bind("<<ComboboxSelected>>", lambda e: self.update_live_preview())
        
        self.preview_box = tk.Frame(
            self.preview_frame, bg="#040a18", highlightbackground="#1d4ed8", highlightthickness=2, padx=12, pady=10
        )
        self.preview_box.pack(fill="both", expand=True)
        
        self.lbl_preview_speaker = tk.Label(
            self.preview_box, text="", bg="#0e1e3e", fg="#38bdf8", font=("Segoe UI", 9, "bold"), anchor="w",
            padx=8, pady=2, relief="solid", borderwidth=1
        )
        
        self.txt_preview_body = tk.Text(
            self.preview_box, bg="#040a18", fg="#ffffff", font=("Segoe UI", 10), height=4, wrap="word", relief="flat", state="disabled"
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
        self.txt_preview_body.tag_configure('prev_prompt', foreground='#38bdf8', font=('Segoe UI', 10, 'bold'))

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

    def dialogue_undo(self, event=None):
        try:
            self.txt_dialogue.edit_undo()
            self.highlight_syntax()
            self.update_live_preview()
            self.update_length_label()
        except tk.TclError:
            pass
        return "break"

    def dialogue_redo(self, event=None):
        try:
            self.txt_dialogue.edit_redo()
            self.highlight_syntax()
            self.update_live_preview()
            self.update_length_label()
        except tk.TclError:
            pass
        return "break"

    def setup_entry_undo(self, entry):
        entry._undo_stack = [entry.get()]
        entry._redo_stack = []
        def on_key(event):
            if event.keysym in ("Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R", "z", "y", "Z"):
                return
            val = entry.get()
            if not entry._undo_stack or entry._undo_stack[-1] != val:
                entry._undo_stack.append(val)
                entry._redo_stack.clear()
                if len(entry._undo_stack) > 50:
                    entry._undo_stack.pop(0)
        def do_undo(event):
            if len(entry._undo_stack) > 1:
                cur = entry._undo_stack.pop()
                entry._redo_stack.append(cur)
                prev = entry._undo_stack[-1]
                entry.delete(0, tk.END)
                entry.insert(0, prev)
                self.update_length_label()
                self.update_live_preview()
            return "break"
        def do_redo(event):
            if entry._redo_stack:
                nxt = entry._redo_stack.pop()
                entry._undo_stack.append(nxt)
                entry.delete(0, tk.END)
                entry.insert(0, nxt)
                self.update_length_label()
                self.update_live_preview()
            return "break"
        entry.bind("<KeyRelease>", on_key, add="+")
        entry.bind("<Control-z>", do_undo)
        entry.bind("<Control-y>", do_redo)
        entry.bind("<Control-Z>", do_redo)

    def setup_context_menu(self, widget):
        widget.bind("<Button-3>", lambda e, w=widget: self.show_context_menu(e, w))
        if sys.platform == "darwin":
            widget.bind("<Button-2>", lambda e, w=widget: self.show_context_menu(e, w))

    def show_context_menu(self, event, widget):
        try:
            widget.focus_set()
        except Exception:
            pass

        # Set insertion cursor to click position if no text is actively selected
        if isinstance(widget, (ttk.Entry, tk.Entry)):
            if not widget.selection_present():
                try:
                    idx = widget.index(f"@{event.x}")
                    widget.icursor(idx)
                except Exception:
                    pass
        elif isinstance(widget, tk.Text):
            if not widget.tag_ranges("sel"):
                try:
                    idx = widget.index(f"@{event.x},{event.y}")
                    widget.mark_set("insert", idx)
                except Exception:
                    pass

        menu = tk.Menu(self.root, tearoff=0, bg=self.card_color, fg=self.text_color,
                       activebackground=self.accent_color, activeforeground="white")

        can_undo = False
        can_redo = False
        if isinstance(widget, tk.Text):
            can_undo = True
            can_redo = True
        elif isinstance(widget, (ttk.Entry, tk.Entry)):
            can_undo = len(getattr(widget, '_undo_stack', [])) > 1
            can_redo = bool(getattr(widget, '_redo_stack', []))

        def do_undo():
            if isinstance(widget, tk.Text):
                self.dialogue_undo(None)
            elif isinstance(widget, (ttk.Entry, tk.Entry)):
                if len(getattr(widget, '_undo_stack', [])) > 1:
                    cur = widget._undo_stack.pop()
                    widget._redo_stack.append(cur)
                    prev = widget._undo_stack[-1]
                    widget.delete(0, tk.END)
                    widget.insert(0, prev)
                    self.update_length_label()
                    self.update_live_preview()

        def do_redo():
            if isinstance(widget, tk.Text):
                self.dialogue_redo(None)
            elif isinstance(widget, (ttk.Entry, tk.Entry)):
                if getattr(widget, '_redo_stack', []):
                    nxt = widget._redo_stack.pop()
                    widget._undo_stack.append(nxt)
                    widget.delete(0, tk.END)
                    widget.insert(0, nxt)
                    self.update_length_label()
                    self.update_live_preview()

        menu.add_command(label="Undo", accelerator="Ctrl+Z", command=do_undo, state="normal" if can_undo else "disabled")
        menu.add_command(label="Redo", accelerator="Ctrl+Y", command=do_redo, state="normal" if can_redo else "disabled")
        menu.add_separator()

        has_sel = False
        try:
            if isinstance(widget, tk.Text):
                has_sel = bool(widget.tag_ranges("sel"))
            elif isinstance(widget, (ttk.Entry, tk.Entry)):
                has_sel = widget.selection_present()
        except Exception:
            has_sel = False

        has_clip = False
        try:
            if self.root.clipboard_get():
                has_clip = True
        except Exception:
            has_clip = False

        menu.add_command(label="Cut", accelerator="Ctrl+X", state="normal" if has_sel else "disabled",
                         command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", accelerator="Ctrl+C", state="normal" if has_sel else "disabled",
                         command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", accelerator="Ctrl+V", state="normal" if has_clip else "disabled",
                         command=lambda: widget.event_generate("<<Paste>>"))

        def do_delete():
            try:
                if isinstance(widget, tk.Text) and widget.tag_ranges("sel"):
                    widget.delete("sel.first", "sel.last")
                    self.on_dialogue_key_release(None)
                elif isinstance(widget, (ttk.Entry, tk.Entry)) and widget.selection_present():
                    widget.delete(widget.index("sel.first"), widget.index("sel.last"))
                    self.update_length_label()
                    self.update_live_preview()
            except Exception:
                pass

        menu.add_command(label="Delete", state="normal" if has_sel else "disabled", command=do_delete)
        menu.add_separator()

        def do_select_all():
            try:
                if isinstance(widget, tk.Text):
                    widget.tag_add("sel", "1.0", "end-1c")
                    widget.mark_set("insert", "1.0")
                elif isinstance(widget, (ttk.Entry, tk.Entry)):
                    widget.select_range(0, tk.END)
                    widget.icursor(tk.END)
            except Exception:
                pass

        menu.add_command(label="Select All", accelerator="Ctrl+A", command=do_select_all)
        menu.add_separator()

        # Quick Control Tag Insert Submenu
        menu_tags = tk.Menu(menu, tearoff=0, bg=self.card_color, fg=self.text_color,
                            activebackground=self.accent_color, activeforeground="white")

        def insert_tag_pair(tag_open, tag_close=""):
            try:
                if isinstance(widget, tk.Text):
                    if widget.tag_ranges("sel"):
                        s1 = widget.index("sel.first")
                        s2 = widget.index("sel.last")
                        sel_text = widget.get(s1, s2)
                        widget.delete(s1, s2)
                        widget.insert(s1, f"{tag_open}{sel_text}{tag_close}")
                    else:
                        widget.insert("insert", f"{tag_open}{tag_close}")
                    self.on_dialogue_key_release(None)
                elif isinstance(widget, (ttk.Entry, tk.Entry)):
                    if widget.selection_present():
                        s1 = widget.index("sel.first")
                        s2 = widget.index("sel.last")
                        sel_text = widget.get()[s1:s2]
                        widget.delete(s1, s2)
                        widget.insert(s1, f"{tag_open}{sel_text}{tag_close}")
                    else:
                        widget.insert(tk.INSERT, f"{tag_open}{tag_close}")
                    self.update_length_label()
                    self.update_live_preview()
            except Exception:
                pass

        menu_tags.add_command(label=r"Line Break (\n)", command=lambda: insert_tag_pair(r"\n"))
        menu_tags.add_command(label="Player Pause ({PAUSE})", command=lambda: insert_tag_pair("{PAUSE}"))
        menu_tags.add_command(label="Timed Delay ({TIME:1E})", command=lambda: insert_tag_pair("{TIME:1E}"))
        menu_tags.add_separator()
        menu_tags.add_command(label="Yellow Highlight ({CLR:YELLOW})", command=lambda: insert_tag_pair("{CLR:YELLOW}", "{CLR:WHITE}"))
        menu_tags.add_command(label="Red Highlight ({CLR:RED})", command=lambda: insert_tag_pair("{CLR:RED}", "{CLR:WHITE}"))
        menu_tags.add_command(label="Blue Highlight ({CLR:BLUE})", command=lambda: insert_tag_pair("{CLR:BLUE}", "{CLR:WHITE}"))
        menu_tags.add_command(label="Cyan Highlight ({CLR:OL_CYAN})", command=lambda: insert_tag_pair("{CLR:OL_CYAN}", "{CLR:WHITE}"))
        menu_tags.add_command(label="Pink Highlight ({CLR:PINK})", command=lambda: insert_tag_pair("{CLR:PINK}", "{CLR:WHITE}"))
        menu_tags.add_separator()
        menu_tags.add_command(label="Choice Option ({CHOICE:01})", command=lambda: insert_tag_pair("{CHOICE:01}"))
        menu_tags.add_command(label="Variable Slot ({VAR:00})", command=lambda: insert_tag_pair("{VAR:00}"))
        menu.add_cascade(label="Insert Control Tag", menu=menu_tags)

        # Translation memory option
        tm_text = getattr(self, 'active_tm_suggestion', None)
        if tm_text:
            disp_tm = tm_text.replace("\n", " ").strip()
            if len(disp_tm) > 25:
                disp_tm = disp_tm[:25] + "..."
            menu.add_command(
                label=f"⚡ Apply Lore TM: '{disp_tm}'",
                accelerator="Ctrl+T",
                command=self.apply_translation_memory
            )
        else:
            menu.add_command(label="⚡ Apply Lore TM", accelerator="Ctrl+T", state="disabled")

        menu.add_separator()
        menu.add_command(label="Apply Current Edits", accelerator="Ctrl+Enter", command=self.apply_row_edits)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

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
            val = t.split(':', 1)[1].strip()
            m_info = getattr(self, 'macro_db', {}).get(val.lower())
            if m_info:
                return f"[Macro: {m_info['text']}]\nCategory: {m_info['category']} ({m_info['tag']})\nResolves to in-game text '{m_info['text']}'."
            return f"[Macro Reference: {val}]\nDynamic character, NPC, or location name lookup."
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
        field_badge = ""
        if mode in ('sps2', 'msg') and hasattr(self, 'txt_dialogue'):
            raw_text = self.txt_dialogue.get("1.0", "end-1c")
        elif mode == 'kernel':
            selected_field = self.cmb_prev_field.get() if hasattr(self, 'cmb_prev_field') else "Auto (Active Field)"
            active_focus = self.root.focus_get()

            if selected_field == "Simplified Desc (Scan)":
                raw_text = self.ent_sdesc.get() if hasattr(self, 'ent_sdesc') else ""
                field_badge = "SCAN"
            elif selected_field == "Description (Sensor)":
                raw_text = self.ent_desc.get() if hasattr(self, 'ent_desc') else ""
                field_badge = "SENSOR"
            elif selected_field == "Name":
                raw_text = self.ent_name.get() if hasattr(self, 'ent_name') else ""
                field_badge = "NAME"
            elif selected_field == "Simplified Name":
                raw_text = self.ent_sname.get() if hasattr(self, 'ent_sname') else ""
                field_badge = "SHORT NAME"
            else:  # Auto (Active Field)
                if hasattr(self, 'ent_sdesc') and active_focus == self.ent_sdesc:
                    raw_text = self.ent_sdesc.get()
                    field_badge = "SCAN"
                elif hasattr(self, 'ent_desc') and active_focus == self.ent_desc:
                    raw_text = self.ent_desc.get()
                    field_badge = "SENSOR"
                elif hasattr(self, 'ent_name') and active_focus == self.ent_name:
                    raw_text = self.ent_name.get()
                    field_badge = "NAME"
                elif hasattr(self, 'ent_sname') and active_focus == self.ent_sname:
                    raw_text = self.ent_sname.get()
                    field_badge = "SHORT NAME"
                else:
                    # Smart auto: Prefer Scan description (ent_sdesc) if present (e.g. monster Scan text), then Sensor (ent_desc), then Name
                    if hasattr(self, 'ent_sdesc') and self.ent_sdesc.get():
                        raw_text = self.ent_sdesc.get()
                        field_badge = "SCAN"
                    elif hasattr(self, 'ent_desc') and self.ent_desc.get():
                        raw_text = self.ent_desc.get()
                        field_badge = "SENSOR"
                    elif hasattr(self, 'ent_name') and self.ent_name.get():
                        raw_text = self.ent_name.get()
                        field_badge = "NAME"
                    else:
                        raw_text = ""
        else:
            raw_text = self.ent_name.get() if hasattr(self, 'ent_name') else ""
            
        pc_names = {
            '00': 'Tidus', '01': 'Yuna', '02': 'Auron', '03': 'Kimahri',
            '04': 'Wakka', '05': 'Lulu', '06': 'Rikku', '07': 'Seymour',
            '08': 'Valefor', '09': 'Ifrit', '0A': 'Ixion', '0B': 'Shiva',
            '0C': 'Bahamut', '0D': 'Anima', '0E': 'Yojimbo',
            '0F': 'Cindy', '10': 'Sandy', '11': 'Mindy'
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
                    m_info = getattr(self, 'macro_db', {}).get(mcr_id.lower())
                    speaker = m_info['text'] if m_info else mcr_id
                    
                if remainder:
                    body_lines = [remainder] + lines[1:]
                else:
                    body_lines = lines[1:]
            elif mode == 'kernel' and hasattr(self, 'ent_name') and self.ent_name.get():
                speaker = self.ent_name.get()
                if field_badge:
                    speaker = f"{speaker} ({field_badge})"
                
        if speaker:
            self.lbl_preview_speaker.config(text=f"✦  {speaker.upper()}  ✦")
            self.lbl_preview_speaker.pack(anchor="w", pady=(0, 4))
        else:
            self.lbl_preview_speaker.pack_forget()
            
        body = '\n'.join(body_lines)
        
        # 3. Resolve inline character and macro tags into actual names
        body = re.sub(r'\{PC:([0-9a-fA-F]+)\}', lambda m: pc_names.get(m.group(1).upper(), f"Character #{m.group(1)}"), body)
        def _resolve_macro(m):
            m_tag = m.group(1).lower()
            m_info = getattr(self, 'macro_db', {}).get(m_tag)
            if m_info:
                return m_info['text']
            return f"[{m.group(0)}]"
        body = re.sub(r'\{(?:MCR|MACRO):([a-zA-Z0-9]+)\}', _resolve_macro, body)
        
        # 4. Resolve choices into in-game interactive selection prompt (with cursor pointer)
        choice_matches = list(re.finditer(r'\{CHOICE:([0-9a-fA-F]+)\}', body))
        if choice_matches:
            self.total_choices = len(choice_matches)
            if self.active_choice_idx >= self.total_choices:
                self.active_choice_idx = 0
            if hasattr(self, 'frame_choice_ctrls'):
                self.frame_choice_ctrls.pack(side="right", padx=(0, 8))
                self.lbl_choice_stat.config(text=f"Choice {self.active_choice_idx + 1}/{self.total_choices}")
            
            curr_c_idx = 0
            def _replace_choice(match):
                nonlocal curr_c_idx
                is_active = (curr_c_idx == self.active_choice_idx)
                curr_c_idx += 1
                return '  👉  ' if is_active else '      '
            body = re.sub(r'\{CHOICE:[0-9a-fA-F]+\}\s*', _replace_choice, body)
        else:
            self.total_choices = 0
            self.active_choice_idx = 0
            if hasattr(self, 'frame_choice_ctrls'):
                self.frame_choice_ctrls.pack_forget()

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
                    if '  👉  ' in part:
                        subparts = part.split('  👉  ')
                        for i, sp in enumerate(subparts):
                            if i > 0:
                                self.txt_preview_body.insert(tk.END, "  👉  ", "prev_choice")
                            if sp:
                                self.txt_preview_body.insert(tk.END, sp, cur_tag)
                    else:
                        self.txt_preview_body.insert(tk.END, part, cur_tag)

        # In-game blinking prompt cursor (Pillar 5)
        if '{PAUSE}' in raw_text:
            self._has_pause_prompt = True
            self.txt_preview_body.insert(tk.END, "  ▼", "prev_prompt")
        else:
            self._has_pause_prompt = False
                        
        self.txt_preview_body.config(state="disabled")

        # 11. Live Dialogue Box Ruler & Layout Check
        if hasattr(self, 'lbl_preview_layout_warn'):
            raw_preview_lines = [l for l in body.split('\n') if l.strip()]
            max_line_len = 0
            overflow_info = None
            for idx, pline in enumerate(raw_preview_lines, 1):
                clean_pline = re.sub(r'\{CLR:[^}]+\}', '', pline)
                plen = len(clean_pline)
                if plen > max_line_len:
                    max_line_len = plen
                if plen > 43 and overflow_info is None:
                    overflow_info = (idx, plen)
            
            line_cnt = len(raw_preview_lines)
            if overflow_info:
                self.lbl_preview_layout_warn.config(
                    text=f"⚠️ Line {overflow_info[0]}: {overflow_info[1]} chars (Exceeds ~42-char box width)",
                    fg="#f87171"
                )
            elif line_cnt > 4:
                self.lbl_preview_layout_warn.config(
                    text=f"⚠️ {line_cnt} lines (Exceeds standard 4-line box height)",
                    fg="#fbbf24"
                )
            elif line_cnt > 0:
                self.lbl_preview_layout_warn.config(
                    text=f"✓ Fit OK ({line_cnt} line{'s' if line_cnt != 1 else ''}, max {max_line_len} chars)",
                    fg="#4ade80"
                )
            else:
                self.lbl_preview_layout_warn.config(text="")

        # 12. Cutscene VO Reading Speed & Pacing Estimator (Pillar 3)
        if hasattr(self, 'lbl_timing_estimate'):
            time_tags = re.findall(r'\{TIME:([0-9a-fA-F]+)\}', raw_text)
            clean_dialogue = re.sub(r'\{[^}]+\}', '', raw_text).replace('\r', '').replace('\n', ' ').strip()
            clean_chars = len(clean_dialogue)
            clean_words = len(clean_dialogue.split())
            
            if time_tags:
                total_f = sum(int(h, 16) for h in time_tags)
                sec = total_f / 30.0
                if sec > 0 and clean_chars > 0:
                    cps = clean_chars / sec
                    wpm = (clean_words / sec) * 60.0
                    if cps > 20:
                        self.lbl_timing_estimate.config(
                            text=f"⏱️ {sec:.1f}s ({total_f}f) | 🔴 {cps:.1f} CPS ({int(wpm)} WPM) - TOO FAST",
                            fg="#f87171"
                        )
                    elif cps > 15:
                        self.lbl_timing_estimate.config(
                            text=f"⏱️ {sec:.1f}s ({total_f}f) | 🟡 {cps:.1f} CPS ({int(wpm)} WPM) - Fast",
                            fg="#fbbf24"
                        )
                    else:
                        self.lbl_timing_estimate.config(
                            text=f"⏱️ {sec:.1f}s ({total_f}f) | 🟢 {cps:.1f} CPS ({int(wpm)} WPM) - Optimal",
                            fg="#4ade80"
                        )
                else:
                    self.lbl_timing_estimate.config(
                        text=f"⏱️ Pause: {total_f} frames (~{sec:.1f}s)",
                        fg="#38bdf8"
                    )
            elif clean_chars > 0:
                est_sec = max(1.0, clean_chars / 13.0)
                self.lbl_timing_estimate.config(
                    text=f"⏱️ Est. Read: ~{est_sec:.1f}s ({clean_chars} chars, {clean_words} words)",
                    fg="#94a3b8"
                )
            else:
                self.lbl_timing_estimate.config(text="")

    def prev_choice_option(self):
        """Navigates to previous choice option in live preview (Pillar 5)."""
        if self.total_choices > 1:
            self.active_choice_idx = (self.active_choice_idx - 1) % self.total_choices
            self.update_live_preview()

    def next_choice_option(self):
        """Navigates to next choice option in live preview (Pillar 5)."""
        if self.total_choices > 1:
            self.active_choice_idx = (self.active_choice_idx + 1) % self.total_choices
            self.update_live_preview()

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

    def on_game_target_changed(self, event=None):
        new_game = self.cmb_game_target.get()
        if new_game == getattr(self, 'active_game', None):
            return
        self.active_game = new_game
        self.config["active_game"] = new_game
        self.save_config()
        self.apply_theme(new_game)
        
        cur_path = self.ent_master_path.get().strip()
        if cur_path:
            norm_path = cur_path.replace("\\", "/")
            if "Final Fantasy X-2" in new_game and "/ffx/master" in norm_path.lower():
                swapped = re.sub(r'/ffx/master', '/ffx2/master', norm_path, flags=re.IGNORECASE)
                swapped_os = os.path.normpath(swapped)
                if os.path.exists(swapped_os):
                    self.ent_master_path.delete(0, tk.END)
                    self.ent_master_path.insert(0, swapped_os)
                    self.codec.ffx_master_path = swapped_os
                    cur_path = swapped_os
            elif "Final Fantasy X" == new_game and "/ffx2/master" in norm_path.lower():
                swapped = re.sub(r'/ffx2/master', '/ffx/master', norm_path, flags=re.IGNORECASE)
                swapped_os = os.path.normpath(swapped)
                if os.path.exists(swapped_os):
                    self.ent_master_path.delete(0, tk.END)
                    self.ent_master_path.insert(0, swapped_os)
                    self.codec.ffx_master_path = swapped_os
                    cur_path = swapped_os

        if not self.is_embedded:
            self.root.title(f"{new_game} - Text & Localization Studio {APP_VERSION}")
            
        self.log(f"Switched game target to '{new_game}'.", "info")
        if cur_path and os.path.exists(cur_path):
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
                if not os.path.exists(kernel_path):
                    kernel_path = os.path.join(d, "kernel")
                if os.path.exists(kernel_path) or os.path.exists(os.path.join(d, "menu")):
                    locs.append(name)
                    
        if not locs:
            # Maybe the path entered was already the localization subfolder (e.g. jppc)
            parent_dir = os.path.dirname(path)
            kernel_dir = os.path.join(path, "battle", "kernel")
            if not os.path.exists(kernel_dir):
                kernel_dir = os.path.join(path, "kernel")
            if os.path.exists(kernel_dir) or os.path.exists(os.path.join(path, "menu")):
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
            messagebox.showwarning("Warning", "Could not find any 'battle/kernel' or 'kernel' subfolders inside the master folder.")

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
        self.load_macro_dictionary()
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
            if not os.path.exists(kernel_path):
                kernel_path = os.path.join(loc_dir, "kernel")
            if os.path.exists(kernel_path):
                for name in os.listdir(kernel_path):
                    if name.endswith(".bin") and (name in FILE_RECORD_SIZES or name.startswith("monmagic")):
                        self.file_map[name] = os.path.join(kernel_path, name)
        elif "Arena" in category or "Help" in category:
            help_paths = [os.path.join(loc_dir, "help"), os.path.join(loc_dir, "menu", "help")]
            for hp in help_paths:
                if os.path.exists(hp):
                    for root, dirs, files in os.walk(hp):
                        for f in files:
                            if f.endswith(".sps2") or f.endswith(".bin"):
                                rel = os.path.relpath(os.path.join(root, f), hp).replace("\\", "/")
                                if rel.endswith("_page.sps2") or any(sub in rel.lower() for sub in ["/gcm/", "/gnm/", "/gxm/", "gcm/", "gnm/", "gxm/"]):
                                    continue
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
                    if (name.endswith(".bin") or name == "macrodic.dcp") and not name.startswith("ffxsjis"):
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

    def has_unapplied_editor_edits(self):
        """Checks if the active text/entry widgets contain modifications not yet committed to self.records."""
        if not getattr(self, 'records', None):
            return False
            
        target_id = getattr(self, 'current_entry_id', None)
        if target_id is None:
            sel = self.tree.selection() if hasattr(self, 'tree') else ()
            if sel:
                try:
                    target_id = int(sel[0])
                except ValueError:
                    target_id = sel[0]
        if target_id is None:
            return False
            
        record = next((r for r in self.records if r['id'] == target_id or str(r['id']) == str(target_id)), None)
        if not record:
            return False

        mode = getattr(self, 'active_mode', 'kernel')
        if mode in ('sps2', 'msg', 'macro') and hasattr(self, 'txt_dialogue'):
            curr_text = self.txt_dialogue.get("1.0", "end-1c")
            if curr_text != record.get('name', ''):
                return True
        elif mode == 'albhed':
            if hasattr(self, 'ent_name') and self.ent_name.get() != record.get('name', ''):
                return True
        else:
            if hasattr(self, 'ent_name') and (
                self.ent_name.get() != record.get('name', '') or
                self.ent_sname.get() != record.get('sname', '') or
                self.ent_desc.get() != record.get('desc', '') or
                self.ent_sdesc.get() != record.get('sdesc', '')
            ):
                return True
            if getattr(self, 'active_file_name', '') == "w_name.bin" and hasattr(self, 'ent_wakka'):
                if (
                    self.ent_wakka.get() != record.get('w_wakka', '') or
                    self.ent_lulu.get() != record.get('w_lulu', '') or
                    self.ent_rikku.get() != record.get('w_rikku', '')
                ):
                    return True
        return False

    def has_unsaved_changes(self):
        """Checks if either editor widgets have unapplied edits or records in memory differ from disk."""
        return self.has_unapplied_editor_edits() or getattr(self, 'is_dirty', False)

    def on_window_closing(self):
        if self.has_unsaved_changes():
            current_name = getattr(self, 'active_file_name', 'active file')
            ans = messagebox.askyesnocancel(
                "Unsaved Changes",
                f"You have unsaved changes in '{current_name}'.\n\n"
                "Would you like to save your changes before exiting?"
            )
            if ans is True:
                if self.has_unapplied_editor_edits():
                    self.apply_row_edits()
                saved = self.save_bin_file()
                if not saved or self.has_unsaved_changes():
                    return
                self.root.destroy()
            elif ans is False:
                self.root.destroy()
            else:
                return
        else:
            self.root.destroy()

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

        # Check for unsaved changes before switching files
        if getattr(self, 'active_file_path', None) and os.path.abspath(filepath) != os.path.abspath(self.active_file_path):
            if self.has_unsaved_changes():
                current_name = getattr(self, 'active_file_name', 'active file')
                ans = messagebox.askyesnocancel(
                    "Unsaved Changes",
                    f"You have unsaved changes in '{current_name}'.\n\n"
                    "Would you like to save your changes before opening a different file?"
                )
                if ans is True:
                    if self.has_unapplied_editor_edits():
                        self.apply_row_edits()
                    saved = self.save_bin_file()
                    if not saved or self.has_unsaved_changes():
                        if hasattr(self, 'active_file_key'):
                            self.cmb_bin_file.set(self.active_file_key)
                        return
                elif ans is None:
                    if hasattr(self, 'active_file_key'):
                        self.cmb_bin_file.set(self.active_file_key)
                    return
            
        self.active_file_key = selected_key
        self.active_file_path = filepath
        self.read_active_file()

    def read_active_file(self):
        filepath = self.active_file_path
        self.active_file_name = os.path.basename(filepath)
        self.is_dirty = False
        self.current_entry_id = None
        
        # Check file mode
        norm_path = filepath.replace("\\", "/").lower()
        if "macrodic" in norm_path or norm_path.endswith(".dcp"):
            self.active_mode = "macro"
        elif norm_path.endswith(".sps2"):
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
            if hasattr(self, 'frame_prev_field'):
                self.frame_prev_field.pack(side="right")

            self.lbl_field_sname.grid(row=1, column=0, sticky="w", pady=5, padx=(0, 5))
            self.ent_sname.grid(row=1, column=1, sticky="ew", pady=5)
            self.lbl_field_desc.grid(row=2, column=0, sticky="w", pady=5, padx=(0, 5))
            self.ent_desc.grid(row=2, column=1, sticky="ew", pady=5)
            self.lbl_field_sdesc.grid(row=3, column=0, sticky="w", pady=5, padx=(0, 5))
            self.ent_sdesc.grid(row=3, column=1, sticky="ew", pady=5)
            
            if self.active_file_name == "w_name.bin":
                is_ffx2 = ("X-2" in getattr(self, "active_game", "Final Fantasy X"))
                if is_ffx2:
                    self.lbl_field_name.config(text="Yuna (Gunner):")
                    self.lbl_field_sname.config(text="Rikku (Thief):")
                    self.lbl_field_desc.config(text="Paine (Warrior):")
                    self.lbl_field_sdesc.config(text="Extra Slot 4:")
                    self.lbl_field_wakka.grid(row=4, column=0, sticky="w", pady=5, padx=(0, 5))
                    self.lbl_field_wakka.config(text="Extra Slot 5:")
                    self.ent_wakka.grid(row=4, column=1, sticky="ew", pady=5)
                    self.lbl_field_lulu.grid(row=5, column=0, sticky="w", pady=5, padx=(0, 5))
                    self.lbl_field_lulu.config(text="Extra Slot 6:")
                    self.ent_lulu.grid(row=5, column=1, sticky="ew", pady=5)
                    self.lbl_field_rikku.grid(row=6, column=0, sticky="w", pady=5, padx=(0, 5))
                    self.lbl_field_rikku.config(text="Extra Slot 7:")
                    self.ent_rikku.grid(row=6, column=1, sticky="ew", pady=5)
                else:
                    self.lbl_field_name.config(text="Tidus:")
                    self.lbl_field_sname.config(text="Yuna:")
                    self.lbl_field_desc.config(text="Auron:")
                    self.lbl_field_sdesc.config(text="Kimahri:")
                    self.lbl_field_wakka.grid(row=4, column=0, sticky="w", pady=5, padx=(0, 5))
                    self.lbl_field_wakka.config(text="Wakka:")
                    self.ent_wakka.grid(row=4, column=1, sticky="ew", pady=5)
                    self.lbl_field_lulu.grid(row=5, column=0, sticky="w", pady=5, padx=(0, 5))
                    self.lbl_field_lulu.config(text="Lulu:")
                    self.ent_lulu.grid(row=5, column=1, sticky="ew", pady=5)
                    self.lbl_field_rikku.grid(row=6, column=0, sticky="w", pady=5, padx=(0, 5))
                    self.lbl_field_rikku.config(text="Rikku:")
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
            if hasattr(self, 'frame_prev_field'):
                self.frame_prev_field.pack_forget()

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
            self.is_dirty = False
            self.current_entry_id = None
            self.log(f"Successfully loaded {len(records)} entries (IDs {min_idx} to {max_idx}).", "success")
            
            # Update Dashboard Recent Files Config
            self.add_recent_file(filepath)
            
            self.filter_treeview()
            self.index_translation_memory()
            
            # Select first entry automatically to initialize editor & preview
            children = self.tree.get_children()
            if children:
                self.tree.selection_set(children[0])
                self.tree.see(children[0])
                self.on_tree_row_selected(None)
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
        self.update_recent_files_menu()

    def update_recent_files_menu(self):
        if not hasattr(self, 'menu_recent'):
            return
        self.menu_recent.delete(0, tk.END)
        recent = self.config.get("recent_files", [])
        valid_recent = [p for p in recent if os.path.exists(p)]
        if not valid_recent:
            self.menu_recent.add_command(label="(No Recent Files)", state="disabled")
            return
            
        for idx, filepath in enumerate(valid_recent[:10], start=1):
            fname = os.path.basename(filepath)
            pdir = os.path.basename(os.path.dirname(filepath))
            disp = f"{idx}. {fname}" + (f"  [{pdir}]" if pdir else "")
            if len(disp) > 55:
                disp = disp[:52] + "..."
            self.menu_recent.add_command(
                label=disp,
                command=lambda p=filepath: self.load_from_absolute_path(p)
            )
        self.menu_recent.add_separator()
        self.menu_recent.add_command(label="Clear Recent Files List", command=self.clear_recent_files)

    def clear_recent_files(self):
        self.config["recent_files"] = []
        self.save_config()
        self.update_recent_files_menu()

    def load_from_absolute_path(self, filepath):
        filepath = os.path.abspath(filepath)
        if not os.path.exists(filepath):
            messagebox.showerror("File Not Found", f"The file no longer exists at path:\n{filepath}")
            return
            
        # Check for unsaved changes before loading a different file
        if getattr(self, 'active_file_path', None) and os.path.abspath(filepath) != os.path.abspath(self.active_file_path):
            if self.has_unsaved_changes():
                current_name = getattr(self, 'active_file_name', 'active file')
                ans = messagebox.askyesnocancel(
                    "Unsaved Changes",
                    f"You have unsaved changes in '{current_name}'.\n\n"
                    "Would you like to save your changes before opening a different file?"
                )
                if ans is True:
                    if self.has_unapplied_editor_edits():
                        self.apply_row_edits()
                    saved = self.save_bin_file()
                    if not saved or self.has_unsaved_changes():
                        return
                elif ans is None:
                    return

        norm_path = filepath.replace("\\", "/")
        parts = norm_path.split("/")
        
        try:
            # Check if this file belongs to a known localization folder under a master path
            known_locs = ["new_uspc", "jppc", "uspc", "germanpc", "frenchpc", "italianpc", "spanishpc", "chpc", "twpc", "krpc"]
            loc_idx = -1
            for i, p in enumerate(parts):
                if p.lower() in known_locs:
                    loc_idx = i
                    break
            
            if loc_idx != -1:
                loc = parts[loc_idx]
                master_path = "/".join(parts[:loc_idx])
                filename = parts[-1]
                rel_sub = "/".join(parts[loc_idx+1:])
                
                self.ent_master_path.delete(0, tk.END)
                self.ent_master_path.insert(0, os.path.abspath(master_path))
                self.codec.ffx_master_path = os.path.abspath(master_path)
                
                self.scan_localizations()
                self.cmb_local.set(loc)
                self.on_localization_changed()
                
                rel_lower = rel_sub.lower()
                cat_to_set = None
                for cat in getattr(self, 'cmb_category', {}).cget("values"):
                    if "kernel" in rel_lower and "Kernel" in cat:
                        cat_to_set = cat
                        break
                    elif ("help" in rel_lower or "arena" in rel_lower) and "Help" in cat:
                        cat_to_set = cat
                        break
                    elif "event" in rel_lower and "Story" in cat:
                        cat_to_set = cat
                        break
                    elif ("battle/btl" in rel_lower or "btl" in rel_lower) and "Quotes" in cat:
                        cat_to_set = cat
                        break
                    elif ("menu" in rel_lower or "cloud" in rel_lower) and "Menu" in cat:
                        cat_to_set = cat
                        break
                
                if cat_to_set:
                    self.cmb_category.set(cat_to_set)
                    self.on_category_changed()
                
                matching_keys = [k for k in getattr(self, 'file_map', {}).keys() if k == filename or k.endswith("/" + filename) or k == rel_sub]
                if matching_keys:
                    self.cmb_bin_file.set(matching_keys[0])
                    self.active_file_path = filepath
                    self.read_active_file()
                else:
                    self.active_file_path = filepath
                    self.read_active_file()
            else:
                # Standalone file outside master path
                self.active_file_path = filepath
                self.read_active_file()
        except Exception as e:
            self.log(f"Error loading file: {e}", "error")
            messagebox.showerror("Load Error", f"Failed to load file:\n{str(e)}")

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
            elif mode == "macro":
                display_desc = desc
                match = (not query or query in str(r['id']).lower() or query in name.lower() or query in str(desc).lower())
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

    def _apply_edits_for_record_id(self, target_id):
        record = next((r for r in self.records if r['id'] == target_id or str(r['id']) == str(target_id)), None)
        if not record:
            return
        mode = getattr(self, 'active_mode', 'kernel')
        if mode in ("sps2", "msg", "macro") and hasattr(self, 'txt_dialogue'):
            text_val = self.txt_dialogue.get("1.0", "end-1c")
            record['name'] = text_val
            name_clean = text_val.replace("\r\n", " ").replace("\n", " ")
            if mode == "macro":
                desc_clean = record.get('desc', '')
                tag_key = str(record['id']).lower()
                if hasattr(self, 'macro_db') and tag_key in self.macro_db:
                    self.macro_db[tag_key]['text'] = text_val
            else:
                desc_clean = f"Ptr: 0x{record.get('ptr', 0):X}" if 'ptr' in record else ""
        elif mode == "albhed":
            record['name'] = self.ent_name.get()
            name_clean = record['name'].replace("\r\n", " ").replace("\n", " ")
            desc_clean = record.get('desc', '')
        else:
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
            
        tree_id = str(target_id) if not self.tree.exists(target_id) else target_id
        if self.tree.exists(tree_id):
            self.tree.item(tree_id, values=(record['id'], name_clean, desc_clean))
        self.is_dirty = True
        self.log(f"Auto-applied modifications to entry ID {target_id}.")

    def on_tree_row_selected(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        item_id_raw = sel[0]
        try:
            entry_id = int(item_id_raw)
            record = next((r for r in self.records if r['id'] == entry_id), None)
        except ValueError:
            record = next((r for r in self.records if str(r['id']) == item_id_raw), None)
            entry_id = item_id_raw
        if not record:
            return
            
        old_id = getattr(self, 'current_entry_id', None)
        if old_id is not None and str(old_id) != str(entry_id) and self.has_unapplied_editor_edits():
            ans = messagebox.askyesnocancel(
                "Unapplied Edits",
                f"Entry ID {old_id} has modifications in the editor that haven't been applied to the table.\n\n"
                f"Do you want to apply these modifications before selecting Entry ID {entry_id}?"
            )
            if ans is True:
                self._apply_edits_for_record_id(old_id)
            elif ans is None:
                prev_tree_id = str(old_id) if not self.tree.exists(old_id) else old_id
                self.tree.selection_set(prev_tree_id)
                return

        self.current_entry_id = entry_id
        self.active_choice_idx = 0
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

        if hasattr(self, 'txt_dialogue'):
            self.txt_dialogue.edit_reset()
        for ent in (self.ent_name, self.ent_sname, self.ent_desc, self.ent_sdesc, self.ent_wakka, self.ent_lulu, self.ent_rikku):
            if hasattr(ent, '_undo_stack'):
                ent._undo_stack = [ent.get()]
                ent._redo_stack = []
        
        self.update_length_label()
        self.update_live_preview()
        
        if hasattr(self, 'var_show_ref') and self.var_show_ref.get():
            self.update_reference_display(entry_id)

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

        # Translation Memory lookup (Pillar 3)
        self.check_translation_memory()

    def update_length_label(self):
        charset = self.cmb_charset.get()
        mode = getattr(self, 'active_mode', 'kernel')
        
        if mode in ("sps2", "msg") and hasattr(self, 'txt_dialogue'):
            cur_text = self.txt_dialogue.get("1.0", "end-1c")
            name_bytes = len(self.codec.encode_ffx_string(cur_text, charset))
            if name_bytes > 500:
                msg = f"🔴 Current Message: {name_bytes} bytes (High memory usage)"
                color = "#ef4444"
            elif name_bytes > 300:
                msg = f"🟡 Current Message: {name_bytes} bytes"
                color = "#facc15"
            else:
                msg = f"🟢 Current Message: {name_bytes} bytes"
                color = "#4ade80"
            self.lbl_len_warn.config(text=msg, fg=color)
            return
        elif mode != "kernel":
            name_bytes = len(self.codec.encode_ffx_string(self.ent_name.get(), charset))
            msg = f"🟢 Current Message: {name_bytes} bytes"
            self.lbl_len_warn.config(text=msg, fg="#4ade80")
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
        pct = (total_pool_size / 65535.0) * 100
        
        rec_status = f"Entry: {total_rec_bytes}B"
        pool_status = f"Pool: {total_pool_size} / 65535B ({pct:.1f}%)"
        
        if total_pool_size > 65535 or total_rec_bytes > 800:
            msg = f"🔴 OVERFLOW: {rec_status} | {pool_status}"
            color = "#ef4444"
        elif total_pool_size > 60000 or total_rec_bytes > 500:
            msg = f"🟡 WARNING: {rec_status} | {pool_status}"
            color = "#facc15"
        else:
            msg = f"🟢 SAFE: {rec_status} | {pool_status}"
            color = "#4ade80"
            
        self.lbl_len_warn.config(text=msg, fg=color)

    def toggle_reference_view(self):
        if self.var_show_ref.get():
            self.lbl_ref_loc.pack(side="left", padx=(12, 4))
            self.cmb_ref_local.pack(side="left")
            self.btn_copy_ref.pack(side="right")
            if hasattr(self, 'btn_diff_ref'):
                self.btn_diff_ref.pack(side="right", padx=(0, 6))
            self.ref_content_frame.pack(fill="x", pady=(4, 0))
            sel = self.tree.selection()
            if sel:
                self.update_reference_display(sel[0])
        else:
            self.lbl_ref_loc.pack_forget()
            self.cmb_ref_local.pack_forget()
            self.btn_copy_ref.pack_forget()
            if hasattr(self, 'btn_diff_ref'):
                self.btn_diff_ref.pack_forget()
            self.ref_content_frame.pack_forget()

    def on_ref_locale_changed(self, event=None):
        sel = self.tree.selection()
        if sel:
            self.update_reference_display(sel[0])

    def get_reference_records_for_file(self, target_filepath, ref_loc="new_uspc"):
        if not self.codec.ffx_master_path or not os.path.exists(target_filepath):
            return []
        active_loc = self.cmb_local.get()
        active_loc_dir = os.path.join(self.codec.ffx_master_path, active_loc)
        try:
            rel = os.path.relpath(target_filepath, active_loc_dir)
        except Exception:
            rel = os.path.basename(target_filepath)
        ref_path = os.path.join(self.codec.ffx_master_path, ref_loc, rel)
        if not os.path.exists(ref_path):
            fname = os.path.basename(target_filepath)
            for root, dirs, files in os.walk(os.path.join(self.codec.ffx_master_path, ref_loc)):
                if fname in files:
                    ref_path = os.path.join(root, fname)
                    break
        if not os.path.exists(ref_path):
            return []
        cache_key = (ref_loc, ref_path)
        if not hasattr(self, '_ref_cache'):
            self._ref_cache = {}
        if cache_key in self._ref_cache:
            return self._ref_cache[cache_key][0]
        try:
            charset = "us" if ref_loc in ("new_uspc", "new_itpc", "new_depc", "new_fpc", "new_espc") else "jp"
            recs, _, _, _, mode = self.codec.load_any_ffx_file(ref_path, 16, charset)
            self._ref_cache[cache_key] = (recs, mode)
            return recs
        except Exception:
            return []

    def update_reference_display(self, entry_id):
        if not hasattr(self, 'var_show_ref') or not self.var_show_ref.get():
            return
            
        ref_loc = self.cmb_ref_local.get()
        if not ref_loc or not self.active_file_path:
            return
            
        recs = self.get_reference_records_for_file(self.active_file_path, ref_loc)
        matching_rec = None
        for r in recs:
            if str(r.get('id', '')) == str(entry_id):
                matching_rec = r
                break
                
        self.current_ref_record = matching_rec
        self.txt_ref_display.config(state="normal")
        self.txt_ref_display.delete("1.0", "end")
        if matching_rec:
            if self.active_mode == 'kernel':
                if self.active_file_name == "w_name.bin":
                    disp = f"[Tidus]: {matching_rec.get('name','')}\n[Yuna]: {matching_rec.get('sname','')}\n[Auron]: {matching_rec.get('desc','')}\n[Kimahri]: {matching_rec.get('sdesc','')}"
                else:
                    disp = f"[Name]: {matching_rec.get('name','')}\n[Desc]: {matching_rec.get('desc','')}\n[S.Desc]: {matching_rec.get('sdesc','')}"
            else:
                disp = matching_rec.get('name', '')
            self.txt_ref_display.insert("1.0", disp)
        else:
            self.txt_ref_display.insert("1.0", f"(Entry '{entry_id}' not found in {ref_loc})")
        self.txt_ref_display.config(state="disabled")

    def copy_ref_to_editor(self):
        if not getattr(self, 'current_ref_record', None):
            messagebox.showinfo("Reference", "No reference entry loaded for this row.")
            return
        r = self.current_ref_record
        if self.active_mode == 'kernel':
            self.ent_name.delete(0, "end")
            self.ent_name.insert(0, r.get('name', ''))
            self.ent_sname.delete(0, "end")
            self.ent_sname.insert(0, r.get('sname', ''))
            self.ent_desc.delete(0, "end")
            self.ent_desc.insert(0, r.get('desc', ''))
            self.ent_sdesc.delete(0, "end")
            self.ent_sdesc.insert(0, r.get('sdesc', ''))
            if self.active_file_name == "w_name.bin" and hasattr(self, 'ent_wakka'):
                self.ent_wakka.delete(0, "end")
                self.ent_wakka.insert(0, r.get('w_wakka', ''))
                self.ent_lulu.delete(0, "end")
                self.ent_lulu.insert(0, r.get('w_lulu', ''))
                self.ent_rikku.delete(0, "end")
                self.ent_rikku.insert(0, r.get('w_rikku', ''))
        else:
            if hasattr(self, 'txt_dialogue'):
                self.txt_dialogue.delete("1.0", "end")
                self.txt_dialogue.insert("1.0", r.get('name', ''))
                self.highlight_syntax()
        self.update_length_label()
        self.update_live_preview()
        self.log(f"Copied reference text from {self.cmb_ref_local.get()} into editor.", "info")

    def apply_row_edits(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "No entry selected. Double-click or select an entry in the table first.")
            return
            
        item_id_raw = sel[0]
        try:
            entry_id = int(item_id_raw)
            record = next((r for r in self.records if r['id'] == entry_id), None)
        except ValueError:
            record = next((r for r in self.records if str(r['id']) == item_id_raw), None)
            entry_id = item_id_raw
        if not record:
            return
            
        mode = getattr(self, 'active_mode', 'kernel')
        charset = self.cmb_charset.get()
        
        if mode in ("sps2", "msg", "macro") and hasattr(self, 'txt_dialogue'):
            text_val = self.txt_dialogue.get("1.0", "end-1c")
            record['name'] = text_val
            name_clean = text_val.replace("\r\n", " ").replace("\n", " ")
            if mode == "macro":
                desc_clean = record.get('desc', '')
                tag_key = str(record['id']).lower()
                if hasattr(self, 'macro_db') and tag_key in self.macro_db:
                    self.macro_db[tag_key]['text'] = text_val
            else:
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
        self.is_dirty = True
        self.current_entry_id = record['id']
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

        ref_loc = self.cmb_ref_local.get() if hasattr(self, 'cmb_ref_local') else "new_uspc"
        ans_delta = messagebox.askyesno("Export Delta Patch?",
            f"Do you want to export as a Delta Patch CSV?\n\n"
            f"Select 'Yes' to export ONLY modified / differing entries (compared to reference '{ref_loc}').\n"
            "Select 'No' to export all entries (Full table).")

        def is_delta_modified(rec, ref_rec, fmode):
            if not ref_rec:
                return True
            if fmode == "kernel":
                if rec.get('name') != ref_rec.get('name') or rec.get('sname') != ref_rec.get('sname') or rec.get('desc') != ref_rec.get('desc') or rec.get('sdesc') != ref_rec.get('sdesc'):
                    return True
                if rec.get('w_wakka') != ref_rec.get('w_wakka') or rec.get('w_lulu') != ref_rec.get('w_lulu') or rec.get('w_rikku') != ref_rec.get('w_rikku'):
                    return True
                return False
            else:
                return rec.get('name') != ref_rec.get('name')
            
        if ans is True:
            # Batch mode
            target_dir = filedialog.askdirectory(title="Select Target Folder for Batch CSV Export")
            if not target_dir:
                return
                
            charset = self.cmb_charset.get()
            exported = []
            
            for key, fpath in getattr(self, 'file_map', {}).items():
                safe_name = key.replace("/", "_").replace("\\", "_")
                suffix = "_delta.csv" if ans_delta else ".csv"
                csv_path = os.path.join(target_dir, f"{os.path.splitext(safe_name)[0]}{suffix}")
                try:
                    recs, min_id, max_id, magic, fmode = self.codec.load_any_ffx_file(fpath, 16, charset)
                    ref_recs = self.get_reference_records_for_file(fpath, ref_loc) if ans_delta else []
                    ref_map = {str(r.get('id', '')): r for r in ref_recs}

                    if ans_delta and ref_recs:
                        recs_to_export = [r for r in recs if is_delta_modified(r, ref_map.get(str(r.get('id', ''))), fmode)]
                    else:
                        recs_to_export = recs

                    if ans_delta and not recs_to_export:
                        continue

                    with open(csv_path, "w", encoding="utf-8", newline="") as f:
                        writer = csv.writer(f)
                        if fmode == "kernel":
                            if os.path.basename(fpath) == "w_name.bin":
                                writer.writerow(["ID", "Name", "SimplifiedName", "Description", "SimplifiedDescription", "Wakka", "Lulu", "Rikku"])
                                for r in recs_to_export:
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
                                for r in recs_to_export:
                                    writer.writerow([
                                        r['id'],
                                        clean_csv_cell(r['name']),
                                        clean_csv_cell(r['sname']),
                                        clean_csv_cell(r['desc']),
                                        clean_csv_cell(r['sdesc'])
                                    ])
                        else:
                            writer.writerow(["ID", "Text"])
                            for r in recs_to_export:
                                writer.writerow([r['id'], clean_csv_cell(r['name'])])
                    exported.append(key)
                except Exception as e:
                    self.log(f"Failed to batch export '{key}': {e}", "error")
            
            if exported:
                self.log(f"Successfully batch exported {len(exported)} files to CSV ({'Delta Patch' if ans_delta else 'Full'}) in: {target_dir}", "success")
                messagebox.showinfo("Export Successful", f"Batch export completed successfully!\n\nExported {len(exported)} files ({'Delta Patch' if ans_delta else 'Full'}).")
            else:
                messagebox.showinfo("Export Notice", "No modified files were found to export." if ans_delta else "No files were exported.")
        else:
            # Single file mode
            base_safe = self.active_file_name.replace('.bin', '').replace('.sps2', '')
            init_name = f"{base_safe}_delta.csv" if ans_delta else f"{base_safe}_export.csv"
            save_path = filedialog.asksaveasfilename(
                title=f"Export Table to CSV ({'Delta Patch' if ans_delta else 'Full'})",
                filetypes=[("CSV Files", "*.csv")],
                defaultextension=".csv",
                initialfile=init_name
            )
            if not save_path:
                return
                
            self.log(f"Exporting entries to CSV: {save_path}...")
            try:
                ref_recs = self.get_reference_records_for_file(self.active_file_path, ref_loc) if ans_delta else []
                ref_map = {str(r.get('id', '')): r for r in ref_recs}

                if ans_delta and ref_recs:
                    recs_to_export = [r for r in self.records if is_delta_modified(r, ref_map.get(str(r.get('id', ''))), mode)]
                else:
                    recs_to_export = self.records

                with open(save_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    if mode == "kernel":
                        if self.active_file_name == "w_name.bin":
                            writer.writerow(["ID", "Name", "SimplifiedName", "Description", "SimplifiedDescription", "Wakka", "Lulu", "Rikku"])
                            for r in recs_to_export:
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
                            for r in recs_to_export:
                                writer.writerow([
                                    r['id'],
                                    clean_csv_cell(r['name']),
                                    clean_csv_cell(r['sname']),
                                    clean_csv_cell(r['desc']),
                                    clean_csv_cell(r['sdesc'])
                                ])
                    else:
                        writer.writerow(["ID", "Text"])
                        for r in recs_to_export:
                            writer.writerow([r['id'], clean_csv_cell(r['name'])])
                self.log(f"Successfully exported {len(recs_to_export)} rows to CSV ({'Delta Patch' if ans_delta else 'Full Table'}).", "success")
                messagebox.showinfo("Export Successful", f"Successfully exported {len(recs_to_export)} records ({'Delta Patch' if ans_delta else 'Full Table'}) to:\n{save_path}")
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

            is_event_cat = (
                "cutscene" in self.cmb_category.get().lower() or
                "story" in self.cmb_category.get().lower() or
                any("event" in f.lower() for f in getattr(self, 'file_map', {}).keys())
            )
            auto_shift_ps2_batch = None
            if is_event_cat:
                ans_batch = messagebox.askyesnocancel(
                    "Event Cutscenes: PS2-to-PC Line Offset Check",
                    "⚠️ Notice: You are batch importing into Event Cutscene files.\n\n"
                    "In PC Remaster, cutscene files reserve lines 0 to 3 for PC background installation & engine strings ('Installing... min remaining'). Actual dialogue begins at line 4.\n\n"
                    "If your CSVs were exported from a PS2 mod (where dialogue begins at line 0), they require a +4 line offset to align correctly with PC cutscenes.\n\n"
                    "Would you like to automatically shift imported line IDs by +4 for any PS2 event files that start dialogue at line 0?\n\n"
                    "• Click 'Yes' to automatically apply +4 offset when PS2 dialogue is detected.\n"
                    "• Click 'No' to import all line IDs exactly as written in the CSVs.\n"
                    "• Click 'Cancel' to abort batch import."
                )
                if ans_batch is None:
                    return
                auto_shift_ps2_batch = (ans_batch is True)
            
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

                        file_has_install = (
                            len(recs) >= 4 and
                            any("installing" in str(recs[i].get('name', '')).lower() or 
                                "remaining" in str(recs[i].get('name', '')).lower() 
                                for i in range(min(4, len(recs))))
                        )
                        f_offset = 0
                        if auto_shift_ps2_batch and file_has_install:
                            try:
                                with open(csv_path, "r", encoding="utf-8") as f_peek:
                                    p_reader = csv.reader(f_peek)
                                    next(p_reader, None)
                                    p_row = next(p_reader, None)
                                    if p_row and len(p_row) > 1:
                                        p_txt = p_row[1].lower()
                                        if "installing" not in p_txt and "remaining" not in p_txt:
                                            f_offset = 4
                            except Exception:
                                pass

                        with open(csv_path, "r", encoding="utf-8") as f:
                            reader = csv.reader(f)
                            header = next(reader, None)
                            if not header: continue
                            for row in reader:
                                if not row: continue
                                try:
                                    rid = int(row[0]) + f_offset
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

            # Check for PS2 vs PC Remaster Event dialogue offset
            is_event_file = (
                mode in ("msg", "sps2") and (
                    "event" in getattr(self, 'active_file_path', '').replace("\\", "/").lower() or
                    "cutscene" in self.cmb_category.get().lower() or
                    "story" in self.cmb_category.get().lower()
                )
            )
            has_install_header = (
                is_event_file and len(self.records) >= 4 and
                any("installing" in str(self.records[i].get('name', '')).lower() or 
                    "remaining" in str(self.records[i].get('name', '')).lower() 
                    for i in range(min(4, len(self.records))))
            )
            
            line_offset = 0
            if has_install_header:
                try:
                    with open(open_path, "r", encoding="utf-8") as f_peek:
                        peek_reader = csv.reader(f_peek)
                        next(peek_reader, None)
                        first_row = next(peek_reader, None)
                        if first_row and len(first_row) > 1:
                            first_text = first_row[1].lower()
                            if "installing" not in first_text and "remaining" not in first_text:
                                ans_offset = messagebox.askyesnocancel(
                                    "PS2-to-PC Line Offset Detected",
                                    "⚠️ Notice: The CSV being imported appears to be from a PS2 mod or is missing the 4 PC engine header lines.\n\n"
                                    "In the PC Remaster, Event Cutscene files reserve lines 0 to 3 for background installation & engine strings ('Installing... min remaining'). Actual story dialogue begins at line 4.\n\n"
                                    "If imported without an offset, dialogue lines will be shifted by 4 lines, causing misaligned cutscene dialogue in-game!\n\n"
                                    "Would you like the tool to automatically shift imported line IDs by +4 so the dialogue matches the PC Remaster cutscene script?\n\n"
                                    "• Click 'Yes' to automatically apply +4 offset (Recommended for PS2 mods).\n"
                                    "• Click 'No' to import line IDs exactly as written in the CSV.\n"
                                    "• Click 'Cancel' to abort import."
                                )
                                if ans_offset is None:
                                    return
                                if ans_offset is True:
                                    line_offset = 4
                except Exception:
                    pass
                
            self.log(f"Importing entries from CSV: {open_path} (Offset: +{line_offset})...")
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
                            rid = int(row[0]) + line_offset
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
        dialog.geometry("480x280")
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
        
        opts_frame = ttk.Frame(dialog)
        opts_frame.grid(row=3, column=1, sticky="w", padx=15, pady=5)

        var_case = tk.BooleanVar(value=False)
        chk_case = ttk.Checkbutton(opts_frame, text="Case Sensitive", variable=var_case)
        chk_case.pack(side="left", padx=(0, 15))

        var_regex = tk.BooleanVar(value=False)
        chk_regex = ttk.Checkbutton(opts_frame, text="Regular Expressions (Regex)", variable=var_regex)
        chk_regex.pack(side="left")
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=15, pady=15)

        def compile_pattern(find_txt, case_sens, is_regex):
            flags = 0 if case_sens else re.IGNORECASE
            if is_regex:
                return re.compile(find_txt, flags)
            else:
                return re.compile(re.escape(find_txt), flags)

        def collect_matches(find_txt, replace_txt, scope, case_sens, is_regex):
            try:
                pattern = compile_pattern(find_txt, case_sens, is_regex)
            except Exception as e:
                messagebox.showerror("Regex Error", f"Invalid Regular Expression pattern:\n{e}")
                return None

            matches = [] # list of dicts: {disp_name, fpath, id, field, old, new, is_mem, rec}
            if scope == "Current File only":
                fields = ['name', 'sname', 'desc', 'sdesc'] if self.active_mode == 'kernel' else ['name']
                if self.active_file_name == "w_name.bin":
                    fields.extend(['w_wakka', 'w_lulu', 'w_rikku'])

                for r in self.records:
                    for fld in fields:
                        orig = r.get(fld, "")
                        if not orig: continue
                        try:
                            new_val, sub_cnt = pattern.subn(replace_txt, orig)
                            if sub_cnt > 0:
                                matches.append({
                                    'file': self.active_file_name,
                                    'fpath': self.active_file_path,
                                    'id': r['id'],
                                    'field': fld,
                                    'old': orig,
                                    'new': new_val,
                                    'is_mem': True,
                                    'rec': r
                                })
                        except Exception:
                            pass
            elif scope == "Current Category files":
                charset = self.cmb_charset.get()
                for fname, fpath in self.file_map.items():
                    try:
                        recs, min_id, max_id, magic, mode = self.codec.load_any_ffx_file(fpath, 16, charset)
                        fields = ['name', 'sname', 'desc', 'sdesc'] if mode == 'kernel' else ['name']
                        if fname == "w_name.bin":
                            fields.extend(['w_wakka', 'w_lulu', 'w_rikku'])
                        for r in recs:
                            for fld in fields:
                                orig = r.get(fld, "")
                                if not orig: continue
                                new_val, sub_cnt = pattern.subn(replace_txt, orig)
                                if sub_cnt > 0:
                                    matches.append({
                                        'file': fname,
                                        'fpath': fpath,
                                        'id': r['id'],
                                        'field': fld,
                                        'old': orig,
                                        'new': new_val,
                                        'is_mem': False,
                                        'rec': r
                                    })
                    except Exception:
                        pass
            else:
                loc = self.cmb_local.get()
                loc_dir = os.path.join(self.codec.ffx_master_path, loc)
                all_files = []
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
                                rel = os.path.relpath(os.path.join(root, f), help_dir).replace("\\", "/")
                                if not rel.endswith("_page.sps2") and not any(sub in rel.lower() for sub in ["/gcm/", "/gnm/", "/gxm/", "gcm/", "gnm/", "gxm/"]):
                                    all_files.append((f"help/{rel}", os.path.join(root, f)))
                evt_dir = os.path.join(loc_dir, "event", "obj_ps3")
                if not os.path.exists(evt_dir): evt_dir = os.path.join(loc_dir, "event", "obj_psv")
                if not os.path.exists(evt_dir): evt_dir = os.path.join(loc_dir, "event")
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
                        if (f.endswith(".bin") or f == "macrodic.dcp") and not f.startswith("ffxsjis"):
                            all_files.append((f"menu/{f}", os.path.join(menu_dir, f)))

                charset = self.cmb_charset.get()
                for disp_name, fpath in all_files:
                    try:
                        recs, min_id, max_id, magic, mode = self.codec.load_any_ffx_file(fpath, 16, charset)
                        fields = ['name', 'sname', 'desc', 'sdesc'] if mode == 'kernel' else ['name']
                        if "w_name.bin" in fpath.lower():
                            fields.extend(['w_wakka', 'w_lulu', 'w_rikku'])
                        for r in recs:
                            for fld in fields:
                                orig = r.get(fld, "")
                                if not orig: continue
                                new_val, sub_cnt = pattern.subn(replace_txt, orig)
                                if sub_cnt > 0:
                                    matches.append({
                                        'file': disp_name,
                                        'fpath': fpath,
                                        'id': r['id'],
                                        'field': fld,
                                        'old': orig,
                                        'new': new_val,
                                        'is_mem': False,
                                        'rec': r
                                    })
                    except Exception:
                        pass
            return matches

        def run_preview():
            find_txt = ent_find.get()
            replace_txt = ent_replace.get()
            scope = cmb_scope.get()
            case_sens = var_case.get()
            is_regex = var_regex.get()

            if not find_txt:
                messagebox.showwarning("Warning", "Please enter text to find.")
                return

            matches = collect_matches(find_txt, replace_txt, scope, case_sens, is_regex)
            if matches is None:
                return
            if not matches:
                messagebox.showinfo("Preview Matches", f"No occurrences found for '{find_txt}'.")
                return

            # Open Preview Modal Window
            prev_win = tk.Toplevel(dialog)
            prev_win.title(f"🔍 Search & Replace Preview - {len(matches)} Matches")
            prev_win.geometry("860x520")
            prev_win.configure(bg=self.bg_color)
            prev_win.transient(dialog)
            prev_win.grab_set()

            p_hdr = ttk.Frame(prev_win, padding=(15, 10))
            p_hdr.pack(fill="x")
            tk.Label(p_hdr, text=f"Found {len(matches)} match(es) across {len(set(m['file'] for m in matches))} file(s)", font=("Segoe UI", 11, "bold"), fg=self.accent_color, bg=self.bg_color).pack(anchor="w")
            tk.Label(p_hdr, text=f"Find: '{find_txt}'  ➔  Replace: '{replace_txt}' (Regex: {is_regex}, Case Sensitive: {case_sens})", font=("Segoe UI", 9), fg=self.text_dim, bg=self.bg_color).pack(anchor="w")

            tbl_frame = ttk.Frame(prev_win, padding=10)
            tbl_frame.pack(fill="both", expand=True)

            p_tree = ttk.Treeview(tbl_frame, columns=("file", "id", "field", "old", "new"), show="headings")
            p_tree.heading("file", text="File")
            p_tree.heading("id", text="ID")
            p_tree.heading("field", text="Field")
            p_tree.heading("old", text="Before")
            p_tree.heading("new", text="After")

            p_tree.column("file", width=140, anchor="w")
            p_tree.column("id", width=55, anchor="center")
            p_tree.column("field", width=75, anchor="w")
            p_tree.column("old", width=280, anchor="w")
            p_tree.column("new", width=280, anchor="w")

            p_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=p_tree.yview)
            p_tree.configure(yscrollcommand=p_scroll.set)
            p_tree.pack(side="left", fill="both", expand=True)
            p_scroll.pack(side="right", fill="y")

            for m in matches:
                p_tree.insert("", tk.END, values=(m['file'], m['id'], m['field'], m['old'].replace("\n", "{\\n}"), m['new'].replace("\n", "{\\n}")))

            b_bar = ttk.Frame(prev_win, padding=(15, 10))
            b_bar.pack(fill="x")

            def execute_from_preview():
                prev_win.destroy()
                run_replace()

            btn_apply_prev = tk.Button(b_bar, text=f"✅ Apply All {len(matches)} Replacements", command=execute_from_preview,
                                       bg=self.accent_color, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=15, pady=4)
            btn_apply_prev.pack(side="right", padx=(8, 0))
            self.bind_hover(btn_apply_prev, is_primary=True)

            btn_cancel_prev = tk.Button(b_bar, text="Cancel", command=prev_win.destroy,
                                        bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9), relief="flat", padx=12, pady=4)
            btn_cancel_prev.pack(side="right")
            self.bind_hover(btn_cancel_prev)
        
        def run_replace():
            find_txt = ent_find.get()
            replace_txt = ent_replace.get()
            scope = cmb_scope.get()
            case_sens = var_case.get()
            is_regex = var_regex.get()
            
            if not find_txt:
                messagebox.showwarning("Warning", "Please enter text to find.")
                return

            try:
                pattern = compile_pattern(find_txt, case_sens, is_regex)
            except Exception as e:
                messagebox.showerror("Regex Error", f"Invalid Regular Expression:\n{e}")
                return
                
            if scope == "Current File only":
                count = 0
                fields = ['name', 'sname', 'desc', 'sdesc'] if self.active_mode == 'kernel' else ['name']
                if self.active_file_name == "w_name.bin":
                    fields.extend(['w_wakka', 'w_lulu', 'w_rikku'])

                for r in self.records:
                    for field in fields:
                        orig = r.get(field, "")
                        if not orig:
                            continue
                        new_val, sub_count = pattern.subn(replace_txt, orig)
                        if sub_count > 0:
                            r[field] = new_val
                            count += sub_count
                if count > 0:
                    self.log(f"Search & Replace: Replaced {count} occurrences in current file memory.", "success")
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
                                new_val, sub_count = pattern.subn(replace_txt, orig)
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
                                rel = os.path.relpath(os.path.join(root, f), help_dir).replace("\\", "/")
                                if not rel.endswith("_page.sps2") and not any(sub in rel.lower() for sub in ["/gcm/", "/gnm/", "/gxm/", "gcm/", "gnm/", "gxm/"]):
                                    all_files.append((f"help/{rel}", os.path.join(root, f)))
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
                        if (f.endswith(".bin") or f == "macrodic.dcp") and not f.startswith("ffxsjis"):
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
                                new_val, sub_count = pattern.subn(replace_txt, orig)
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
        
        btn_run = tk.Button(btn_frame, text="Replace All", command=run_replace, bg=self.accent_color, fg="white",
                             font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.accent_hover, activeforeground="white", padx=15, pady=4)
        btn_run.pack(side="right")
        self.bind_hover(btn_run, is_primary=True)

        btn_prev = tk.Button(btn_frame, text="🔍 Preview Matches (Dry Run)", command=run_preview, bg=self.card_color, fg=self.text_color,
                             font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=12, pady=4)
        btn_prev.pack(side="right", padx=(0, 8))
        self.bind_hover(btn_prev)
        
        btn_cancel = tk.Button(btn_frame, text="Cancel", command=dialog.destroy, bg=self.card_color, fg=self.text_color,
                               font=("Segoe UI", 9, "bold"), relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=15, pady=4)
        btn_cancel.pack(side="left")
        self.bind_hover(btn_cancel)

    def save_bin_file(self):
        if not self.records or not self.active_file_path:
            messagebox.showwarning("Warning", "No active file loaded to save.")
            return False
            
        # Double check if any editing is unsaved in entry boxes
        sel = self.tree.selection()
        if sel:
            entry_id = int(sel[0]) if sel[0].isdigit() else sel[0]
            record = next((r for r in self.records if r['id'] == entry_id or str(r['id']) == str(entry_id)), None)
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
                elif self.active_mode in ('sps2', 'msg', 'macro') and hasattr(self, 'txt_dialogue'):
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
                        return False
                        
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
                return False

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
            self.is_dirty = False
            self.log(f"Repack complete! Successfully saved {written_size} bytes to '{self.active_file_name}'.", "success")
            messagebox.showinfo("Save Successful", f"File repacked successfully!\n\nFile: {self.active_file_name}\nBytes: {written_size}")
            return True
        except Exception as e:
            self.log(f"Repack failed: {e}", "error")
            messagebox.showerror("Save Error", f"Failed to repack and save file:\n{str(e)}")
            return False

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

    def show_macro_dictionary_dialog(self):
        """
        Modal browser for all in-game {MCR:...} macros across sections
        (Characters & NPCs, Blitzball Players & Techs, Field Locations, World Regions).
        Provides real-time search, category filtering, and 1-click insertion/copying.
        """
        if not hasattr(self, 'macro_db') or not self.macro_db:
            self.load_macro_dictionary()

        dialog = tk.Toplevel(self.root)
        dialog.title(f"🔍 FFX Macro Dictionary Browser ({len(self.macro_db)} Terms)")
        dialog.geometry("780x540")
        dialog.minsize(640, 420)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center relative to main window
        dialog.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        dx = rx + max(0, (rw - 780) // 2)
        dy = ry + max(0, (rh - 540) // 2)
        dialog.geometry(f"+{dx}+{dy}")

        # Header Frame
        header = ttk.Frame(dialog, padding=(18, 14, 18, 6))
        header.pack(fill="x")

        tk.Label(
            header,
            text="FFX In-Game Macro Dictionary ({MCR:...})",
            font=("Segoe UI", 13, "bold"),
            fg=self.accent_color,
            bg=self.bg_color
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Search characters, blitzball players/techs, and locations. Double-click or click 'Insert into Text' to place tag into active editor.",
            font=("Segoe UI", 9),
            fg=self.text_dim,
            bg=self.bg_color
        ).pack(anchor="w", pady=(2, 0))

        # Filter bar
        filter_frame = tk.Frame(dialog, bg=self.card_color, padx=12, pady=8, highlightbackground=self.border_color, highlightthickness=1)
        filter_frame.pack(fill="x", padx=18, pady=(4, 10))

        tk.Label(filter_frame, text="Search:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_color).pack(side="left", padx=(0, 6))
        
        ent_search = ttk.Entry(filter_frame, width=26, font=("Segoe UI", 9))
        ent_search.pack(side="left", padx=(0, 14))
        ent_search.focus_set()

        tk.Label(filter_frame, text="Category:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_color).pack(side="left", padx=(0, 6))

        categories = ["All Categories", "Characters & NPCs", "Blitzball Players", "Blitzball Techniques", "Field & Map Locations", "World Regions & Places"]
        cmb_cat = ttk.Combobox(filter_frame, values=categories, state="readonly", width=22, font=("Segoe UI", 9))
        cmb_cat.set("All Categories")
        cmb_cat.pack(side="left", padx=(0, 10))

        btn_clear = tk.Button(
            filter_frame, text="Clear", command=lambda: (ent_search.delete(0, tk.END), cmb_cat.set("All Categories"), refresh_list()),
            bg=self.bg_color, fg=self.text_dim, font=("Segoe UI", 8), relief="flat", padx=8, pady=2
        )
        btn_clear.pack(side="left")
        self.bind_hover(btn_clear)

        # Table container
        table_frame = tk.Frame(dialog, bg=self.bg_color, padx=18)
        table_frame.pack(fill="both", expand=True)

        cols = ("tag", "category", "text")
        tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        tree.heading("tag", text="Macro Tag", anchor="w")
        tree.heading("category", text="Category", anchor="w")
        tree.heading("text", text="In-Game Name / Text", anchor="w")

        tree.column("tag", width=120, minwidth=100, stretch=False)
        tree.column("category", width=190, minwidth=140, stretch=False)
        tree.column("text", width=420, minwidth=250, stretch=True)

        tree_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        # Edit Strip for in-memory modification of macros
        edit_strip = tk.Frame(dialog, bg=self.card_color, padx=12, pady=6, highlightbackground=self.border_color, highlightthickness=1)
        edit_strip.pack(fill="x", padx=18, pady=(6, 4))
        
        tk.Label(edit_strip, text="Selected Macro Text:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_color).pack(side="left", padx=(0, 6))
        ent_macro_text = ttk.Entry(edit_strip, font=("Segoe UI", 9))
        ent_macro_text.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def apply_macro_edit():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Warning", "Select a macro entry in the table first.")
                return
            new_text = ent_macro_text.get()
            vals = tree.item(sel[0], "values")
            tag = vals[0]
            cat = vals[1]
            tag_clean = tag.replace("{MCR:", "").replace("}", "").strip().lower()
            if tag_clean in self.macro_db:
                self.macro_db[tag_clean]['text'] = new_text
            tree.item(sel[0], values=(tag, cat, new_text))
            lbl_count.config(text=f"Updated '{tag}' to '{new_text}' (In-memory).")
            self.update_live_preview()

        btn_apply_macro = tk.Button(edit_strip, text="✏️ Apply Edit", command=apply_macro_edit,
                                    bg=self.accent_color, fg="white", font=("Segoe UI", 8, "bold"), relief="flat", padx=10, pady=2)
        btn_apply_macro.pack(side="left")
        self.bind_hover(btn_apply_macro, is_primary=True)

        def save_macrodic_to_disk():
            loc = self.cmb_local.get()
            charset = self.cmb_charset.get()
            default_path = os.path.join(self.codec.ffx_master_path, loc, "menu", "macrodic.dcp") if self.codec.ffx_master_path else "macrodic.dcp"
            save_path = filedialog.asksaveasfilename(
                title="Save macrodic.dcp",
                initialfile="macrodic.dcp",
                initialdir=os.path.dirname(default_path) if os.path.exists(os.path.dirname(default_path)) else None,
                defaultextension=".dcp",
                filetypes=[("FFX Macro Dictionary", "*.dcp"), ("All Files", "*.*")]
            )
            if not save_path:
                return
            bak = save_path + ".bak"
            if os.path.exists(save_path) and not os.path.exists(bak):
                import shutil
                shutil.copy2(save_path, bak)
            res = self.codec.write_macrodic_dcp(save_path, self.macro_db, charset)
            if res > 0:
                self.log(f"Successfully saved {res} bytes to macrodic.dcp: {save_path}", "success")
                messagebox.showinfo("Success", f"Successfully saved macrodic.dcp ({res} bytes)!\n\nPath:\n{save_path}")
            else:
                messagebox.showerror("Error", "Failed to write macrodic.dcp file.")

        # Bottom Action Bar
        bottom = tk.Frame(dialog, bg=self.bg_color, padx=18, pady=12)
        bottom.pack(fill="x")

        lbl_count = tk.Label(bottom, text="", font=("Segoe UI", 9, "italic"), fg=self.text_dim, bg=self.bg_color)
        lbl_count.pack(side="left")

        btn_close = tk.Button(
            bottom, text="Close", command=dialog.destroy,
            bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9),
            relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=14, pady=4
        )
        btn_close.pack(side="right", padx=(8, 0))
        self.bind_hover(btn_close)

        btn_save_macro_dcp = tk.Button(
            bottom, text="💾 Save macrodic.dcp", command=save_macrodic_to_disk,
            bg="#10b981", fg="white", font=("Segoe UI", 9, "bold"),
            relief="flat", activebackground="#059669", activeforeground="white", padx=12, pady=4
        )
        btn_save_macro_dcp.pack(side="right", padx=(8, 0))
        self.bind_hover(btn_save_macro_dcp, is_primary=True)

        def get_selected_tag():
            sel = tree.selection()
            if not sel:
                return None
            vals = tree.item(sel[0], "values")
            return vals[0] if vals else None

        def copy_selected():
            tag = get_selected_tag()
            if tag:
                self.root.clipboard_clear()
                self.root.clipboard_append(tag)
                lbl_count.config(text=f"Copied {tag} to clipboard!")

        def insert_selected():
            tag = get_selected_tag()
            if tag:
                self.insert_tag(tag)
                dialog.destroy()

        btn_insert = tk.Button(
            bottom, text="Insert into Text", command=insert_selected,
            bg=self.accent_color, fg="white", font=("Segoe UI", 9, "bold"),
            relief="flat", activebackground=self.accent_hover, activeforeground="white", padx=14, pady=4
        )
        btn_insert.pack(side="right", padx=(8, 0))
        self.bind_hover(btn_insert, is_primary=True)

        btn_copy = tk.Button(
            bottom, text="📋 Copy Tag", command=copy_selected,
            bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9),
            relief="flat", activebackground=self.border_color, activeforeground=self.text_color, padx=12, pady=4
        )
        btn_copy.pack(side="right")
        self.bind_hover(btn_copy)

        def on_macro_tree_select(event):
            sel = tree.selection()
            if sel:
                vals = tree.item(sel[0], "values")
                ent_macro_text.delete(0, tk.END)
                ent_macro_text.insert(0, vals[2] if len(vals) > 2 else "")
        tree.bind("<<TreeviewSelect>>", on_macro_tree_select)

        def refresh_list(event=None):
            query = ent_search.get().strip().lower()
            cat_filter = cmb_cat.get()
            
            for row in tree.get_children():
                tree.delete(row)
                
            count = 0
            for tag_key, item in sorted(self.macro_db.items(), key=lambda x: (x[1].get('sec_id', 0), x[1].get('item_id', 0))):
                item_cat = item.get('category', '')
                item_text = item.get('text', '')
                item_tag = item.get('tag', '')

                if cat_filter != "All Categories" and item_cat != cat_filter:
                    continue

                if query:
                    if (query not in item_text.lower() and 
                        query not in item_tag.lower() and 
                        query not in item_cat.lower()):
                        continue

                tree.insert("", "end", values=(item_tag, item_cat, item_text))
                count += 1

            lbl_count.config(text=f"Showing {count} of {len(self.macro_db)} macro terms (double-click row to insert)")

        ent_search.bind("<KeyRelease>", refresh_list)
        cmb_cat.bind("<<ComboboxSelected>>", refresh_list)
        tree.bind("<Double-1>", lambda e: insert_selected())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        refresh_list()

    def open_mod_packager_dialog(self):
        """
        1-Click Mod Packaging Engine for Spira Mod Manager & Nexus Mods.
        Packages modified/active localization files into a release-ready .zip
        with modinfo.spiramod, modinfo.json, and the standard ffx_ps2/ffx/master/<loc>/... tree.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("📦 Package Mod for Spira Mod Manager & Nexus Mods")
        dialog.geometry("560x580")
        dialog.minsize(500, 480)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center relative to main window
        dialog.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        dx = rx + max(0, (rw - 560) // 2)
        dy = ry + max(0, (rh - 580) // 2)
        dialog.geometry(f"+{dx}+{dy}")

        header = ttk.Frame(dialog, padding=(18, 14, 18, 6))
        header.pack(fill="x")
        tk.Label(header, text="📦 1-Click Mod Packaging Engine", font=("Segoe UI", 13, "bold"), fg=self.accent_color, bg=self.bg_color).pack(anchor="w")
        tk.Label(header, text="Generates a 100% Spira Mod Manager & Nexus Mods compatible release archive (.zip) with modinfo metadata and correct relative paths.",
                 font=("Segoe UI", 9), fg=self.text_dim, bg=self.bg_color, wraplength=520, justify="left").pack(anchor="w", pady=(3, 0))

        content = ttk.Frame(dialog, padding=(18, 6, 18, 10))
        content.pack(fill="both", expand=True)

        # Mod Metadata Group
        grp_meta = ttk.LabelFrame(content, text=" Mod Information ", padding=12)
        grp_meta.pack(fill="x", pady=(0, 10))
        grp_meta.columnconfigure(1, weight=1)

        ttk.Label(grp_meta, text="Mod Name:").grid(row=0, column=0, sticky="w", pady=4)
        ent_mod_name = ttk.Entry(grp_meta)
        loc = self.cmb_local.get() if hasattr(self, 'cmb_local') else "new_uspc"
        is_ffx2 = ("X-2" in getattr(self, "active_game", "Final Fantasy X"))
        game_tag = "FFX-2" if is_ffx2 else "FFX"
        ent_mod_name.insert(0, f"{game_tag} {loc.upper()} Text Translation Patch")
        ent_mod_name.grid(row=0, column=1, sticky="ew", pady=4, padx=(8, 0))

        ttk.Label(grp_meta, text="Author / Creator:").grid(row=1, column=0, sticky="w", pady=4)
        ent_author = ttk.Entry(grp_meta)
        ent_author.insert(0, "NfgOdin / Translator")
        ent_author.grid(row=1, column=1, sticky="ew", pady=4, padx=(8, 0))

        ttk.Label(grp_meta, text="Version:").grid(row=2, column=0, sticky="w", pady=4)
        ent_ver = ttk.Entry(grp_meta)
        ent_ver.insert(0, "1.0.0")
        ent_ver.grid(row=2, column=1, sticky="ew", pady=4, padx=(8, 0))

        ttk.Label(grp_meta, text="Category:").grid(row=3, column=0, sticky="w", pady=4)
        cmb_cat = ttk.Combobox(grp_meta, state="readonly", values=[
            "Miscellaneous",
            "User Interface",
            "Gameplay and Balancing",
            "Armour and Clothing",
            "Audio",
            "Models and Textures",
            "Saved Games",
            "Utilities",
            "Visuals and Graphics",
            "General"
        ])
        cmb_cat.set("Miscellaneous")
        cmb_cat.grid(row=3, column=1, sticky="ew", pady=4, padx=(8, 0))

        ttk.Label(grp_meta, text="Nexus Mod ID (Optional):").grid(row=4, column=0, sticky="w", pady=4)
        ent_nexus = ttk.Entry(grp_meta)
        ent_nexus.grid(row=4, column=1, sticky="ew", pady=4, padx=(8, 0))

        ttk.Label(grp_meta, text="Description:").grid(row=5, column=0, sticky="nw", pady=4)
        txt_desc = tk.Text(grp_meta, height=3, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9), relief="flat", highlightbackground=self.border_color, highlightthickness=1)
        txt_desc.insert("1.0", f"Localization and dialogue text modifications for {'Final Fantasy X-2' if is_ffx2 else 'Final Fantasy X'} ({loc}). Compatible with Spira Mod Manager and manual install.")
        txt_desc.grid(row=5, column=1, sticky="ew", pady=4, padx=(8, 0))

        # File Selection Scope Group
        grp_scope = ttk.LabelFrame(content, text=" Packaging Scope ", padding=12)
        grp_scope.pack(fill="x", pady=(0, 10))

        var_scope = tk.StringVar(value="modified")
        ttk.Radiobutton(grp_scope, text="Modified files only (files with .bak backups or active session changes)", variable=var_scope, value="modified").pack(anchor="w", pady=3)
        ttk.Radiobutton(grp_scope, text=f"All files in the currently active category ({self.cmb_category.get() if hasattr(self, 'cmb_category') else 'Category'})", variable=var_scope, value="category").pack(anchor="w", pady=3)
        ttk.Radiobutton(grp_scope, text=f"All supported files in active localization folder ({loc})", variable=var_scope, value="loc").pack(anchor="w", pady=3)

        # Output Zip Path Group
        grp_out = ttk.LabelFrame(content, text=" Output Release Archive (.zip) ", padding=12)
        grp_out.pack(fill="x", pady=(0, 10))
        grp_out.columnconfigure(0, weight=1)

        ent_out_zip = ttk.Entry(grp_out)
        default_zip_name = f"{ent_mod_name.get().replace(' ', '_')}_v{ent_ver.get()}.zip"
        ent_out_zip.insert(0, os.path.abspath(default_zip_name))
        ent_out_zip.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        def browse_zip_out():
            p = filedialog.asksaveasfilename(
                title="Select Output Release Zip",
                initialfile=os.path.basename(ent_out_zip.get()),
                defaultextension=".zip",
                filetypes=[("Zip Archive", "*.zip")]
            )
            if p:
                ent_out_zip.delete(0, tk.END)
                ent_out_zip.insert(0, os.path.abspath(p))

        btn_browse_zip = tk.Button(grp_out, text="Browse...", command=browse_zip_out, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9), relief="flat")
        btn_browse_zip.grid(row=0, column=1, sticky="e")
        self.bind_hover(btn_browse_zip)

        def encode_spiramod_meta(meta_dict):
            try:
                import json, base64
                json_str = json.dumps(meta_dict, indent=2)
                key = b"AuronTidusYunaRikkuLuluWakkaKimahri"
                data_bytes = json_str.encode('utf-8')
                obfuscated = bytes([b ^ key[i % len(key)] for i, b in enumerate(data_bytes)])
                return base64.b64encode(obfuscated).decode('utf-8')
            except Exception:
                return ""

        def build_package():
            name = ent_mod_name.get().strip() or "FFX Mod"
            author = ent_author.get().strip() or "Modder"
            version = ent_ver.get().strip() or "1.0.0"
            category = cmb_cat.get()
            nexus_id = ent_nexus.get().strip()
            desc = txt_desc.get("1.0", "end").strip()
            out_path = ent_out_zip.get().strip()
            scope = var_scope.get()

            if not out_path:
                messagebox.showwarning("Warning", "Please specify an output zip filename.")
                return

            # Gather target files to package
            files_to_pack = [] # list of (abs_path, rel_path_in_zip)
            master_p = self.codec.ffx_master_path
            loc_name = self.cmb_local.get()
            loc_dir = os.path.join(master_p, loc_name) if master_p else ""
            is_ffx2 = ("X-2" in getattr(self, "active_game", "Final Fantasy X"))
            game_dir = "ffx2" if is_ffx2 else "ffx"
            game_meta = "FFX-2" if is_ffx2 else "FFX"

            if scope == "modified":
                # Find all files with .bak backups in loc_dir
                if loc_dir and os.path.exists(loc_dir):
                    for root, dirs, files in os.walk(loc_dir):
                        for f in files:
                            if f.endswith(".bak"):
                                orig_f = f[:-4]
                                orig_abs = os.path.join(root, orig_f)
                                if os.path.exists(orig_abs):
                                    rel_from_loc = os.path.relpath(orig_abs, loc_dir).replace("\\", "/")
                                    rel_in_zip = f"ffx_ps2/{game_dir}/master/{loc_name}/{rel_from_loc}"
                                    files_to_pack.append((orig_abs, rel_in_zip))
                # Also include active file if loaded and not already in list
                if self.active_file_path and os.path.exists(self.active_file_path):
                    if not any(f[0] == self.active_file_path for f in files_to_pack):
                        rel_from_loc = os.path.relpath(self.active_file_path, loc_dir).replace("\\", "/") if loc_dir else self.active_file_name
                        rel_in_zip = f"ffx_ps2/{game_dir}/master/{loc_name}/{rel_from_loc}"
                        files_to_pack.append((self.active_file_path, rel_in_zip))
            elif scope == "category":
                for rel_key, fpath in getattr(self, 'file_map', {}).items():
                    if os.path.exists(fpath):
                        rel_from_loc = os.path.relpath(fpath, loc_dir).replace("\\", "/") if loc_dir else rel_key
                        rel_in_zip = f"ffx_ps2/{game_dir}/master/{loc_name}/{rel_from_loc}"
                        files_to_pack.append((fpath, rel_in_zip))
            else: # full loc
                if loc_dir and os.path.exists(loc_dir):
                    for root, dirs, files in os.walk(loc_dir):
                        for f in files:
                            if f.endswith(".bak") or f.endswith(".tmp"): continue
                            abs_p = os.path.join(root, f)
                            rel_from_loc = os.path.relpath(abs_p, loc_dir).replace("\\", "/")
                            rel_in_zip = f"ffx_ps2/{game_dir}/master/{loc_name}/{rel_from_loc}"
                            files_to_pack.append((abs_p, rel_in_zip))

            if not files_to_pack:
                messagebox.showwarning("No Files Found", 
                    "No matching modified or localization files were found to package.\n\n"
                    "Make sure you have saved edits (which generates .bak backups), or select 'All files in category'.")
                return

            try:
                import zipfile, json
                rel_manifest_files = [rel for (_, rel) in files_to_pack]
                export_meta = {
                    "name": name,
                    "game": game_meta,
                    "author": author,
                    "creator": author,
                    "version": version,
                    "category": category,
                    "description": desc,
                    "nexus_id": nexus_id,
                    "link": f"https://www.nexusmods.com/{'finalfantasyx2' if is_ffx2 else 'finalfantasyx'}/mods/{nexus_id}" if nexus_id else "",
                    "files": rel_manifest_files,
                    "generator": f"FFX & FFX-2 Text & Localization Studio {APP_VERSION} (Spira Mod Manager Ready)"
                }

                spiramod_data = encode_spiramod_meta(export_meta)
                json_data = json.dumps(export_meta, indent=2)

                os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
                with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
                    # Write metadata manifests at root
                    z.writestr("modinfo.spiramod", spiramod_data)
                    z.writestr("modinfo.json", json_data)
                    # Write files
                    for abs_p, rel_p in files_to_pack:
                        z.write(abs_p, rel_p)

                pkg_size = os.path.getsize(out_path) / 1024.0
                self.log(f"Mod Packager: Created release archive '{os.path.basename(out_path)}' ({len(files_to_pack)} files, {pkg_size:.1f} KB).", "success")
                dialog.destroy()
                messagebox.showinfo("Packaging Complete!",
                    f"🎉 Successfully packaged mod release archive!\n\n"
                    f"• Archive: {os.path.basename(out_path)}\n"
                    f"• Packaged Files: {len(files_to_pack)}\n"
                    f"• Size: {pkg_size:.1f} KB\n"
                    f"• Location: {out_path}\n\n"
                    "100% Compatible with:\n"
                    "✓ Spira Mod Manager (Install via 'Install Mod Archive' or Drag & Drop)\n"
                    "✓ Nexus Mods / Vortex / Manual extract")
            except Exception as e:
                self.log(f"Mod packaging failed: {e}", "error")
                messagebox.showerror("Packaging Error", f"Failed to build mod archive:\n{e}")

        # Bottom Button Bar
        btn_bar = ttk.Frame(dialog, padding=(18, 10))
        btn_bar.pack(fill="x")

        btn_build = tk.Button(btn_bar, text="📦 Build Release Archive (.zip)", command=build_package,
                              bg=self.accent_color, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", activebackground=self.accent_hover, activeforeground="white", padx=18, pady=6)
        btn_build.pack(side="right")
        self.bind_hover(btn_build, is_primary=True)

        btn_cancel = tk.Button(btn_bar, text="Cancel", command=dialog.destroy,
                               bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9), relief="flat", padx=12, pady=4)
        btn_cancel.pack(side="right", padx=(0, 10))
        self.bind_hover(btn_cancel)

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

    def build_menu_bar(self):
        menubar = tk.Menu(self.root, bg=self.card_color, fg=self.text_color, activebackground=self.accent_color, activeforeground="white")
        
        # File Menu
        menu_file = tk.Menu(menubar, tearoff=0, bg=self.card_color, fg=self.text_color, activebackground=self.accent_color, activeforeground="white")
        menu_file.add_command(label="💾 Repack & Save .bin File", command=self.save_bin_file, accelerator="Ctrl+S")
        menu_file.add_separator()
        self.menu_recent = tk.Menu(menu_file, tearoff=0, bg=self.card_color, fg=self.text_color, activebackground=self.accent_color, activeforeground="white")
        menu_file.add_cascade(label="Recent Files", menu=self.menu_recent)
        self.update_recent_files_menu()
        menu_file.add_separator()
        menu_file.add_command(label="📥 Export CSV (Single/Batch)...", command=self.export_csv, accelerator="Ctrl+Shift+E")
        menu_file.add_command(label="📤 Import CSV (Single/Batch)...", command=self.import_csv, accelerator="Ctrl+Shift+I")
        menu_file.add_separator()
        menu_file.add_command(label="📦 Package Mod (SpiraMM / Nexus)...", command=self.open_mod_packager_dialog, accelerator="Ctrl+Shift+P")
        menu_file.add_separator()
        menu_file.add_command(label="Exit", command=self.on_window_closing)
        menubar.add_cascade(label="File", menu=menu_file)

        # Edit Menu
        menu_edit = tk.Menu(menubar, tearoff=0, bg=self.card_color, fg=self.text_color, activebackground=self.accent_color, activeforeground="white")
        menu_edit.add_command(label="Apply Current Edits", command=self.apply_row_edits, accelerator="Ctrl+Enter")
        menu_edit.add_separator()
        menu_edit.add_command(label="🔍 Focus Search", command=self.focus_search, accelerator="Ctrl+F")
        menu_edit.add_command(label="Find Next Entry", command=self.find_next_match, accelerator="F3")
        menu_edit.add_command(label="Find Previous Entry", command=self.find_prev_match, accelerator="Shift+F3")
        menu_edit.add_separator()
        menu_edit.add_command(label="🔎 Global Search & Replace...", command=self.open_search_replace_dialog)
        menu_edit.add_command(label="⚡ Batch Replacement Rulesets...", command=self.open_batch_ruleset_dialog)
        menubar.add_cascade(label="Edit", menu=menu_edit)

        # View Menu
        menu_view = tk.Menu(menubar, tearoff=0, bg=self.card_color, fg=self.text_color, activebackground=self.accent_color, activeforeground="white")
        menu_view.add_command(label="Toggle Dual-Locale Reference Split", command=self.toggle_reference_split_hotkey, accelerator="Ctrl+R")
        menu_view.add_command(label="Visual Side-by-Side Diff...", command=self.open_visual_diff_dialog)
        menubar.add_cascade(label="View", menu=menu_view)

        # QA & Tools Menu
        menu_tools = tk.Menu(menubar, tearoff=0, bg=self.card_color, fg=self.text_color, activebackground=self.accent_color, activeforeground="white")
        menu_tools.add_command(label="🛡️ QA Syntax & Crash Auditor...", command=self.open_qa_auditor_dialog, accelerator="Ctrl+Shift+Q")
        menu_tools.add_command(label="📊 Translation & Progress Dashboard...", command=self.open_project_dashboard_dialog)
        menu_tools.add_separator()
        menu_tools.add_command(label="📚 Canonical Multi-Language Lore Glossary...", command=self.show_canonical_lore_dialog)
        menu_tools.add_command(label="🔍 In-Game Macro Dictionary...", command=self.show_macro_dictionary_dialog)
        menu_tools.add_command(label="📖 Control Tags Cheat Sheet...", command=self.show_cheat_sheet_dialog)
        menubar.add_cascade(label="QA & Tools", menu=menu_tools)

        # Help Menu
        menu_help = tk.Menu(menubar, tearoff=0, bg=self.card_color, fg=self.text_color, activebackground=self.accent_color, activeforeground="white")
        menu_help.add_command(label="About Studio", command=self.show_about_dialog)
        menubar.add_cascade(label="Help", menu=menu_help)

        self.root.config(menu=menubar)

    def setup_global_shortcuts(self):
        self.root.bind("<Control-s>", lambda e: (self.save_bin_file(), "break")[1])
        self.root.bind("<Control-S>", lambda e: (self.save_bin_file(), "break")[1])
        self.root.bind("<Control-f>", lambda e: (self.focus_search(), "break")[1])
        self.root.bind("<Control-F>", lambda e: (self.focus_search(), "break")[1])
        self.root.bind("<F3>", lambda e: (self.find_next_match(), "break")[1])
        self.root.bind("<Shift-F3>", lambda e: (self.find_prev_match(), "break")[1])
        self.root.bind("<Control-r>", lambda e: (self.toggle_reference_split_hotkey(), "break")[1])
        self.root.bind("<Control-R>", lambda e: (self.toggle_reference_split_hotkey(), "break")[1])
        self.root.bind("<Control-Shift-E>", lambda e: (self.export_csv(), "break")[1])
        self.root.bind("<Control-Shift-e>", lambda e: (self.export_csv(), "break")[1])
        self.root.bind("<Control-Shift-I>", lambda e: (self.import_csv(), "break")[1])
        self.root.bind("<Control-Shift-i>", lambda e: (self.import_csv(), "break")[1])
        self.root.bind("<Control-Shift-P>", lambda e: (self.open_mod_packager_dialog(), "break")[1])
        self.root.bind("<Control-Shift-p>", lambda e: (self.open_mod_packager_dialog(), "break")[1])
        self.root.bind("<Control-Shift-Q>", lambda e: (self.open_qa_auditor_dialog(), "break")[1])
        self.root.bind("<Control-Shift-q>", lambda e: (self.open_qa_auditor_dialog(), "break")[1])
        self.root.bind("<Control-t>", lambda e: (self.apply_translation_memory(), "break")[1])
        self.root.bind("<Control-T>", lambda e: (self.apply_translation_memory(), "break")[1])
        self.root.bind("<Control-Return>", lambda e: (self.apply_row_edits(), "break")[1])

    def focus_search(self):
        if hasattr(self, 'ent_search'):
            self.ent_search.focus_set()
            self.ent_search.select_range(0, tk.END)

    def find_next_match(self):
        children = self.tree.get_children()
        if not children:
            return
        sel = self.tree.selection()
        if not sel or sel[0] not in children:
            next_item = children[0]
        else:
            curr_idx = children.index(sel[0])
            next_idx = (curr_idx + 1) % len(children)
            next_item = children[next_idx]
        self.tree.selection_set(next_item)
        self.tree.see(next_item)
        self.on_tree_row_selected(None)

    def find_prev_match(self):
        children = self.tree.get_children()
        if not children:
            return
        sel = self.tree.selection()
        if not sel or sel[0] not in children:
            prev_item = children[-1]
        else:
            curr_idx = children.index(sel[0])
            prev_idx = (curr_idx - 1) % len(children)
            prev_item = children[prev_idx]
        self.tree.selection_set(prev_item)
        self.tree.see(prev_item)
        self.on_tree_row_selected(None)

    def toggle_reference_split_hotkey(self):
        if hasattr(self, 'var_show_ref'):
            self.var_show_ref.set(not self.var_show_ref.get())
            self.toggle_reference_view()

    def _start_prompt_blink(self):
        if self._prompt_after_id:
            try:
                self.root.after_cancel(self._prompt_after_id)
            except Exception:
                pass
            self._prompt_after_id = None
        self._blink_prompt_tick()

    def _blink_prompt_tick(self):
        self._blink_state = not self._blink_state
        if hasattr(self, 'txt_preview_body') and hasattr(self, '_has_pause_prompt') and self._has_pause_prompt:
            try:
                fg = getattr(self, 'speaker_fg', '#38bdf8') if self._blink_state else getattr(self, 'preview_bg', '#040a18')
                self.txt_preview_body.tag_configure('prev_prompt', foreground=fg)
            except Exception:
                pass
        try:
            self._prompt_after_id = self.root.after(500, self._blink_prompt_tick)
        except Exception:
            pass

    def open_qa_auditor_dialog(self):
        """
        Automated QA & Crash Prevention Engine (Pillar 2).
        Deep-scans for:
        - Bracket balance ({ vs })
        - Unknown/malformed engine tags
        - Unclosed color tags ({CLR:...} without terminating {CLR:WHITE})
        - Dialogue line width overflow (>43 chars)
        - Dialogue line height overflow (>4 lines)
        - Entry byte overflow (>500B warning, >800B critical)
        - 16-bit offset pool overflow (>60,000B warning, >65,535B FATAL)
        Provides double-click jump to file/entry and 1-click Auto-Fix.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("🛡️ Automated QA & Syntax Crash Auditor")
        dialog.geometry("860x600")
        dialog.minsize(720, 480)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        dx = rx + max(0, (rw - 860) // 2)
        dy = ry + max(0, (rh - 600) // 2)
        dialog.geometry(f"+{dx}+{dy}")

        header = ttk.Frame(dialog, padding=(18, 14, 18, 6))
        header.pack(fill="x")
        tk.Label(header, text="🛡️ Automated QA & Syntax Crash Auditor", font=("Segoe UI", 13, "bold"), fg=self.accent_color, bg=self.bg_color).pack(anchor="w")
        tk.Label(header, text="Deep-scans text records for syntax corruption, unclosed tags, ruler overflow, byte overflow, and fatal 16-bit offset pool limits.",
                 font=("Segoe UI", 9), fg=self.text_dim, bg=self.bg_color).pack(anchor="w", pady=(2, 0))

        # Controls Strip
        ctrl_frame = tk.Frame(dialog, bg=self.card_color, padx=12, pady=8, highlightbackground=self.border_color, highlightthickness=1)
        ctrl_frame.pack(fill="x", padx=18, pady=(4, 8))

        tk.Label(ctrl_frame, text="Audit Scope:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_color).pack(side="left", padx=(0, 6))
        cmb_scope = ttk.Combobox(ctrl_frame, values=["Current File", "Current Category", "Entire Localization"], state="readonly", width=18, font=("Segoe UI", 9))
        cmb_scope.set("Current File")
        cmb_scope.pack(side="left", padx=(0, 14))

        tk.Label(ctrl_frame, text="Severity Filter:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_color).pack(side="left", padx=(0, 6))
        cmb_sev = ttk.Combobox(ctrl_frame, values=["All Issues", "🔴 Critical Only", "🟡 Warnings Only"], state="readonly", width=16, font=("Segoe UI", 9))
        cmb_sev.set("All Issues")
        cmb_sev.pack(side="left", padx=(0, 14))

        # Results treeview
        tree_frame = tk.Frame(dialog, bg=self.bg_color, padx=18)
        tree_frame.pack(fill="both", expand=True)

        cols = ("sev", "file", "id", "field", "issue", "snip")
        tree_audit = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        tree_audit.heading("sev", text="Severity", anchor="center")
        tree_audit.heading("file", text="File", anchor="w")
        tree_audit.heading("id", text="ID", anchor="center")
        tree_audit.heading("field", text="Field", anchor="w")
        tree_audit.heading("issue", text="Detected Issue", anchor="w")
        tree_audit.heading("snip", text="Snippet / Preview", anchor="w")

        tree_audit.column("sev", width=85, minwidth=70, stretch=False, anchor="center")
        tree_audit.column("file", width=130, minwidth=100, stretch=False)
        tree_audit.column("id", width=55, minwidth=45, stretch=False, anchor="center")
        tree_audit.column("field", width=80, minwidth=70, stretch=False)
        tree_audit.column("issue", width=300, minwidth=180, stretch=True)
        tree_audit.column("snip", width=190, minwidth=120, stretch=True)

        tree_audit.tag_configure("critical", foreground="#f87171", background="#2a1215")
        tree_audit.tag_configure("warning", foreground="#fbbf24", background="#261e12")
        tree_audit.tag_configure("info", foreground="#38bdf8", background="#111c2e")

        scr = ttk.Scrollbar(tree_frame, orient="vertical", command=tree_audit.yview)
        tree_audit.configure(yscrollcommand=scr.set)
        tree_audit.pack(side="left", fill="both", expand=True)
        scr.pack(side="right", fill="y")

        # Bottom Bar
        bottom = tk.Frame(dialog, bg=self.bg_color, padx=18, pady=10)
        bottom.pack(fill="x")

        lbl_summary = tk.Label(bottom, text="Ready to audit.", font=("Segoe UI", 9, "bold"), fg=self.text_dim, bg=self.bg_color)
        lbl_summary.pack(side="left")

        all_detected_issues = []

        def run_scanner():
            nonlocal all_detected_issues
            for r in tree_audit.get_children():
                tree_audit.delete(r)
            all_detected_issues.clear()
            
            scope = cmb_scope.get()
            sev_filter = cmb_sev.get()
            charset = self.cmb_charset.get() if hasattr(self, 'cmb_charset') else 'us'

            files_to_scan = [] # list of (file_label, full_path, records_or_none)
            if scope == "Current File":
                if self.active_file_path and os.path.exists(self.active_file_path):
                    files_to_scan.append((self.active_file_name, self.active_file_path, self.records))
            elif scope == "Current Category":
                for rel, fpath in getattr(self, 'file_map', {}).items():
                    if os.path.exists(fpath):
                        recs = self.records if (fpath == self.active_file_path) else None
                        files_to_scan.append((rel, fpath, recs))
            else: # Entire Localization
                loc = self.cmb_local.get()
                loc_dir = os.path.join(self.codec.ffx_master_path, loc) if self.codec.ffx_master_path else ""
                if loc_dir and os.path.exists(loc_dir):
                    for root, dirs, files in os.walk(loc_dir):
                        for f in files:
                            if f.endswith(".bin") or f.endswith(".sps2") or f.endswith(".dcp"):
                                if f.endswith(".bak") or f.startswith("ffxsjis") or f.endswith("_page.sps2"):
                                    continue
                                fp = os.path.join(root, f)
                                rel = os.path.relpath(fp, loc_dir).replace("\\", "/")
                                recs = self.records if (fp == self.active_file_path) else None
                                files_to_scan.append((rel, fp, recs))

            if not files_to_scan:
                messagebox.showwarning("Warning", "No files found to audit.")
                return

            crit_count = 0
            warn_count = 0

            for fname, fpath, loaded_recs in files_to_scan:
                recs = loaded_recs
                if recs is None:
                    try:
                        record_len = FILE_RECORD_SIZES.get(os.path.basename(fname), 16)
                        recs, _, _, _, _ = self.codec.load_any_ffx_file(fpath, record_len, charset)
                    except Exception:
                        recs = []

                if not recs:
                    continue

                # 1. Check String Pool 16-bit Limit
                unique_strings = set()
                for r in recs:
                    for fld in ('name', 'sname', 'desc', 'sdesc', 'w_wakka', 'w_lulu', 'w_rikku'):
                        v = r.get(fld)
                        if v and isinstance(v, str):
                            unique_strings.add(v)
                pool_size = sum(len(self.codec.encode_ffx_string(s, charset)) + 1 for s in unique_strings)
                if pool_size > 65535:
                    iss = ('🔴 CRITICAL', fname, 0, 'FILE_POOL', f"FATAL POINTER OVERFLOW: Pool is {pool_size}B (>65,535B 16-bit limit)! WILL CRASH ENGINE", f"{len(unique_strings)} strings", False, None, fpath)
                    all_detected_issues.append(iss)
                    crit_count += 1
                elif pool_size > 60000:
                    iss = ('🟡 WARNING', fname, 0, 'FILE_POOL', f"Pool size {pool_size}B is dangerously close to 65,535B limit!", f"{len(unique_strings)} strings", False, None, fpath)
                    all_detected_issues.append(iss)
                    warn_count += 1

                # 2. Check Each Entry
                for r in recs:
                    eid = r.get('id', 0)
                    fields_to_check = [('name', r.get('name', ''))]
                    for optional_field in ('sname', 'desc', 'sdesc', 'w_wakka', 'w_lulu', 'w_rikku'):
                        if optional_field in r and r.get(optional_field):
                            fields_to_check.append((optional_field, r.get(optional_field, '')))

                    for fld, val in fields_to_check:
                        if not val or not isinstance(val, str):
                            continue
                            
                        # Brackets
                        n_open = val.count('{')
                        n_close = val.count('}')
                        if n_open != n_close:
                            iss = ('🔴 CRITICAL', fname, eid, fld, f"Unbalanced braces: {n_open} '{{' vs {n_close} '}}'", val[:60], False, None, fpath)
                            all_detected_issues.append(iss)
                            crit_count += 1

                        # Tags
                        tags = re.findall(r'\{([^}]+)\}', val)
                        for t in tags:
                            ct = t.strip()
                            if ' ' in t:
                                iss = ('🟡 WARNING', fname, eid, fld, f"Whitespace inside tag: '{{{t}}}'", f"{{{t}}}", True, 'normalize_tag_whitespace', fpath)
                                all_detected_issues.append(iss)
                                warn_count += 1
                            known = ("CLR:", "TIME:", "WAIT:", "KEY:", "CHOICE:", "CHOICE-END", "VAR:", "VO_VAR:",
                                     "NUM:", "NAME:", "MACRO:", "MCR:", "CHAR:", "ITEM:", "MAP:", "SPACE:",
                                     "PAD_", "BTN_", "PC:", "CTRL:", "CMD:", "UNKP:", "UNK:", "PAUSE", "NEWLINE")
                            if not any(ct.upper().startswith(k) or ct.upper() == k for k in known):
                                iss = ('🟡 WARNING', fname, eid, fld, f"Unrecognized engine tag: '{{{t}}}'", f"{{{t}}}", False, None, fpath)
                                all_detected_issues.append(iss)
                                warn_count += 1

                        # Trailing whitespace on lines
                        if any(l.endswith(' ') or l.endswith('\t') for l in lines):
                            iss = ('🟡 WARNING', fname, eid, fld, "Trailing whitespace detected on line(s)", val[:40], True, 'trim_trailing_whitespace', fpath)
                            all_detected_issues.append(iss)
                            warn_count += 1

                        # Color tag closure
                        clrs = re.findall(r'\{CLR:([^}]+)\}', val)
                        if clrs:
                            last_clr = clrs[-1].upper()
                            if last_clr != "WHITE":
                                iss = ('🟡 WARNING', fname, eid, fld, f"Unclosed color tag (ends in '{last_clr}', will leak without {{CLR:WHITE}})", val[-40:], True, 'append_white', fpath)
                                all_detected_issues.append(iss)
                                warn_count += 1

                        # Line length and height
                        lines = val.replace("{\\n}", "\n").replace("{/n}", "\n").replace("{n}", "\n").split('\n')
                        clean_lines = [re.sub(r'\{[^}]+\}', '', l) for l in lines]
                        for l_idx, cl in enumerate(clean_lines, 1):
                            if len(cl) > 50:
                                iss = ('🔴 CRITICAL', fname, eid, fld, f"Line {l_idx} overflow: {len(cl)} chars (>50 chars, cutoff imminent)", cl[:45] + "...", False, None, fpath)
                                all_detected_issues.append(iss)
                                crit_count += 1
                            elif len(cl) > 43:
                                iss = ('🟡 WARNING', fname, eid, fld, f"Line {l_idx} width: {len(cl)} chars (safe width ~42-43 chars)", cl[:45] + "...", False, None, fpath)
                                all_detected_issues.append(iss)
                                warn_count += 1
                        if len(clean_lines) > 4:
                            iss = ('🟡 WARNING', fname, eid, fld, f"Height overflow: {len(clean_lines)} lines (box displays max 4 lines)", clean_lines[0][:40], False, None, fpath)
                            all_detected_issues.append(iss)
                            warn_count += 1

                        # Entry byte length
                        try:
                            encoded_len = len(self.codec.encode_ffx_string(val, charset))
                            if encoded_len > 800:
                                iss = ('🔴 CRITICAL', fname, eid, fld, f"Entry size {encoded_len}B exceeds 800B capacity limit!", val[:40], False, None, fpath)
                                all_detected_issues.append(iss)
                                crit_count += 1
                            elif encoded_len > 500:
                                iss = ('🟡 WARNING', fname, eid, fld, f"Entry size {encoded_len}B is high (>500B)", val[:40], False, None, fpath)
                                all_detected_issues.append(iss)
                                warn_count += 1
                        except Exception:
                            pass

            self.current_audit_issues = list(all_detected_issues)
            populate_audit_tree()
            lbl_summary.config(text=f"Scan complete across {len(files_to_scan)} file(s):  🔴 {crit_count} Critical  |  🟡 {warn_count} Warnings")

        def populate_audit_tree():
            for r in tree_audit.get_children():
                tree_audit.delete(r)
            sev_filter = cmb_sev.get()
            
            for iss in all_detected_issues:
                sev = iss[0]
                if "Critical" in sev_filter and "CRITICAL" not in sev:
                    continue
                if "Warnings" in sev_filter and "WARNING" not in sev:
                    continue
                tag = "critical" if "CRITICAL" in sev else ("warning" if "WARNING" in sev else "info")
                tree_audit.insert("", "end", values=(iss[0], iss[1], iss[2], iss[3], iss[4], iss[5]), tags=(tag,))

        cmb_sev.bind("<<ComboboxSelected>>", lambda e: populate_audit_tree())

        def on_audit_double_click(event):
            sel = tree_audit.selection()
            if not sel:
                return
            vals = tree_audit.item(sel[0], "values")
            fname = vals[1]
            try:
                target_id = int(vals[2])
            except ValueError:
                target_id = vals[2]
            target_fld = vals[3]

            matching_iss = next((i for i in all_detected_issues if i[1] == fname and str(i[2]) == str(target_id) and i[3] == target_fld), None)
            if not matching_iss:
                return
            target_fpath = matching_iss[8]

            if target_fpath != self.active_file_path:
                switched = False
                for k, p in getattr(self, 'file_map', {}).items():
                    if p == target_fpath or os.path.basename(p) == fname or k == fname:
                        self.cmb_bin_file.set(k)
                        self.on_bin_file_selected()
                        switched = True
                        break
                if not switched and os.path.exists(target_fpath):
                    self.load_from_absolute_path(target_fpath)

            if str(target_id) in self.tree.get_children():
                self.tree.selection_set(str(target_id))
                self.tree.see(str(target_id))
                self.on_tree_row_selected(None)
                
                if target_fld == 'name' and hasattr(self, 'ent_name'):
                    self.ent_name.focus_set()
                elif target_fld == 'desc' and hasattr(self, 'ent_desc'):
                    self.ent_desc.focus_set()
                elif hasattr(self, 'txt_dialogue'):
                    self.txt_dialogue.focus_set()

        tree_audit.bind("<Double-1>", on_audit_double_click)

        def auto_fix_safe_issues():
            safe_issues = [i for i in all_detected_issues if i[6]]
            if not safe_issues:
                messagebox.showinfo("Auto-Fix", "No safe issues (e.g. unclosed color tags, tag whitespace, trailing whitespace) detected to auto-fix.")
                return

            if not messagebox.askyesno("Confirm Auto-Fix",
                f"Found {len(safe_issues)} safe issues across audited files:\n\n"
                f"• Close unclosed color tags with {{CLR:WHITE}}\n"
                f"• Normalize whitespace inside engine tags\n"
                f"• Trim trailing whitespace on dialogue lines\n\n"
                f"Auto-fix these safe issues (automatic .bak backups will be created)?"):
                return

            issues_by_file = {}
            for iss in safe_issues:
                issues_by_file.setdefault(iss[8], []).append(iss)

            charset = self.cmb_charset.get() if hasattr(self, 'cmb_charset') else 'us'
            fixed_count = 0
            fixed_files = 0

            for fpath, f_issues in issues_by_file.items():
                if fpath == self.active_file_path:
                    file_modified = False
                    for iss in f_issues:
                        eid, fld, fix_kind = iss[2], iss[3], iss[7]
                        rec = next((r for r in self.records if str(r.get('id')) == str(eid)), None)
                        if rec and fld in rec and isinstance(rec[fld], str):
                            s = rec[fld]
                            new_s = s
                            if fix_kind == 'append_white':
                                if not new_s.endswith("{CLR:WHITE}"):
                                    new_s = new_s + "{CLR:WHITE}"
                            elif fix_kind == 'normalize_tag_whitespace':
                                new_s = re.sub(r'\{\s*([A-Za-z0-9_]+)\s*(?::\s*([^}]+?)\s*)?\}',
                                               lambda m: f"{{{m.group(1)}:{m.group(2).strip()}}}" if m.group(2) else f"{{{m.group(1)}}}", new_s)
                            elif fix_kind == 'trim_trailing_whitespace':
                                new_s = '\n'.join(line.rstrip() for line in new_s.split('\n'))
                            if new_s != s:
                                rec[fld] = new_s
                                fixed_count += 1
                                file_modified = True
                    if file_modified:
                        fixed_files += 1
                        self.filter_treeview()
                        sel = self.tree.selection()
                        if sel:
                            self.on_tree_row_selected(None)
                        self.update_live_preview()
                elif os.path.exists(fpath):
                    try:
                        record_len = FILE_RECORD_SIZES.get(os.path.basename(fpath), 16)
                        recs, min_id, max_id, magic_part, m = self.codec.load_any_ffx_file(fpath, record_len, charset)
                        file_modified = False
                        for iss in f_issues:
                            eid, fld, fix_kind = iss[2], iss[3], iss[7]
                            rec = next((r for r in recs if str(r.get('id')) == str(eid)), None)
                            if rec and fld in rec and isinstance(rec[fld], str):
                                s = rec[fld]
                                new_s = s
                                if fix_kind == 'append_white':
                                    if not new_s.endswith("{CLR:WHITE}"):
                                        new_s = new_s + "{CLR:WHITE}"
                                elif fix_kind == 'normalize_tag_whitespace':
                                    new_s = re.sub(r'\{\s*([A-Za-z0-9_]+)\s*(?::\s*([^}]+?)\s*)?\}',
                                                   lambda m: f"{{{m.group(1)}:{m.group(2).strip()}}}" if m.group(2) else f"{{{m.group(1)}}}", new_s)
                                elif fix_kind == 'trim_trailing_whitespace':
                                    new_s = '\n'.join(line.rstrip() for line in new_s.split('\n'))
                                if new_s != s:
                                    rec[fld] = new_s
                                    fixed_count += 1
                                    file_modified = True
                        if file_modified:
                            bak_p = fpath + ".bak"
                            if not os.path.exists(bak_p):
                                shutil.copy2(fpath, bak_p)
                            self.codec.save_any_ffx_file(fpath, recs, min_id, max_id, magic_part, charset)
                            fixed_files += 1
                    except Exception as err:
                        self.log(f"Error auto-fixing file {fpath}: {err}", "error")

            if fixed_count > 0:
                self.log(f"Auto-fixed {fixed_count} safe issues across {fixed_files} file(s).", "success")

            run_scanner()
            messagebox.showinfo("Auto-Fix Completed", f"Successfully auto-fixed {fixed_count} safe issues across {fixed_files} file(s)!\n\nRemember to save active file changes (Ctrl+S).")

        def export_audit_csv():
            if not all_detected_issues:
                messagebox.showwarning("Warning", "No audit issues to export. Run the scanner first!")
                return
            p = filedialog.asksaveasfilename(
                title="Export QA Audit Report CSV",
                defaultextension=".csv",
                filetypes=[("CSV Spreadsheet", "*.csv"), ("All Files", "*.*")]
            )
            if not p:
                return
            try:
                with open(p, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Severity", "File", "Entry ID", "Field", "Issue Detected", "Snippet / Details", "File Path"])
                    for iss in all_detected_issues:
                        writer.writerow([iss[0], iss[1], iss[2], iss[3], iss[4], iss[5], iss[8]])
                messagebox.showinfo("Export Successful", f"Successfully exported {len(all_detected_issues)} audit issues to:\n{os.path.basename(p)}")
                self.log(f"Exported QA audit report ({len(all_detected_issues)} rows) to {p}", "success")
            except Exception as err:
                messagebox.showerror("Export Failed", f"Failed to export CSV report:\n{err}")

        btn_run = tk.Button(ctrl_frame, text="🔍 Run Audit Scanner", command=run_scanner, bg=self.accent_color, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=2)
        btn_run.pack(side="left", padx=(10, 6))
        self.bind_hover(btn_run, is_primary=True)

        btn_fix = tk.Button(ctrl_frame, text="⚡ 1-Click Auto-Fix Safe Issues", command=auto_fix_safe_issues, bg=self.card_color, fg="#4ade80", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=2)
        btn_fix.pack(side="left", padx=(0, 6))
        self.bind_hover(btn_fix)

        btn_export = tk.Button(ctrl_frame, text="📄 Export Audit Report (CSV)", command=export_audit_csv, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=2)
        btn_export.pack(side="left")
        self.bind_hover(btn_export)

        btn_close = tk.Button(bottom, text="Close", command=dialog.destroy, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9), relief="flat", padx=14, pady=3)
        btn_close.pack(side="right")
        self.bind_hover(btn_close)

        dialog.after(100, run_scanner)

    def open_project_dashboard_dialog(self):
        """
        Translation Memory & Progress Dashboard (Pillar 3).
        Calculates string counts and completion rates across all categories
        by comparing against the vanilla baseline (new_uspc).
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("📊 Translation Memory & Progress Dashboard")
        dialog.geometry("760x560")
        dialog.minsize(640, 440)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        dx = rx + max(0, (rw - 760) // 2)
        dy = ry + max(0, (rh - 560) // 2)
        dialog.geometry(f"+{dx}+{dy}")

        header = ttk.Frame(dialog, padding=(18, 14, 18, 6))
        header.pack(fill="x")
        tk.Label(header, text="📊 Translation Memory & Progress Dashboard", font=("Segoe UI", 13, "bold"), fg=self.accent_color, bg=self.bg_color).pack(anchor="w")
        loc = self.cmb_local.get() if hasattr(self, 'cmb_local') else "new_uspc"
        tk.Label(header, text=f"Tracks localized completion against vanilla reference (new_uspc) for active localization: {loc}",
                 font=("Segoe UI", 9), fg=self.text_dim, bg=self.bg_color).pack(anchor="w", pady=(2, 0))

        # Overall Progress Card
        card_overall = tk.Frame(dialog, bg=self.card_color, padx=16, pady=12, highlightbackground=self.border_color, highlightthickness=1)
        card_overall.pack(fill="x", padx=18, pady=(6, 12))

        lbl_tot_rate = tk.Label(card_overall, text="Project Overall Progress: Calculating...", font=("Segoe UI", 11, "bold"), fg=self.text_color, bg=self.card_color)
        lbl_tot_rate.pack(anchor="w", pady=(0, 6))

        pbar_overall = ttk.Progressbar(card_overall, orient="horizontal", mode="determinate")
        pbar_overall.pack(fill="x", pady=(0, 6))

        lbl_tot_counts = tk.Label(card_overall, text="", font=("Segoe UI", 9), fg=self.text_dim, bg=self.card_color)
        lbl_tot_counts.pack(anchor="w")

        # Active File Card
        card_file = tk.Frame(dialog, bg=self.card_color, padx=16, pady=10, highlightbackground=self.border_color, highlightthickness=1)
        card_file.pack(fill="x", padx=18, pady=(0, 12))

        lbl_file_title = tk.Label(card_file, text=f"Active File Progress ({self.active_file_name or 'No file loaded'}):", font=("Segoe UI", 10, "bold"), fg=self.text_color, bg=self.card_file if hasattr(self, 'card_file') else self.card_color)
        lbl_file_title.pack(anchor="w", pady=(0, 4))

        pbar_file = ttk.Progressbar(card_file, orient="horizontal", mode="determinate")
        pbar_file.pack(fill="x", pady=(0, 4))

        lbl_file_stat = tk.Label(card_file, text="", font=("Segoe UI", 9), fg=self.text_dim, bg=self.card_color)
        lbl_file_stat.pack(anchor="w")

        # Category Breakdown Table
        lbl_cat_head = tk.Label(dialog, text="Category Breakdown:", font=("Segoe UI", 10, "bold"), fg=self.text_color, bg=self.bg_color)
        lbl_cat_head.pack(anchor="w", padx=18, pady=(0, 4))

        tree_cat = ttk.Treeview(dialog, columns=("cat", "files", "total", "trans", "pct"), show="headings", height=6)
        tree_cat.heading("cat", text="Category", anchor="w")
        tree_cat.heading("files", text="Files", anchor="center")
        tree_cat.heading("total", text="Total Strings", anchor="center")
        tree_cat.heading("trans", text="Modified / Translated", anchor="center")
        tree_cat.heading("pct", text="Completion %", anchor="center")

        tree_cat.column("cat", width=220, minwidth=160, stretch=True)
        tree_cat.column("files", width=70, minwidth=60, stretch=False, anchor="center")
        tree_cat.column("total", width=110, minwidth=90, stretch=False, anchor="center")
        tree_cat.column("trans", width=140, minwidth=110, stretch=False, anchor="center")
        tree_cat.column("pct", width=120, minwidth=90, stretch=False, anchor="center")
        tree_cat.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        # Bottom Bar
        bottom = tk.Frame(dialog, bg=self.bg_color, padx=18, pady=8)
        bottom.pack(fill="x")

        def get_file_string_count(filepath):
            try:
                ext = os.path.splitext(filepath)[1].lower()
                with open(filepath, "rb") as f:
                    header = f.read(32)
                if len(header) < 16:
                    return 0
                if ext == ".sps2":
                    if len(header) >= 20:
                        hdr = struct.unpack("<5I", header[:20])
                        ptr_table_off = hdr[4]
                        fsize = os.path.getsize(filepath)
                        if 0 <= ptr_table_off < fsize:
                            with open(filepath, "rb") as f2:
                                f2.seek(ptr_table_off)
                                p_bytes = f2.read(4)
                                if len(p_bytes) == 4:
                                    first_ptr = struct.unpack("<I", p_bytes)[0]
                                    if first_ptr > ptr_table_off and first_ptr <= fsize:
                                        return (first_ptr - ptr_table_off) // 4
                elif ext == ".bin":
                    # Check kernel table header
                    min_idx, max_idx, rec_len, tot_len = struct.unpack("<HHHH", header[8:16])
                    if 0 < rec_len <= 128 and 0 <= min_idx <= max_idx < 10000:
                        return max_idx - min_idx + 1
                    # Check dialogue pointer table
                    raw_first_ptr = struct.unpack("<I", header[:4])[0]
                    fsize = os.path.getsize(filepath)
                    if 0 < raw_first_ptr <= fsize and raw_first_ptr % 4 == 0:
                        count = raw_first_ptr // 4
                        if 0 < count < 5000:
                            return count
            except Exception:
                pass
            return 12

        def compute_metrics():
            if self.records and self.active_file_path:
                ref_recs = self.get_reference_records_for_file(self.active_file_path, "new_uspc")
                ref_map = {r['id']: r for r in ref_recs}
                f_tot = len(self.records)
                f_mod = 0
                for r in self.records:
                    orig = ref_map.get(r['id'])
                    if not orig or r.get('name') != orig.get('name') or r.get('desc') != orig.get('desc'):
                        f_mod += 1
                f_pct = (f_mod / max(1, f_tot)) * 100.0
                pbar_file['value'] = f_pct
                lbl_file_stat.config(text=f"{f_mod} of {f_tot} strings differing from vanilla reference ({f_pct:.1f}% customized)")
            else:
                pbar_file['value'] = 0
                lbl_file_stat.config(text="No file records loaded.")

            for r in tree_cat.get_children():
                tree_cat.delete(r)

            categories = [
                ("⚔️ Battle Kernel Tables", "battle/kernel"),
                ("🏟️ Monster Arena & Help", "help"),
                ("📜 Story & Cutscene Dialogue", "event"),
                ("🎙️ Battle Quotes & Voice", "battle/btl"),
                ("⚙️ Menu & System Text", "menu")
            ]

            grand_total = 0
            grand_trans = 0
            loc_name = self.cmb_local.get() if hasattr(self, 'cmb_local') else "new_uspc"
            master_p = self.codec.ffx_master_path

            for c_name, sub in categories:
                c_dir = os.path.join(master_p, loc_name, sub) if master_p else ""
                c_files = 0
                c_total = 0
                c_trans = 0
                if c_dir and os.path.exists(c_dir):
                    for root, dirs, files in os.walk(c_dir):
                        for f in files:
                            if f.endswith(".bin") or f.endswith(".sps2") or f.endswith(".dcp"):
                                if f.endswith(".bak") or f.startswith("ffxsjis"): continue
                                fp = os.path.join(root, f)
                                str_cnt = get_file_string_count(fp)
                                c_files += 1
                                c_total += str_cnt
                                if os.path.exists(fp + ".bak"):
                                    c_trans += str_cnt
                pct = (c_trans / max(1, c_total)) * 100.0 if c_total else 0.0
                tree_cat.insert("", "end", values=(c_name, c_files, c_total, c_trans, f"{pct:.1f}%"))
                grand_total += c_total
                grand_trans += c_trans

            tot_pct = (grand_trans / max(1, grand_total)) * 100.0 if grand_total else 0.0
            pbar_overall['value'] = tot_pct
            lbl_tot_rate.config(text=f"Project Overall Progress: {tot_pct:.1f}%")
            lbl_tot_counts.config(text=f"{grand_trans} translated strings out of ~{grand_total} total localization strings across Spira")

        btn_refresh = tk.Button(bottom, text="🔄 Recalculate Metrics", command=compute_metrics, bg=self.accent_color, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=3)
        btn_refresh.pack(side="left")
        self.bind_hover(btn_refresh, is_primary=True)

        btn_close = tk.Button(bottom, text="Close", command=dialog.destroy, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9), relief="flat", padx=14, pady=3)
        btn_close.pack(side="right")
        self.bind_hover(btn_close)

        dialog.after(100, compute_metrics)

    def open_batch_ruleset_dialog(self):
        """
        Reusable Batch Replacement Ruleset Manager (Pillar 4).
        Enables localization teams to create, save, load, and execute JSON rulesets
        across single files or the entire localization tree.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("⚡ Reusable Batch Replacement Ruleset Manager")
        dialog.geometry("780x560")
        dialog.minsize(660, 440)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        dx = rx + max(0, (rw - 780) // 2)
        dy = ry + max(0, (rh - 560) // 2)
        dialog.geometry(f"+{dx}+{dy}")

        header = ttk.Frame(dialog, padding=(18, 14, 18, 6))
        header.pack(fill="x")
        tk.Label(header, text="⚡ Reusable Batch Replacement Ruleset Manager", font=("Segoe UI", 13, "bold"), fg=self.accent_color, bg=self.bg_color).pack(anchor="w")
        tk.Label(header, text="Define sequential nomenclature rulesets (e.g., standardizing ability or item names) and batch apply them with automatic backups.",
                 font=("Segoe UI", 9), fg=self.text_dim, bg=self.bg_color).pack(anchor="w", pady=(2, 0))

        # Rule Editor Strip
        ed_strip = tk.Frame(dialog, bg=self.card_color, padx=14, pady=10, highlightbackground=self.border_color, highlightthickness=1)
        ed_strip.pack(fill="x", padx=18, pady=(4, 10))

        tk.Label(ed_strip, text="Find Pattern:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_color).grid(row=0, column=0, sticky="w", padx=(0, 6))
        ent_find = ttk.Entry(ed_strip, width=22)
        ent_find.grid(row=0, column=1, sticky="ew", padx=(0, 12))

        tk.Label(ed_strip, text="Replace With:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_color).grid(row=0, column=2, sticky="w", padx=(0, 6))
        ent_repl = ttk.Entry(ed_strip, width=22)
        ent_repl.grid(row=0, column=3, sticky="ew", padx=(0, 12))

        var_mc = tk.BooleanVar(value=True)
        chk_mc = ttk.Checkbutton(ed_strip, text="Match Case", variable=var_mc)
        chk_mc.grid(row=0, column=4, padx=(0, 8))

        var_rgx = tk.BooleanVar(value=False)
        chk_rgx = ttk.Checkbutton(ed_strip, text="Regex", variable=var_rgx)
        chk_rgx.grid(row=0, column=5, padx=(0, 12))

        tree_rules = ttk.Treeview(dialog, columns=("num", "find", "repl", "mc", "regex"), show="headings", height=8)
        tree_rules.heading("num", text="#", anchor="center")
        tree_rules.heading("find", text="Find Pattern", anchor="w")
        tree_rules.heading("repl", text="Replace With", anchor="w")
        tree_rules.heading("mc", text="Match Case", anchor="center")
        tree_rules.heading("regex", text="Regex", anchor="center")

        tree_rules.column("num", width=45, minwidth=35, stretch=False, anchor="center")
        tree_rules.column("find", width=250, minwidth=140, stretch=True)
        tree_rules.column("repl", width=250, minwidth=140, stretch=True)
        tree_rules.column("mc", width=90, minwidth=70, stretch=False, anchor="center")
        tree_rules.column("regex", width=80, minwidth=60, stretch=False, anchor="center")
        tree_rules.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        def refresh_rules_table():
            for r in tree_rules.get_children():
                tree_rules.delete(r)
            for i, rule in enumerate(self.batch_rules, 1):
                tree_rules.insert("", "end", values=(i, rule['find'], rule['replace'], "Yes" if rule.get('match_case') else "No", "Yes" if rule.get('regex') else "No"))

        def add_rule():
            f = ent_find.get().strip()
            r = ent_repl.get()
            if not f:
                messagebox.showwarning("Warning", "Find pattern cannot be empty.")
                return
            self.batch_rules.append({"find": f, "replace": r, "match_case": var_mc.get(), "regex": var_rgx.get()})
            refresh_rules_table()
            ent_find.delete(0, tk.END)
            ent_repl.delete(0, tk.END)

        def delete_rule():
            sel = tree_rules.selection()
            if not sel:
                return
            idx = tree_rules.index(sel[0])
            if 0 <= idx < len(self.batch_rules):
                self.batch_rules.pop(idx)
                refresh_rules_table()

        def clear_rules():
            self.batch_rules.clear()
            refresh_rules_table()

        def load_ruleset():
            p = filedialog.askopenfilename(title="Load Ruleset JSON", filetypes=[("JSON Ruleset", "*.json"), ("All Files", "*.*")])
            if p:
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        rules = json.load(f)
                        if isinstance(rules, list):
                            self.batch_rules = rules
                            refresh_rules_table()
                            messagebox.showinfo("Success", f"Loaded {len(rules)} rules from {os.path.basename(p)}.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load ruleset: {e}")

        def save_ruleset():
            if not self.batch_rules:
                messagebox.showwarning("Warning", "No rules to save.")
                return
            p = filedialog.asksaveasfilename(title="Save Ruleset JSON", defaultextension=".json", filetypes=[("JSON Ruleset", "*.json")])
            if p:
                try:
                    with open(p, "w", encoding="utf-8") as f:
                        json.dump(self.batch_rules, f, indent=2)
                        messagebox.showinfo("Success", f"Ruleset saved successfully to {os.path.basename(p)}.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save ruleset: {e}")

        btn_add = tk.Button(ed_strip, text="➕ Add Rule", command=add_rule, bg=self.accent_color, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=2)
        btn_add.grid(row=0, column=6)
        self.bind_hover(btn_add, is_primary=True)

        act_strip = tk.Frame(dialog, bg=self.bg_color, padx=18, pady=4)
        act_strip.pack(fill="x")

        btn_del = tk.Button(act_strip, text="🗑️ Delete Selected", command=delete_rule, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8), relief="flat", padx=8, pady=2)
        btn_del.pack(side="left", padx=(0, 6))
        self.bind_hover(btn_del)

        btn_clr = tk.Button(act_strip, text="🧹 Clear All", command=clear_rules, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8), relief="flat", padx=8, pady=2)
        btn_clr.pack(side="left", padx=(0, 14))
        self.bind_hover(btn_clr)

        btn_load = tk.Button(act_strip, text="📁 Load Ruleset (.json)", command=load_ruleset, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2)
        btn_load.pack(side="left", padx=(0, 6))
        self.bind_hover(btn_load)

        btn_save = tk.Button(act_strip, text="💾 Save Ruleset (.json)", command=save_ruleset, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2)
        btn_save.pack(side="left")
        self.bind_hover(btn_save)

        bottom = tk.Frame(dialog, bg=self.card_color, padx=18, pady=10, highlightbackground=self.border_color, highlightthickness=1)
        bottom.pack(fill="x", side="bottom")

        def apply_rules_to_string(text, rules):
            out = text
            rep_count = 0
            for r in rules:
                pat = r['find']
                repl = r['replace']
                mc = r.get('match_case', True)
                is_rgx = r.get('regex', False)
                if is_rgx:
                    flags = 0 if mc else re.IGNORECASE
                    try:
                        out, n = re.subn(pat, repl, out, flags=flags)
                        rep_count += n
                    except Exception:
                        pass
                else:
                    if mc:
                        n = out.count(pat)
                        out = out.replace(pat, repl)
                        rep_count += n
                    else:
                        pattern = re.compile(re.escape(pat), re.IGNORECASE)
                        out, n = pattern.subn(repl, out)
                        rep_count += n
            return out, rep_count

        def execute_on_file():
            if not self.records:
                messagebox.showwarning("Warning", "No active file records loaded.")
                return
            if not self.batch_rules:
                messagebox.showwarning("Warning", "Ruleset is empty.")
                return
            tot = 0
            for r in self.records:
                for fld in ('name', 'sname', 'desc', 'sdesc', 'w_wakka', 'w_lulu', 'w_rikku'):
                    if fld in r and isinstance(r[fld], str):
                        new_s, n = apply_rules_to_string(r[fld], self.batch_rules)
                        if n > 0:
                            r[fld] = new_s
                            tot += n
            self.filter_treeview()
            sel = self.tree.selection()
            if sel:
                self.on_tree_row_selected(None)
            self.update_live_preview()
            self.log(f"Batch rules executed: Replaced {tot} occurrences in active file.", "success")
            messagebox.showinfo("Success", f"Replaced {tot} occurrences in active file!\n\nRemember to save changes (Ctrl+S).")

        btn_run_file = tk.Button(bottom, text="▶️ Execute on Current File", command=execute_on_file, bg=self.accent_color, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4)
        btn_run_file.pack(side="left", padx=(0, 10))
        self.bind_hover(btn_run_file, is_primary=True)

        def execute_on_entire_loc():
            if not self.batch_rules:
                messagebox.showwarning("Warning", "Ruleset is empty. Add at least one rule first.")
                return
            loc_name = self.cmb_local.get() if hasattr(self, 'cmb_local') else "new_uspc"
            master_p = self.codec.ffx_master_path
            loc_dir = os.path.join(master_p, loc_name) if master_p else ""
            if not loc_dir or not os.path.exists(loc_dir):
                messagebox.showerror("Error", f"Localization directory '{loc_name}' not found under Master folder.")
                return
                
            if not messagebox.askyesno("Confirm Batch Localization Run",
                f"Apply all {len(self.batch_rules)} rule(s) across all .bin and .sps2 files in '{loc_name}'?\n\n"
                f"• An automatic .bak backup will be generated for every modified file before writing.\n"
                f"• This operation directly modifies localization files on disk.\n\n"
                f"Proceed with batch localization execution?"):
                return
                
            charset = self.cmb_charset.get() if hasattr(self, 'cmb_charset') else 'us'
            total_files = 0
            mod_files = 0
            total_reps = 0
            
            for root, dirs, files in os.walk(loc_dir):
                for f in files:
                    if f.endswith(".bak") or f.startswith("ffxsjis"):
                        continue
                    if not (f.endswith(".bin") or f.endswith(".sps2") or f.endswith(".dcp")):
                        continue
                    
                    fpath = os.path.join(root, f)
                    total_files += 1
                    try:
                        record_len = FILE_RECORD_SIZES.get(f, 16)
                        recs, min_id, max_id, magic_part, m = self.codec.load_any_ffx_file(fpath, record_len, charset)
                        file_reps = 0
                        for r in recs:
                            for fld in ('name', 'sname', 'desc', 'sdesc', 'w_wakka', 'w_lulu', 'w_rikku'):
                                if fld in r and isinstance(r[fld], str):
                                    new_s, n = apply_rules_to_string(r[fld], self.batch_rules)
                                    if n > 0:
                                        r[fld] = new_s
                                        file_reps += n
                        if file_reps > 0:
                            bak_p = fpath + ".bak"
                            if not os.path.exists(bak_p):
                                shutil.copy2(fpath, bak_p)
                            self.codec.save_any_ffx_file(fpath, recs, min_id, max_id, magic_part, charset)
                            mod_files += 1
                            total_reps += file_reps
                            
                            if fpath == self.active_file_path:
                                self.records = recs
                                self.filter_treeview()
                                sel = self.tree.selection()
                                if sel:
                                    self.on_tree_row_selected(None)
                                self.update_live_preview()
                    except Exception as err:
                        self.log(f"Error executing rules on {f}: {err}", "error")
            
            self.log(f"Batch Localization Complete: Processed {total_files} files, modified {mod_files} files, {total_reps} replacements made.", "success")
            messagebox.showinfo("Batch Execution Complete",
                f"Batch localization execution complete!\n\n"
                f"• Scanned files: {total_files}\n"
                f"• Modified files: {mod_files}\n"
                f"• Total replacements: {total_reps}\n\n"
                f"Automatic .bak backup files were created for all modified files.")

        btn_run_loc = tk.Button(bottom, text="🚀 Execute on Entire Localization (All Files)", command=execute_on_entire_loc, bg=self.card_color, fg="#38bdf8", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4)
        btn_run_loc.pack(side="left")
        self.bind_hover(btn_run_loc)

        btn_close = tk.Button(bottom, text="Close", command=dialog.destroy, bg=self.bg_color, fg=self.text_color, font=("Segoe UI", 9), relief="flat", padx=14, pady=4)
        btn_close.pack(side="right")
        self.bind_hover(btn_close)

        refresh_rules_table()

    def open_visual_diff_dialog(self):
        """
        Visual Side-by-Side Diff Viewer (Pillar 4).
        Compares active entry against vanilla baseline (new_uspc) with byte deltas.
        Includes interactive previous/next entry navigation and Alt+Left / Alt+Right hotkeys.
        """
        if not self.records:
            messagebox.showwarning("Warning", "No active records loaded.")
            return

        sel = self.tree.selection()
        start_idx = 0
        if sel:
            try:
                target_id = int(sel[0])
                for i, r in enumerate(self.records):
                    if r['id'] == target_id:
                        start_idx = i
                        break
            except ValueError:
                for i, r in enumerate(self.records):
                    if str(r['id']) == sel[0]:
                        start_idx = i
                        break

        current_diff_idx = start_idx
        ref_recs = self.get_reference_records_for_file(self.active_file_path, "new_uspc") if self.active_file_path else []
        ref_map = {r['id']: r for r in ref_recs}
        charset = self.cmb_charset.get() if hasattr(self, 'cmb_charset') else 'us'

        dialog = tk.Toplevel(self.root)
        dialog.title(f"🔍 Visual String Diff — ({self.active_file_name or 'Entry'})")
        dialog.geometry("780x500")
        dialog.minsize(660, 380)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        dx = rx + max(0, (rw - 780) // 2)
        dy = ry + max(0, (rh - 500) // 2)
        dialog.geometry(f"+{dx}+{dy}")

        header = ttk.Frame(dialog, padding=(18, 14, 18, 6))
        header.pack(fill="x")
        lbl_diff_title = tk.Label(header, text="🔍 Visual Side-by-Side Diff", font=("Segoe UI", 12, "bold"), fg=self.accent_color, bg=self.bg_color)
        lbl_diff_title.pack(anchor="w")

        lbl_diff_sub = tk.Label(header, text="", font=("Segoe UI", 9), fg=self.text_dim, bg=self.bg_color)
        lbl_diff_sub.pack(anchor="w", pady=(2, 0))

        panes = ttk.PanedWindow(dialog, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=18, pady=8)

        # Left: Reference
        f_left = ttk.LabelFrame(panes, text=" Vanilla Reference (new_uspc) ", padding=8)
        panes.add(f_left, weight=1)
        t_ref = tk.Text(f_left, bg="#1a1113", fg="#fca5a5", font=("Consolas", 10), wrap="word", relief="flat")
        t_ref.pack(fill="both", expand=True)

        # Right: Active
        f_right = ttk.LabelFrame(panes, text=" Active / Translated ", padding=8)
        panes.add(f_right, weight=1)
        t_act = tk.Text(f_right, bg="#0d1f14", fg="#86efac", font=("Consolas", 10), wrap="word", relief="flat")
        t_act.pack(fill="both", expand=True)

        bottom = tk.Frame(dialog, bg=self.bg_color, padx=18, pady=10)
        bottom.pack(fill="x")

        def load_entry(idx):
            nonlocal current_diff_idx
            if not self.records or idx < 0 or idx >= len(self.records):
                return
            current_diff_idx = idx
            rec = self.records[idx]
            eid = rec['id']
            ref_rec = ref_map.get(eid)

            active_text = rec.get('name', '')
            if rec.get('desc') and rec.get('desc') != '-':
                active_text += "\n" + rec.get('desc')

            ref_text = ""
            if ref_rec:
                ref_text = ref_rec.get('name', '')
                if ref_rec.get('desc') and ref_rec.get('desc') != '-':
                    ref_text += "\n" + ref_rec.get('desc')

            ref_b = len(self.codec.encode_ffx_string(ref_text, charset)) if ref_text else 0
            act_b = len(self.codec.encode_ffx_string(active_text, charset)) if active_text else 0
            diff_b = act_b - ref_b
            delta_str = f"+{diff_b}B" if diff_b > 0 else f"{diff_b}B"

            dialog.title(f"🔍 Visual String Diff — ID #{eid} ({idx + 1} of {len(self.records)})")
            lbl_diff_title.config(text=f"🔍 Visual Side-by-Side Diff: Entry #{eid}")
            lbl_diff_sub.config(text=f"Entry {idx + 1} of {len(self.records)} in {self.active_file_name or 'file'}  |  Byte Delta: {delta_str}")

            f_left.config(text=f" Vanilla Reference (new_uspc) — {ref_b} Bytes ")
            t_ref.config(state="normal")
            t_ref.delete("1.0", tk.END)
            t_ref.insert("1.0", ref_text if ref_text else "(No reference string found in vanilla new_uspc)")
            t_ref.config(state="disabled")

            f_right.config(text=f" Active / Translated — {act_b} Bytes (Delta: {delta_str}) ")
            t_act.config(state="normal")
            t_act.delete("1.0", tk.END)
            t_act.insert("1.0", active_text)
            t_act.config(state="disabled")

            # Sync main window selection
            if str(eid) in self.tree.get_children():
                self.tree.selection_set(str(eid))
                self.tree.see(str(eid))

            if 'btn_prev' in locals():
                btn_prev.config(state="normal" if idx > 0 else "disabled")
            if 'btn_next' in locals():
                btn_next.config(state="normal" if idx < len(self.records) - 1 else "disabled")

        btn_prev = tk.Button(bottom, text="⬅️ Previous Entry (Alt+Left)", command=lambda: load_entry(current_diff_idx - 1),
                             bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9), relief="flat", padx=10, pady=3)
        btn_prev.pack(side="left", padx=(0, 8))
        self.bind_hover(btn_prev)

        btn_next = tk.Button(bottom, text="Next Entry ➡️ (Alt+Right)", command=lambda: load_entry(current_diff_idx + 1),
                             bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9), relief="flat", padx=10, pady=3)
        btn_next.pack(side="left")
        self.bind_hover(btn_next)

        btn_close = tk.Button(bottom, text="Close", command=dialog.destroy, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9), relief="flat", padx=14, pady=3)
        btn_close.pack(side="right")
        self.bind_hover(btn_close)

        dialog.bind("<Alt-Left>", lambda e: load_entry(current_diff_idx - 1))
        dialog.bind("<Alt-Right>", lambda e: load_entry(current_diff_idx + 1))

        load_entry(current_diff_idx)
        btn_prev.config(state="normal" if current_diff_idx > 0 else "disabled")
        btn_next.config(state="normal" if current_diff_idx < len(self.records) - 1 else "disabled")

    def show_canonical_lore_dialog(self):
        """
        Canonical Lore & Multi-Language Terminology Glossary (Pillar 3).
        Official Square Enix translations across EN, IT, DE, FR, ES, JP.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title(f"📚 Canonical Lore Glossary ({len(CANONICAL_LORE_GLOSSARY)} Terms)")
        dialog.geometry("860x560")
        dialog.minsize(700, 420)
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        dx = rx + max(0, (rw - 860) // 2)
        dy = ry + max(0, (rh - 560) // 2)
        dialog.geometry(f"+{dx}+{dy}")

        header = ttk.Frame(dialog, padding=(18, 14, 18, 6))
        header.pack(fill="x")
        tk.Label(header, text="📚 Canonical Multi-Language Lore Glossary", font=("Segoe UI", 13, "bold"), fg=self.accent_color, bg=self.bg_color).pack(anchor="w")
        tk.Label(header, text="Official Square Enix terminology across 6 languages (EN, IT, DE, FR, ES, JP). Search any term and double-click to copy.",
                 font=("Segoe UI", 9), fg=self.text_dim, bg=self.bg_color).pack(anchor="w", pady=(2, 0))

        # Filter Strip
        f_strip = tk.Frame(dialog, bg=self.card_color, padx=12, pady=8, highlightbackground=self.border_color, highlightthickness=1)
        f_strip.pack(fill="x", padx=18, pady=(4, 10))

        tk.Label(f_strip, text="Search Term:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_color).pack(side="left", padx=(0, 6))
        ent_q = ttk.Entry(f_strip, width=22)
        ent_q.pack(side="left", padx=(0, 14))
        ent_q.focus_set()

        tk.Label(f_strip, text="Category:", font=("Segoe UI", 9, "bold"), fg=self.text_color, bg=self.card_color).pack(side="left", padx=(0, 6))
        cats = ["All Categories", "Characters (FFX)", "Characters (FFX-2)", "Supporting Cast", "Aeons", "Lore & Concepts", "Systems & Mechanics", "Spells & Skills", "Locations"]
        cmb_c = ttk.Combobox(f_strip, values=cats, state="readonly", width=18)
        cmb_c.set("All Categories")
        cmb_c.pack(side="left", padx=(0, 10))

        tree_frame = tk.Frame(dialog, bg=self.bg_color, padx=18)
        tree_frame.pack(fill="both", expand=True)

        cols = ("cat", "en", "it", "de", "fr", "es", "jp")
        tree_lore = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        tree_lore.heading("cat", text="Category", anchor="w")
        tree_lore.heading("en", text="English", anchor="w")
        tree_lore.heading("it", text="Italian", anchor="w")
        tree_lore.heading("de", text="German", anchor="w")
        tree_lore.heading("fr", text="French", anchor="w")
        tree_lore.heading("es", text="Spanish", anchor="w")
        tree_lore.heading("jp", text="Japanese", anchor="w")

        tree_lore.column("cat", width=130, minwidth=100, stretch=False)
        tree_lore.column("en", width=120, minwidth=80, stretch=True)
        tree_lore.column("it", width=120, minwidth=80, stretch=True)
        tree_lore.column("de", width=120, minwidth=80, stretch=True)
        tree_lore.column("fr", width=120, minwidth=80, stretch=True)
        tree_lore.column("es", width=120, minwidth=80, stretch=True)
        tree_lore.column("jp", width=120, minwidth=80, stretch=True)

        scr_l = ttk.Scrollbar(tree_frame, orient="vertical", command=tree_lore.yview)
        tree_lore.configure(yscrollcommand=scr_l.set)
        tree_lore.pack(side="left", fill="both", expand=True)
        scr_l.pack(side="right", fill="y")

        bottom = tk.Frame(dialog, bg=self.bg_color, padx=18, pady=10)
        bottom.pack(fill="x")
        lbl_info = tk.Label(bottom, text="", font=("Segoe UI", 9, "italic"), fg=self.text_dim, bg=self.bg_color)
        lbl_info.pack(side="left")

        def copy_selected(col_idx=1):
            sel = tree_lore.selection()
            if not sel:
                return
            vals = tree_lore.item(sel[0], "values")
            txt = vals[col_idx]
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            lbl_info.config(text=f"Copied '{txt}' to clipboard!")

        def refresh_lore(event=None):
            q = ent_q.get().strip().lower()
            cat_f = cmb_c.get()
            for r in tree_lore.get_children():
                tree_lore.delete(r)
            cnt = 0
            for item in CANONICAL_LORE_GLOSSARY:
                if cat_f != "All Categories" and item.get('category') != cat_f:
                    continue
                if q:
                    matched = False
                    for k in ('en', 'it', 'de', 'fr', 'es', 'jp', 'category'):
                        if q in item.get(k, '').lower():
                            matched = True
                            break
                    if not matched:
                        continue
                tree_lore.insert("", "end", values=(
                    item.get('category', ''),
                    item.get('en', ''),
                    item.get('it', ''),
                    item.get('de', ''),
                    item.get('fr', ''),
                    item.get('es', ''),
                    item.get('jp', '')
                ))
                cnt += 1
            lbl_info.config(text=f"Showing {cnt} of {len(CANONICAL_LORE_GLOSSARY)} terms (Double-click to copy English term)")

        ent_q.bind("<KeyRelease>", refresh_lore)
        cmb_c.bind("<<ComboboxSelected>>", refresh_lore)
        tree_lore.bind("<Double-1>", lambda e: copy_selected(1))

        btn_copy_en = tk.Button(bottom, text="📋 Copy EN", command=lambda: copy_selected(1), bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2)
        btn_copy_en.pack(side="left", padx=(10, 4))
        self.bind_hover(btn_copy_en)

        btn_copy_loc = tk.Button(bottom, text="📋 Copy Active Loc", command=lambda: copy_selected(2), bg=self.card_color, fg=self.text_color, font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=2)
        btn_copy_loc.pack(side="left", padx=4)
        self.bind_hover(btn_copy_loc)

        btn_close = tk.Button(bottom, text="Close", command=dialog.destroy, bg=self.card_color, fg=self.text_color, font=("Segoe UI", 9), relief="flat", padx=14, pady=3)
        btn_close.pack(side="right")
        self.bind_hover(btn_close)

        refresh_lore()

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
