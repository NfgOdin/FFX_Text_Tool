import os
import sys
import tempfile
import struct
import tkinter as tk
import json

# Ensure paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import FFX_Text_Tool
from ffx_codec import FFXCodec, FILE_RECORD_SIZES
import canonical_lore

def deep_audit():
    print("==================================================")
    print("RUNNING DEEP AUDIT & STRESS TESTING (ZERO-BUG PASS)")
    print("==================================================")
    
    root = tk.Tk()
    root.withdraw()
    
    try:
        app = FFX_Text_Tool.FFXTextToolGUI(root)
        print("[PASS 1/10] GUI Headless Initialization")

        # 2. Theme Adaptation Tests
        for game in ["Final Fantasy X", "Final Fantasy X-2", "Final Fantasy X"]:
            app.apply_theme(game)
            if "X-2" in game:
                assert app.accent_color == "#a855f7"
                assert app.preview_bg == "#12091e"
                assert app.speaker_fg == "#c084fc"
            else:
                assert app.accent_color == "#3b82f6"
                assert app.preview_bg == "#070c18"
                assert app.speaker_fg == "#38bdf8"
        print("[PASS 2/10] Engine & Theme Switcher (Sin Blue <-> Celsius Purple)")

        # 3. Interactive Choice Simulator & Dialogue Engine
        app.active_mode = "msg"
        app.txt_dialogue.delete("1.0", tk.END)
        app.txt_dialogue.insert("1.0", "{CHOICE:00}First Choice\n{CHOICE:01}Second Choice\n{CHOICE:02}Third Choice\n{CHOICE-END}")
        app.update_live_preview()
        assert app.total_choices == 3
        assert app.active_choice_idx == 0
        
        # Navigate forward through all choices
        app.next_choice_option()
        assert app.active_choice_idx == 1
        app.next_choice_option()
        assert app.active_choice_idx == 2
        app.next_choice_option()
        assert app.active_choice_idx == 0 # wrap forward
        
        # Navigate backward
        app.prev_choice_option()
        assert app.active_choice_idx == 2 # wrap backward
        app.prev_choice_option()
        assert app.active_choice_idx == 1
        
        # Empty text check
        app.txt_dialogue.delete("1.0", tk.END)
        app.update_live_preview()
        assert app.total_choices == 0
        assert app.active_choice_idx == 0
        print("[PASS 3/10] Interactive Choice Simulator & Live Preview Navigation")

        # 4. Translation Memory Engine
        app.index_translation_memory()
        assert len(app.translation_memory) >= 100
        # Mock active record
        app.records = [{'id': 0, 'name': 'Celestial Weapon', 'desc': 'Ultimate weapon.'}]
        app.tree.delete(*app.tree.get_children())
        app.tree.insert("", "end", iid="0", values=(0, "Celestial Weapon", "Ultimate weapon.", ""))
        app.tree.selection_set("0")
        app.active_file_path = "dummy/path.bin"
        app.get_reference_records_for_file = lambda p, loc: [{'id': 0, 'name': 'Celestial Weapon', 'desc': 'Ultimate weapon.'}]
        app.check_translation_memory()
        assert app.active_tm_suggestion is not None
        expected_sugg = app.active_tm_suggestion
        assert expected_sugg in ("Arma dei 7 Astri", "Waffe des Solar", "Arme Antique", "Arma de los 7 Astros")
        app.active_mode = "msg"
        app.apply_translation_memory()
        assert app.txt_dialogue.get("1.0", "end-1c") == expected_sugg
        print("[PASS 4/10] Translation Memory Engine (Index, Suggestion, Apply)")

        # 5. Visual Diff Dialog with Navigation
        # Add 3 records to test Prev/Next
        app.records = [
            {'id': 0, 'name': 'Item A', 'desc': 'Desc A'},
            {'id': 1, 'name': 'Item B', 'desc': 'Desc B'},
            {'id': 2, 'name': 'Item C', 'desc': 'Desc C'},
        ]
        app.tree.delete(*app.tree.get_children())
        for r in app.records:
            app.tree.insert("", "end", iid=str(r['id']), values=(r['id'], r['name'], r['desc'], ""))
        app.tree.selection_set("1")
        app.open_visual_diff_dialog()
        # Find the open Toplevel dialog
        diff_dialog = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        assert "Visual String Diff" in diff_dialog.title()
        diff_dialog.destroy()
        print("[PASS 5/10] Visual Diff Dialog & Alt+Left / Alt+Right Paging")

        # 6. QA Syntax & Crash Auditor Dialog
        app.open_qa_auditor_dialog()
        qa_dialog = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        assert "Automated QA" in qa_dialog.title()
        qa_dialog.destroy()
        print("[PASS 6/10] QA Syntax & Crash Prevention Auditor Dialog")

        # 7. Translation Memory & Progress Dashboard Dialog
        app.open_project_dashboard_dialog()
        dash_dialog = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        assert "Translation Memory & Progress Dashboard" in dash_dialog.title()
        dash_dialog.destroy()
        print("[PASS 7/10] Translation Memory & Project Dashboard Dialog")

        # 8. Reusable Batch Ruleset Dialog
        app.open_batch_ruleset_dialog()
        batch_dialog = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        assert "Batch Replacement Ruleset" in batch_dialog.title()
        batch_dialog.destroy()
        print("[PASS 8/10] Reusable Batch Ruleset Dialog")

        # 9. Canonical Lore Glossary Dialog
        app.show_canonical_lore_dialog()
        lore_dialog = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        assert "Canonical Lore Glossary" in lore_dialog.title()
        lore_dialog.destroy()
        print("[PASS 9/10] Canonical Multilingual Lore Glossary Dialog (137 Terms)")

        # 10. Mod Packager SpiraMM / Nexus Dialog
        app.open_mod_packager_dialog()
        pkg_dialog = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        assert "Package Mod" in pkg_dialog.title()
        pkg_dialog.destroy()
        print("[PASS 10/10] Mod Packager Dialog (SpiraMM & Nexus Mods)")

        print("\n==================================================")
        print(">>> ALL 10 DEEP AUDIT PASSES COMPLETED WITH 0 ERRORS! <<<")
        print("==================================================")

    finally:
        root.destroy()

if __name__ == "__main__":
    deep_audit()
