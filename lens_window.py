#!/usr/bin/env python3
"""Pure Win32 layered window for real-time descrambling. No Qt."""
import math
import gc
import logging
import ctypes
from ctypes import wintypes
import numpy as np
import cv2
from seed import Seed
from scrambler import descramble_image

logger = logging.getLogger(__name__)

# Optional high-performance screen capture using mss (Windows DXGI)
try:
    import mss
    _MSS_AVAILABLE = True
except Exception:
    _MSS_AVAILABLE = False

# ------------------------------------------------------------------
# Win32 module handles
# ------------------------------------------------------------------
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# ------------------------------------------------------------------
# Win32 constants
# ------------------------------------------------------------------
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_TIMER = 0x0113
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_MOUSEMOVE = 0x0200
WM_RBUTTONUP = 0x0205
WM_KEYDOWN = 0x0100
WM_COMMAND = 0x0111
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_OEM_PLUS = 0xBB
VK_OEM_MINUS = 0xBD
MK_LBUTTON = 0x0001
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
CS_DBLCLKS = 0x0008
WM_HOTKEY = 0x0312
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_DONOTROUND = 1
WDA_EXCLUDEFROMCAPTURE = 0x11
AC_SRC_OVER = 0
AC_SRC_ALPHA = 1
ULW_ALPHA = 0x00000002
BI_RGB = 0
TPM_RIGHTBUTTON = 0x0002

# ------------------------------------------------------------------
# Win32 structures
# ------------------------------------------------------------------
class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]

class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", wintypes.BYTE),
        ("BlendFlags", wintypes.BYTE),
        ("SourceConstantAlpha", wintypes.BYTE),
        ("AlphaFormat", wintypes.BYTE),
    ]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]

# ------------------------------------------------------------------
# Win32 function signatures (x64 safety)
# ------------------------------------------------------------------
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_longlong

user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wintypes.ATOM

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
    wintypes.DWORD, wintypes.INT, wintypes.INT, wintypes.INT, wintypes.INT,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND,
    wintypes.INT, wintypes.INT, wintypes.INT, wintypes.INT,
    wintypes.UINT
]
user32.SetWindowPos.restype = wintypes.BOOL

user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND, wintypes.HDC,
    ctypes.POINTER(wintypes.POINT), ctypes.POINTER(wintypes.SIZE),
    wintypes.HDC, ctypes.POINTER(wintypes.POINT),
    wintypes.COLORREF, ctypes.POINTER(BLENDFUNCTION), wintypes.DWORD
]
user32.UpdateLayeredWindow.restype = wintypes.BOOL

# ------------------------------------------------------------------
# Helper macros
# ------------------------------------------------------------------
def GET_X_LPARAM(lp):
    return ctypes.c_int16(lp & 0xFFFF).value

def GET_Y_LPARAM(lp):
    return ctypes.c_int16((lp >> 16) & 0xFFFF).value

# ------------------------------------------------------------------
# WNDPROC storage (prevents GC of the ctypes callback)
# ------------------------------------------------------------------
_WNDPROC_REF = None

