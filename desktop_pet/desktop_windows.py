"""Other apps' windows: their top edges are perches the pet can sit on.

window_rects() asks the OS for visible app windows, front to back, as
(id, x1, y1, x2, y2) in Qt's logical coordinates. macOS and Windows only;
elsewhere (or if the OS call fails) there are simply no perches.
perches() turns those into the stretches of top edge that aren't hidden
behind a window in front.
"""
import ctypes
import os
import sys


def perches(rects, min_width, min_top, max_top):
    """Visible top-edge segments: [{"id", "left", "x1", "x2", "top"}].
    "left" is the window's own left edge, used to follow a window that moves."""
    out = []
    for i, (wid, x1, y1, x2, _y2) in enumerate(rects):
        if not (min_top <= y1 <= max_top):
            continue
        segs = [(x1, x2)]
        for _fid, fx1, fy1, fx2, fy2 in rects[:i]:       # windows in front of this one
            if fy1 <= y1 <= fy2:
                segs = _subtract(segs, fx1, fx2)
        out += [{"id": wid, "left": x1, "x1": a, "x2": b, "top": y1}
                for a, b in segs if b - a >= min_width]
    return out


def _subtract(segs, a, b):
    out = []
    for s, e in segs:
        if b <= s or a >= e:
            out.append((s, e))
            continue
        if a > s:
            out.append((s, a))
        if b < e:
            out.append((b, e))
    return out


_failed = False


def window_rects(scale=1.0):
    """scale: physical pixels per Qt pixel (only matters on Windows)."""
    global _failed
    if _failed:
        return []
    try:
        if sys.platform == "darwin":
            return _mac_rects()
        if sys.platform == "win32":
            return [(w, x1 / scale, y1 / scale, x2 / scale, y2 / scale)
                    for w, x1, y1, x2, y2 in _win_rects()]
    except Exception as e:                               # never let this crash the pet
        print("Can't read other windows, no perching:", e)
        _failed = True
    return []


# ----------------------------------------------------------------------
# macOS: CoreGraphics window list (bounds need no screen-recording permission)
# ----------------------------------------------------------------------
_mac = None


class _CGRect(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double),
                ("w", ctypes.c_double), ("h", ctypes.c_double)]


def _mac_lib():
    global _mac
    if _mac:
        return _mac
    cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    vp = ctypes.c_void_p
    cg.CGWindowListCopyWindowInfo.restype = vp
    cg.CGWindowListCopyWindowInfo.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
    cg.CGRectMakeWithDictionaryRepresentation.restype = ctypes.c_bool
    cg.CGRectMakeWithDictionaryRepresentation.argtypes = [vp, ctypes.POINTER(_CGRect)]
    cf.CFArrayGetCount.restype = ctypes.c_long
    cf.CFArrayGetCount.argtypes = [vp]
    cf.CFArrayGetValueAtIndex.restype = vp
    cf.CFArrayGetValueAtIndex.argtypes = [vp, ctypes.c_long]
    cf.CFDictionaryGetValue.restype = vp
    cf.CFDictionaryGetValue.argtypes = [vp, vp]
    cf.CFNumberGetValue.restype = ctypes.c_bool
    cf.CFNumberGetValue.argtypes = [vp, ctypes.c_int, vp]
    cf.CFStringCreateWithCString.restype = vp
    cf.CFStringCreateWithCString.argtypes = [vp, ctypes.c_char_p, ctypes.c_uint32]
    cf.CFRelease.argtypes = [vp]
    keys = {k: cf.CFStringCreateWithCString(None, k.encode(), 0x08000100)   # UTF-8
            for k in ("kCGWindowLayer", "kCGWindowOwnerPID", "kCGWindowNumber",
                      "kCGWindowAlpha", "kCGWindowBounds")}
    _mac = (cg, cf, keys)
    return _mac


def _mac_rects():
    cg, cf, keys = _mac_lib()

    def num(d, key, double=False):
        ref = cf.CFDictionaryGetValue(d, keys[key])
        if not ref:
            return None
        val = ctypes.c_double() if double else ctypes.c_int64()
        cf.CFNumberGetValue(ref, 6 if double else 4, ctypes.byref(val))   # Float64 / SInt64
        return val.value

    arr = cg.CGWindowListCopyWindowInfo(1 | 16, 0)   # on screen only, no desktop elements
    if not arr:
        return []
    out, me = [], os.getpid()
    try:
        for i in range(cf.CFArrayGetCount(arr)):
            d = cf.CFArrayGetValueAtIndex(arr, i)
            if num(d, "kCGWindowLayer") != 0 or num(d, "kCGWindowOwnerPID") == me:
                continue                             # menu bar, Dock, overlays, ourselves
            alpha = num(d, "kCGWindowAlpha", double=True)
            if alpha is not None and alpha < 0.1:
                continue
            r = _CGRect()
            if not cg.CGRectMakeWithDictionaryRepresentation(
                    cf.CFDictionaryGetValue(d, keys["kCGWindowBounds"]), ctypes.byref(r)):
                continue
            if r.w < 80 or r.h < 40:
                continue
            out.append((num(d, "kCGWindowNumber"), r.x, r.y, r.x + r.w, r.y + r.h))
    finally:
        cf.CFRelease(arr)
    return out


# ----------------------------------------------------------------------
# Windows: EnumWindows walks top-level windows front to back
# ----------------------------------------------------------------------
def _win_rects():
    from ctypes import wintypes
    user32, dwm = ctypes.windll.user32, ctypes.windll.dwmapi
    me = os.getpid()
    out = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        if user32.GetWindowTextLengthW(hwnd) == 0:
            return True
        if user32.GetWindowLongW(hwnd, -20) & 0x80:          # GWL_EXSTYLE, WS_EX_TOOLWINDOW
            return True
        cloaked = wintypes.DWORD()
        dwm.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), 4)   # DWMWA_CLOAKED
        if cloaked.value:
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == me:
            return True
        r = wintypes.RECT()                                  # frame without the drop shadow
        if dwm.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r)) != 0:
            user32.GetWindowRect(hwnd, ctypes.byref(r))
        if r.right - r.left >= 80 and r.bottom - r.top >= 40:
            out.append((int(hwnd), r.left, r.top, r.right, r.bottom))
        return True

    user32.EnumWindows(visit, 0)
    return out
