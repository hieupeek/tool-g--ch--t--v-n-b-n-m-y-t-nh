#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoTyper Pro - Tool tự động gõ văn bản thông minh
Hỗ trợ cả Windows và macOS. Hoạt động mượt mà cả khi gõ vào Remote Desktop (AnyDesk, TeamViewer, RDP...).
Tương thích hoàn hảo 100% với macOS (xử lý triệt để lỗi Dark Mode của Tkinter 8.5).
"""

import sys
import os
import time
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox


def safe_print(*args, **kwargs):
    """Print không bao giờ crash: bản .exe (--noconsole) và run.bat (pythonw)
    trên Windows không có stdout — print() thường sẽ quăng
    'RuntimeError: lost sys.stdout' và sập app ngay lúc mở."""
    try:
        if sys.stdout is None:
            return
        print(*args, **kwargs)
    except Exception:
        pass

# Xác định hệ điều hành
IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

# Khởi tạo API hệ thống tương ứng
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32

    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    INPUT_KEYBOARD = 1

    VK_CONTROL = 0x11
    VK_SHIFT = 0x10
    VK_RETURN = 0x0D
    VK_ESCAPE = 0x1B

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong)
        ]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        _anonymous_ = ("_input",)
        _fields_ = [
            ("type", wintypes.DWORD),
            ("_input", _INPUT)
        ]

    def _to_utf16_units(char_unicode):
        """Tách 1 ký tự Python thành các đơn vị UTF-16 cho KEYEVENTF_UNICODE.
        Ký tự ngoài BMP (emoji...) phải gửi dưới dạng cặp surrogate, nếu không
        wScan (WORD 16-bit) sẽ bị cắt và gõ ra ký tự rác."""
        code = ord(char_unicode)
        if code < 0x10000:
            return (code,)
        code -= 0x10000
        return (0xD800 + (code >> 10), 0xDC00 + (code & 0x3FF))

    def _send_unicode_unit(unit):
        inputs = (INPUT * 2)()
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].ki.wVk = 0
        inputs[0].ki.wScan = unit
        inputs[0].ki.dwFlags = KEYEVENTF_UNICODE
        inputs[0].ki.time = 0
        inputs[0].ki.dwExtraInfo = 0

        inputs[1].type = INPUT_KEYBOARD
        inputs[1].ki.wVk = 0
        inputs[1].ki.wScan = unit
        inputs[1].ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        inputs[1].ki.time = 0
        inputs[1].ki.dwExtraInfo = 0

        user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

    def send_key_win(vk_code=0, char_unicode=None):
        """Gửi phím trên Windows bằng SendInput (hỗ trợ Unicode tiếng Việt đầy đủ)"""
        if char_unicode is not None:
            for unit in _to_utf16_units(char_unicode):
                _send_unicode_unit(unit)
            return
        inputs = (INPUT * 2)()
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].ki.wVk = vk_code
        inputs[0].ki.wScan = 0
        inputs[0].ki.dwFlags = 0
        inputs[0].ki.time = 0
        inputs[0].ki.dwExtraInfo = 0

        inputs[1].type = INPUT_KEYBOARD
        inputs[1].ki.wVk = vk_code
        inputs[1].ki.wScan = 0
        inputs[1].ki.dwFlags = KEYEVENTF_KEYUP
        inputs[1].ki.time = 0
        inputs[1].ki.dwExtraInfo = 0

        user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

elif IS_MAC:
    import ctypes
    from ctypes import util

    cg_path = util.find_library('ApplicationServices')
    cf_path = util.find_library('CoreFoundation')
    
    cg = ctypes.cdll.LoadLibrary(cg_path) if cg_path else None
    cf = ctypes.cdll.LoadLibrary(cf_path) if cf_path else None

    if cg:
        cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
        cg.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]
        cg.CGEventKeyboardSetUnicodeString.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p]
        cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]

    if cf:
        cf.CFRelease.argtypes = [ctypes.c_void_p]

    # Khe nghỉ giữa key-down và key-up: gửi 2 sự kiện dính liền nhau khiến
    # nhiều app đích (web, remote desktop, ô chat...) nuốt mất phím,
    # đặc biệt là ký tự ngay sau phím Enter.
    _KEY_DOWN_UP_GAP = 0.004  # giây

    def send_char_mac(char):
        """Gõ ký tự trên macOS bằng CoreGraphics CGEvent"""
        if cg is None or cf is None:
            return
        try:
            if char == '\n':
                evt_down = cg.CGEventCreateKeyboardEvent(None, 36, True)
                evt_up = cg.CGEventCreateKeyboardEvent(None, 36, False)
                cg.CGEventPost(0, evt_down)
                time.sleep(_KEY_DOWN_UP_GAP)
                cg.CGEventPost(0, evt_up)
                cf.CFRelease(evt_down)
                cf.CFRelease(evt_up)
            elif char == '\t':
                evt_down = cg.CGEventCreateKeyboardEvent(None, 48, True)
                evt_up = cg.CGEventCreateKeyboardEvent(None, 48, False)
                cg.CGEventPost(0, evt_down)
                time.sleep(_KEY_DOWN_UP_GAP)
                cg.CGEventPost(0, evt_up)
                cf.CFRelease(evt_down)
                cf.CFRelease(evt_up)
            else:
                evt_down = cg.CGEventCreateKeyboardEvent(None, 0, True)
                evt_up = cg.CGEventCreateKeyboardEvent(None, 0, False)
                cg.CGEventKeyboardSetUnicodeString(evt_down, len(char), char)
                cg.CGEventKeyboardSetUnicodeString(evt_up, len(char), char)
                cg.CGEventPost(0, evt_down)
                time.sleep(_KEY_DOWN_UP_GAP)
                cg.CGEventPost(0, evt_up)
                cf.CFRelease(evt_down)
                cf.CFRelease(evt_up)
        except Exception as e:
            safe_print(f"Loi CGEvent khi go '{char}': {e}")

    def is_mac_accessibility_granted():
        """Kiểm tra xem app đã được cấp quyền Trợ năng chưa"""
        try:
            if cg is None:
                return False
            return bool(cg.AXIsProcessTrusted())
        except Exception:
            return False

    def open_mac_accessibility_settings():
        """Mở trực tiếp trang cài đặt Trợ năng trên macOS"""
        os.system('open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"')

    def force_macos_aqua_appearance():
        """Ép dùng Light Appearance (Aqua) để Tk 8.5 không bị chữ trắng-trên-nền-trắng.
        Bản cũ đổi argtypes liên tục trên cùng 1 hàm objc_msgSend nên thực tế
        không có tác dụng (và còn có thể crash trên arm64). Bản này dùng mỗi
        prototype riêng cho từng kiểu chữ ký, thất bại thì bỏ qua an toàn."""
        try:
            from ctypes import util as _util, cdll as _cdll, c_void_p as _c_void_p, c_char_p as _c_char_p, CFUNCTYPE as _CFUNCTYPE
            objc_path = _util.find_library('objc')
            if not objc_path:
                return
            objc = _cdll.LoadLibrary(objc_path)
            objc.objc_getClass.restype = _c_void_p
            objc.objc_getClass.argtypes = [_c_char_p]
            objc.sel_registerName.restype = _c_void_p
            objc.sel_registerName.argtypes = [_c_char_p]

            # Mỗi kiểu chữ ký dùng 1 prototype riêng (không mutate chung 1 hàm)
            _msg_0 = _CFUNCTYPE(_c_void_p, _c_void_p, _c_void_p)(('objc_msgSend', objc))
            _msg_cstr = _CFUNCTYPE(_c_void_p, _c_void_p, _c_void_p, _c_char_p)(('objc_msgSend', objc))
            _msg_id = _CFUNCTYPE(_c_void_p, _c_void_p, _c_void_p, _c_void_p)(('objc_msgSend', objc))

            NSApplication = objc.objc_getClass(b'NSApplication')
            NSString = objc.objc_getClass(b'NSString')
            NSAppearance = objc.objc_getClass(b'NSAppearance')
            if not NSApplication or not NSString or not NSAppearance:
                return

            app = _msg_0(NSApplication, objc.sel_registerName(b'sharedApplication'))
            aqua_str = _msg_cstr(NSString, objc.sel_registerName(b'stringWithUTF8String:'), b'NSAppearanceNameAqua')
            if not app or not aqua_str:
                return
            aqua_appearance = _msg_id(NSAppearance, objc.sel_registerName(b'appearanceNamed:'), aqua_str)
            if not aqua_appearance:
                return
            _msg_id(app, objc.sel_registerName(b'setAppearance:'), aqua_appearance)
        except Exception:
            pass


BUILD_TAG = "v2-gray-editor-2026-10-05"


class AutoTyperApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"AutoTyper Pro - Tự Động Gõ Chữ [{BUILD_TAG}]")
        self.root.geometry("680x620")
        self.root.minsize(600, 540)

        # Áp dụng fix giao diện cho macOS
        if IS_MAC:
            force_macos_aqua_appearance()

        # Trạng thái luồng
        self.is_typing = False
        self.stop_requested = False
        self.is_counting_down = False
        self.current_char_index = 0

        self.setup_ui()
        self.start_hotkey_listener()

    def setup_ui(self):
        # Tk 8.5 trên macOS (Python hệ thống) không hỗ trợ Dark Mode:
        # mọi Label/Frame đặt màu nền chữ cứng (bg/fg) đều có thể render thành
        # chữ trắng-trên-nền-trắng rồi "tàng hình" (đúng như ảnh chụp lỗi).
        # Vì vậy trên macOS: KHÔNG đặt bg/fg cứng cho các nhãn trang trí,
        # để hệ thống tự chọn màu theo Light/Dark. Ô soạn thảo ép nền xám
        # đậm + chữ trắng để luôn tương phản, không bao giờ tàng hình.
        CHROME_BG = None if IS_MAC else "#e8eaed"
        CHROME_FG_TITLE = None if IS_MAC else "#1a73e8"
        CHROME_FG_SUB = None if IS_MAC else "#5f6368"
        CHROME_FG_LABEL = None  # nhãn thường: luôn dùng màu hệ thống

        # 1. Header Frame
        if CHROME_BG:
            header = tk.Frame(self.root, bg=CHROME_BG, padx=16, pady=10)
        else:
            header = tk.Frame(self.root, padx=16, pady=10)
        header.pack(fill=tk.X)

        title_lbl = tk.Label(
            header,
            text="⚡ AutoTyper Pro - Tự Động Gõ Văn Bản",
            font=("Helvetica", 14, "bold"),
            **({"bg": CHROME_BG} if CHROME_BG else {}),
            **({"fg": CHROME_FG_TITLE} if CHROME_FG_TITLE else {}),
        )
        title_lbl.pack(side=tk.LEFT)

        hotkey_tag = "Ctrl + Shift + Enter" if IS_WINDOWS else "Phím Bắt Đầu / Đếm Ngược"
        sub_lbl = tk.Label(
            header,
            text=f"Phím tắt: [{hotkey_tag}] | Dừng: [Esc]",
            font=("Helvetica", 10),
            **({"bg": CHROME_BG} if CHROME_BG else {}),
            **({"fg": CHROME_FG_SUB} if CHROME_FG_SUB else {}),
        )
        sub_lbl.pack(side=tk.RIGHT)

        # Banner cảnh báo quyền Trợ năng trên macOS nếu chưa cấp
        if IS_MAC and not is_mac_accessibility_granted():
            perm_box = tk.Frame(self.root, bg="#ff9800", padx=12, pady=6)
            perm_box.pack(fill=tk.X)
            
            tk.Label(
                perm_box, 
                text="⚠️ macOS cần quyền Trợ năng (Accessibility) để gõ vào Word / Docs / Remote:", 
                font=("Helvetica", 10, "bold"), 
                fg="white", 
                bg="#ff9800"
            ).pack(side=tk.LEFT, padx=5)

            tk.Button(
                perm_box, 
                text="🔓 Mở Cài Đặt Ngay", 
                font=("Helvetica", 9, "bold"), 
                command=open_mac_accessibility_settings,
                bg="white", 
                fg="black", 
                relief=tk.RAISED,
                padx=8, pady=2,
                cursor="hand2"
            ).pack(side=tk.RIGHT, padx=5)

        # 2. Khung chính chứa toàn bộ điều khiển
        main = tk.Frame(self.root, padx=16, pady=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Thanh công cụ trên ô soạn thảo
        toolbar = tk.Frame(main)
        toolbar.pack(fill=tk.X, pady=(0, 6))

        lbl_input = tk.Label(
            toolbar,
            text="📝 Dán hoặc nhập văn bản cần gõ vào khung xám bên dưới:",
            font=("Helvetica", 11, "bold"),
            **({"fg": CHROME_FG_LABEL} if CHROME_FG_LABEL else {}),
        )
        lbl_input.pack(side=tk.LEFT)

        btn_clear = tk.Button(
            toolbar, 
            text="🗑 Xóa hết", 
            font=("Helvetica", 9), 
            command=self.clear_text,
            padx=8, pady=2,
            cursor="hand2"
        )
        btn_clear.pack(side=tk.RIGHT, padx=(6, 0))

        btn_paste = tk.Button(
            toolbar, 
            text="📋 Dán từ Clipboard", 
            font=("Helvetica", 9, "bold"), 
            command=self.paste_from_clipboard,
            padx=10, pady=2,
            fg="#1a73e8",
            cursor="hand2"
        )
        btn_paste.pack(side=tk.RIGHT)

        # 3. Ô SOẠN THẢO VĂN BẢN (KHUNG TRẮNG + VIỀN ĐẬM + TIÊU ĐỀ RIÊNG)
        # Bọc trong LabelFrame có tiêu đề: kể cả khi màu nền hệ thống đổi
        # (Light/Dark, Tk 8.5/8.6) thì khung + tiêu đề vẫn luôn nhìn thấy,
        # không bao giờ "hòa vào nền trắng" như bản dùng Frame+SUNKEN+FLAT cũ.
        editor_box = tk.LabelFrame(
            main,
            text=" Nội dung văn bản — bấm vào khung xám để sửa ",
            font=("Helvetica", 10, "bold"),
            bd=2,
            padx=6,
            pady=6,
        )
        editor_box.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        text_container = tk.Frame(editor_box, bd=1, relief=tk.SOLID)
        text_container.pack(fill=tk.BOTH, expand=True)

        self.text_editor = tk.Text(
            text_container,
            bg="#424242",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#3390ec",
            selectforeground="#ffffff",
            font=("Menlo" if IS_MAC else "Consolas", 12),
            wrap=tk.WORD,
            relief=tk.SOLID,
            bd=1,
            highlightthickness=2,
            highlightbackground="#1a73e8",
            highlightcolor="#1a73e8",
            padx=10,
            pady=10,
            height=8,
            undo=True,
            autoseparators=True,
            maxundo=-1,
            takefocus=True,
        )
        scrollbar = tk.Scrollbar(text_container, command=self.text_editor.yview)
        self.text_editor.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Đánh dấu phần chữ đã gõ dở (xám nhạt để vẫn đọc được trên nền xám đậm)
        self.text_editor.tag_configure("typed", foreground="#b0b0b0")
        # Chữ gợi ý (placeholder): giúp người dùng LUÔN thấy ô nhập,
        # kể cả khi chưa dán gì. Mọi chỗ đọc nội dung đều dùng get_content()
        # để tự loại placeholder ra.
        self._placeholder_text = (
            "Dán văn bản vào đây (Ctrl+V / Cmd+V hoặc nút \"Dán từ Clipboard\" bên trên),\n"
            "rồi bấm [BẮT ĐẦU GÕ]. Bạn có thể sửa trực tiếp trong khung này."
        )
        self._placeholder_active = False
        self.text_editor.tag_configure("placeholder", foreground="#c9c9c9")
        self._show_placeholder()

        # Cập nhật đếm ký tự với MỌI thay đổi (gõ, dán, cắt, undo...),
        # không chỉ KeyRelease như bản cũ.
        self.text_editor.bind("<KeyRelease>", self.update_char_count)
        self.text_editor.bind("<<Paste>>", self._on_text_modified)
        self.text_editor.bind("<<Cut>>", self._on_text_modified)
        self.text_editor.bind("<<Undo>>", self._on_text_modified)
        self.text_editor.bind("<<Redo>>", self._on_text_modified)
        self.text_editor.bind("<FocusIn>", self._on_editor_focus_in)
        self.text_editor.bind("<FocusOut>", self._on_editor_focus_out)
        self.text_editor.bind("<Button-1>", self._on_editor_click, add="+")
        # macOS: Cmd+A / Cmd+V / Cmd+C / Cmd+X cho ô Text
        self.text_editor.bind("<Command-a>", lambda e: (self.text_editor.tag_add("sel", "1.0", tk.END), "break")[1])
        self.text_editor.bind("<Command-A>", lambda e: (self.text_editor.tag_add("sel", "1.0", tk.END), "break")[1])
        # Menu chuột phải: Cắt / Sao chép / Dán / Chọn tất cả
        self._build_editor_context_menu()

        # Dòng thông tin số ký tự (dùng màu hệ thống để không bị tàng hình trên Tk 8.5)
        self.info_label = tk.Label(
            main,
            text="0 ký tự | 0 từ | 0 dòng",
            font=("Helvetica", 9),
            anchor="e"
        )
        self.info_label.pack(fill=tk.X, pady=(2, 8))

        # 4. Khung tùy chọn (Tốc độ & Đếm ngược)
        opts_box = tk.LabelFrame(main, text=" Cài đặt gõ ", font=("Helvetica", 10, "bold"), padx=12, pady=8)
        opts_box.pack(fill=tk.X, pady=(0, 8))

        # Tốc độ
        speed_row = tk.Frame(opts_box)
        speed_row.pack(fill=tk.X, pady=3)

        tk.Label(
            speed_row, 
            text="Tốc độ gõ (Độ trễ mỗi ký tự):", 
            font=("Helvetica", 10),
            width=26, anchor="w"
        ).pack(side=tk.LEFT)

        self.speed_scale = tk.Scale(
            speed_row, 
            from_=5, to=150, 
            orient=tk.HORIZONTAL, 
            showvalue=False,
            command=self.on_speed_change
        )
        self.speed_scale.set(35)
        self.speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        self.lbl_speed_val = tk.Label(
            speed_row, 
            text="35 ms", 
            font=("Helvetica", 10, "bold"), 
            fg="#1a73e8", 
            width=6, anchor="e"
        )
        self.lbl_speed_val.pack(side=tk.RIGHT)

        # Mô phỏng người gõ & Đếm ngược
        mode_row = tk.Frame(opts_box)
        mode_row.pack(fill=tk.X, pady=(4, 2))

        self.var_human_sim = tk.BooleanVar(value=True)
        cb_human = tk.Checkbutton(
            mode_row, 
            text="Mô phỏng người gõ thật (Tốc độ ngẫu nhiên ±15ms, nghỉ dấu câu)", 
            variable=self.var_human_sim,
            font=("Helvetica", 9)
        )
        cb_human.pack(side=tk.LEFT)

        cd_frame = tk.Frame(mode_row)
        cd_frame.pack(side=tk.RIGHT)

        tk.Label(cd_frame, text="Đếm ngược:", font=("Helvetica", 9)).pack(side=tk.LEFT, padx=(0, 4))
        self.countdown_sec = tk.IntVar(value=3)
        for sec in [1, 3, 5]:
            tk.Radiobutton(
                cd_frame,
                text=f"{sec}s",
                variable=self.countdown_sec,
                value=sec,
                font=("Helvetica", 9),
                command=self._refresh_start_text,
            ).pack(side=tk.LEFT, padx=2)

        # 5. Thanh tiến trình
        self.progress_bar = ttk.Progressbar(main, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 6))

        # 6. Dòng trạng thái
        self.status_label = tk.Label(
            main, 
            text="● Sẵn sàng: Dán văn bản vào ô xám rồi bấm [BẮT ĐẦU GÕ]", 
            font=("Helvetica", 10, "bold"), 
            fg="#2e7d32"
        )
        self.status_label.pack(pady=(0, 8))

        # 7. Hàng nút bấm điều khiển chính
        btn_bar = tk.Frame(main)
        btn_bar.pack(fill=tk.X)

        self.btn_start = tk.Button(
            btn_bar, 
            text="▶ BẮT ĐẦU GÕ (Đếm ngược 3s)", 
            font=("Helvetica", 11, "bold"), 
            bg="#2e7d32", 
            fg="black" if IS_MAC else "white", 
            padx=16, pady=8,
            command=self.start_typing_countdown,
            cursor="hand2"
        )
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.btn_reset = tk.Button(
            btn_bar, 
            text="↻ Gõ lại từ đầu", 
            font=("Helvetica", 10, "bold"), 
            padx=12, pady=8,
            command=self.reset_typing_progress,
            cursor="hand2"
        )
        self.btn_reset.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop = tk.Button(
            btn_bar, 
            text="⏹ DỪNG LẠI (Esc)", 
            font=("Helvetica", 11, "bold"), 
            bg="#c62828", 
            fg="black" if IS_MAC else "white", 
            padx=16, pady=8,
            command=self.request_stop,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.btn_stop.pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def on_speed_change(self, val):
        try:
            ms = int(float(val))
        except (TypeError, ValueError):
            ms = self.speed_scale.get()
        self.lbl_speed_val.config(text=f"{ms} ms")

    # ---------- Quản lý nội dung ô soạn thảo (placeholder + đọc/ghi an toàn) ----------

    def _show_placeholder(self):
        """Hiện chữ gợi ý mờ khi ô đang trống (ô vẫn focus & sửa được)."""
        if self.text_editor.get("1.0", "end-1c"):
            self._placeholder_active = False
            return
        self._placeholder_active = True
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert("1.0", self._placeholder_text, "placeholder")
        # Đặt con trỏ về đầu nhưng KHÔNG chọn chữ gợi ý
        self.text_editor.mark_set("insert", "1.0")

    def _hide_placeholder(self):
        """Xóa chữ gợi ý khi người dùng bắt đầu nhập/dán thật."""
        if not self._placeholder_active:
            return
        self._placeholder_active = False
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.tag_remove("placeholder", "1.0", tk.END)

    def _on_editor_focus_in(self, event=None):
        # Không xóa placeholder ngay khi focus (để user vẫn đọc được gợi ý),
        # chỉ xóa khi họ gõ ký tự đầu tiên / dán (xử lý ở _on_editor_click và paste).
        return

    def _on_editor_focus_out(self, event=None):
        if not self.text_editor.get("1.0", "end-1c").strip():
            self._show_placeholder()

    def _on_editor_click(self, event=None):
        # Click vào ô đang hiện placeholder -> xóa gợi ý để gõ ngay
        if self._placeholder_active:
            self._hide_placeholder()
            self.update_char_count()
            # chặn hành vi mặc định đặt cursor rồi mới xóa gây lệch: vẫn cho
            # click tiếp tục bình thường nên không trả về "break".
        return

    def _on_text_modified(self, event=None):
        # Chạy sau khi Tk đã dán/cắt/undo xong
        self.root.after(10, self._after_external_edit)

    def _after_external_edit(self):
        if self._placeholder_active and self.text_editor.get("1.0", "end-1c") != self._placeholder_text:
            # Người dùng vừa dán đè lên placeholder -> dọn dẹp
            content = self.text_editor.get("1.0", "end-1c")
            if self._placeholder_text in content:
                content = content.replace(self._placeholder_text, "")
                self.text_editor.delete("1.0", tk.END)
                self.text_editor.insert("1.0", content)
            self._placeholder_active = False
            self.text_editor.tag_remove("placeholder", "1.0", tk.END)
        if not self.text_editor.get("1.0", "end-1c").strip():
            self._show_placeholder()
        self.update_char_count()

    def get_content(self):
        """Nội dung THẬT để gõ (đã loại placeholder, giữ nguyên dòng trống giữa)."""
        if getattr(self, "_placeholder_active", False):
            return ""
        return self.text_editor.get("1.0", "end-1c")

    def set_content(self, text):
        """Ghi nội dung vào ô (xóa placeholder, đặt undo-separator, đếm lại)."""
        self.text_editor.delete("1.0", tk.END)
        self._placeholder_active = False
        self.text_editor.tag_remove("placeholder", "1.0", tk.END)
        if text:
            self.text_editor.insert("1.0", text)
            try:
                self.text_editor.edit_separator()
            except Exception:
                pass
            self.text_editor.mark_set("insert", tk.END)
        else:
            self._show_placeholder()
        self.text_editor.see(tk.END)
        self.update_char_count()

    def _build_editor_context_menu(self):
        menu = tk.Menu(self.text_editor, tearoff=0)
        menu.add_command(label="✂️ Cắt", command=lambda: self.text_editor.event_generate("<<Cut>>"))
        menu.add_command(label="📄 Sao chép", command=lambda: self.text_editor.event_generate("<<Copy>>"))
        menu.add_command(label="📋 Dán", command=lambda: self.text_editor.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="🔍 Chọn tất cả", command=lambda: self.text_editor.tag_add("sel", "1.0", tk.END))
        self._editor_menu = menu
        # macOS: chuột phải là Button-2, các nền khác là Button-3
        self.text_editor.bind("<Button-2>", self._popup_editor_menu, add="+")
        self.text_editor.bind("<Button-3>", self._popup_editor_menu, add="+")
        self.text_editor.bind("<Control-v>", lambda e: self.text_editor.event_generate("<<Paste>>"))
        self.text_editor.bind("<Control-a>", lambda e: (self.text_editor.tag_add("sel", "1.0", tk.END), "break")[1])

    def _popup_editor_menu(self, event):
        try:
            if self._placeholder_active:
                self._hide_placeholder()
            self._editor_menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass
        finally:
            try:
                self._editor_menu.grab_release()
            except Exception:
                pass
        return "break"

    def _start_button_text(self):
        return f"▶ BẮT ĐẦU GÕ (Đếm ngược {self.countdown_sec.get()}s)"

    def _refresh_start_text(self):
        # Chỉ đổi nhãn khi đang ở trạng thái sẵn sàng (không gõ/dừng giữa chừng)
        if not self.is_typing and not self.is_counting_down and self.current_char_index == 0:
            self.btn_start.config(text=self._start_button_text())

    def update_char_count(self, event=None):
        # Nếu đang gõ phím đầu tiên đè lên placeholder -> dọn placeholder trước
        if getattr(self, "_placeholder_active", False):
            raw = self.text_editor.get("1.0", "end-1c")
            if raw != self._placeholder_text and raw.strip():
                self._placeholder_active = False
                self.text_editor.tag_remove("placeholder", "1.0", tk.END)
            else:
                self.info_label.config(text="0 ký tự | 0 từ | 0 dòng")
                return
        content = self.get_content()
        chars = len(content)
        words = len(content.split()) if chars > 0 else 0
        lines = len(content.splitlines()) if chars > 0 else 0
        self.info_label.config(text=f"{chars} ký tự | {words} từ | {lines} dòng")

    def clear_text(self):
        self.set_content("")
        self.reset_typing_progress()
        self.text_editor.focus_set()
        self.set_status("Đã xóa toàn bộ nội dung trong ô.", "#5f6368")

    def _read_system_clipboard(self):
        """Đọc clipboard: thử Tk trước, macOS fallback sang `pbpaste`."""
        try:
            text = self.root.clipboard_get()
            if text:
                return text
        except Exception:
            pass
        if IS_MAC:
            try:
                import subprocess
                out = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
                if out.returncode == 0 and out.stdout:
                    return out.stdout
            except Exception:
                pass
        return ""

    def paste_from_clipboard(self):
        try:
            clipboard_text = self._read_system_clipboard()
            if not clipboard_text.strip():
                messagebox.showwarning("Thông báo", "Bộ nhớ tạm (Clipboard) hiện không có văn bản!")
                return
            self.set_content(clipboard_text)
            self.reset_typing_progress()
            self.text_editor.focus_set()
            self.set_status("Đã dán văn bản từ clipboard — bạn có thể sửa trực tiếp trong khung!", "#1a73e8")
        except Exception:
            messagebox.showwarning("Thông báo", "Không thể lấy nội dung từ Clipboard!")

    def reset_typing_progress(self):
        """Đặt lại tiến trình để gõ lại từ ký tự đầu tiên"""
        self.current_char_index = 0
        self.progress_bar.config(value=0)
        self.text_editor.tag_remove("typed", "1.0", tk.END)
        self.btn_start.config(text=self._start_button_text())
        self.set_status("Đã đặt lại: Sẵn sàng gõ từ đầu!", "#2e7d32")

    def set_status(self, text, color=None):
        self.status_label.config(text=f"● {text}")
        if color:
            self.status_label.config(fg=color)

    def start_typing_countdown(self):
        """Bắt đầu quy trình đếm ngược trước khi gõ"""
        if self.is_typing or self.is_counting_down:
            return

        if IS_MAC and not is_mac_accessibility_granted():
            if messagebox.askyesno(
                "Cấp quyền Trợ năng trên macOS", 
                "macOS cần quyền Trợ năng (Accessibility) để cho phép tự động gõ vào các ứng dụng khác (Word, Google Docs, Remote Desktop...).\n\nBạn có muốn mở Cài đặt hệ thống để cấp quyền ngay không?"
            ):
                open_mac_accessibility_settings()
            return

        content = self.get_content()
        if not content.strip():
            messagebox.showwarning("Văn bản trống", "Vui lòng nhập hoặc dán nội dung vào ô màu xám trước khi bắt đầu!")
            return

        self.is_counting_down = True
        self.stop_requested = False
        self.btn_start.config(state=tk.DISABLED)
        self.btn_reset.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        delay = self.countdown_sec.get()
        threading.Thread(target=self._countdown_worker, args=(delay,), daemon=True).start()

    def _countdown_worker(self, seconds_left):
        action_name = "tiếp tục gõ" if self.current_char_index > 0 else "gõ"
        for s in range(seconds_left, 0, -1):
            if self.stop_requested:
                self.is_counting_down = False
                self.root.after(0, self._on_stopped)
                return
            msg = f"ĐANG ĐẾM NGƯỢC: {s} giây (Hãy click chuột vào ô cần {action_name} trên Word/Docs/Remote)..."
            self.root.after(0, lambda m=msg: self.set_status(m, "#e65100"))
            time.sleep(1)

        self.is_counting_down = False
        if not self.stop_requested:
            # Chờ app đích nhận focus ổn định rồi mới gõ, tránh mất ký tự
            # ĐẦU TIÊN khi người dùng click chuột vào ô đích hơi muộn.
            time.sleep(0.4)
            self.root.after(0, self._start_typing_process)

    def _start_typing_process(self):
        """Khởi chạy luồng gõ văn bản từ vị trí hiện tại"""
        content = self.get_content()
        total_len = len(content)
        if not content or self.current_char_index >= total_len:
            self._on_finished()
            return

        self.is_typing = True
        self.stop_requested = False
        self.btn_start.config(state=tk.DISABLED)
        self.btn_reset.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        base_delay_ms = self.speed_scale.get()
        is_human = self.var_human_sim.get()

        threading.Thread(
            target=self._typing_worker, 
            args=(content, base_delay_ms, is_human), 
            daemon=True
        ).start()

    def _typing_worker(self, content, base_delay_ms, is_human):
        total_len = len(content)
        self.root.after(0, lambda: self.progress_bar.configure(maximum=total_len, value=self.current_char_index))

        start_idx = self.current_char_index

        for idx in range(start_idx, total_len):
            if self.stop_requested:
                break

            char = content[idx]

            # Thực hiện gõ ký tự
            self.send_char(char)
            self.current_char_index = idx + 1

            # Cập nhật UI
            if idx % 5 == 0 or idx == total_len - 1 or idx == start_idx:
                cur_val = self.current_char_index
                percent = int((cur_val / total_len) * 100)
                msg = f"Đang gõ: {cur_val}/{total_len} ký tự ({percent}%) - Ấn Esc để dừng"
                self.root.after(0, lambda v=cur_val, m=msg: self._update_progress(v, m))

            # Độ trễ (delay)
            delay = base_delay_ms / 1000.0
            if is_human:
                variation = random.uniform(-0.015, 0.025)
                delay = max(0.005, delay + variation)
                if char in [".", "!", "?", "\n"]:
                    delay += random.uniform(0.08, 0.18)

            time.sleep(delay)

            # Sau ký tự xuống dòng: app đích (Word/Docs/web/chat/remote/IME
            # tiếng Việt...) cần thời gian xuống dòng + ổn định con trỏ.
            # Nghỉ thêm để ký tự ĐẦU DÒNG KẾ TIẾP không bị nuốt mất.
            # Luôn áp dụng kể cả khi tắt "mô phỏng người gõ".
            if char == "\n":
                time.sleep(0.15)

        self.is_typing = False
        if self.stop_requested:
            self.root.after(0, self._on_stopped)
        else:
            self.root.after(0, self._on_finished)

    def _update_progress(self, val, msg):
        self.progress_bar.config(value=val)
        self.set_status(msg, "#1a73e8")
        # Đánh dấu phần chữ đã gõ xong
        self.text_editor.tag_remove("typed", "1.0", tk.END)
        self.text_editor.tag_add("typed", "1.0", f"1.0 + {val} chars")

    def _on_finished(self):
        self.is_typing = False
        self.is_counting_down = False
        self.current_char_index = 0
        self.btn_start.config(state=tk.NORMAL, text=self._start_button_text())
        self.btn_reset.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.progress_bar.config(value=self.progress_bar['maximum'])
        self.text_editor.tag_remove("typed", "1.0", tk.END)
        self.set_status("✔ ĐÃ HOÀN THÀNH gõ toàn bộ văn bản!", "#2e7d32")

    def _on_stopped(self):
        self.is_typing = False
        self.is_counting_down = False
        self.btn_start.config(state=tk.NORMAL, text=f"▶ TIẾP TỤC GÕ (từ ký tự {self.current_char_index + 1})")
        self.btn_reset.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.set_status(f"⏹ ĐÃ TẠM DỪNG tại ký tự {self.current_char_index}. Bấm Tiếp tục gõ để chạy tiếp.", "#c62828")

    def request_stop(self):
        """Yêu cầu dừng khẩn cấp"""
        self.stop_requested = True

    def send_char(self, char):
        """Hàm trừu tượng gửi 1 ký tự dựa theo hệ điều hành"""
        try:
            if IS_WINDOWS:
                if char == "\n":
                    send_key_win(vk_code=VK_RETURN)
                elif char == "\t":
                    send_key_win(vk_code=0x09)
                else:
                    send_key_win(char_unicode=char)
            elif IS_MAC:
                send_char_mac(char)
        except Exception as e:
            safe_print(f"Lỗi khi gửi ký tự '{char}': {e}")

    def start_hotkey_listener(self):
        """Lắng nghe phím tắt toàn cục trong một luồng riêng biệt"""
        if IS_WINDOWS:
            def win_listener():
                last_enter_state = False
                while True:
                    try:
                        if user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
                            if self.is_typing or self.is_counting_down:
                                self.request_stop()
                                time.sleep(0.3)

                        ctrl_pressed = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                        shift_pressed = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
                        enter_pressed = bool(user32.GetAsyncKeyState(VK_RETURN) & 0x8000)

                        if ctrl_pressed and shift_pressed and enter_pressed:
                            if not last_enter_state:
                                last_enter_state = True
                                if not self.is_typing and not self.is_counting_down:
                                    # Đi qua countdown (có kiểm tra văn bản trống/quyền)
                                    # thay vì gõ ngay như bản cũ.
                                    self.root.after(0, self.start_typing_countdown)
                        else:
                            last_enter_state = False

                        time.sleep(0.02)
                    except Exception:
                        time.sleep(0.1)

            threading.Thread(target=win_listener, daemon=True).start()

        elif IS_MAC:
            self.root.bind("<Control-Shift-Return>", lambda e: self.start_typing_countdown(), add="+")
            self.root.bind("<Command-Shift-Return>", lambda e: self.start_typing_countdown(), add="+")
            self.root.bind("<Escape>", lambda e: self.request_stop(), add="+")


def is_system_tk_broken():
    """Tk 8.5 đi kèm hệ thống không vẽ được chữ (Label/Text/Scale/Progressbar...)
    trên macOS mới — chỉ nút bấm hiện, còn lại trắng trơn. Tk >= 8.6 thì bình thường."""
    try:
        return bool(IS_MAC) and float(tk.TkVersion) < 8.6
    except Exception:
        return False


def print_tk_warning():
    safe_print("=" * 70, flush=True)
    safe_print("CANH BAO: Python hien tai dung Tk 8.5 cua he thong.", flush=True)
    safe_print("Tk 8.5 KHONG ve duoc chu tren macOS nay: o soan thao, cac nhan,", flush=True)
    safe_print("thanh toc do... se TRANG TRON (chi nut bam hien). Day la loi cua", flush=True)
    safe_print("thu vien Tk he thong, KHONG phai loi code cua app.", flush=True)
    safe_print("", flush=True)
    safe_print("FIX TRIET DE (1 lenh, giu nguyen app):", flush=True)
    safe_print("    brew install python@3.12", flush=True)
    safe_print("roi chay app bang Python moi:", flush=True)
    safe_print("    /opt/homebrew/bin/python3 auto_typer.py", flush=True)
    safe_print("=" * 70, flush=True)


def main():
    safe_print(f"AutoTyper dang chay build: {BUILD_TAG} | Tk {tk.TkVersion}", flush=True)
    if is_system_tk_broken():
        print_tk_warning()
    root = tk.Tk()
    app = AutoTyperApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
