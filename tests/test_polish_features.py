import os
import sys
import tkinter as tk
from tkinter import ttk
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import FFX_Text_Tool
from FFX_Text_Tool import FFXTextToolGUI
from ffx_codec import FFXCodec

class TestPolishFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()
        cls.app = FFXTextToolGUI(cls.root)
        
        # Populate dummy records
        cls.app.records = [
            {'id': 0, 'name': 'Potion', 'sname': 'Pot', 'desc': 'Restores 200 HP.', 'sdesc': 'HP+200'},
            {'id': 1, 'name': 'Hi-Potion', 'sname': 'HiPot', 'desc': 'Restores 1000 HP.', 'sdesc': 'HP+1000'}
        ]
        cls.app.active_mode = 'kernel'
        cls.app.active_file_path = "C:/dummy/item_txt.bin"
        cls.app.active_file_name = "item_txt.bin"
        cls.app.current_entry_id = 0
        cls.app.is_dirty = False
        cls.app.ent_name.delete(0, tk.END)
        cls.app.ent_name.insert(0, "Potion")
        cls.app.ent_sname.delete(0, tk.END)
        cls.app.ent_sname.insert(0, "Pot")
        cls.app.ent_desc.delete(0, tk.END)
        cls.app.ent_desc.insert(0, "Restores 200 HP.")
        cls.app.ent_sdesc.delete(0, tk.END)
        cls.app.ent_sdesc.insert(0, "HP+200")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_01_unsaved_changes_detection(self):
        # Clean state
        self.assertFalse(self.app.has_unapplied_editor_edits())
        self.assertFalse(self.app.has_unsaved_changes())

        # Modify entry box
        self.app.ent_name.delete(0, tk.END)
        self.app.ent_name.insert(0, "Super Potion")
        self.assertTrue(self.app.has_unapplied_editor_edits())
        self.assertTrue(self.app.has_unsaved_changes())

        # Apply edit
        self.app._apply_edits_for_record_id(0)
        self.assertTrue(self.app.is_dirty)
        self.assertFalse(self.app.has_unapplied_editor_edits())
        self.assertTrue(self.app.has_unsaved_changes())

        # Reset clean
        self.app.is_dirty = False
        self.assertFalse(self.app.has_unsaved_changes())

    def test_02_recent_files_menu(self):
        self.assertTrue(hasattr(self.app, 'menu_recent'))
        dummy_path = os.path.abspath(__file__)
        self.app.add_recent_file(dummy_path)
        self.assertIn(dummy_path, self.app.config.get("recent_files", []))
        
        # Verify menu items exist
        item_count = self.app.menu_recent.index(tk.END)
        self.assertGreaterEqual(item_count, 1)

        # Clear recent files
        self.app.clear_recent_files()
        self.assertEqual(len(self.app.config.get("recent_files", [])), 0)

    def test_03_context_menu_bindings(self):
        # Verify Button-3 binding on text and entry widgets
        for widget in (self.app.ent_name, self.app.ent_sname, self.app.txt_dialogue):
            binds = widget.bind()
            self.assertIn("<Button-3>", binds)

    def test_04_pyinstaller_spec_bundling(self):
        spec_path = os.path.join(os.path.dirname(__file__), "..", "FFX_Text_Tool.spec")
        self.assertTrue(os.path.exists(spec_path))
        with open(spec_path, "r", encoding="utf-8") as f:
            spec_content = f.read()
        self.assertIn("ffx_encoding", spec_content)

    def test_05_codec_bundled_charset_path(self):
        codec = FFXCodec()
        sys._MEIPASS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        try:
            found = codec.find_charset_file("us")
            self.assertIsNotNone(found)
            self.assertTrue(os.path.exists(found))
        finally:
            delattr(sys, "_MEIPASS")

if __name__ == "__main__":
    unittest.main()
