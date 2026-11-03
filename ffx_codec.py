import os
import sys
import struct

COLOR_MAP = {
    0x41: "WHITE",
    0x43: "YELLOW",
    0x52: "GREY",
    0x88: "BLUE",
    0x94: "RED",
    0x97: "PINK",
    0xA1: "OL_PURPLE",
    0xB1: "OL_CYAN"
}
COLOR_REV = {v: k for k, v in COLOR_MAP.items()}

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

class FFXCodec:
    def __init__(self, ffx_master_path=None):
        self.ffx_master_path = ffx_master_path
        self.byte_to_char_maps = {}
        self.char_to_byte_maps = {}
        self.loaded_charsets = set()
        
    def find_charset_file(self, charset):
        # List of potential paths to look for ffxsjistbl_*.bin
        search_paths = []
        if hasattr(sys, "_MEIPASS"):
            search_paths.append(os.path.join(sys._MEIPASS, "ffx_encoding"))
            search_paths.append(sys._MEIPASS)
        if self.ffx_master_path:
            search_paths.append(os.path.join(self.ffx_master_path, "jppc", "ffx_encoding"))
            search_paths.append(os.path.join(self.ffx_master_path, "ffx_encoding"))
            
        # Relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        search_paths.append(os.path.join(script_dir, "..", "VBF Browser", "Extracted", "ffx_ps2", "ffx", "master", "jppc", "ffx_encoding"))
        search_paths.append(os.path.join(script_dir, "..", "VBF Browser", "extracted", "ffx_ps2", "ffx", "master", "jppc", "ffx_encoding"))
        search_paths.append(os.path.join(script_dir, "..", "..", "Misc Tools", "FF10 Rando", "input", "ffx_ps2", "ffx", "master", "jppc", "ffx_encoding"))
        search_paths.append(os.path.join(script_dir, "jppc", "ffx_encoding"))
        search_paths.append(os.path.join(script_dir, "ffx_encoding"))
        search_paths.append(script_dir)
        
        for p in search_paths:
            full_path = os.path.join(p, f"ffxsjistbl_{charset}.bin")
            if os.path.exists(full_path):
                return full_path
        return None

    def load_charset(self, charset):
        if charset in self.loaded_charsets:
            return True
            
        filepath = self.find_charset_file(charset)
        if not filepath:
            # Fallback to loading an empty mapping or raise error
            return False
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                charset_chars = f.read()
                
            byte_to_char = {i + 0x30: c for i, c in enumerate(charset_chars)}
            char_to_byte = {c: i + 0x30 for i, c in enumerate(charset_chars)}
            
            self.byte_to_char_maps[charset] = byte_to_char
            self.char_to_byte_maps[charset] = char_to_byte
            self.loaded_charsets.add(charset)
            return True
        except Exception:
            return False

    def decode_ffx_bytes(self, table, offset, charset="us"):
        self.load_charset(charset)
        byte_to_char = self.byte_to_char_maps.get(charset, {})
        
        if offset < 0 or offset >= len(table):
            return ""
            
        # Get string bounds (stop at 0x00 terminator, handling multi-byte arguments)
        end = offset
        last_takes_args = False
        last_was_04 = False
        while end < len(table) and (table[end] != 0x00 or last_takes_args or last_was_04):
            last_was_04 = (table[end] == 0x04)
            last_takes_args = (not last_takes_args) and (0x2B <= table[end] <= 0x2F)
            end += 1
            
        bytes_subset = table[offset:end]
        out = []
        i = 0
        extra_five_sections = False
        
        while i < len(bytes_subset):
            idx = bytes_subset[i]
            extra_offset = 0x410 if extra_five_sections else 0
            extra_five_sections = False
            
            if idx >= 0x30:
                char_idx = idx + extra_offset
                c = byte_to_char.get(char_idx)
                if c:
                    out.append(c)
                else:
                    out.append(f"{{UNKDBLCHR:04:{idx:02X}}}" if extra_offset else f"{{UNKCHR:{idx:02X}}}")
            elif idx >= 0x2B:
                section = idx - 0x2B
                i += 1
                if i >= len(bytes_subset):
                    break
                low_byte = bytes_subset[i]
                actual_idx = section * 0xD0 + low_byte
                char_idx = actual_idx + extra_offset
                c = byte_to_char.get(char_idx)
                if c:
                    out.append(c)
                else:
                    out.append(f"{{UNKTPLCHR:04:{idx:02X}:{low_byte:02X}}}" if extra_offset else f"{{UNKDBLCHR:{idx:02X}:{low_byte:02X}}}")
            else:
                if extra_offset != 0:
                    char_idx = idx + extra_offset
                    c = byte_to_char.get(char_idx)
                    if c:
                        out.append(c)
                    else:
                        out.append(f"{{UNKDBLCHR:04:{idx:02X}}}")
                elif idx == 0x01:
                    out.append("{PAUSE}")
                elif idx == 0x03:
                    out.append("\n")
                elif idx == 0x04:
                    extra_five_sections = True
                elif idx == 0x07:
                    i += 1
                    if i >= len(bytes_subset): break
                    pixels = bytes_subset[i] - 0x30
                    out.append(f"{{SPACE:{pixels:02X}}}")
                elif idx == 0x09:
                    i += 1
                    if i >= len(bytes_subset): break
                    var_idx = bytes_subset[i] - 0x30
                    out.append(f"{{TIME:{var_idx:02X}}}")
                elif idx == 0x0A:
                    i += 1
                    if i >= len(bytes_subset): break
                    clr = bytes_subset[i]
                    clr_name = COLOR_MAP.get(clr, f"{clr:02X}")
                    out.append(f"{{CLR:{clr_name}}}")
                elif idx == 0x0B:
                    i += 1
                    if i >= len(bytes_subset): break
                    ctrl_idx = bytes_subset[i]
                    out.append(f"{{CTRL:{ctrl_idx:02X}}}")
                elif idx == 0x10:
                    i += 1
                    if i >= len(bytes_subset): break
                    rawValue = bytes_subset[i]
                    if rawValue == 0xFF:
                        out.append("{CHOICE-END}")
                    else:
                        choice_idx = rawValue - 0x30
                        out.append(f"{{CHOICE:{choice_idx:02X}}}")
                elif idx == 0x12:
                    i += 1
                    if i >= len(bytes_subset): break
                    var_idx = bytes_subset[i] - 0x30
                    out.append(f"{{VAR:{var_idx:02X}}}")
                elif idx == 0x13:
                    if i + 1 < len(bytes_subset) and bytes_subset[i+1] <= 0x43:
                        i += 1
                        pc_idx = bytes_subset[i] - 0x30
                        out.append(f"{{PC:{pc_idx:02X}}}")
                    else:
                        section = idx - 0x13
                        i += 1
                        if i >= len(bytes_subset): break
                        line = bytes_subset[i]
                        out.append(f"{{MCR:s{section:02X}l{line:02X}}}")
                elif 0x13 <= idx <= 0x22:
                    section = idx - 0x13
                    i += 1
                    if i >= len(bytes_subset): break
                    line = bytes_subset[i]
                    out.append(f"{{MCR:s{section:02X}l{line:02X}}}")
                elif idx == 0x23:
                    i += 1
                    if i >= len(bytes_subset): break
                    var_idx = bytes_subset[i]
                    out.append(f"{{KEY:{var_idx:02X}}}")
                elif idx == 0x27:
                    i += 1
                    if i >= len(bytes_subset): break
                    arg = bytes_subset[i]
                    out.append(f"{{UNK27:{arg:02X}}}")
                elif idx == 0x28:
                    i += 1
                    if i >= len(bytes_subset): break
                    var_idx = bytes_subset[i] - 0x30
                    out.append(f"{{CMD:28:{var_idx:02X}}}")
                elif idx == 0x2A:
                    i += 1
                    if i >= len(bytes_subset): break
                    var_idx = bytes_subset[i] - 0x30
                    out.append(f"{{CMD:2A:{var_idx:02X}}}")
                else:
                    i += 1
                    if i >= len(bytes_subset): break
                    var_idx = bytes_subset[i] - 0x30
                    out.append(f"{{CMD:{idx:02X}:{var_idx:02X}}}")
            i += 1
            
        return "".join(out)

    def char_to_bytes(self, char, charset="us"):
        self.load_charset(charset)
        char_to_byte = self.char_to_byte_maps.get(charset, {})
        
        if char == "\n":
            return [0x03]
        index_value = char_to_byte.get(char)
        if index_value is None:
            return None
            
        bytes_out = []
        if index_value >= 0x100:
            section = 0x2B
            while True:
                section += 1
                index_value -= 0xD0
                if index_value < 0x100:
                    break
            if section >= 0x30:
                bytes_out.append(0x04)
                if section >= 0x31:
                    bytes_out.append(section - 0x05)
            else:
                bytes_out.append(section)
        bytes_out.append(index_value)
        return bytes_out

    def parse_command(self, cmd):
        if cmd == "PAUSE":
            return [0x01]
        elif cmd in ("\\n", "\n", "n"):
            return [0x03]
        elif cmd == "CHOICE-END":
            return [0x10, 0xFF]
        elif cmd.startswith("SPACE:"):
            pixels = int(cmd[6:], 16)
            return [0x07, pixels + 0x30]
        elif cmd.startswith("TIME:"):
            var_idx = int(cmd[5:], 16)
            return [0x09, var_idx + 0x30]
        elif cmd.startswith("CLR:") or cmd.startswith("COLOR:"):
            color_name = cmd.split(":")[1]
            color_byte = COLOR_REV.get(color_name)
            if color_byte is None:
                color_byte = int(color_name, 16)
            return [0x0A, color_byte]
        elif cmd.startswith("CTRL:"):
            ctrl_idx = int(cmd[5:], 16)
            return [0x0B, ctrl_idx]
        elif cmd.startswith("CHOICE:"):
            choice_idx = int(cmd[7:], 16)
            return [0x10, choice_idx + 0x30]
        elif cmd.startswith("VAR:"):
            var_idx = int(cmd[4:], 16)
            return [0x12, var_idx + 0x30]
        elif cmd.startswith("PC:"):
            pc = int(cmd[3:], 16)
            return [0x13, pc + 0x30]
        elif cmd.startswith("MCR:") or cmd.startswith("MACRO:"):
            # Support both {MCR:s00l01} and legacy {MCR:s00l-2F}
            s_idx = cmd.index('s')
            l_idx = cmd.index('l')
            section = int(cmd[s_idx + 1 : l_idx], 16) + 0x13
            l_str = cmd[l_idx + 1:]
            if l_str.startswith("-"):
                line = (int(l_str, 16) + 0x30) & 0xFF
            else:
                line = int(l_str, 16)
            return [section, line]
        elif cmd.startswith("KEY:"):
            key_item_idx = int(cmd[4:], 16)
            return [0x23, key_item_idx]
        elif cmd.startswith("KEY04:"):
            key_item_idx = int(cmd[6:], 16)
            return [0x04, 0x23, key_item_idx]
        elif cmd.startswith("UNK27:"):
            arg = int(cmd[6:], 16)
            return [0x27, arg]
        elif cmd.startswith("UNK0427:"):
            arg = int(cmd[8:], 16)
            return [0x04, 0x27, arg]
        elif cmd.startswith("CMD:"):
            parts = cmd.split(":")
            if len(parts) == 3:
                cmd_idx = int(parts[1], 16)
                var_idx = int(parts[2], 16)
                return [cmd_idx, var_idx + 0x30]
        elif cmd.startswith("UNKCHR:"):
            parts = cmd.split(":")
            return [int(parts[1], 16)]
        elif cmd.startswith("UNKDBLCHR:"):
            parts = cmd.split(":")
            if len(parts) == 3:
                return [int(parts[1], 16), int(parts[2], 16)]
            elif len(parts) == 2:
                return [int(parts[1], 16)]
        elif cmd.startswith("UNKTPLCHR:"):
            parts = cmd.split(":")
            if len(parts) == 4:
                return [int(parts[1], 16), int(parts[2], 16), int(parts[3], 16)]
        return None

    def encode_ffx_string(self, string, charset="us"):
        byte_list = []
        i = 0
        while i < len(string):
            chr_char = string[i]
            if chr_char == "{":
                end_idx = string[i:].find("}")
                if end_idx != -1:
                    cmd_content = string[i+1 : i+end_idx]
                    cmd_bytes = self.parse_command(cmd_content)
                    if cmd_bytes is not None:
                        byte_list.extend(cmd_bytes)
                        i += end_idx + 1
                        continue
            
            char_bytes = self.char_to_bytes(chr_char, charset)
            if char_bytes is not None:
                byte_list.extend(char_bytes)
            i += 1
        return byte_list

    def read_ffx_text_bin(self, filepath, record_length, charset="us"):
        """
        Reads an FFX text bin file.
        Returns a tuple: (records_list, min_idx, max_idx, magic_part)
        Each record in records_list is a dict:
        {
          'id': index,
          'name': str,
          'sname': str,
          'desc': str,
          'sdesc': str,
          'extra_bytes': bytes (binary part from 0x10 to record_length)
        }
        """
        with open(filepath, "rb") as f:
            file_bytes = f.read()
            
        if len(file_bytes) < 20:
            raise ValueError("File is too small to be a valid FFX .bin file.")
            
        header = file_bytes[:20]
        magic_part = header[:8]
        min_idx, max_idx, rec_len, tot_len = struct.unpack("<HHHH", header[8:16])
        
        # Override record_length if it is read from file header
        if rec_len != record_length:
            # Game's actual record length takes priority
            record_length = rec_len
            
        data_bytes = file_bytes[20 : 20+tot_len]
        string_bytes = list(file_bytes[20+tot_len :])
        
        record_count = max_idx - min_idx + 1
        records = []
        base_name = os.path.basename(filepath).lower()

        # ply_save.bin stores ONLY the character name at 0:2 and name_key at 2:4;
        # bytes 4..148 contain character starting HP, MP, stats, and equipment.
        if ("ply_save" in base_name or record_length == 148):
            for idx in range(record_count):
                rec_offset = idx * record_length
                rec_data = data_bytes[rec_offset : rec_offset + record_length]
                name_off, name_key = struct.unpack("<HH", rec_data[0:4])
                name = self.decode_ffx_bytes(string_bytes, name_off, charset)
                records.append({
                    "id": idx + min_idx,
                    "name": name,
                    "name_key": name_key,
                    "sname": "",
                    "sname_key": 0,
                    "desc": "",
                    "desc_key": 0,
                    "sdesc": "",
                    "sdesc_key": 0,
                    "extra_bytes": rec_data[4:] # All 144 bytes preserved intact
                })
            return records, min_idx, max_idx, magic_part

        for idx in range(record_count):
            rec_offset = idx * record_length
            rec_data = data_bytes[rec_offset : rec_offset+record_length]
            if len(rec_data) < 16:
                # Pad to 16 if needed
                rec_data = rec_data + b"\x00" * (16 - len(rec_data))
                
            name_off, name_key = struct.unpack("<HH", rec_data[0:4])
            sname_off, sname_key = struct.unpack("<HH", rec_data[4:8])
            desc_off, desc_key = struct.unpack("<HH", rec_data[8:12])
            sdesc_off, sdesc_key = struct.unpack("<HH", rec_data[12:16])
            
            name = self.decode_ffx_bytes(string_bytes, name_off, charset)
            sname = self.decode_ffx_bytes(string_bytes, sname_off, charset)
            desc = self.decode_ffx_bytes(string_bytes, desc_off, charset)
            sdesc = self.decode_ffx_bytes(string_bytes, sdesc_off, charset)
            
            extra_bytes = rec_data[16:]
            
            rec_dict = {
                "id": idx + min_idx,
                "name": name,
                "name_key": name_key,
                "sname": sname,
                "sname_key": sname_key,
                "desc": desc,
                "desc_key": desc_key,
                "sdesc": sdesc,
                "sdesc_key": sdesc_key,
                "extra_bytes": extra_bytes
            }

            # Extended support for w_name.bin (Party equipment names across 7 characters)
            if record_length == 72 and len(rec_data) >= 72:
                w_wakka_off, w_wakka_key = struct.unpack("<HH", rec_data[16:20])
                w_lulu_off, w_lulu_key = struct.unpack("<HH", rec_data[20:24])
                w_rikku_off, w_rikku_key = struct.unpack("<HH", rec_data[24:28])
                rec_dict["w_wakka"] = self.decode_ffx_bytes(string_bytes, w_wakka_off, charset)
                rec_dict["w_wakka_key"] = w_wakka_key
                rec_dict["w_lulu"] = self.decode_ffx_bytes(string_bytes, w_lulu_off, charset)
                rec_dict["w_lulu_key"] = w_lulu_key
                rec_dict["w_rikku"] = self.decode_ffx_bytes(string_bytes, w_rikku_off, charset)
                rec_dict["w_rikku_key"] = w_rikku_key
                rec_dict["extra_bytes"] = rec_data[28:] # 44 bytes remaining (slots 7..13 + suffix pointers)
                if idx == 0 and len(string_bytes) >= 16384:
                    rec_dict["_w_name_tail_pool"] = bytes(string_bytes[16384:])

            records.append(rec_dict)
            
        return records, min_idx, max_idx, magic_part

    def write_ffx_text_bin(self, filepath, records, min_idx, max_idx, magic_part, charset="us"):
        """
        Repacks and saves records back to a .bin file.
        """
        base_name = os.path.basename(filepath).lower()

        # Specialized repacker for w_name.bin to preserve internal character equipment suffix structures
        if "w_name" in base_name or (records and "w_wakka" in records[0]):
            return self._write_w_name_bin(filepath, records, min_idx, max_idx, magic_part, charset)

        # Specialized repacker for ply_save.bin (148-byte records: 4-byte header for Name, 144 bytes stats)
        if "ply_save" in base_name or (records and len(records[0].get("extra_bytes", b"")) == 144):
            return self._write_ply_save_bin(filepath, records, min_idx, max_idx, magic_part, charset)

        # Encode all strings and prepare unique mappings
        refs = []
        for r in records:
            refs.append(('name', r['name'], r))
            refs.append(('sname', r['sname'], r))
            refs.append(('desc', r['desc'], r))
            refs.append(('sdesc', r['sdesc'], r))
            
        encoded_cache = {}
        for ref_type, s, r in refs:
            if s not in encoded_cache:
                encoded_cache[s] = self.encode_ffx_string(s, charset) + [0x00]
                
        # Sort by encoded length ascending to build deterministic buffer
        refs_sorted = sorted(refs, key=lambda x: len(encoded_cache[x[1]]))
        
        unique_map = {}
        byte_list = []
        rec_offsets = {id(r): {} for r in records}
        
        for ref_type, s, r in refs_sorted:
            if s in unique_map:
                offset = unique_map[s]
            else:
                offset = len(byte_list)
                unique_map[s] = offset
                byte_list.extend(encoded_cache[s])
                
            rec_offsets[id(r)][ref_type] = offset
            
        # Rebuild structured record bytes
        data_blocks = []
        record_length = 16
        if records:
            record_length = 16 + len(records[0]['extra_bytes'])
            
        for r in records:
            offs = rec_offsets[id(r)]
            header_bytes = struct.pack("<HHHHHHHH",
                offs.get('name', 0), r.get('name_key', 0),
                offs.get('sname', 0), r.get('sname_key', 0),
                offs.get('desc', 0), r.get('desc_key', 0),
                offs.get('sdesc', 0), r.get('sdesc_key', 0)
            )
            record_block = header_bytes + r['extra_bytes']
            data_blocks.append(record_block)
            
        data_bytes = b"".join(data_blocks)
        string_buffer = bytes(byte_list)
        
        # Build 20-byte file header
        tot_len = len(data_bytes)
        file_header = magic_part + struct.pack("<HHHH", min_idx, max_idx, record_length, tot_len) + struct.pack("<I", 20)
        
        # Write file
        with open(filepath, "wb") as f:
            f.write(file_header + data_bytes + string_buffer)
            
        return len(file_header + data_bytes + string_buffer)

    def _write_w_name_bin(self, filepath, records, min_idx, max_idx, magic_part, charset="us"):
        """
        Specialized repacker for w_name.bin (72-byte records) to preserve suffix and tail offset structures.
        Main weapon/armor strings are kept within 0x0000..0x3FFF (0..16383), and the tail suffix pool
        is anchored at 0x4000 (16384).
        """
        tail_bytes = b""
        if records and "_w_name_tail_pool" in records[0]:
            tail_bytes = records[0]["_w_name_tail_pool"]
        elif os.path.exists(filepath):
            with open(filepath, "rb") as f:
                orig_raw = f.read()
            if len(orig_raw) > 20:
                tot_l = struct.unpack("<H", orig_raw[14:16])[0]
                if 20 + tot_l + 16384 <= len(orig_raw):
                    tail_bytes = orig_raw[20 + tot_l + 16384 :]

        unique_map = {}
        main_string_bytes = []

        def get_off(s):
            if s not in unique_map:
                unique_map[s] = len(main_string_bytes)
                main_string_bytes.extend(self.encode_ffx_string(s, charset))
                main_string_bytes.append(0x00)
            return unique_map[s]

        hyphen_off = get_off("-")

        out_data = bytearray()
        for r in records:
            extra_b = bytearray(r.get("extra_bytes", b"\x00" * 44))
            if len(extra_b) < 44:
                extra_b.extend(b"\x00" * (44 - len(extra_b)))
            full_rec = bytearray(72)
            # Slots 0..3 (Tidus, Yuna, Auron, Kimahri)
            full_rec[0:4] = struct.pack("<HH", get_off(r["name"]), r.get("name_key", 0))
            full_rec[4:8] = struct.pack("<HH", get_off(r["sname"]), r.get("sname_key", 0))
            full_rec[8:12] = struct.pack("<HH", get_off(r["desc"]), r.get("desc_key", 0))
            full_rec[12:16] = struct.pack("<HH", get_off(r["sdesc"]), r.get("sdesc_key", 0))
            # Slots 4..6 (Wakka, Lulu, Rikku)
            full_rec[16:20] = struct.pack("<HH", get_off(r.get("w_wakka", "")), r.get("w_wakka_key", 0))
            full_rec[20:24] = struct.pack("<HH", get_off(r.get("w_lulu", "")), r.get("w_lulu_key", 0))
            full_rec[24:28] = struct.pack("<HH", get_off(r.get("w_rikku", "")), r.get("w_rikku_key", 0))
            # Copy remaining 44 bytes (slots 7..13, suffix pointers 56..70, flags 70..72)
            full_rec[28:72] = extra_b[:44]
            # Standardize slots 7..13 to hyphen offset while preserving key bytes
            for s_idx in range(7, 14):
                full_rec[s_idx * 4 : s_idx * 4 + 2] = struct.pack("<H", hyphen_off)
            out_data.extend(full_rec)

        if len(main_string_bytes) > 16384:
            raise ValueError(f"Total weapon/armor name string pool ({len(main_string_bytes)} bytes) exceeds 16,384 byte limit for 0x4000 suffix alignment.")

        padded_main = bytes(main_string_bytes) + b"\x00" * (16384 - len(main_string_bytes))
        full_str_buf = padded_main + tail_bytes
        file_hdr = magic_part + struct.pack("<HHHH", min_idx, max_idx, 72, len(out_data)) + struct.pack("<I", 20)

        with open(filepath, "wb") as f:
            f.write(file_hdr + bytes(out_data) + full_str_buf)

        return len(file_hdr + bytes(out_data) + full_str_buf)

    def _write_ply_save_bin(self, filepath, records, min_idx, max_idx, magic_part, charset="us"):
        """
        Specialized repacker for ply_save.bin (148-byte records: 4-byte header for Name, 144 bytes stats).
        """
        unique_map = {}
        byte_list = []

        def get_off(s):
            if s not in unique_map:
                unique_map[s] = len(byte_list)
                byte_list.extend(self.encode_ffx_string(s, charset))
                byte_list.append(0x00)
            return unique_map[s]

        out_data = bytearray()
        for r in records:
            extra_b = r.get("extra_bytes", b"\x00" * 144)
            if len(extra_b) < 144:
                extra_b = extra_b + b"\x00" * (144 - len(extra_b))
            rec_hdr = struct.pack("<HH", get_off(r["name"]), r.get("name_key", 0))
            out_data.extend(rec_hdr + extra_b)

        tot_len = len(out_data)
        file_hdr = magic_part + struct.pack("<HHHH", min_idx, max_idx, 148, tot_len) + struct.pack("<I", 20)

        with open(filepath, "wb") as f:
            f.write(file_hdr + bytes(out_data) + bytes(byte_list))

        return len(file_hdr + bytes(out_data) + bytes(byte_list))

    def read_ffx_sps2(self, filepath, charset="us"):
        """
        Reads an FFX .sps2 Screen Presentation / Script file (e.g. mon_boku.sps2, now_help.sps2).
        Returns: records, min_id, max_id, magic_part
        """
        self.load_charset(charset)
        with open(filepath, "rb") as f:
            data = f.read()

        if len(data) < 36:
            raise ValueError(f"File '{filepath}' is too small to be a valid .sps2 file ({len(data)} bytes).")

        hdr = struct.unpack("<5I", data[:20])
        ptr_table_off = hdr[4]
        if ptr_table_off >= len(data):
            raise ValueError(f"Invalid pointer table offset {ptr_table_off} in .sps2 header.")

        first_ptr = struct.unpack("<I", data[ptr_table_off : ptr_table_off + 4])[0]
        if first_ptr < ptr_table_off or first_ptr > len(data):
            raise ValueError(f"Invalid first string pointer {first_ptr} in .sps2 file.")

        num_ptrs = (first_ptr - ptr_table_off) // 4
        ptrs = [struct.unpack("<I", data[ptr_table_off + i * 4 : ptr_table_off + (i + 1) * 4])[0] for i in range(num_ptrs)]

        records = []
        for i in range(num_ptrs):
            start = ptrs[i]
            end = ptrs[i + 1] if i + 1 < num_ptrs else len(data)
            chunk = data[start:end]
            text = self.decode_ffx_bytes(chunk, 0, charset)
            records.append({
                "id": i,
                "name": text,
                "sname": "",
                "desc": "",
                "sdesc": "",
                "raw_chunk": chunk,
                "ptr": start
            })

        min_id = 0
        max_id = max(0, len(records) - 1)
        magic_part = data[:36]
        return records, min_id, max_id, magic_part

    def write_ffx_sps2(self, filepath, records, min_idx=0, max_idx=0, magic_part=None, charset="us"):
        """
        Repacks and saves records back to an .sps2 file.
        Updates edited text entries while preserving raw presentation bytecode packets.
        """
        self.load_charset(charset)
        repacked_chunks = []
        for r in records:
            raw_c = r.get("raw_chunk", b"")
            orig_dec = self.decode_ffx_bytes(raw_c, 0, charset) if raw_c else ""
            if r["name"] != orig_dec or not raw_c:
                new_enc = bytes(self.encode_ffx_string(r["name"], charset) + [0x00])
                repacked_chunks.append(new_enc)
            else:
                repacked_chunks.append(raw_c)

        num_ptrs = len(records)
        ptr_table_off = 36
        new_first_ptr = ptr_table_off + num_ptrs * 4
        new_ptrs = []
        cur_off = new_first_ptr
        for ch in repacked_chunks:
            new_ptrs.append(cur_off)
            cur_off += len(ch)

        new_hdr = struct.pack("<5I", 1, 0, cur_off, 0, ptr_table_off) + b"\x00" * 16
        out_bytes = new_hdr + b"".join(struct.pack("<I", p) for p in new_ptrs) + b"".join(repacked_chunks)

        with open(filepath, "wb") as f:
            f.write(out_bytes)

        return len(out_bytes)

    def read_albheddic_bin(self, filepath, charset="us"):
        """
        Reads the Al Bhed dictionary substitution table (menu/albheddic.bin).
        Each entry is 4 bytes: [original_char, albhed_translated_char, primer_id, 0x00].
        """
        self.load_charset(charset)
        tbl = self.byte_to_char_maps.get(charset, {})
        with open(filepath, "rb") as f:
            data = f.read()

        num_entries = len(data) // 4
        records = []
        for i in range(num_entries):
            b0, b1, b2, b3 = data[i * 4 : (i + 1) * 4]
            c0 = tbl.get(b0, f"\\x{b0:02X}")
            c1 = tbl.get(b1, f"\\x{b1:02X}")
            primer_str = f"Al Bhed Primer {b2 + 1}"
            records.append({
                "id": i,
                "name": f"{c0} -> {c1}",
                "sname": c1,
                "desc": f"Translates original letter '{c0}' into '{c1}' ({primer_str})",
                "sdesc": primer_str,
                "b0": b0,
                "b1": b1,
                "b2": b2,
                "b3": b3
            })
        min_id = 0
        max_id = max(0, len(records) - 1)
        magic_part = b""
        return records, min_id, max_id, magic_part

    def write_albheddic_bin(self, filepath, records, min_idx=0, max_idx=0, magic_part=b"", charset="us"):
        """
        Repacks and saves the Al Bhed dictionary substitution table (menu/albheddic.bin).
        """
        self.load_charset(charset)
        rev = self.char_to_byte_maps.get(charset, {})
        out = bytearray()
        for r in records:
            b0 = r.get("b0", 0)
            b1 = r.get("b1", 0)
            nm = r.get("name", "")
            if "->" in nm:
                char_trans = nm.split("->")[1].strip()
            else:
                char_trans = nm.strip()
            if char_trans in rev:
                b1 = rev[char_trans]
            out.extend([b0, b1, r.get("b2", 0), r.get("b3", 0)])

        with open(filepath, "wb") as f:
            f.write(out)
        return len(out)

    def read_ffx_msg_bin(self, filepath, charset="us"):
        """
        Reads an FFX Message Table .bin file (used by event/obj_ps3 cutscenes, battle/btl quotes, menu/menumain.bin, cloudsave).
        Header contains a 32-bit pointer table from offset 0 up to first_ptr.
        Returns: records, min_id, max_id, magic_part
        """
        self.load_charset(charset)
        with open(filepath, "rb") as f:
            data = f.read()

        if len(data) < 4:
            return [], 0, 0, b""

        raw_first_ptr = struct.unpack("<I", data[:4])[0]
        if raw_first_ptr == 0:
            return [], 0, 0, b""

        first_ptr = raw_first_ptr
        if first_ptr > len(data):
            p_24 = raw_first_ptr & 0x00FFFFFF
            p_16 = raw_first_ptr & 0xFFFF
            if 4 <= p_24 <= len(data):
                first_ptr = p_24
            elif 4 <= p_16 <= len(data):
                first_ptr = p_16
            else:
                raise ValueError(f"Invalid first string pointer {raw_first_ptr} in message file.")

        num_ptrs = first_ptr // 4
        ptrs = [struct.unpack("<I", data[i * 4 : (i + 1) * 4])[0] for i in range(num_ptrs)]

        records = []
        for i, raw_p in enumerate(ptrs):
            p_val = raw_p
            if p_val > len(data):
                p_24 = raw_p & 0x00FFFFFF
                p_16 = raw_p & 0xFFFF
                if p_24 < len(data):
                    p_val = p_24
                elif p_16 < len(data):
                    p_val = p_16

            if 0 < p_val < len(data):
                text = self.decode_ffx_bytes(data, p_val, charset)
            else:
                text = ""

            high_flags = 0
            if (raw_p & 0xFF000000) != 0 and (raw_p & 0x00FFFFFF) < len(data):
                high_flags = raw_p & 0xFF000000
            elif (raw_p & 0xFFFF0000) != 0 and (raw_p & 0xFFFF) < len(data):
                high_flags = raw_p & 0xFFFF0000

            records.append({
                "id": i,
                "name": text,
                "sname": "",
                "desc": "",
                "sdesc": "",
                "ptr": p_val,
                "high_flags": high_flags
            })

        min_id = 0
        max_id = max(0, len(records) - 1)
        magic_part = b""
        return records, min_id, max_id, magic_part

    def write_ffx_msg_bin(self, filepath, records, min_idx=0, max_idx=0, magic_part=b"", charset="us"):
        """
        Repacks and saves records back to an FFX Message Table .bin file.
        Rebuilds the 32-bit pointer table and deduplicated string pool.
        """
        self.load_charset(charset)
        str_to_pool_off = {}
        pool_bytes = []
        new_ptrs = []

        new_first_ptr = len(records) * 4
        for r in records:
            s = r["name"]
            if s not in str_to_pool_off:
                str_to_pool_off[s] = len(pool_bytes)
                pool_bytes.extend(self.encode_ffx_string(s, charset) + [0x00])
            offset = new_first_ptr + str_to_pool_off[s]
            high_flags = r.get("high_flags", 0)
            new_ptrs.append(offset | high_flags)

        out_data = bytearray()
        for p in new_ptrs:
            out_data.extend(struct.pack("<I", p))
        out_data.extend(bytes(pool_bytes))

        with open(filepath, "wb") as f:
            f.write(out_data)

        return len(out_data)

    def load_any_ffx_file(self, filepath, record_len=16, charset="us"):
        """
        Unified loader that detects whether a file is:
        - SPS2 Presentation package (.sps2)
        - Fixed-record Kernel Table (.bin in battle/kernel)
        - Al Bhed Cipher Dictionary (menu/albheddic.bin)
        - Message Table (.bin in event, battle/btl, menu, cloudsave)
        """
        norm_path = filepath.replace("\\", "/").lower()
        base_name = os.path.basename(norm_path)
        if "macrodic" in base_name or norm_path.endswith(".dcp"):
            raw_macros = self.read_macrodic_dcp(filepath, charset)
            records = []
            for k, m in sorted(raw_macros.items(), key=lambda x: (x[1]['sec_id'], x[1]['item_id'])):
                records.append({
                    'id': f"s{m['sec_id']:02X}l{m['item_id']:02X}",
                    'name': m['text'],
                    'sname': m['tag'],
                    'desc': m['category'],
                    'sdesc': f"Section {m['sec_id']}, Item {m['item_id']}",
                    'sec_id': m['sec_id'],
                    'item_id': m['item_id'],
                    'tag': m['tag']
                })
            min_idx = 0
            max_idx = len(records) - 1 if records else 0
            return records, min_idx, max_idx, b"", "macro"
        elif norm_path.endswith(".sps2"):
            records, min_id, max_id, magic_part = self.read_ffx_sps2(filepath, charset)
            return records, min_id, max_id, magic_part, "sps2"
        elif "albheddic" in base_name:
            records, min_id, max_id, magic_part = self.read_albheddic_bin(filepath, charset)
            return records, min_id, max_id, magic_part, "albhed"
        elif "battle/kernel" in norm_path or base_name in FILE_RECORD_SIZES or "w_name" in base_name:
            rec_len = FILE_RECORD_SIZES.get(base_name, record_len)
            records, min_id, max_id, magic_part = self.read_ffx_text_bin(filepath, rec_len, charset)
            return records, min_id, max_id, magic_part, "kernel"
        else:
            records, min_id, max_id, magic_part = self.read_ffx_msg_bin(filepath, charset)
            return records, min_id, max_id, magic_part, "msg"

    def save_any_ffx_file(self, filepath, records, min_idx, max_idx, magic_part, charset="us"):
        """
        Unified saver that routes saving to the appropriate repacker.
        """
        norm_path = filepath.replace("\\", "/").lower()
        base_name = os.path.basename(norm_path)
        if "macrodic" in base_name or norm_path.endswith(".dcp"):
            macro_dict = {}
            for r in records:
                k = str(r.get('id', '')).lower()
                macro_dict[k] = {
                    'sec_id': r.get('sec_id', 0),
                    'item_id': r.get('item_id', 0),
                    'text': r.get('name', ''),
                    'tag': r.get('tag', f"{{MCR:{k}}}")
                }
            return self.write_macrodic_dcp(filepath, macro_dict, charset)
        elif norm_path.endswith(".sps2"):
            return self.write_ffx_sps2(filepath, records, min_idx, max_idx, magic_part, charset)
        elif "albheddic" in base_name:
            return self.write_albheddic_bin(filepath, records, min_idx, max_idx, magic_part, charset)
        elif "battle/kernel" in norm_path or base_name in FILE_RECORD_SIZES or "w_name" in base_name:
            return self.write_ffx_text_bin(filepath, records, min_idx, max_idx, magic_part, charset)
        else:
            return self.write_ffx_msg_bin(filepath, records, min_idx, max_idx, magic_part, charset)

    def read_macrodic_dcp(self, filepath, charset="us"):
        """
        Parses macrodic.dcp binary file across all sections and extracts macro definitions.
        Returns a dictionary mapping tag keys (e.g. 's06l7d') to dicts:
        {'tag': '{MCR:s06l7D}', 'sec_id': 6, 'item_id': 125, 'category': 'Characters & NPCs', 'text': 'Yevon'}
        """
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            if len(data) < 64:
                return {}
            hdr = struct.unpack('<16I', data[:64])
            sec_cats = {
                0x06: 'Characters & NPCs',
                0x07: 'Blitzball Players',
                0x08: 'Blitzball Techniques',
                0x0B: 'Field & Map Locations',
                0x0D: 'World Regions & Places'
            }
            macro_dict = {}
            for sec_idx, sec_off in enumerate(hdr):
                if sec_off == 0 or sec_off >= len(data):
                    continue
                # Determine pointer table size by finding the first valid string pointer
                count = 0
                for probe in range(sec_off, min(sec_off + 4096, len(data) - 1), 2):
                    ptr_val = struct.unpack('<H', data[probe:probe+2])[0]
                    if ptr_val > 0 and ptr_val <= len(data) - sec_off:
                        count = ptr_val // 2
                        break
                if count <= 0:
                    continue
                cat = sec_cats.get(sec_idx, f'Section {sec_idx:02X}')
                for item_idx in range(count):
                    ptr_pos = sec_off + item_idx * 2
                    if ptr_pos + 2 > len(data):
                        break
                    ptr = struct.unpack('<H', data[ptr_pos:ptr_pos+2])[0]
                    if ptr == 0:
                        continue
                    str_off = sec_off + ptr
                    if str_off >= len(data):
                        continue
                    txt = self.decode_ffx_bytes(data, str_off, charset)
                    if txt and txt not in ('noname', 'None'):
                        tag_key = f"s{sec_idx:02x}l{item_idx:02x}".lower()
                        macro_dict[tag_key] = {
                            'tag': f"{{MCR:s{sec_idx:02X}l{item_idx:02X}}}",
                            'sec_id': sec_idx,
                            'item_id': item_idx,
                            'category': cat,
                            'text': txt
                        }
            return macro_dict
        except Exception:
            return {}

    def write_macrodic_dcp(self, filepath, macro_dict, charset="us"):
        """
        Packs a dictionary of macro definitions into a valid FFX macrodic.dcp binary file.
        Accepts macro_dict in format {tag_key: {'sec_id': int, 'item_id': int, 'text': str, ...}} or {'s06l7d': 'Text'}.
        """
        try:
            sections = {}
            for k, val in macro_dict.items():
                if isinstance(val, dict):
                    sec_id = int(val.get('sec_id', 0))
                    item_id = int(val.get('item_id', 0))
                    text = str(val.get('text', ''))
                else:
                    m = re.match(r's([0-9a-fA-F]{2})l([0-9a-fA-F]{2})', k)
                    if m:
                        sec_id = int(m.group(1), 16)
                        item_id = int(m.group(2), 16)
                    else:
                        continue
                    text = str(val)
                if sec_id not in sections:
                    sections[sec_id] = {}
                sections[sec_id][item_id] = text

            hdr_offsets = [0] * 16
            curr_offset = 64
            section_bytes = {}

            for s in range(16):
                if s not in sections or not sections[s]:
                    continue
                items = sections[s]
                max_id = max(items.keys())
                count = max_id + 1

                ptr_table_size = count * 2
                str_data = bytearray()
                ptrs = [0] * count

                # Anchor ptrs[0] to the start of the string table for compatibility
                ptrs[0] = ptr_table_size
                str_data.extend(b'\x00')

                for item_idx in range(count):
                    if item_idx in items and items[item_idx]:
                        t = items[item_idx]
                        encoded = bytes(self.encode_ffx_string(t, charset)) + b'\x00'
                        ptrs[item_idx] = ptr_table_size + len(str_data)
                        str_data.extend(encoded)

                sec_body = bytearray()
                for p in ptrs:
                    sec_body.extend(struct.pack('<H', p))
                sec_body.extend(str_data)
                while len(sec_body) % 4 != 0:
                    sec_body.append(0)

                hdr_offsets[s] = curr_offset
                section_bytes[s] = sec_body
                curr_offset += len(sec_body)

            out_buf = bytearray()
            for off in hdr_offsets:
                out_buf.extend(struct.pack('<I', off))
            for s in range(16):
                if s in section_bytes:
                    out_buf.extend(section_bytes[s])

            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(out_buf)
            return len(out_buf)
        except Exception:
            return 0