# ------------------------------------------------------------------
# LensWindow
# ------------------------------------------------------------------
class LensWindow:
    _class_registered = False
    _class_name = "RealTimeMixLens"

    def __init__(self):
        logger.info("LensWindow init")
        self.seed: Seed | None = None
        self._hwnd = None
        self._timer_id = 1
        self._mss = None
        if _MSS_AVAILABLE:
            try:
                self._mss = mss.mss()
                logger.info("mss initialized")
            except Exception as e:
                logger.warning("mss init failed: %s", e)

        # Callbacks to MainWindow
        self.on_close = None
        self.on_size_changed = None

        # Drag / resize state
        self._dragging = False
        self._resizing = False
        self._resize_dir = None
        self._drag_start_mouse = (0, 0)
        self._drag_start_win = (0, 0, 0, 0)
        self._resize_start_mouse = (0, 0)
        self._resize_start_rect = (0, 0, 0, 0)
        self._resize_margin = 16

        # Display state
        self._pending_phys_size = None
        self._hdc_mem = None
        self._hbmp = None
        self._hbmp_old = None
        self._dib_bits = None
        self._last_blend_w = 0
        self._last_blend_h = 0

        self.border_phase = 0.0
        self.frame_count = 0
        self._use_display_affinity = False

        self._ensure_class()
        self._create_window()
        logger.info("LensWindow init done")

    # ------------------------------------------------------------------
    # Window class / creation
    # ------------------------------------------------------------------
    def _ensure_class(self):
        if LensWindow._class_registered:
            return
        inst = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.style = CS_DBLCLKS
        wc.lpfnWndProc = ctypes.cast(self._wndproc_cfunc(), ctypes.c_void_p)
        wc.hInstance = inst
        wc.hCursor = ctypes.windll.user32.LoadCursorW(0, 32512)  # IDC_ARROW
        wc.hbrBackground = 0
        wc.lpszClassName = LensWindow._class_name
        if ctypes.windll.user32.RegisterClassExW(ctypes.byref(wc)) == 0:
            err = ctypes.windll.kernel32.GetLastError()
            raise RuntimeError(f"RegisterClassExW failed: {err}")
        LensWindow._class_registered = True
        logger.info("Window class registered")

    def _wndproc_cfunc(self):
        global _WNDPROC_REF
        if _WNDPROC_REF is None:
            _WNDPROC_REF = ctypes.WINFUNCTYPE(
                ctypes.c_longlong,
                wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
            )(self._wndproc)
        return _WNDPROC_REF

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_DESTROY:
            if self.on_close:
                try:
                    self.on_close()
                except Exception:
                    logger.exception("on_close callback failed")
            return 0
        if msg == WM_TIMER and wparam == self._timer_id:
            try:
                self._on_timer()
            except Exception:
                logger.exception("Unhandled exception in WM_TIMER")
            return 0
        if msg == WM_LBUTTONDOWN:
            self._on_lbuttondown(GET_X_LPARAM(lparam), GET_Y_LPARAM(lparam))
            return 0
        if msg == WM_LBUTTONUP:
            self._on_lbuttonup()
            return 0
        if msg == WM_MOUSEMOVE:
            self._on_mousemove(GET_X_LPARAM(lparam), GET_Y_LPARAM(lparam), wparam)
            return 0
        if msg == WM_LBUTTONDBLCLK:
            self.stop()
            if self.on_close:
                try:
                    self.on_close()
                except Exception:
                    logger.exception("on_close callback failed")
            return 0
        if msg == WM_RBUTTONUP:
            self._on_rbuttonup(GET_X_LPARAM(lparam), GET_Y_LPARAM(lparam))
            return 0
        if msg == WM_HOTKEY:
            hid = wparam & 0xFFFF
            if hid == 1:
                self._nudge(-1, 0)
            elif hid == 2:
                self._nudge(1, 0)
            elif hid == 3:
                self._nudge(0, -1)
            elif hid == 4:
                self._nudge(0, 1)
            elif hid == 5:
                self._adjust_scale(0.001)
            elif hid == 6:
                self._adjust_scale(-0.001)
            return 0
        if msg == WM_COMMAND:
            self._on_command(wparam)
            return 0
        return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _create_window(self):
        inst = ctypes.windll.kernel32.GetModuleHandleW(None)
        self._hwnd = ctypes.windll.user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            LensWindow._class_name,
            "RealTimeMix Lens",
            WS_POPUP,
            100, 100, 640, 360,
            0, 0, inst, 0
        )
        if not self._hwnd:
            err = ctypes.windll.kernel32.GetLastError()
            raise RuntimeError(f"CreateWindowExW failed: {err}")
        logger.info("Window created hwnd=%s", self._hwnd)

    # ------------------------------------------------------------------
    # Public interface (mirrors old LensWidget)
    # ------------------------------------------------------------------
    def set_seed(self, seed: Seed):
        logger.info("set_seed aspect=%d:%d bs=%d val=%d",
                    seed.aspect_w, seed.aspect_h, seed.block_size, seed.seed)
        self.seed = seed

    def is_visible(self) -> bool:
        if not self._hwnd:
            return False
        return bool(ctypes.windll.user32.IsWindowVisible(self._hwnd))

    def width(self) -> int:
        if not self._hwnd:
            return 0
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(self._hwnd, ctypes.byref(rect))
        return rect.right - rect.left

    def height(self) -> int:
        if not self._hwnd:
            return 0
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(self._hwnd, ctypes.byref(rect))
        return rect.bottom - rect.top

    def set_size_from_scale(self, scale: float):
        if not self.seed:
            return
        phys_w = max(100, round(self.seed.aspect_w * scale))
        phys_h = max(100, round(self.seed.aspect_h * scale))
        self._pending_phys_size = (phys_w, phys_h)
        if self.is_visible():
            self._set_phys_size(phys_w, phys_h)
        logger.info("set_size_from_scale: scale=%.2f phys=%dx%d", scale, phys_w, phys_h)

    def resize(self, w: int, h: int):
        """Compatibility shim for MainWindow custom preset."""
        self._pending_phys_size = None
        ctypes.windll.user32.SetWindowPos(
            self._hwnd, 0, 0, 0, max(100, w), max(100, h),
            SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE
        )

    def move(self, x: int, y: int):
        """Move window to physical pixel position without changing size."""
        if not self._hwnd:
            return
        ctypes.windll.user32.SetWindowPos(
            self._hwnd, 0, int(x), int(y), 0, 0,
            SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
        )

    def set_size_fit_screen(self):
        if not self.seed:
            return
        # Get primary monitor physical size
        sx = ctypes.windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN
        sy = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
        aspect = self.seed.aspect_w / max(self.seed.aspect_h, 1)
        if sx / max(sy, 1) > aspect:
            phys_w = int(sy * aspect)
            phys_h = sy
        else:
            phys_w = sx
            phys_h = int(sx / aspect)
        self._pending_phys_size = (phys_w, phys_h)
        if self.is_visible():
            self._set_phys_size(phys_w, phys_h)
        logger.info("set_size_fit_screen: phys=%dx%d", phys_w, phys_h)

    def start(self):
        logger.info("LensWindow start")
        self.frame_count = 0
        ctypes.windll.user32.ShowWindow(self._hwnd, 1)  # SW_SHOWNORMAL
        ctypes.windll.user32.SetTimer(self._hwnd, self._timer_id, 50, 0)

        # Register global hotkeys for pixel nudge (no focus required)
        user32.RegisterHotKey(self._hwnd, 1, MOD_CONTROL | MOD_SHIFT, VK_LEFT)
        user32.RegisterHotKey(self._hwnd, 2, MOD_CONTROL | MOD_SHIFT, VK_RIGHT)
        user32.RegisterHotKey(self._hwnd, 3, MOD_CONTROL | MOD_SHIFT, VK_UP)
        user32.RegisterHotKey(self._hwnd, 4, MOD_CONTROL | MOD_SHIFT, VK_DOWN)
        # Scale adjust hotkeys: Ctrl+Shift++ / Ctrl+Shift+-
        user32.RegisterHotKey(self._hwnd, 5, MOD_CONTROL | MOD_SHIFT, VK_OEM_PLUS)
        user32.RegisterHotKey(self._hwnd, 6, MOD_CONTROL | MOD_SHIFT, VK_OEM_MINUS)

        # Apply exact physical size if preset was set before show()
        if self._pending_phys_size:
            pw, ph = self._pending_phys_size
            self._set_phys_size(pw, ph)

        # Remove rounded corners (Win11)
        try:
            pref = ctypes.c_int(DWMWCP_DONOTROUND)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                self._hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(pref), ctypes.sizeof(pref)
            )
            logger.info("DWM corner preference set to DONOTROUND")
        except Exception:
            logger.debug("DWM corner preference not available")

        # Exclude from capture (Win10 2004+)
        try:
            ok = ctypes.windll.user32.SetWindowDisplayAffinity(self._hwnd, WDA_EXCLUDEFROMCAPTURE)
            if ok:
                self._use_display_affinity = True
                logger.info("SetWindowDisplayAffinity succeeded")
            else:
                logger.warning("SetWindowDisplayAffinity failed")
        except Exception as e:
            logger.warning("SetWindowDisplayAffinity not available: %s", e)

    def stop(self):
        logger.info("LensWindow stop")
        ctypes.windll.user32.KillTimer(self._hwnd, self._timer_id)
        user32.UnregisterHotKey(self._hwnd, 1)
        user32.UnregisterHotKey(self._hwnd, 2)
        user32.UnregisterHotKey(self._hwnd, 3)
        user32.UnregisterHotKey(self._hwnd, 4)
        user32.UnregisterHotKey(self._hwnd, 5)
        user32.UnregisterHotKey(self._hwnd, 6)
        ctypes.windll.user32.ShowWindow(self._hwnd, 0)  # SW_HIDE

    def close(self):
        if self._hwnd:
            user32.UnregisterHotKey(self._hwnd, 1)
            user32.UnregisterHotKey(self._hwnd, 2)
            user32.UnregisterHotKey(self._hwnd, 3)
            user32.UnregisterHotKey(self._hwnd, 4)
            user32.UnregisterHotKey(self._hwnd, 5)
            user32.UnregisterHotKey(self._hwnd, 6)
            ctypes.windll.user32.DestroyWindow(self._hwnd)
            self._hwnd = None
        self._release_bitmap()

    # ------------------------------------------------------------------
    # Bitmap / display helpers
    # ------------------------------------------------------------------
    def _ensure_bitmap(self, w: int, h: int):
        if self._hdc_mem and self._last_blend_w == w and self._last_blend_h == h:
            return
        self._release_bitmap()
        hdc_screen = ctypes.windll.user32.GetDC(0)
        self._hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
        ctypes.windll.user32.ReleaseDC(0, hdc_screen)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h  # top-down DIB
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        self._dib_bits = ctypes.c_void_p()
        self._hbmp = ctypes.windll.gdi32.CreateDIBSection(
            self._hdc_mem, ctypes.byref(bmi), 0,
            ctypes.byref(self._dib_bits), 0, 0
        )
        self._hbmp_old = ctypes.windll.gdi32.SelectObject(self._hdc_mem, self._hbmp)
        self._last_blend_w = w
        self._last_blend_h = h

    def _release_bitmap(self):
        if self._hdc_mem:
            if self._hbmp_old:
                ctypes.windll.gdi32.SelectObject(self._hdc_mem, self._hbmp_old)
                self._hbmp_old = None
            if self._hbmp:
                ctypes.windll.gdi32.DeleteObject(self._hbmp)
                self._hbmp = None
            ctypes.windll.gdi32.DeleteDC(self._hdc_mem)
            self._hdc_mem = None
            self._dib_bits = None
            self._last_blend_w = 0
            self._last_blend_h = 0

    def _update_layered(self, bgra: np.ndarray, x: int, y: int, w: int, h: int):
        self._ensure_bitmap(w, h)
        # Copy numpy BGRA data into DIB bits
        arr = np.ascontiguousarray(bgra)
        ctypes.memmove(self._dib_bits, arr.ctypes.data, arr.nbytes)
        blend = BLENDFUNCTION()
        blend.BlendOp = AC_SRC_OVER
        blend.BlendFlags = 0
        blend.SourceConstantAlpha = 255
        blend.AlphaFormat = AC_SRC_ALPHA
        pt_src = wintypes.POINT(0, 0)
        pt_dst = wintypes.POINT(x, y)
        size = wintypes.SIZE(w, h)
        ctypes.windll.user32.UpdateLayeredWindow(
            self._hwnd, 0, ctypes.byref(pt_dst), ctypes.byref(size),
            self._hdc_mem, ctypes.byref(pt_src), 0,
            ctypes.byref(blend), ULW_ALPHA
        )

    # ------------------------------------------------------------------
    # Core timer loop
    # ------------------------------------------------------------------
    def _on_timer(self):
        if not self.seed or not self.is_visible():
            return
        hwnd = self._hwnd
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        x, y = rect.left, rect.top
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 0 or h <= 0:
            return

        # Correct size drift if a preset is active
        if self._pending_phys_size:
            pw, ph = self._pending_phys_size
            if w != pw or h != ph:
                logger.debug("correcting size drift %dx%d -> %dx%d", w, h, pw, ph)
                self._set_phys_size(pw, ph)
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                x, y = rect.left, rect.top
                w = rect.right - rect.left
                h = rect.bottom - rect.top

        if self._dragging or self._resizing:
            return

        # Capture
        frame = self._capture_with_mss(x, y, w, h)
        if frame is None or frame.size == 0:
            return

        # Resize to seed original dimensions
        orig_w = self.seed.aspect_w
        orig_h = self.seed.aspect_h
        if frame.shape[1] != orig_w or frame.shape[0] != orig_h:
            frame = cv2.resize(frame, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

        out = descramble_image(frame, self.seed)
        if out is None or out.size == 0:
            return

        # Scale descrambled result to window size for display
        if out.shape[1] != w or out.shape[0] != h:
            out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)

        # BGR -> BGRA (premultiplied alpha = 255)
        bgra = cv2.cvtColor(out, cv2.COLOR_BGR2BGRA)
        self._update_layered(bgra, x, y, w, h)

        self.border_phase += 0.15
        if self.border_phase > 2 * math.pi:
            self.border_phase -= 2 * math.pi

        self.frame_count += 1
        if self.frame_count % 40 == 0:
            gc.collect()

    def _capture_with_mss(self, x, y, w, h):
        if self._mss is None:
            return None
        try:
            monitor = {"left": x, "top": y, "width": w, "height": h}
            sct_img = self._mss.grab(monitor)
            arr = np.frombuffer(sct_img.raw, np.uint8).reshape((h, w, 4))
            frame = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
            return frame
        except Exception as e:
            logger.error("mss capture failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # Window position / size
    # ------------------------------------------------------------------
    def _set_phys_size(self, phys_w: int, phys_h: int):
        SWP_NOMOVE = 0x0002
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        ctypes.windll.user32.SetWindowPos(
            self._hwnd, 0, 0, 0, phys_w, phys_h,
            SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE
        )
        if self.on_size_changed:
            try:
                self.on_size_changed(phys_w, phys_h)
            except Exception:
                logger.exception("on_size_changed callback failed")

    def _nudge(self, dx: int, dy: int):
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(self._hwnd, ctypes.byref(rect))
        nx = rect.left + dx
        ny = rect.top + dy
        ctypes.windll.user32.SetWindowPos(
            self._hwnd, 0, nx, ny, 0, 0,
            SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
        )
        logger.debug("nudge: phys dx=%d dy=%d pos=%d+%d", dx, dy, nx, ny)

    def _adjust_scale(self, delta: float):
        """Adjust scale by delta (e.g. +0.001 or -0.001 = ±0.1%) keeping top-left anchored."""
        if not self.seed:
            return
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(self._hwnd, ctypes.byref(rect))
        current_w = rect.right - rect.left
        current_scale = current_w / self.seed.aspect_w
        new_scale = max(0.1, min(2.5, current_scale + delta))
        self.set_size_from_scale(new_scale)
        logger.debug("adjust_scale: delta=%+.2f scale=%.3f", delta, new_scale)

    # ------------------------------------------------------------------
    # Mouse handlers
    # ------------------------------------------------------------------
    def _get_resize_dir(self, cx: int, cy: int, w: int, h: int):
        m = self._resize_margin
        near_left = cx < m
        near_right = cx > w - m
        near_top = cy < m
        near_bottom = cy > h - m
        if near_top and near_left:
            return 'tl'
        if near_top and near_right:
            return 'tr'
        if near_bottom and near_left:
            return 'bl'
        if near_bottom and near_right:
            return 'br'
        if near_left:
            return 'left'
        if near_right:
            return 'right'
        if near_bottom:
            return 'bottom'
        return None

    def _on_lbuttondown(self, cx: int, cy: int):
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(self._hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        rdir = self._get_resize_dir(cx, cy, w, h)
        if rdir:
            self._resizing = True
            self._resize_dir = rdir
            pt = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            self._resize_start_mouse = (pt.x, pt.y)
            self._resize_start_rect = (rect.left, rect.top, w, h)
        else:
            self._dragging = True
            pt = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            self._drag_start_mouse = (pt.x, pt.y)
            self._drag_start_win = (rect.left, rect.top, w, h)

    def _on_lbuttonup(self):
        if self._resizing:
            self._resizing = False
            self._resize_dir = None
            self._pending_phys_size = None
            if self.on_size_changed:
                w = self.width()
                h = self.height()
                try:
                    self.on_size_changed(w, h)
                except Exception:
                    logger.exception("on_size_changed callback failed")
        self._dragging = False

    def _on_mousemove(self, cx: int, cy: int, keys: int):
        if not (keys & MK_LBUTTON):
            # Hover cursor
            rect = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(self._hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            rdir = self._get_resize_dir(cx, cy, w, h)
            cursor_id = 32512  # IDC_ARROW
            if rdir in ('left', 'right'):
                cursor_id = 32644  # IDC_SIZEWE
            elif rdir == 'bottom':
                cursor_id = 32645  # IDC_SIZENS
            elif rdir in ('tl', 'br'):
                cursor_id = 32642  # IDC_SIZENWSE
            elif rdir in ('tr', 'bl'):
                cursor_id = 32643  # IDC_SIZENESW
            ctypes.windll.user32.SetCursor(ctypes.windll.user32.LoadCursorW(0, cursor_id))
            return

        if self._resizing:
            pt = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            dx = pt.x - self._resize_start_mouse[0]
            dy = pt.y - self._resize_start_mouse[1]
            rl, rt, rw, rh = self._resize_start_rect
            aspect = (self.seed.aspect_w / max(self.seed.aspect_h, 1)) if self.seed else None

            if self._resize_dir == 'left':
                raw_w = rw - dx
                raw_h = rh
            elif self._resize_dir == 'right':
                raw_w = rw + dx
                raw_h = rh
            elif self._resize_dir == 'bottom':
                raw_w = rw
                raw_h = rh + dy
            elif self._resize_dir == 'tl':
                raw_w = rw - dx
                raw_h = rh - dy
            elif self._resize_dir == 'tr':
                raw_w = rw + dx
                raw_h = rh - dy
            elif self._resize_dir == 'bl':
                raw_w = rw - dx
                raw_h = rh + dy
            elif self._resize_dir == 'br':
                raw_w = rw + dx
                raw_h = rh + dy
            else:
                return

            if aspect:
                if self._resize_dir in ('left', 'right'):
                    nw = max(100, raw_w)
                    nh = int(nw / aspect)
                elif self._resize_dir == 'bottom':
                    nh = max(100, raw_h)
                    nw = int(nh * aspect)
                else:
                    if abs(dx) >= abs(dy):
                        nw = max(100, raw_w)
                        nh = int(nw / aspect)
                    else:
                        nh = max(100, raw_h)
                        nw = int(nh * aspect)
            else:
                nw = max(100, raw_w)
                nh = max(100, raw_h)

            if self._resize_dir == 'left':
                nx = rl + rw - nw
                ny = rt
            elif self._resize_dir == 'right':
                nx = rl
                ny = rt
            elif self._resize_dir == 'bottom':
                nx = rl
                ny = rt
            elif self._resize_dir == 'tl':
                nx = rl + rw - nw
                ny = rt + rh - nh
            elif self._resize_dir == 'tr':
                nx = rl
                ny = rt + rh - nh
            elif self._resize_dir == 'bl':
                nx = rl + rw - nw
                ny = rt
            elif self._resize_dir == 'br':
                nx = rl
                ny = rt

            ctypes.windll.user32.SetWindowPos(
                self._hwnd, 0, nx, ny, nw, nh,
                SWP_NOZORDER | SWP_NOACTIVATE
            )
            return

        if self._dragging:
            pt = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            dx = pt.x - self._drag_start_mouse[0]
            dy = pt.y - self._drag_start_mouse[1]
            nx = self._drag_start_win[0] + dx
            ny = self._drag_start_win[1] + dy
            ctypes.windll.user32.SetWindowPos(
                self._hwnd, 0, nx, ny, 0, 0,
                SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
            )
            self._pending_phys_size = None
            return

    # ------------------------------------------------------------------
    # Keyboard handler
    # ------------------------------------------------------------------
    def _on_keydown(self, vk: int):
        ctrl = bool(ctypes.windll.user32.GetKeyState(VK_CONTROL) & 0x8000)
        shift = bool(ctypes.windll.user32.GetKeyState(VK_SHIFT) & 0x8000)
        if not (ctrl and shift):
            return
        if vk == VK_LEFT:
            self._nudge(-1, 0)
        elif vk == VK_RIGHT:
            self._nudge(1, 0)
        elif vk == VK_UP:
            self._nudge(0, -1)
        elif vk == VK_DOWN:
            self._nudge(0, 1)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------
    def _on_rbuttonup(self, cx: int, cy: int):
        hmenu = ctypes.windll.user32.CreatePopupMenu()
        # Menu IDs
        ID_100 = 101
        ID_150 = 102
        ID_200 = 103
        ID_FIT = 104
        ID_CUSTOM = 105
        ID_CLOSE = 106
        MF_STRING = 0x0000
        ctypes.windll.user32.AppendMenuW(hmenu, MF_STRING, ID_100, "100% Original")
        ctypes.windll.user32.AppendMenuW(hmenu, MF_STRING, ID_150, "150% Zoom")
        ctypes.windll.user32.AppendMenuW(hmenu, MF_STRING, ID_200, "200% Zoom")
        ctypes.windll.user32.AppendMenuW(hmenu, MF_STRING, ID_FIT, "Fit Screen")
        ctypes.windll.user32.AppendMenuW(hmenu, MF_STRING, ID_CUSTOM, "Custom width...")
        ctypes.windll.user32.AppendMenuW(hmenu, MF_STRING, ID_CLOSE, "Close lens")
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        ctypes.windll.user32.TrackPopupMenu(
            hmenu, TPM_RIGHTBUTTON, pt.x, pt.y, 0, self._hwnd, 0
        )
        ctypes.windll.user32.DestroyMenu(hmenu)

    def _on_command(self, wparam: int):
        cmd = wparam & 0xFFFF
        if cmd == 101:
            self.set_size_from_scale(1.0)
        elif cmd == 102:
            self.set_size_from_scale(1.5)
        elif cmd == 103:
            self.set_size_from_scale(2.0)
        elif cmd == 104:
            self.set_size_fit_screen()
        elif cmd == 105:
            self._show_custom_width_dialog()
        elif cmd == 106:
            self.stop()
            if self.on_close:
                try:
                    self.on_close()
                except Exception:
                    logger.exception("on_close callback failed")

    def _show_custom_width_dialog(self):
        try:
            from PyQt6.QtWidgets import QInputDialog
            w, ok = QInputDialog.getInt(None, "Custom Width", "Width:", self.width(), 100, 3840)
            if ok and self.seed:
                aspect = self.seed.aspect_w / max(self.seed.aspect_h, 1)
                h = max(100, int(w / aspect))
                self._pending_phys_size = None
                ctypes.windll.user32.SetWindowPos(
                    self._hwnd, 0, 0, 0, w, h,
                    SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE
                )
        except Exception:
            logger.exception("custom width dialog failed")
