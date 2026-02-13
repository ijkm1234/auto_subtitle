import ctypes
import json
from ctypes import wintypes
import threading
import time
import sys

import numpy as np
from sympy.strategies.core import switch
from win32con import DT_WORDBREAK

# --- Constants ---
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000

LWA_ALPHA = 0x00000002
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01

WM_DESTROY = 0x0002
WM_NCHITTEST = 0x0084
WM_LBUTTONDOWN = 0x0201
WM_NCLBUTTONDOWN  = 0x00A1
WM_MOVING = 0x0216
WM_EXITSIZEMOVE = 0x0232
WM_TIMER = 0x0113
WM_USER = 0x0400
WM_APP = 0x8000

HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOREDRAW = 0x0008
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_HIDEWINDOW = 0x0080

HTCAPTION = 2
HTCLIENT = 1
HTTRANSPARENT = -1

FW_BOLD = 700
ANSI_CHARSET = 0
OUT_DEFAULT_PRECIS = 0
CLIP_DEFAULT_PRECIS = 0
DEFAULT_QUALITY = 0
NONANTIALIASED_QUALITY = 3
ANTIALIASED_QUALITY = 4
DEFAULT_PITCH = 0
FF_DONTCARE = 0

DT_CENTER = 0x00000001
DT_VCENTER = 0x00000004
DT_SINGLELINE = 0x00000020
DT_CALCRECT = 0x00000400

BI_RGB = 0
DIB_RGB_COLORS = 0

# --- Types & Compat ---
# Determine 32 vs 64 bit
IS_64_BIT = ctypes.sizeof(ctypes.c_void_p) == 8

if IS_64_BIT:
    ULONG_PTR = ctypes.c_uint64
    LONG_PTR = ctypes.c_int64
else:
    ULONG_PTR = ctypes.c_uint32
    LONG_PTR = ctypes.c_int32

HANDLE = ctypes.c_void_p
HWND = HANDLE
HDC = HANDLE
HBITMAP = HANDLE
HFONT = HANDLE
HBRUSH = HANDLE
HCURSOR = HANDLE
HICON = HANDLE
HINSTANCE = HANDLE
HMENU = HANDLE

WPARAM = ULONG_PTR
LPARAM = LONG_PTR
LRESULT = LONG_PTR


# --- Structs ---
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte),
        ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_byte),
        ("AlphaFormat", ctypes.c_byte),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wintypes.DWORD * 3)]


# --- Libraries ---
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# --- Function Prototypes (Argtypes/Restypes) ---
# Define WNDPROC signature
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, HWND, ctypes.c_uint, WPARAM, LPARAM)


class WNDCLASSEX(ctypes.Structure):
    _fields_ = [
        ('cbSize', ctypes.c_uint),
        ('style', ctypes.c_uint),
        ('lpfnWndProc', WNDPROC),
        ('cbClsExtra', ctypes.c_int),
        ('cbWndExtra', ctypes.c_int),
        ('hInstance', HINSTANCE),
        ('hIcon', HICON),
        ('hCursor', HCURSOR),
        ('hbrBackground', HBRUSH),
        ('lpszMenuName', ctypes.c_wchar_p),
        ('lpszClassName', ctypes.c_wchar_p),
        ('hIconSm', HICON)
    ]


# user32 definitions
user32.DefWindowProcW.argtypes = [HWND, ctypes.c_uint, WPARAM, LPARAM]
user32.DefWindowProcW.restype = LRESULT

user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEX)]
user32.RegisterClassExW.restype = ctypes.c_uint16

user32.CreateWindowExW.argtypes = [
    ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    HWND, HMENU, HINSTANCE, ctypes.c_void_p
]
user32.CreateWindowExW.restype = HWND

user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), HWND, ctypes.c_uint, ctypes.c_uint]
user32.GetMessageW.restype = wintypes.BOOL

user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = LRESULT

user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None

user32.PostMessageW.argtypes = [HWND, ctypes.c_uint, WPARAM, LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL

user32.SetWindowPos.argtypes = [HWND, HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.SetWindowPos.restype = wintypes.BOOL

user32.SetTimer.argtypes = [HWND, ULONG_PTR, ctypes.c_uint, ctypes.c_void_p]
user32.SetTimer.restype = ULONG_PTR

user32.UpdateLayeredWindow.argtypes = [
    HWND, HDC, ctypes.POINTER(POINT), ctypes.POINTER(SIZE),
    HDC, ctypes.POINTER(POINT), ctypes.c_uint, ctypes.POINTER(BLENDFUNCTION), ctypes.c_uint
]
user32.UpdateLayeredWindow.restype = wintypes.BOOL

user32.ScreenToClient.argtypes = [HWND, ctypes.POINTER(POINT)]
user32.ScreenToClient.restype = wintypes.BOOL

user32.LoadCursorW.argtypes = [HINSTANCE, ctypes.c_void_p]  # Using c_void_p for resource ID
user32.LoadCursorW.restype = HCURSOR

user32.GetDC.argtypes = [HWND]
user32.GetDC.restype = HDC

user32.ReleaseDC.argtypes = [HWND, HDC]
user32.ReleaseDC.restype = ctypes.c_int

user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

user32.FillRect.argtypes = [HDC, ctypes.POINTER(RECT), HBRUSH]
user32.FillRect.restype = ctypes.c_int

user32.DrawTextW.argtypes = [HDC, ctypes.c_wchar_p, ctypes.c_int, ctypes.POINTER(RECT), ctypes.c_uint]
user32.DrawTextW.restype = ctypes.c_int

gdi32.CreateSolidBrush.argtypes = [ctypes.c_uint]
gdi32.CreateSolidBrush.restype = HBRUSH

# gdi32 definitions
gdi32.CreateCompatibleDC.argtypes = [HDC]
gdi32.CreateCompatibleDC.restype = HDC

gdi32.DeleteDC.argtypes = [HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

gdi32.DeleteObject.argtypes = [HANDLE]
gdi32.DeleteObject.restype = wintypes.BOOL

gdi32.SelectObject.argtypes = [HDC, HANDLE]
gdi32.SelectObject.restype = HANDLE

gdi32.CreateFontW.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
    ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_wchar_p
]
gdi32.CreateFontW.restype = HFONT

gdi32.GetTextExtentPoint32W.argtypes = [HDC, ctypes.c_wchar_p, ctypes.c_int, ctypes.POINTER(SIZE)]
gdi32.GetTextExtentPoint32W.restype = wintypes.BOOL

gdi32.CreateDIBSection.argtypes = [HDC, ctypes.POINTER(BITMAPINFO), ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p),
                                   HANDLE, ctypes.c_uint]
gdi32.CreateDIBSection.restype = HBITMAP

gdi32.SetBkMode.argtypes = [HDC, ctypes.c_int]
gdi32.SetBkMode.restype = ctypes.c_int

gdi32.SetTextColor.argtypes = [HDC, ctypes.c_uint]
gdi32.SetTextColor.restype = ctypes.c_uint

gdi32.GetDeviceCaps.argtypes = [HDC, ctypes.c_int]
gdi32.GetDeviceCaps.restype = ctypes.c_int


# --- Class Implementation ---

class SubtitleRect:
    _window_cls_name = "SubtitleRectClass"
    _class_registered = False

    BTN_KEY_HIDDEN='hidden'
    BTN_KEY_DRAG= 'drag'

    def __init__(self, font_size=24,x=200,y=200):
        self.hwnd = None
        self.texts = []
        self.pos_x = x
        self.pos_y = y
        self.font_size = font_size
        self.padding_x = 10
        self.padding_y = 5
        self.lock = threading.Lock()
        self.text_items = []  # List of RECT relative to window
        self.win_width = 0
        self.win_height = 0
        self.subtitle_visible = True  # 字幕可见状态
        self.button_font_size = 10
        self.button_items = []  # 按钮位置

        # Keep references to prevent GC
        self._wnd_proc_cb = WNDPROC(self._wnd_proc)

        self.thread = threading.Thread(target=self._run_thread, daemon=True)
        self.thread.start()

        # Wait for window creation
        start = time.time()
        while not self.hwnd and time.time() - start < 5:
            time.sleep(0.01)

    def draw(self, texts):
        t = texts[:]
        t.reverse()
        self.texts=t
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_APP + 1, 0, 0)

    def clean(self):
        self.texts = []
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_APP + 1, 0, 0)

    def _run_thread(self):
        try:
            self._create_window()
            self._message_loop()
        except Exception as e:
            print(f"Error in SubtitleRect thread: {e}")

    def _create_window(self):
        hinst = kernel32.GetModuleHandleW(None)
        if not SubtitleRect._class_registered:
            wc = WNDCLASSEX()
            wc.cbSize = ctypes.sizeof(WNDCLASSEX)
            wc.lpfnWndProc = self._wnd_proc_cb  # Use the bound callback
            wc.hInstance = hinst
            wc.lpszClassName = SubtitleRect._window_cls_name
            wc.hCursor = user32.LoadCursorW(None, ctypes.c_void_p(32512))  # IDC_ARROW

            if not user32.RegisterClassExW(ctypes.byref(wc)):
                err = kernel32.GetLastError()
                # 1410 = Class already exists
                if err != 1410:
                    print(f"RegisterClassExW failed: {err}")
            SubtitleRect._class_registered = True

        self.hwnd = user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            SubtitleRect._window_cls_name,
            "SubtitleRect",
            WS_POPUP | WS_VISIBLE,
            0, 0, 0, 0,
            None, None, hinst, None
        )

        if not self.hwnd:
            print(f"CreateWindowExW failed: {kernel32.GetLastError()}")

        # Set a timer to reinforce TopMost (100ms interval)
        user32.SetTimer(self.hwnd, 1, 100, None)

    def _message_loop(self):
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _wnd_proc(self, hwnd, msg, wParam, lParam):
        try:
            if msg == WM_APP + 1:
                self._update_layered_window()
                return 0
            elif msg == WM_NCHITTEST:
                return self._handle_nchittest(lParam)
            elif msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            elif msg == WM_EXITSIZEMOVE:
                self._handle_move_end()
                return 0
            elif msg==WM_MOVING:
                return self._handle_moving(lParam)
            elif msg == WM_TIMER:
                user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOREDRAW)
                return 0
            elif msg == WM_NCLBUTTONDOWN:
                x = ctypes.c_short(lParam & 0xFFFF).value
                y = ctypes.c_short((lParam >> 16) & 0xFFFF).value
                pt = POINT(x, y)
                user32.ScreenToClient(self.hwnd, ctypes.byref(pt))
                btn_key=self._in_button(pt.x, pt.y)
                if btn_key==self.BTN_KEY_HIDDEN:
                    self.subtitle_visible = not self.subtitle_visible
                    self._update_layered_window()
                    return 0

            return user32.DefWindowProcW(hwnd, msg, wParam, lParam)
        except Exception as e:
            print(f"Error in WndProc: {e}")
            return user32.DefWindowProcW(hwnd, msg, wParam, lParam)

    def _handle_nchittest(self, lParam):
        # lParam is 64-bit on x64, packed x,y
        # Use simple bit masking for unsigned, then cast to short for signed
        x = ctypes.c_short(lParam & 0xFFFF).value
        y = ctypes.c_short((lParam >> 16) & 0xFFFF).value

        pt = POINT(x, y)
        user32.ScreenToClient(self.hwnd, ctypes.byref(pt))

        with self.lock:
            if self._in_button(pt.x, pt.y):
                return HTCAPTION

        return HTTRANSPARENT

    def _wrap_text(self, hdc, text, max_width):
        if not text:
            return []
        
        import re
        
        # 只调用两次GDI：分别计算半角和全角字符宽度
        half_size = SIZE()
        full_size = SIZE()
        gdi32.GetTextExtentPoint32W(hdc, "a", 1, ctypes.byref(half_size))
        gdi32.GetTextExtentPoint32W(hdc, "中", 1, ctypes.byref(full_size))
        half_width = half_size.cx
        full_width = full_size.cx
        
        def calc_text_width(s):
            """根据字符类型计算文本宽度"""
            width = 0
            for char in s:
                if ord(char) < 128:  # 半角字符 (ASCII)
                    width += half_width
                else:  # 全角字符
                    width += full_width
            return width

        tokens = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+|[^\u4e00-\u9fff\s\w]|\s', text)

        wrapped_lines = []
        current_line = ""
        current_width = 0
        
        for token in tokens:
            token_width = calc_text_width(token)
            
            # 检查添加这个token后是否超过最大宽度
            # 注意：如果不是第一个token，需要加一个半角空格宽度
            new_width = current_width + token_width
            
            if new_width + self.padding_x * 2 <= max_width:
                # 可以添加到当前行
                if current_line:
                    current_line += token
                else:
                    current_line = token
                current_width = new_width
            else:
                # 当前行已满，保存并开始新行
                if current_line:
                    wrapped_lines.append(current_line)
                current_line = token
                current_width = token_width
        
        # 添加最后一行
        if current_line:
            wrapped_lines.append(current_line)
        wrapped_lines.reverse()
        return wrapped_lines

    def _update_layered_window(self):
        start=time.time()
        texts = self.texts[:]
        if not texts:
            user32.SetWindowPos(self.hwnd, 0, 0, 0, 0, 0, SWP_HIDEWINDOW)
            return

        # 1. Measure texts
        hdc = user32.GetDC(self.hwnd)
        mem_dc = gdi32.CreateCompatibleDC(hdc)

        # Create Font
        font_height = -int(self.font_size * gdi32.GetDeviceCaps(hdc, 90) / 72)
        hfont = gdi32.CreateFontW(font_height, 0, 0, 0, FW_BOLD, 0, 0, 0,
                                  ANSI_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                                  NONANTIALIASED_QUALITY, DEFAULT_PITCH | FF_DONTCARE, "Cambria")
        # Create button font
        button_font_height = -int(self.button_font_size * gdi32.GetDeviceCaps(hdc, 90) / 72)
        button_hfont = gdi32.CreateFontW(button_font_height, 0, 0, 0, FW_BOLD, 0, 0, 0,
                                         ANSI_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                                         NONANTIALIASED_QUALITY, DEFAULT_PITCH | FF_DONTCARE, "Cambria")

        old_font = gdi32.SelectObject(mem_dc, hfont)

        # Get screen width for text wrapping
        screen_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        max_text_width = screen_width - 100  # Leave some margin

        # Wrap long texts
        wrapped_texts = []
        if self.subtitle_visible:
            for text in texts:
                wrapped_lines = self._wrap_text(mem_dc, text, max_text_width)
                wrapped_texts.extend(wrapped_lines)

        button_infos = [
            {
                'key': self.BTN_KEY_DRAG,
                'text': '✥'
            },
            {
                'key': self.BTN_KEY_HIDDEN,
                'text': '隐藏' if self.subtitle_visible else '显示'
            }
        ]

        lines_info = []
        total_w = 0
        total_h = 0

        max_text=''
        for text in wrapped_texts:
            size = SIZE()
            gdi32.GetTextExtentPoint32W(mem_dc, text, len(text), ctypes.byref(size))
            w = size.cx + self.padding_x * 2
            h = size.cy + self.padding_y * 2
            lines_info.append({'text': text, 'w': w, 'h': h})
            total_w = max(total_w, w)
            total_h += h

        old_button_font = gdi32.SelectObject(mem_dc, button_hfont)
        btns_width = 0
        btns_height = 0
        for btn in button_infos:
            size = SIZE()
            gdi32.GetTextExtentPoint32W(mem_dc, btn['text'], len(btn['text']), ctypes.byref(size))
            button_width = size.cx + self.padding_x * 2
            button_height = size.cy + self.padding_y * 2
            btn['w'] = button_width
            btn['h'] = button_height
            btns_width += button_width + self.padding_x
            btns_height = max(btns_height, button_height)
        gdi32.SelectObject(mem_dc, old_button_font)

        if len(button_infos) > 0:
            btns_width -= self.padding_x
        total_w = max(total_w, btns_width)
        total_h += btns_height

        # 2. Create DIB
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = total_w
        bmi.bmiHeader.biHeight = -total_h  # Top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        bits = ctypes.c_void_p()
        hbitmap = gdi32.CreateDIBSection(mem_dc, ctypes.byref(bmi), DIB_RGB_COLORS, ctypes.byref(bits), None, 0)
        old_bitmap = gdi32.SelectObject(mem_dc, hbitmap)
        # 3. Draw

        # Calculate layout
        new_text_items = []
        y_cursor = total_h - btns_height
        for i, info in enumerate(wrapped_texts):
            w = lines_info[i]['w']
            h = lines_info[i]['h']

            y = y_cursor - h
            x = (total_w - w) // 2
            r = RECT(x, y, x + w, y + h)
            text_item = {'rect': r, 'text': wrapped_texts[i], 'rect_type': 'text'}
            new_text_items.append(text_item)
            y_cursor -= h

        btn_y = total_h - btns_height
        btn_x = (total_w - btns_width) // 2
        btn_items = []
        for btn in button_infos:
            # 添加按钮
            button_width = btn['w']
            button_height = btn['h']
            button_rect = RECT(btn_x, btn_y, btn_x + button_width, btn_y + button_height)
            btn_item = {
                'rect': button_rect,
                'text': btn['text'],
                'rect_type': 'button',
                'btn_key': btn['key']
            }
            btn_items.append(btn_item)
            btn_x += button_width + self.padding_x

        # Draw Backgrounds & Text
        gdi32.SetBkMode(mem_dc, 1)  # TRANSPARENT
        gdi32.SetTextColor(mem_dc, 0xFFFFFF)  # RGB(255,255,255)

        # Prepare pointer to bits
        n_pixels = total_w * total_h
        p_pixels = ctypes.cast(bits, ctypes.POINTER(ctypes.c_uint32 * n_pixels))
        pixel_arr = p_pixels.contents

        bg_color = 0x000000
        brush = gdi32.CreateSolidBrush(bg_color)

        for item in new_text_items:
            r = item['rect']
            user32.FillRect(mem_dc, ctypes.byref(r), brush)
            user32.DrawTextW(mem_dc, item['text'], -1, ctypes.byref(r), DT_CENTER | DT_VCENTER | DT_SINGLELINE)

        old_button_font = gdi32.SelectObject(mem_dc, button_hfont)
        for item in btn_items:
            r = item['rect']
            user32.FillRect(mem_dc, ctypes.byref(r), brush)
            user32.DrawTextW(mem_dc, item['text'], -1, ctypes.byref(r), DT_CENTER | DT_VCENTER | DT_SINGLELINE)
        gdi32.SelectObject(mem_dc, old_button_font)

        gdi32.DeleteObject(brush)
        gdi32.DeleteObject(button_hfont)
        # Fix Alpha Channel - 使用NumPy向量化优化
        width = total_w
        # 将ctypes数组转换为numpy数组（零拷贝）
        pixel_np = np.ctypeslib.as_array(pixel_arr)
        draw_items=[]
        draw_items.extend(new_text_items)
        draw_items.extend(btn_items)

        for item in draw_items:
            r = item['rect']
            # 提取矩形区域
            top, bottom = r.top, r.bottom
            left, right = r.left, r.right

            # 计算切片索引
            row_starts = np.arange(top, bottom) * width
            # 创建二维索引网格
            indices = row_starts[:, np.newaxis] + np.arange(left, right)

            # 获取当前区域的像素值
            vals = pixel_np[indices.ravel()]

            # 向量化条件处理
            is_white = (vals & 0x00FFFFFF) == 0x00FFFFFF

            # 预计算alpha值
            alpha_val = 0xAA000000 if item['rect_type'] == 'button' else 0x80000000

            # 向量化赋值
            pixel_np[indices.ravel()] = np.where(
                is_white,
                0xFFFFFFFF,
                vals | alpha_val
            )
        with self.lock:
            self.text_items = new_text_items
            self.button_items = btn_items
            self.win_width = total_w
            self.win_height = total_h
            # 4. UpdateLayeredWindow
            pos_x, pos_y = self.pos_x, self.pos_y
            win_x = pos_x - self.win_width//2
            win_y = pos_y - self.win_height

            ptSrc = POINT(0, 0)
            ptDst = POINT(win_x, win_y)
            wsize = SIZE(total_w, total_h)
            blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)

            user32.UpdateLayeredWindow(self.hwnd, 0, ctypes.byref(ptDst), ctypes.byref(wsize),
                                       mem_dc, ctypes.byref(ptSrc), 0, ctypes.byref(blend), ULW_ALPHA)

            # Force TopMost immediately after update and ensure window is shown
            user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOREDRAW | SWP_SHOWWINDOW)

        # Cleanup
        gdi32.SelectObject(mem_dc, old_bitmap)
        gdi32.SelectObject(mem_dc, old_font)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteObject(hfont)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(self.hwnd, hdc)
        print(f'_update_layered_window end : {self.pos_x}, {self.pos_y} {win_x}, {win_y} elapse {time.time()-start}')


    def _in_button(self,x,y):
        for item in self.button_items:
            rect = item['rect']
            if rect.left <= x <= rect.right and rect.top <= y <= rect.bottom:
                return item['btn_key']
        return ''

    def _handle_move_end(self):
        with self.lock:
            rect = RECT()
            user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
            new_pos_x = rect.left + self.win_width//2
            new_pos_y = rect.top + self.win_height
            self.pos_x = new_pos_x
            self.pos_y = new_pos_y

    def _handle_moving(self, lParam):
        with self.lock:
            rect_ptr = ctypes.cast(lParam, ctypes.POINTER(RECT))
            rect = rect_ptr.contents
            rect_w=rect.right-rect.left
            rect_h=rect.bottom-rect.top

            self.pos_x = rect.left+rect_w//2
            self.pos_y = rect.top+rect_h
            rect.left=self.pos_x-self.win_width//2
            rect.top=self.pos_y-self.win_height
            rect.right=rect.left+self.win_width
            rect.bottom=rect.top+self.win_height
            return 1


if __name__ == "__main__":
    # Test
    rect = SubtitleRect()
    texts=[
        ['111'],
        ['111','222222'],
        ['111','2222222222222222222222222222222','333']
        ]
    i=0
    rect.draw(texts[i])
    while True:
        rect.draw(texts[i%len(texts)])
        i+=1
        time.sleep(1)