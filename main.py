#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH Tunnel Manager — رابط گرافیکی PyQt5 برای مدیریت تونل SOCKS با autossh.
A friendly PyQt5 GUI to manage a SOCKS tunnel via autossh (Ubuntu/Linux).

ویژگی‌ها / Features:
  • اجرای autossh -M <mon> -D <dyn> -N <user>@<ip> -p <ssh_port> ...
  • توقف امن تونل + گزینهٔ pkill autossh
  • تنظیم/خاموش‌کردن SOCKS سیستم؛ هنگام قطع، پراکسی روی Automatic می‌رود
  • چند «سرور» (پروفایل): IP، پورت SSH، پورت تونل، پورت مانیتور و …
  • دکمهٔ پاور بزرگ برای فعال/غیرفعال
  • بررسی نصب autossh در اولین اجرا + دستور نصب
  • دو تم روشن/تاریک + انتخاب زبان (فارسی / English)
  • پنل لاگ کرکره‌ای زنده
  • آیکن سینی سیستم برای اتصال/قطع سریع
"""

import json
import os
import platform
import shutil
import signal
import socket
import struct
import subprocess
import sys
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

# ───────── HiDPI (قبل از QApplication) ─────────
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

APP_NAME = "SSH Tunnel Manager"
APP_SLUG = "ssh-tunnel-manager"
APP_VERSION = "1.2.1"
CONFIG_DIR = Path.home() / ".config" / APP_SLUG
_OLD_CONFIG_DIR = Path.home() / ".config" / "autossh-manager"
# مهاجرت خودکار از نام قدیمی تا داده‌های کاربر (سرورها/تنظیمات) از دست نرود
try:
    if _OLD_CONFIG_DIR.exists() and not CONFIG_DIR.exists():
        _OLD_CONFIG_DIR.rename(CONFIG_DIR)
except Exception:
    pass
CONFIG_FILE = CONFIG_DIR / "config.json"

# ════════════════════════════ ترجمه‌ها / Translations ════════════════════════
TR = {
    "fa": {
        "tab_home": "خانه", "tab_servers": "سرورها", "tab_settings": "تنظیمات",
        "status_off": "قطع", "status_connecting": "در حال اتصال…",
        "status_on": "متصل", "status_error": "خطا",
        "status_reconnecting": "در حال اتصال مجدد…",
        "no_server": "سروری نیست", "pick_hint": "از تب سرورها یکی بساز",
        "info_server": "سرور", "info_tunnel": "پورت تونل (SOCKS)", "info_socks": "SOCKS سیستم",
        "btn_set_socks": "تنظیم SOCKS سیستم", "btn_auto_proxy": "حالت خودکار (Automatic)",
        "socks_active": "فعال (پورت {p})", "socks_off": "خاموش",
        "socks_auto": "خودکار (Automatic)", "socks_unknown": "نامشخص",
        "proxy_manual": "تنظیم خودکار پراکسی روی این سیستم پشتیبانی نمی‌شود. در برنامه‌ات SOCKS را روی 127.0.0.1:{p} بگذار.",
        "servers_title": "سرورها", "new_server": "＋ سرور جدید",
        "edit": "ویرایش", "del_title": "حذف", "del_q": "این سرور حذف شود؟",
        "settings_title": "تنظیمات",
        "autossh_label": "وضعیت autossh:", "autossh_yes": "✅ نصب است",
        "autossh_no": "❌ نصب نیست", "autossh_unchecked": "بررسی نشده",
        "copy_install": "کپی دستور نصب", "recheck": "بررسی مجدد",
        "ui_scale": "اندازهٔ رابط:", "app_theme": "تم برنامه:",
        "toggle_theme": "تغییر روشن/تاریک", "language": "زبان برنامه:",
        "cleanup_hint": "بستن همهٔ تونل‌هایی که توسط همین برنامه ساخته شده‌اند:",
        "pkill": "بستن تونل‌های برنامه",
        "pkill_done": "{n} تونلِ ساخته‌شده توسط برنامه بسته شد و پراکسی سیستم به حالت خودکار بازگشت.",
        "pkill_none": "هیچ تونلِ فعالی که توسط این برنامه ساخته شده باشد پیدا نشد.",
        "logs_title": "لاگ‌های اتصال",
        "startup_title": "راه‌اندازی خودکار",
        "autostart_chk": "اجرای برنامه هنگام روشن‌شدن سیستم",
        "autoconnect_chk": "اتصال خودکار به آخرین سرور هنگام اجرا",
        "term_proxy_title": "پراکسی ترمینال / کل سیستم",
        "term_proxy_chk": "هدایت ترمینال به تونل هنگام اتصال (خودکار)",
        "term_proxy_hint": ("با فعال‌بودن این گزینه، هنگام اتصالِ تونل متغیرهای محیطی پراکسی نوشته "
                            "می‌شوند و هنگام قطع، خودکار پاک می‌شوند؛ پس اینترنت معمولی سیستم در حالت "
                            "قطع مختل نمی‌شود. برنامه همچنین خطِ لازم را به‌صورت خودکار به فایل‌های شِل "
                            "(.bashrc/.zshrc/.profile) اضافه/حذف می‌کند.\n"
                            "⚠️ توجه: متغیرهای محیطی فقط روی ترمینال‌هایی اثر می‌گذارند که «بعد از» تغییر "
                            "باز می‌شوند. برای ترمینال‌هایِ همین‌حالا باز، یک‌بار `source ~/.bashrc` بزن یا "
                            "ترمینال تازه باز کن. کل سیستم به‌صورت شفاف (همهٔ برنامه‌ها) بدون مسیریابی TUN "
                            "ممکن نیست؛ این روش ترمینال و ابزارهای خط‌فرمان را پوشش می‌دهد."),
        "term_proxy_copy": "کپی دستور بازخوانی (source ~/.bashrc)",
        "term_proxy_reload_hint": "خط لازم خودکار به فایل‌های شِل اضافه شد. برای ترمینال‌هایِ همین‌حالا باز، یک‌بار `source ~/.bashrc` بزن یا ترمینال تازه باز کن.",
        "verifying": "در حال بررسی تونل…",
        "verify_fail": "❌ تونل برقرار نشد: پورت SOCKS پاسخ نمی‌دهد.",
        "verify_fwd_fail": "❌ خطای forwarding پورت مانیتور ({m}). این پورت روی سرور آزاد نیست. تونل برقرار نشد.\nراه‌حل: پورت مانیتور (-M) را در تنظیمات سرور به 0 تغییر بده یا پورت دیگری انتخاب کن.",
        "verify_ssh255": "❌ ssh با خطای 255 خارج شد؛ اتصال ناموفق بود.",
        "dlg_title": "سرور", "f_name": "نام سرور:", "f_ip": "IP سرور:",
        "f_user": "کاربر:", "f_ssh": "پورت اتصال به سرور (SSH):",
        "f_dyn": "پورت تونل (-D):", "f_mon": "پورت مانیتور (-M، ۰=خاموش، پیشنهادی):",
        "f_key": "فایل کلید SSH:", "f_pass": "رمز عبور:", "f_extra": "تنظیمات اضافی:",
        "set_socks_chk": "تنظیم خودکار SOCKS سیستم هنگام اتصال",
        "save": "ذخیره", "cancel": "انصراف", "error": "خطا", "enter_ip": "IP سرور را وارد کن.",
        "ph_name": "مثلاً سرور آلمان", "ph_ip": "0.0.0.0",
        "ph_key": "~/.ssh/id_rsa  (پیشنهادی)",
        "ph_pass": "اختیاری — فقط اگر کلید نداری (با sshpass)",
        "ph_extra": "گزینه‌های اضافی ssh، مثلاً -o Compression=yes",
        "tray_connect": "اتصال", "tray_disconnect": "قطع اتصال",
        "tray_pick": "انتخاب سرور", "tray_show": "نمایش پنجره",
        "tray_quit": "خروج", "tray_none": "— سروری نیست —",
        "tray_hint": "برنامه در سینی سیستم اجرا می‌ماند. برای خروج کامل، از منوی سینی «خروج» را بزن.",
        "warn_pick": "اول یک سرور بساز و انتخاب کن.",
        "inst_title": "autossh نصب نیست",
        "inst_text": "برنامهٔ autossh روی سیستم پیدا نشد.\nبرای استفاده باید نصبش کنی.",
        "inst_info": "دستور نصب:\nsudo apt update && sudo apt install -y autossh",
        "ok": "باشه",
        "fa_name": "فارسی", "en_name": "English",
    },
    "en": {
        "tab_home": "Home", "tab_servers": "Servers", "tab_settings": "Settings",
        "status_off": "Disconnected", "status_connecting": "Connecting…",
        "status_on": "Connected", "status_error": "Error",
        "status_reconnecting": "Reconnecting…",
        "no_server": "No server", "pick_hint": "Create one in the Servers tab",
        "info_server": "Server", "info_tunnel": "Tunnel port (SOCKS)", "info_socks": "System SOCKS",
        "btn_set_socks": "Set system SOCKS", "btn_auto_proxy": "Automatic mode",
        "socks_active": "Active (port {p})", "socks_off": "Off",
        "socks_auto": "Automatic", "socks_unknown": "Unknown",
        "proxy_manual": "Auto proxy isn't supported on this system. Set your app's SOCKS to 127.0.0.1:{p}.",
        "servers_title": "Servers", "new_server": "＋ New server",
        "edit": "Edit", "del_title": "Delete", "del_q": "Delete this server?",
        "settings_title": "Settings",
        "autossh_label": "autossh status:", "autossh_yes": "✅ Installed",
        "autossh_no": "❌ Not installed", "autossh_unchecked": "Not checked",
        "copy_install": "Copy install command", "recheck": "Re-check",
        "ui_scale": "UI size:", "app_theme": "App theme:",
        "toggle_theme": "Toggle light/dark", "language": "Language:",
        "cleanup_hint": "Close all tunnels started by this app:",
        "pkill": "Close app tunnels",
        "pkill_done": "Closed {n} tunnel(s) created by this app and reset the system proxy to Automatic.",
        "pkill_none": "No active tunnels created by this app were found.",
        "logs_title": "Connection logs",
        "startup_title": "Startup",
        "autostart_chk": "Start app when the system boots",
        "autoconnect_chk": "Auto-connect to the last server on launch",
        "term_proxy_title": "Terminal / system-wide proxy",
        "term_proxy_chk": "Route the terminal through the tunnel on connect (automatic)",
        "term_proxy_hint": ("When enabled, proxy env vars are written on connect and cleared on "
                            "disconnect, so your normal internet isn't broken while the tunnel is off. "
                            "The app also adds/removes the needed line in your shell startup files "
                            "(.bashrc/.zshrc/.profile) automatically.\n"
                            "⚠️ Note: env vars only affect terminals opened AFTER the change. For "
                            "terminals already open, run `source ~/.bashrc` once or open a new terminal. "
                            "Truly system-wide (every app) routing needs TUN routing and isn't done here; "
                            "this covers the terminal and command-line tools."),
        "term_proxy_copy": "Copy reload command (source ~/.bashrc)",
        "term_proxy_reload_hint": "The shell line was added automatically. For terminals already open, run `source ~/.bashrc` once or open a new terminal.",
        "verifying": "Verifying tunnel…",
        "verify_fail": "❌ Tunnel not established: SOCKS port is not responding.",
        "verify_fwd_fail": "❌ Monitor port forwarding failed ({m}). That port isn't free on the server. Tunnel not established.\nFix: set the monitor port (-M) to 0 in the server settings, or pick a different port.",
        "verify_ssh255": "❌ ssh exited with status 255; connection failed.",
        "dlg_title": "Server", "f_name": "Server name:", "f_ip": "Server IP:",
        "f_user": "User:", "f_ssh": "Server SSH port:",
        "f_dyn": "Tunnel port (-D):", "f_mon": "Monitor port (-M, 0=off, recommended):",
        "f_key": "SSH key file:", "f_pass": "Password:", "f_extra": "Extra options:",
        "set_socks_chk": "Auto-set system SOCKS on connect",
        "save": "Save", "cancel": "Cancel", "error": "Error", "enter_ip": "Please enter the server IP.",
        "ph_name": "e.g. Germany server", "ph_ip": "0.0.0.0",
        "ph_key": "~/.ssh/id_rsa  (recommended)",
        "ph_pass": "optional — only if you have no key (uses sshpass)",
        "ph_extra": "extra ssh options, e.g. -o Compression=yes",
        "tray_connect": "Connect", "tray_disconnect": "Disconnect",
        "tray_pick": "Select server", "tray_show": "Show window",
        "tray_quit": "Quit", "tray_none": "— no server —",
        "tray_hint": "The app keeps running in the system tray. Use 'Quit' in the tray menu to exit.",
        "warn_pick": "Create and select a server first.",
        "inst_title": "autossh not installed",
        "inst_text": "autossh was not found on your system.\nYou need to install it.",
        "inst_info": "Install command:\nsudo apt update && sudo apt install -y autossh",
        "ok": "OK",
        "fa_name": "فارسی", "en_name": "English",
    },
}

# ════════════════════════════ پالت رنگ تم‌ها ════════════════════════════
THEMES = {
    "light": {
        "bg": "#f4f6fb", "card": "#ffffff", "card2": "#f0f3fa",
        "text": "#1d2433", "muted": "#6b7488", "border": "#e3e8f2",
        "accent": "#2f6df6", "accent_dim": "#dbe6ff",
        "on": "#19b56b", "off": "#9aa3b5", "busy": "#f3a312", "danger": "#e2463f",
        "log_bg": "#0e1320", "log_text": "#cdd6e8",
    },
    "dark": {
        "bg": "#0f1320", "card": "#171c2b", "card2": "#1e2436",
        "text": "#e8ecf6", "muted": "#8a93a8", "border": "#272f44",
        "accent": "#5b8cff", "accent_dim": "#22304f",
        "on": "#22c178", "off": "#5b6479", "busy": "#f5b23d", "danger": "#f0625b",
        "log_bg": "#080b13", "log_text": "#b9c2d8",
    },
}


def qss(c: dict) -> str:
    return f"""
    * {{ font-family: 'Segoe UI', 'Vazirmatn', 'Noto Sans', sans-serif; }}
    #root {{ background: {c['bg']}; border-radius: 18px; }}
    #header {{ background: transparent; }}
    #titleLbl {{ color: {c['text']}; font-size: 16px; font-weight: 700; }}
    #winBtn {{ background: transparent; color: {c['muted']}; border: none;
        border-radius: 8px; font-size: 16px; min-width: 30px; min-height: 30px; }}
    #winBtn:hover {{ background: {c['card2']}; color: {c['text']}; }}
    #closeBtn:hover {{ background: {c['danger']}; color: white; }}
    QStackedWidget > QWidget {{ background: transparent; }}
    #card {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 16px; }}
    #subcard {{ background: {c['card2']}; border: 1px solid {c['border']}; border-radius: 12px; }}
    QLabel {{ color: {c['text']}; }}
    #h1 {{ font-size: 20px; font-weight: 700; }}
    #h2 {{ font-size: 14px; font-weight: 600; }}
    #muted {{ color: {c['muted']}; }}
    #status {{ font-size: 15px; font-weight: 700; }}
    #pill {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 22px; }}
    #pillName {{ font-size: 14px; font-weight: 700; color: {c['text']}; }}
    #pillSub  {{ font-size: 11px; color: {c['muted']}; }}
    QComboBox {{ background: {c['card']}; color: {c['text']}; border: 1px solid {c['border']};
        border-radius: 10px; padding: 7px 12px; min-height: 20px; }}
    QComboBox:hover {{ border-color: {c['accent']}; }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox QAbstractItemView {{ background: {c['card']}; color: {c['text']};
        border: 1px solid {c['border']}; border-radius: 10px;
        selection-background-color: {c['accent_dim']}; selection-color: {c['text']};
        outline: none; padding: 4px; }}
    QLineEdit {{ background: {c['card']}; color: {c['text']}; border: 1px solid {c['border']};
        border-radius: 10px; padding: 8px 12px; selection-background-color: {c['accent_dim']}; }}
    QLineEdit:focus {{ border-color: {c['accent']}; }}
    QLineEdit[readOnly="true"] {{ background: {c['card2']}; color: {c['muted']}; }}
    QPushButton {{ background: {c['card2']}; color: {c['text']}; border: 1px solid {c['border']};
        border-radius: 10px; padding: 9px 16px; font-weight: 600; }}
    QPushButton:hover {{ border-color: {c['accent']}; }}
    QPushButton:disabled {{ color: {c['muted']}; }}
    #primaryBtn {{ background: {c['accent']}; color: white; border: none; }}
    #dangerBtn {{ color: {c['danger']}; }}
    #dangerBtn:hover {{ border-color: {c['danger']}; }}
    QListWidget {{ background: transparent; border: none; outline: none; }}
    QListWidget::item {{ border: none; padding: 0; margin: 0 0 10px 0; }}
    QListWidget::item:selected {{ background: transparent; }}
    #tabbar {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 16px; }}
    #tabBtn {{ background: transparent; color: {c['muted']}; border: none; border-radius: 12px;
        padding: 10px 4px; font-size: 12px; font-weight: 600; }}
    #tabBtn:hover {{ color: {c['text']}; }}
    #tabBtn:checked {{ background: {c['accent_dim']}; color: {c['accent']}; }}
    #logHeader {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 12px; }}
    #logHeader:hover {{ border-color: {c['accent']}; }}
    #logDrawer {{ background: transparent; border: none; }}
    #logHandle {{ background: transparent; color: {c['muted']}; border: none;
        border-left: 1px solid {c['border']}; border-right: 1px solid {c['border']};
        font-size: 15px; font-weight: 700; }}
    #logHandle:hover {{ color: {c['accent']}; background: {c['accent_dim']}; }}
    QTextEdit#logView {{ background: {c['log_bg']}; color: {c['log_text']};
        border: 1px solid {c['border']}; border-radius: 12px;
        font-family: 'JetBrains Mono', 'DejaVu Sans Mono', monospace; font-size: 12px; padding: 10px; }}
    QSlider::groove:horizontal {{ height: 6px; background: {c['border']}; border-radius: 3px; }}
    QSlider::handle:horizontal {{ background: {c['accent']}; width: 18px; height: 18px;
        margin: -7px 0; border-radius: 9px; }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 5px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QCheckBox {{ color: {c['text']}; spacing: 8px; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px;
        border: 1px solid {c['border']}; background: {c['card']}; }}
    QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; }}
    QDialog {{ background: {c['bg']}; color: {c['text']}; }}
    QDialog QLabel {{ color: {c['text']}; background: transparent; }}
    QMessageBox {{ background: {c['bg']}; color: {c['text']}; }}
    QMessageBox QLabel {{ color: {c['text']}; background: transparent; }}
    QMessageBox QPushButton {{ background: {c['card2']}; color: {c['text']};
        border: 1px solid {c['border']}; border-radius: 10px; padding: 7px 16px;
        font-weight: 600; min-width: 70px; }}
    QMessageBox QPushButton:hover {{ border-color: {c['accent']}; }}
    QToolTip {{ background: {c['card2']}; color: {c['text']};
        border: 1px solid {c['border']}; border-radius: 6px; padding: 4px 8px; }}
    """


# ════════════════════════════ آیکن پاور ════════════════════════════
def _draw_power(p, rect, line_w, gap_top):
    pen = QtGui.QPen(QtGui.QColor("white"))
    pen.setWidthF(line_w);
    pen.setCapStyle(QtCore.Qt.RoundCap)
    p.setPen(pen);
    p.setBrush(QtCore.Qt.NoBrush)
    cx, cy = rect.center().x(), rect.center().y()
    r = rect.width() * 0.26
    arc = QtCore.QRectF(cx - r, cy - r + 2, 2 * r, 2 * r)
    p.drawArc(arc, int((90 + 40) * 16), int(280 * 16))
    p.drawLine(QtCore.QPointF(cx, cy - r - gap_top),
               QtCore.QPointF(cx, cy - rect.width() * 0.02))


def make_power_icon(color: str, size: int = 64) -> QtGui.QIcon:
    pm = QtGui.QPixmap(size, size);
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm);
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    rect = QtCore.QRectF(4, 4, size - 8, size - 8)
    p.setBrush(QtGui.QColor(color));
    p.setPen(QtCore.Qt.NoPen);
    p.drawEllipse(rect)
    _draw_power(p, QtCore.QRectF(0, 0, size, size), size * 0.07, size * 0.07)
    p.end()
    return QtGui.QIcon(pm)


class PowerButton(QtWidgets.QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedSize(140, 140)
        self._ring = QtGui.QColor("#9aa3b5")

    def set_state(self, _state, color):
        self._ring = QtGui.QColor(color);
        self.update()

    def sizeHint(self):
        return QtCore.QSize(140, 140)

    def paintEvent(self, _):
        p = QtGui.QPainter(self);
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)
        cx, cy = rect.center().x(), rect.center().y()
        halo = QtGui.QColor(self._ring);
        halo.setAlpha(40)
        p.setBrush(halo);
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(self.rect().adjusted(2, 2, -2, -2))
        grad = QtGui.QRadialGradient(QtCore.QPointF(cx, cy - 10), rect.width() / 1.4)
        grad.setColorAt(0, QtGui.QColor(self._ring).lighter(118))
        grad.setColorAt(1, QtGui.QColor(self._ring))
        p.setBrush(QtGui.QBrush(grad));
        p.setPen(QtCore.Qt.NoPen);
        p.drawEllipse(rect)
        _draw_power(p, rect, rect.width() * 0.055, rect.width() * 0.10)
        p.end()


# ════════════════════════════ بررسی واقعیِ سلامت تونل ════════════════════════════
def socks_port_listening(port, host="127.0.0.1", timeout=1.0):
    """آیا چیزی روی پورت SOCKS گوش می‌دهد؟ (اتصال TCP ساده)"""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def socks5_handshake_ok(port, host="127.0.0.1", timeout=2.5):
    """یک دست‌دادهٔ SOCKS5 انجام می‌دهد و سپس درخواست CONNECT به یک مقصد
    آزمایشی می‌فرستد تا مطمئن شویم تونل واقعاً از سرِ دیگر هم کار می‌کند.

    خروجی: "ok" اگر CONNECT موفق شد، "handshake" اگر فقط negotiation کار کرد
    (مثلاً مقصد آزمایشی بسته بود ولی تونل برقرار است)، و "" اگر کلاً شکست خورد.

    اگر فقط TCP وصل شود ولی forwarding سمت سرور خراب باشد، ssh معمولاً
    اتصال SOCKS را می‌بندد یا negotiation شکست می‌خورد؛ آن حالت تشخیص داده می‌شود.
    """
    for target_ip in ("1.1.1.1", "8.8.8.8"):
        try:
            s = socket.create_connection((host, int(port)), timeout=timeout)
        except Exception:
            return ""
        try:
            s.settimeout(timeout)
            s.sendall(b"\x05\x01\x00")  # VER=5, NMETHODS=1, METHOD=0
            resp = s.recv(2)
            if len(resp) < 2 or resp[0] != 0x05 or resp[1] == 0xFF:
                return ""
            req = b"\x05\x01\x00\x01" + socket.inet_aton(target_ip) + struct.pack(">H", 80)
            s.sendall(req)
            rep = s.recv(10)
            if len(rep) >= 2 and rep[0] == 0x05 and rep[1] == 0x00:
                return "ok"
            # negotiation کار کرد ولی این مقصد در دسترس نبود → مقصد بعدی
        except Exception:
            return ""
        finally:
            try:
                s.close()
            except Exception:
                pass
    # هر دو مقصد negotiation را رد کردند ولی پاسخ SOCKS معتبر گرفتیم
    return "handshake"


# ════════════════════════════ کنترلر autossh ════════════════════════════
class TunnelController(QtCore.QObject):
    log = QtCore.pyqtSignal(str)
    state_changed = QtCore.pyqtSignal(str)
    pid_started = QtCore.pyqtSignal(int)  # PID تونلِ ساخته‌شده توسط برنامه
    pid_stopped = QtCore.pyqtSignal(int)  # PID تونلی که پایان یافت
    failed = QtCore.pyqtSignal(str)       # کلید پیام شکست برای نمایش/ترجمه

    # الگوهای متنی که نشان‌دهندهٔ شکست واقعی اتصال‌اند
    _FWD_FAIL = "remote port forwarding failed"
    _SSH_255 = "exited with error status 255"

    def __init__(self):
        super().__init__()
        self.proc = None
        self.state = "off"
        self._pid = 0
        self._dyn_port = 0
        self._mon_port = 0
        self._verified = False        # آیا یک‌بار اتصال واقعی تأیید شده؟
        self._fwd_failed = False      # forwarding پورت مانیتور خراب است؟
        self._verify_tries = 0
        self._stopping = False
        self._health_fails = 0        # شمارندهٔ شکست‌های پیاپیِ پایش سلامت
        self._reconnecting = False    # آیا هم‌اکنون در حال اتصال مجدد است؟
        self._verify_timer = QtCore.QTimer(self)
        self._verify_timer.setSingleShot(True)
        self._verify_timer.timeout.connect(self._verify_step)
        # پایش دورهٔ سلامت تونل پس از برقراری (هر ۸ ثانیه)
        self._health_timer = QtCore.QTimer(self)
        self._health_timer.setInterval(8000)
        self._health_timer.timeout.connect(self._health_check)

    def build_command(self, prof):
        ip = prof.get("ip", "").strip()
        user = prof.get("user", "root").strip() or "root"
        ssh_port = str(prof.get("ssh_port", "22")).strip() or "22"
        dyn = str(prof.get("dyn_port", "1085")).strip() or "1085"
        # پورت مانیتور (-M): پیش‌فرض 0 (غیرفعال). مکانیزم remote-forwardِ -M
        # باعث خطای «remote port forwarding failed» و حلقهٔ ری‌استارت می‌شد،
        # چون پس از هر قطعی پورت روی سرور بلافاصله آزاد نمی‌شد. به‌جای آن از
        # ServerAlive خودِ ssh برای تشخیص قطعی استفاده می‌کنیم.
        mon = str(prof.get("mon_port", "0")).strip() or "0"
        key = prof.get("key", "").strip()
        extra = prof.get("extra", "").strip()
        password = prof.get("password", "")
        cmd = ["autossh", "-M", mon, "-D", dyn, "-N",
               # تشخیص سریع قطعی و تلاش پایدار برای اتصال مجدد
               "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=3",
               "-o", "ExitOnForwardFailure=yes",
               "-o", "StrictHostKeyChecking=accept-new",
               "-o", "TCPKeepAlive=yes",
               "-o", "ConnectTimeout=10",
               "-o", "ConnectionAttempts=3",
               "-p", ssh_port]
        if key:
            cmd += ["-i", os.path.expanduser(key)]
        if extra:
            cmd += extra.split()
        cmd += [f"{user}@{ip}"]
        use_sshpass = bool(password) and not key
        if use_sshpass:
            cmd = ["sshpass", "-p", password] + cmd
        return cmd, use_sshpass

    def start(self, prof):
        # اگر فرایندی از قبل هست، ابتدا کامل ببندش تا چند تونل هم‌زمان روی هم
        # جمع نشوند و حافظه را پر نکنند.
        if self.proc is not None:
            if self.proc.state() == QtCore.QProcess.Running:
                self.log.emit("⚠️  Existing tunnel found; closing it before reconnecting…")
            self.stop()
        if not shutil.which("autossh"):
            self.state = "error";
            self.state_changed.emit("error")
            self.log.emit("❌ autossh not installed.")
            return
        cmd, use_sshpass = self.build_command(prof)
        if use_sshpass and not shutil.which("sshpass"):
            self.state = "error";
            self.state_changed.emit("error")
            self.log.emit("❌ sshpass required for password login: sudo apt install sshpass")
            return
        self.state = "connecting";
        self.state_changed.emit("connecting")
        self._verified = False
        self._fwd_failed = False
        self._verify_tries = 0
        self._stopping = False
        self._health_fails = 0
        self._reconnecting = False
        self._dyn_port = int(str(prof.get("dyn_port", "1085")).strip() or "1085")
        self._mon_port = int(str(prof.get("mon_port", "0")).strip() or "0")
        # اطمینان از آزاد بودن پورت محلیِ SOCKS پیش از اجرا (جلوگیری از تداخل)
        self._ensure_local_port_free(self._dyn_port, timeout_ms=1500)
        self.log.emit("───────────────────────────")
        shown = list(cmd)
        if use_sshpass:
            shown[2] = "********"
        self.log.emit("▶  " + " ".join(shown))
        env = QtCore.QProcessEnvironment.systemEnvironment()
        env.insert("AUTOSSH_DEBUG", "1")
        env.insert("AUTOSSH_GATETIME", "0")
        self.proc = QtCore.QProcess()
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._on_output)
        self.proc.started.connect(self._on_started)
        self.proc.finished.connect(self._on_finished)
        self.proc.errorOccurred.connect(lambda err: self.log.emit(f"⚠️  process error: {err}"))
        self.proc.start(cmd[0], cmd[1:])

    def _on_started(self):
        self._pid = int(self.proc.processId()) if self.proc else 0
        if self._pid:
            self.pid_started.emit(self._pid)
        # شروعِ چرخهٔ بررسیِ واقعی پس از فرصت کوتاهِ برقراری
        self._verify_tries = 0
        self._verify_timer.start(1500)

    def _verify_step(self):
        """تا وقتی SOCKS واقعاً جواب بدهد ادامه می‌دهد؛ در صورت شکست
        forwarding یا تمام‌شدن تلاش‌ها، اتصال را ناموفق اعلام می‌کند."""
        if self._stopping or self.proc is None:
            return
        if self._verified:
            return
        # اگر forwarding پورت مانیتور خراب شده، دیگر منتظر نمی‌مانیم
        if self._fwd_failed:
            self._fail("verify_fwd_fail")
            return
        # اگر فرایند autossh مرده باشد
        if self.proc.state() != QtCore.QProcess.Running:
            self._fail("verify_fail")
            return
        # بررسی واقعی: ابتدا گوش‌دادن، سپس دست‌دادن کامل SOCKS5
        if socks_port_listening(self._dyn_port):
            res = socks5_handshake_ok(self._dyn_port)
            # "ok" = CONNECT کامل موفق؛ "handshake" = پراکسی SOCKS زنده است
            if res in ("ok", "handshake") and not self._fwd_failed:
                self._verified = True
                self._health_fails = 0
                self._reconnecting = False
                self.state = "on"
                self.state_changed.emit("on")
                detail = "SOCKS verified" if res == "ok" else "SOCKS responding"
                self.log.emit(f"✅ Tunnel established ({detail}).")
                # شروع پایش دوره‌ای سلامت
                if not self._health_timer.isActive():
                    self._health_timer.start()
                return
        # هنوز آماده نیست → تلاش مجدد تا حدود ۲۰ ثانیه
        self._verify_tries += 1
        if self._verify_tries >= 13:
            self._fail("verify_fail")
            return
        self._verify_timer.start(1500)

    def _health_check(self):
        """پایش دوره‌ای پس از برقراری. اگر تونل واقعاً قطع شده باشد، UI را به
        حالت «در حال اتصال مجدد» می‌برد (نه متصلِ دروغین) و می‌گذارد autossh
        خودش ssh را بازسازی کند؛ با سالم‌شدن دوباره، به «متصل» برمی‌گردد."""
        if self._stopping or self.proc is None or not self._verified:
            return
        # اگر فرایند autossh کلاً مرده، پایش را متوقف کن (on_finished رسیدگی می‌کند)
        if self.proc.state() != QtCore.QProcess.Running:
            return
        alive = socks_port_listening(self._dyn_port) and \
            socks5_handshake_ok(self._dyn_port) in ("ok", "handshake")
        if alive:
            if self._health_fails or self._reconnecting:
                self.log.emit("✅ Tunnel healthy again.")
            self._health_fails = 0
            if self._reconnecting:
                self._reconnecting = False
                self.state = "on"
                self.state_changed.emit("on")
            return
        # ناموفق: شمارنده را زیاد کن
        self._health_fails += 1
        if self._health_fails == 1:
            self.log.emit("⚠️  Tunnel not responding; checking…")
        if self._health_fails >= 2 and not self._reconnecting:
            # تونل واقعاً افتاده → نمایش وضعیت اتصال مجدد (autossh خودش بازسازی می‌کند)
            self._reconnecting = True
            self.state = "reconnecting"
            self.state_changed.emit("reconnecting")
            self.log.emit("🔄 Reconnecting…")
        # اگر خیلی طولانی شد (مثلاً ~۲ دقیقه)، فرایند ssh را به‌زور تازه کن
        if self._health_fails >= 15 and self.proc is not None:
            self.log.emit("🔁 Forcing ssh restart…")
            self._restart_ssh_child()
            self._health_fails = 3  # شمارنده را کمی پایین بیاور تا فوراً دوباره فشار نیاورد

    def _restart_ssh_child(self):
        """به autossh سیگنال می‌دهد فرزند ssh را بازسازی کند (SIGUSR1)؛
        autossh با دریافت این سیگنال، اتصال ssh را از نو برقرار می‌کند."""
        if not hasattr(signal, "SIGUSR1"):
            return  # ویندوز این سیگنال را ندارد؛ autossh خودش بازسازی می‌کند
        try:
            if self.proc is not None and self.proc.processId():
                os.kill(int(self.proc.processId()), signal.SIGUSR1)
        except Exception as e:
            self.log.emit(f"⚠️  restart signal failed: {e}")

    def _fail(self, msg_key):
        """اعلام شکستِ واقعیِ اتصال، نمایش پیام و بستن تمیزِ تونلِ معیوب."""
        if self.state == "error":
            return
        self.log.emit("❌ Connection verification failed.")
        self.failed.emit(msg_key)
        # تونل ناموفق را پاک می‌بندیم تا فرایند معیوب باقی نماند
        self._stopping = True
        self._verify_timer.stop()
        self._health_timer.stop()
        if self.proc is not None:
            try:
                self.proc.terminate()
                if not self.proc.waitForFinished(1500):
                    self.proc.kill()
                    self.proc.waitForFinished(800)
            except Exception:
                pass
            self.proc = None
        if self._pid:
            self.pid_stopped.emit(self._pid)
            self._pid = 0
        self._stopping = False
        self.state = "error"
        self.state_changed.emit("error")

    def _on_output(self):
        if not self.proc:
            return
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        for line in data.splitlines():
            if not line.strip():
                continue
            low = line.lower()
            # تشخیص شکست forwarding پورت مانیتور (-M): علت اصلی اتصال جعلی
            if self._FWD_FAIL in low:
                self._fwd_failed = True
            self.log.emit(line.rstrip())
        # اگر در میانهٔ بررسی forwarding خراب شد، فوراً واکنش نشان بده
        if self._fwd_failed and not self._verified and self.state == "connecting":
            self._verify_timer.stop()
            QtCore.QTimer.singleShot(0, lambda: self._fail("verify_fwd_fail"))

    def _on_finished(self, code, _status):
        self._verify_timer.stop()
        self._health_timer.stop()
        self.log.emit(f"■ autossh exited (code {code}).")
        if self._pid:
            self.pid_stopped.emit(self._pid);
            self._pid = 0
        self.proc = None
        # اگر در حال بستن عمدی به‌علت شکست هستیم، حالت error را خراب نکن
        if self._stopping or self.state == "error":
            return
        # اگر هرگز تأیید نشده بود و خودش مرد → یعنی اتصال شکست خورده
        if not self._verified and self.state == "connecting":
            self.failed.emit("verify_ssh255" if code != 0 else "verify_fail")
            self.state = "error"
            self.state_changed.emit("error")
            return
        self.state = "off";
        self.state_changed.emit("off")

    def stop(self):
        self._stopping = True
        self._verify_timer.stop()
        self._health_timer.stop()
        dyn = self._dyn_port
        if self.proc is not None:
            self.log.emit("⏹  Stopping tunnel…")
            self.proc.terminate()
            if not self.proc.waitForFinished(2500):
                self.proc.kill();
                self.proc.waitForFinished(1500)
            self.proc = None
        if self._pid:
            self.pid_stopped.emit(self._pid);
            self._pid = 0
        self._verified = False
        self._reconnecting = False
        self._health_fails = 0
        # مطمئن شو پورت محلیِ SOCKS واقعاً آزاد شده تا اتصال بعدی فوراً موفق شود
        if dyn:
            self._ensure_local_port_free(dyn)
        self._stopping = False
        self.state = "off";
        self.state_changed.emit("off")

    def _ensure_local_port_free(self, port, timeout_ms=3000):
        """منتظر می‌ماند تا پورت محلی آزاد شود؛ اگر فرایندی هنوز آن را گرفته
        (مثلاً فرزند ssh که دیر بسته)، آن را می‌کشد تا اتصال مجددِ سریع ممکن شود."""
        import time as _t
        deadline = _t.time() + timeout_ms / 1000.0
        while _t.time() < deadline:
            if not socks_port_listening(port, timeout=0.3):
                return True
            _t.sleep(0.2)
        # هنوز اشغال است → تلاش برای کشتنِ نگه‌دارندهٔ پورت
        try:
            out = subprocess.run(
                ["bash", "-lc", f"fuser -k {port}/tcp 2>/dev/null || true"],
                capture_output=True, timeout=3)
            _ = out
        except Exception:
            pass
        _t.sleep(0.3)
        return not socks_port_listening(port, timeout=0.3)


# ════════════════════════════ تشخیص سیستم‌عامل ════════════════════════════
def detect_os():
    s = platform.system()
    if s == "Windows":
        return "windows"
    if s == "Darwin":
        return "macos"
    return "linux"


OS = detect_os()


def linux_distro_ids():
    """خواندن ID و ID_LIKE از /etc/os-release برای تشخیص توزیع."""
    ids = []
    try:
        for line in Path("/etc/os-release").read_text("utf-8").splitlines():
            if line.startswith("ID=") or line.startswith("ID_LIKE="):
                val = line.split("=", 1)[1].strip().strip('"')
                ids += val.replace("-", " ").split()
    except Exception:
        pass
    return [i.lower() for i in ids]


def install_primary_command():
    """بهترین تک‌دستور نصب autossh برای سیستم فعلی."""
    if OS == "windows":
        return "winget install --id=MSYS2.MSYS2 -e   (سپس در MSYS2:  pacman -S autossh)"
    if OS == "macos":
        return "brew install autossh"
    ids = linux_distro_ids()
    if any(x in ids for x in ("debian", "ubuntu", "linuxmint", "pop")):
        return "sudo apt update && sudo apt install -y autossh"
    if any(x in ids for x in ("fedora", "rhel", "centos")):
        return "sudo dnf install -y autossh"
    if any(x in ids for x in ("arch", "manjaro", "endeavouros")):
        return "sudo pacman -S --needed autossh"
    if any(x in ids for x in ("opensuse", "suse")):
        return "sudo zypper install -y autossh"
    if "alpine" in ids:
        return "sudo apk add autossh"
    return "sudo apt install -y autossh    # یا متناسب با پکیج‌منیجر توزیع شما"


def install_note(lang):
    """توضیح کامل‌تر نصب برای دیالوگ هشدار، وابسته به سیستم‌عامل و زبان."""
    cmd = install_primary_command()
    if OS == "windows":
        if lang == "fa":
            return ("روی ویندوز، autossh به‌صورت بومی وجود ندارد. دو راه:\n\n"
                    "۱) WSL (پیشنهادی):\n"
                    "   wsl --install\n"
                    "   سپس داخل اوبونتوی WSL:  sudo apt install -y autossh\n\n"
                    "۲) MSYS2:\n"
                    f"   {cmd}\n\n"
                    "پس از نصب، مطمئن شو autossh در PATH ویندوز هست.")
        return ("autossh has no native Windows build. Two options:\n\n"
                "1) WSL (recommended):\n"
                "   wsl --install\n"
                "   then inside WSL Ubuntu:  sudo apt install -y autossh\n\n"
                "2) MSYS2:\n"
                f"   {cmd}\n\n"
                "After install, make sure autossh is on the Windows PATH.")
    if OS == "macos":
        if lang == "fa":
            return ("روی macOS با Homebrew نصب کن:\n\n"
                    f"   {cmd}\n\n"
                    "اگر Homebrew نداری، اول از brew.sh نصبش کن.")
        return ("On macOS install with Homebrew:\n\n"
                f"   {cmd}\n\n"
                "If you don't have Homebrew, install it from brew.sh first.")
    # linux
    if lang == "fa":
        return f"دستور نصب برای توزیع شما:\n\n   {cmd}"
    return f"Install command for your distro:\n\n   {cmd}"


# ════════════════════════════ پراکسی سیستم (چندسکویی) ════════════════════════════
def gsettings_available():
    return OS == "linux" and shutil.which("gsettings") is not None


def proxy_supported():
    """آیا تنظیم خودکار پراکسی سیستم روی این OS ممکن است؟"""
    return OS == "windows" or gsettings_available()


# --- ویندوز: پراکسی WinINET از طریق رجیستری کاربر (بدون نیاز به ادمین) ---
def _win_set_proxy(enable, server=""):
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                         0, winreg.KEY_WRITE)
    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1 if enable else 0)
    if enable:
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, server)
    winreg.CloseKey(key)
    # اعلام تغییر به سیستم تا بلافاصله اعمال شود
    try:
        import ctypes
        internet = ctypes.windll.Wininet
        internet.InternetSetOptionW(0, 39, 0, 0)  # SETTINGS_CHANGED
        internet.InternetSetOptionW(0, 37, 0, 0)  # REFRESH
    except Exception:
        pass


def _gsettings_set(schema, key, value):
    """تنظیم یک کلید gsettings و تأیید واقعی اعمال آن.

    نکته: gsettings حتی وقتی commit به dconf شکست می‌خورد (مثلاً نبودِ
    باس D-Bus) با کد خروجی صفر بازمی‌گردد. به همین خاطر بعد از set،
    مقدار را دوباره می‌خوانیم و با مقدار موردانتظار مقایسه می‌کنیم.
    """
    res = subprocess.run(["gsettings", "set", schema, key, value],
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            (res.stderr or res.stdout or "gsettings set failed").strip())
    # اگر در stderr هشدار شکست commit بود، یعنی واقعاً اعمال نشده
    if "failed to commit" in (res.stderr or "").lower():
        raise RuntimeError((res.stderr or "").strip())
    return res


def _gsettings_get(schema, key):
    res = subprocess.run(["gsettings", "get", schema, key],
                         capture_output=True, text=True)
    return res.stdout.strip().strip("'") if res.returncode == 0 else None


def set_system_socks(port):
    """تنظیم SOCKS سیستم روی 127.0.0.1:port."""
    if OS == "windows":
        try:
            _win_set_proxy(True, f"socks=127.0.0.1:{port}")
            return True, f"System SOCKS set to 127.0.0.1:{port}."
        except Exception as e:
            return False, str(e)
    if gsettings_available():
        try:
            # ابتدا مقادیر socks، سپس فعال‌سازی حالت manual
            _gsettings_set("org.gnome.system.proxy.socks", "host", "127.0.0.1")
            _gsettings_set("org.gnome.system.proxy.socks", "port", str(int(port)))
            _gsettings_set("org.gnome.system.proxy", "mode", "manual")
            # تأیید: mode باید manual شده باشد
            if _gsettings_get("org.gnome.system.proxy", "mode") != "manual":
                return False, "Could not apply manual proxy mode (gsettings not committed)."
            return True, f"System SOCKS set to 127.0.0.1:{port}."
        except Exception as e:
            return False, str(e)
    return False, f"AUTO_PROXY_UNSUPPORTED:{port}"


def set_system_proxy_auto():
    """هنگام قطع: روی لینوکس → حالت Automatic (فعال)؛ روی ویندوز → غیرفعال (مستقیم).

    در GNOME سه حالت داریم: none / manual / auto. کاربر «حالت اتوماتیک
    فعال» را می‌خواهد، یعنی mode = 'auto'. مهم‌ترین گام تغییرِ خودِ mode
    است؛ پاک‌کردن host/port فقط برای تمیزماندن تنظیمات manual است و نباید
    مانع از تغییر mode شود. پس ابتدا mode را عوض می‌کنیم و آن را تأیید
    می‌کنیم، سپس مقادیر manual را پاک می‌کنیم.
    """
    if OS == "windows":
        try:
            _win_set_proxy(False)
            return True, "System proxy disabled (automatic/direct)."
        except Exception as e:
            return False, str(e)
    if gsettings_available():
        try:
            # گام کلیدی: حالت را روی auto بگذار و تأیید کن
            _gsettings_set("org.gnome.system.proxy", "mode", "auto")
            mode_now = _gsettings_get("org.gnome.system.proxy", "mode")
            if mode_now != "auto":
                return False, (
                    "Could not switch proxy to Automatic mode "
                    f"(mode is still '{mode_now}'). gsettings may have failed "
                    "to commit changes to dconf.")
            # حالا تنظیمات manual را پاک کن (شکستِ این مرحله بحرانی نیست)
            for key, val in (("host", ""), ("port", "0")):
                try:
                    _gsettings_set("org.gnome.system.proxy.socks", key, val)
                except Exception:
                    pass
            return True, "System proxy set to Automatic."
        except Exception as e:
            return False, str(e)
    return False, "AUTO_PROXY_UNSUPPORTED"


# ════════════════════════════ پراکسی ترمینال (متغیرهای محیطی) ════════════════════════════
# نکته: تونل SOCKS بدون مسیریابی TUN نمی‌تواند «به‌صورت شفاف» کل ترافیک
# سیستم را عبور دهد. برای ترمینال، راه استانداردِ بدون‌نیاز‌به‌روت این است
# که متغیرهای http_proxy/https_proxy/all_proxy را در یک فایل بنویسیم و آن را
# در فایل‌های راه‌اندازی شِل (.bashrc/.zshrc/.profile) سورس کنیم. هنگام قطع،
# فایل را خالی می‌کنیم تا پراکسی برود. برنامه این خط را خودکار اضافه/حذف می‌کند.
PROXY_ENV_FILE = CONFIG_DIR / "proxy.env"
_PROXY_ENV_DISPLAY = f"~/.config/{APP_SLUG}/proxy.env"
# نشانه‌های بلوکِ مدیریت‌شده در فایل‌های شِل (برای افزودن/حذف خودکار)
RC_MARK_BEGIN = "# >>> SSH Tunnel Manager proxy >>>"
RC_MARK_END = "# <<< SSH Tunnel Manager proxy <<<"
RC_SOURCE_LINE = f'[ -f "{PROXY_ENV_FILE}" ] && . "{PROXY_ENV_FILE}"'
# فایل‌هایی که خط سورس را در آن‌ها مدیریت می‌کنیم (هرکدام که وجود داشته باشد)
_RC_CANDIDATES = [".bashrc", ".zshrc", ".profile"]


def write_terminal_proxy(port):
    """نوشتن متغیرهای محیطی پراکسی برای ترمینال (شِل‌هایی که فایل را سورس می‌کنند)."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        socks = f"socks5h://127.0.0.1:{int(port)}"
        body = (
            "# auto-generated by SSH Tunnel Manager — do not edit\n"
            f"export http_proxy=\"{socks}\"\n"
            f"export https_proxy=\"{socks}\"\n"
            f"export ftp_proxy=\"{socks}\"\n"
            f"export all_proxy=\"{socks}\"\n"
            f"export HTTP_PROXY=\"{socks}\"\n"
            f"export HTTPS_PROXY=\"{socks}\"\n"
            f"export FTP_PROXY=\"{socks}\"\n"
            f"export ALL_PROXY=\"{socks}\"\n"
            "export no_proxy=\"localhost,127.0.0.1,::1\"\n"
            "export NO_PROXY=\"localhost,127.0.0.1,::1\"\n"
        )
        PROXY_ENV_FILE.write_text(body, "utf-8")
        return True, f"Terminal proxy env written (socks5h 127.0.0.1:{port})."
    except Exception as e:
        return False, str(e)


def clear_terminal_proxy():
    """خالی‌کردن متغیرهای پراکسی ترمینال (unset) هنگام قطع."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        body = (
            "# auto-generated by SSH Tunnel Manager — tunnel is OFF\n"
            "unset http_proxy https_proxy ftp_proxy all_proxy no_proxy\n"
            "unset HTTP_PROXY HTTPS_PROXY FTP_PROXY ALL_PROXY NO_PROXY\n"
        )
        PROXY_ENV_FILE.write_text(body, "utf-8")
        return True, "Terminal proxy env cleared."
    except Exception as e:
        return False, str(e)


def _rc_targets():
    """فایل‌های شِلی که باید خط سورس در آن‌ها مدیریت شود.

    اگر هیچ‌کدام وجود نداشت، .bashrc را به‌عنوان پیش‌فرض می‌سازد.
    """
    home = Path.home()
    found = [home / name for name in _RC_CANDIDATES if (home / name).exists()]
    if not found:
        found = [home / ".bashrc"]
    return found


def _strip_managed_block(text):
    """حذف بلوک مدیریت‌شدهٔ قبلی (بین نشانه‌ها) از متن یک فایل rc."""
    lines = text.splitlines()
    out = []
    skip = False
    for ln in lines:
        if ln.strip() == RC_MARK_BEGIN:
            skip = True
            continue
        if ln.strip() == RC_MARK_END:
            skip = False
            continue
        if not skip:
            out.append(ln)
    return "\n".join(out)


def install_rc_hook():
    """افزودن خودکارِ خط سورسِ proxy.env به فایل‌های شِل (idempotent)."""
    if OS == "windows":
        return False, "Not applicable on Windows."
    done = []
    try:
        for rc in _rc_targets():
            old = rc.read_text("utf-8") if rc.exists() else ""
            cleaned = _strip_managed_block(old)
            block = f"{RC_MARK_BEGIN}\n{RC_SOURCE_LINE}\n{RC_MARK_END}"
            new = (cleaned.rstrip("\n") + "\n\n" + block + "\n") if cleaned.strip() else (block + "\n")
            rc.write_text(new, "utf-8")
            done.append(rc.name)
        return True, "Shell hook installed in: " + ", ".join(done)
    except Exception as e:
        return False, str(e)


def remove_rc_hook():
    """حذف خودکارِ خط سورس از فایل‌های شِل."""
    if OS == "windows":
        return False, "Not applicable on Windows."
    changed = []
    try:
        home = Path.home()
        for name in _RC_CANDIDATES:
            rc = home / name
            if not rc.exists():
                continue
            old = rc.read_text("utf-8")
            if RC_MARK_BEGIN in old:
                rc.write_text(_strip_managed_block(old).rstrip("\n") + "\n", "utf-8")
                changed.append(rc.name)
        if changed:
            return True, "Shell hook removed from: " + ", ".join(changed)
        return True, "No shell hook to remove."
    except Exception as e:
        return False, str(e)


def rc_hook_installed():
    """آیا خط سورس در یکی از فایل‌های شِل هست؟"""
    if OS == "windows":
        return False
    home = Path.home()
    for name in _RC_CANDIDATES:
        rc = home / name
        try:
            if rc.exists() and RC_MARK_BEGIN in rc.read_text("utf-8"):
                return True
        except Exception:
            pass
    return False


# ════════════════════════════ اجرای خودکار هنگام بوت ════════════════════════════
AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / f"{APP_SLUG}.desktop"
_OLD_AUTOSTART_FILE = AUTOSTART_DIR / "autossh-manager.desktop"


def _app_launch_command():
    """دستوری که برنامه را دوباره اجرا می‌کند (همین اسکریپت با همین مفسر پایتون)."""
    script = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else __file__
    py = sys.executable or "python3"
    return f'"{py}" "{script}"'


def autostart_enabled():
    if OS == "linux":
        return AUTOSTART_FILE.exists() or _OLD_AUTOSTART_FILE.exists()
    if OS == "windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run")
            try:
                winreg.QueryValueEx(key, APP_NAME)
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False
    return False


def set_autostart(enable):
    """فعال/غیرفعال‌کردن اجرای برنامه هنگام ورود کاربر."""
    try:
        if OS == "linux":
            if enable:
                AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
                content = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    f"Name={APP_NAME}\n"
                    f"Exec={_app_launch_command()}\n"
                    "X-GNOME-Autostart-enabled=true\n"
                    "Terminal=false\n"
                )
                AUTOSTART_FILE.write_text(content, "utf-8")
                # حذف فایل با نام قدیمی اگر باقی مانده باشد
                if _OLD_AUTOSTART_FILE.exists():
                    try:
                        _OLD_AUTOSTART_FILE.unlink()
                    except Exception:
                        pass
            else:
                for f in (AUTOSTART_FILE, _OLD_AUTOSTART_FILE):
                    if f.exists():
                        try:
                            f.unlink()
                        except Exception:
                            pass
            return True, ""
        if OS == "windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_WRITE)
            if enable:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ,
                                  _app_launch_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True, ""
        return False, "Autostart not supported on this OS."
    except Exception as e:
        return False, str(e)


def _pid_is_autossh(pid):
    """آیا این PID واقعاً یک فرایند autossh است؟ (محافظت در برابر PIDِ بازاستفاده‌شده)"""
    pid = int(pid)
    if pid <= 0:
        return False
    try:
        if OS == "windows":
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                                 capture_output=True, text=True).stdout.lower()
            return "autossh" in out
        # لینوکس/مک: نام فرایند را بخوان
        comm = Path(f"/proc/{pid}/comm").read_text().strip() if OS == "linux" else ""
        if OS == "linux":
            return comm == "autossh"
        out = subprocess.run(["ps", "-p", str(pid), "-o", "comm="],
                             capture_output=True, text=True).stdout.strip()
        return out.endswith("autossh")
    except Exception:
        return False


def kill_pid_tree(pid):
    """کشتن یک PID مشخص و فرزندانش (مثلاً ssh که autossh ساخته)، چندسکویی.

    فقط همان فرایندی را می‌کشد که برنامه ساخته است، و پیش از کشتن مطمئن
    می‌شود که واقعاً autossh است (تا اگر PID بازاستفاده شده باشد، فرایند
    بی‌ربط دیگری کشته نشود).
    """
    pid = int(pid)
    if not _pid_is_autossh(pid):
        return False
    try:
        if OS == "windows":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        subprocess.run(["pkill", "-TERM", "-P", str(pid)], check=False)
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        return True
    except Exception:
        return False


def force_kill_pid(pid):
    """اطمینان از بسته‌شدن: اگر هنوز زنده بود، SIGKILL."""
    pid = int(pid)
    if pid <= 0 or OS == "windows":
        return
    try:
        os.kill(pid, 0)  # هنوز زنده است؟
        subprocess.run(["pkill", "-KILL", "-P", str(pid)], check=False)
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    except ProcessLookupError:
        pass  # قبلاً بسته شده
    except Exception:
        pass


# ════════════════════════════ کشوی جانبی لاگ ════════════════════════════
class LogDrawer(QtWidgets.QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("logDrawer")
        self._w = 360
        self._open = False
        self.setMaximumWidth(0)
        self.setMinimumWidth(0)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 4, 16);
        lay.setSpacing(10)
        head = QtWidgets.QHBoxLayout()
        self.title = QtWidgets.QLabel(title);
        self.title.setObjectName("h2")
        self.close_btn = QtWidgets.QPushButton("✕");
        self.close_btn.setObjectName("winBtn")
        self.close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        head.addWidget(self.title);
        head.addStretch(1);
        head.addWidget(self.close_btn)
        lay.addLayout(head)
        self.view = QtWidgets.QTextEdit();
        self.view.setObjectName("logView")
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.view.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        lay.addWidget(self.view, 1)
        self.anim = QtCore.QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(240)
        self.anim.setEasingCurve(QtCore.QEasingCurve.InOutCubic)
        self.anim.valueChanged.connect(lambda val: self.setMinimumWidth(int(val)))

    def set_title(self, t):
        self.title.setText(t)

    def append(self, text):
        self.view.append(text)
        self.view.verticalScrollBar().setValue(self.view.verticalScrollBar().maximum())


# ════════════════════════════ ردیف سرور ════════════════════════════
class ServerRow(QtWidgets.QWidget):
    edit = QtCore.pyqtSignal(str)
    remove = QtCore.pyqtSignal(str)

    def __init__(self, prof, edit_label, parent=None):
        super().__init__(parent)
        self.pid = prof["id"]
        self.setMinimumHeight(66)
        box = QtWidgets.QFrame(self);
        box.setObjectName("subcard")
        outer = QtWidgets.QVBoxLayout(self);
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(box)
        h = QtWidgets.QHBoxLayout(box);
        h.setContentsMargins(14, 12, 12, 12);
        h.setSpacing(10)
        info = QtWidgets.QVBoxLayout();
        info.setSpacing(3)
        name = QtWidgets.QLabel(prof.get("name", "—"));
        name.setObjectName("h2")
        sub = QtWidgets.QLabel(
            f"{prof.get('user', 'root')}@{prof.get('ip', '—')}:{prof.get('ssh_port', '22')}"
            f"   •   D{prof.get('dyn_port', '1085')}  M{prof.get('mon_port', '0')}")
        sub.setObjectName("muted");
        sub.setStyleSheet("font-size:11px;")
        info.addWidget(name);
        info.addWidget(sub)
        h.addLayout(info, 1)
        eb = QtWidgets.QPushButton(edit_label)
        eb.setCursor(QtCore.Qt.PointingHandCursor)
        eb.setMinimumWidth(84)
        eb.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        eb.clicked.connect(lambda: self.edit.emit(self.pid))
        db = QtWidgets.QPushButton("✕");
        db.setObjectName("dangerBtn")
        db.setFixedWidth(42);
        db.setCursor(QtCore.Qt.PointingHandCursor)
        db.clicked.connect(lambda: self.remove.emit(self.pid))
        h.addWidget(eb, 0);
        h.addWidget(db, 0)


# ════════════════════════════ دیالوگ سرور ════════════════════════════
class ServerDialog(QtWidgets.QDialog):
    def __init__(self, parent, theme, lang, prof=None):
        super().__init__(parent)
        t = TR[lang]
        self._c = theme
        self.setWindowTitle(t["dlg_title"]);
        self.setModal(True);
        self.setMinimumWidth(430)
        self.setStyleSheet(qss(theme))
        # اطمینان از اعمال رنگ پس‌زمینه روی خود پنجرهٔ دیالوگ
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor(theme["bg"]))
        pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(theme["text"]))
        pal.setColor(QtGui.QPalette.Base, QtGui.QColor(theme["card"]))
        pal.setColor(QtGui.QPalette.Text, QtGui.QColor(theme["text"]))
        pal.setColor(QtGui.QPalette.Button, QtGui.QColor(theme["card2"]))
        pal.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(theme["text"]))
        self.setPalette(pal)
        self.setLayoutDirection(QtCore.Qt.RightToLeft if lang == "fa" else QtCore.Qt.LeftToRight)
        prof = prof or {}
        form = QtWidgets.QFormLayout(self)
        form.setSpacing(10);
        form.setContentsMargins(18, 18, 18, 18)
        self.name = QtWidgets.QLineEdit(prof.get("name", ""));
        self.name.setPlaceholderText(t["ph_name"])
        self.ip = QtWidgets.QLineEdit(prof.get("ip", ""));
        self.ip.setPlaceholderText(t["ph_ip"])
        self.user = QtWidgets.QLineEdit(prof.get("user", "root"))
        self.ssh_port = QtWidgets.QLineEdit(str(prof.get("ssh_port", "22")))
        self.dyn_port = QtWidgets.QLineEdit(str(prof.get("dyn_port", "1085")))
        self.mon_port = QtWidgets.QLineEdit(str(prof.get("mon_port", "0")))
        self.mon_port.setPlaceholderText("0")
        self.key = QtWidgets.QLineEdit(prof.get("key", ""));
        self.key.setPlaceholderText(t["ph_key"])
        self.password = QtWidgets.QLineEdit(prof.get("password", ""))
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setPlaceholderText(t["ph_pass"])
        self.extra = QtWidgets.QLineEdit(prof.get("extra", ""));
        self.extra.setPlaceholderText(t["ph_extra"])
        self.set_socks = QtWidgets.QCheckBox(t["set_socks_chk"])
        self.set_socks.setChecked(prof.get("set_socks", True))
        form.addRow(t["f_name"], self.name)
        form.addRow(t["f_ip"], self.ip)
        form.addRow(t["f_user"], self.user)
        form.addRow(t["f_ssh"], self.ssh_port)
        form.addRow(t["f_dyn"], self.dyn_port)
        form.addRow(t["f_mon"], self.mon_port)
        form.addRow(t["f_key"], self.key)
        form.addRow(t["f_pass"], self.password)
        form.addRow(t["f_extra"], self.extra)
        form.addRow("", self.set_socks)
        btns = QtWidgets.QHBoxLayout()
        ok = QtWidgets.QPushButton(t["save"]);
        ok.setObjectName("primaryBtn");
        ok.setCursor(QtCore.Qt.PointingHandCursor)
        ok.clicked.connect(self._accept)
        cancel = QtWidgets.QPushButton(t["cancel"]);
        cancel.setCursor(QtCore.Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        self.set_socks.setCursor(QtCore.Qt.PointingHandCursor)
        btns.addStretch(1);
        btns.addWidget(cancel);
        btns.addWidget(ok)
        form.addRow(btns)
        self._prof = prof;
        self._t = t

    def _accept(self):
        if not self.ip.text().strip():
            mb = QtWidgets.QMessageBox(self)
            mb.setIcon(QtWidgets.QMessageBox.Warning)
            mb.setWindowTitle(self._t["error"])
            mb.setText(self._t["enter_ip"])
            mb.setStyleSheet(qss(self._c))
            mb.exec_()
            return
        self.accept()

    def data(self):
        return {
            "id": self._prof.get("id") or os.urandom(4).hex(),
            "name": self.name.text().strip() or "—",
            "ip": self.ip.text().strip(),
            "user": self.user.text().strip() or "root",
            "ssh_port": self.ssh_port.text().strip() or "22",
            "dyn_port": self.dyn_port.text().strip() or "1085",
            "mon_port": self.mon_port.text().strip() or "0",
            "key": self.key.text().strip(),
            "password": self.password.text(),
            "extra": self.extra.text().strip(),
            "set_socks": self.set_socks.isChecked(),
        }


# ════════════════════════════ پنجرهٔ اصلی ════════════════════════════
class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = self.load_config()
        self.lang = self.cfg.get("lang", "fa")
        self.theme_name = self.cfg.get("theme", "light")
        self.scale = self.cfg.get("scale", 100)
        self._autossh_installed = None
        self._proxy_applied = False
        self.tunnel = TunnelController()
        self.tunnel.log.connect(self.on_log)
        self.tunnel.state_changed.connect(self.on_state)
        self.tunnel.pid_started.connect(self._track_pid)
        self.tunnel.pid_stopped.connect(self._untrack_pid)
        self.tunnel.failed.connect(self._on_tunnel_failed)

        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._drag = None
        self._really_quit = False
        # تایمر دیبانس برای ذخیرهٔ اندازهٔ پنجره هنگام تغییر اندازه
        self._save_size_timer = QtCore.QTimer(self)
        self._save_size_timer.setSingleShot(True)
        self._save_size_timer.timeout.connect(self._persist_window_size)

        self._build_ui()
        self.apply_theme()
        self.refresh_servers()
        self.retranslate()
        self._build_tray()

        scr = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.setMinimumSize(360, 420)
        # عرض/ارتفاع ذخیره‌شده را بازیابی کن؛ در نبودِ آن، عرض پیش‌فرض
        saved_w = self.cfg.get("win_w")
        saved_h = self.cfg.get("win_h")
        default_w = min(int(scr.width() * 0.42), 560)
        init_w = int(saved_w) if saved_w else max(default_w, 430)
        self.resize(init_w, int(saved_h) if saved_h else 640)
        self.move(scr.center().x() - self.width() // 2, scr.center().y() - self.height() // 2)
        # اگر ارتفاعی ذخیره نشده، ارتفاع پیش‌فرض = اندازهٔ محتوای تب «خانه»
        if not saved_h:
            QtCore.QTimer.singleShot(0, self._fit_height_to_home)
        QtCore.QTimer.singleShot(400, self.check_autossh_installed)
        # اتصال خودکار به آخرین سرور هنگام اجرا (اگر هر دو گزینه فعال باشند)
        if self.cfg.get("autostart", False) and self.cfg.get("autoconnect", False):
            QtCore.QTimer.singleShot(900, self._maybe_autoconnect)

    def _fit_height_to_home(self):
        """ارتفاع پیش‌فرض پنجره = ارتفاع محتوای تب خانه. ارتفاع قفل نمی‌شود؛
        کاربر می‌تواند آزادانه تغییرش دهد (و ذخیره می‌شود)."""
        try:
            scr = QtWidgets.QApplication.primaryScreen().availableGeometry()
            home_h = self.home_page.sizeHint().height()
            chrome = self.height() - self.stack.height()  # هدر+تب‌بار+مارجین‌ها
            target = home_h + max(chrome, 0)
            target = max(480, min(target, int(scr.height() * 0.95)))
            self.resize(self.width(), target)
            self.cfg["win_h"] = target
            self.cfg["win_w"] = self.width()
            self.save_config()
            self.move(self.x(), max(scr.top() + 10, scr.center().y() - target // 2))
        except Exception:
            pass

    def _maybe_autoconnect(self):
        if self.tunnel.state in ("on", "connecting", "reconnecting"):
            return
        p = self.active_server()
        if p and shutil.which("autossh"):
            self._cleanup_orphan_tunnels()
            self.on_log("▶ Auto-connecting to last server…")
            self.tunnel.start(p)

    def _cleanup_orphan_tunnels(self):
        """پیش از باز کردن تونل جدید، تونل‌های یتیمِ به‌جامانده از اجرای قبلی
        (که در config ردیابی شده‌اند) را می‌بندد تا چند فرایند روی هم جمع
        نشوند و حافظهٔ سیستم پر نشود."""
        live_pid = int(self.tunnel.proc.processId()) if self.tunnel.proc else 0
        n = 0
        for x in list(self._tracked_pids()):
            try:
                pid = int(x)
            except Exception:
                continue
            if pid and pid != live_pid and _pid_is_autossh(pid):
                if kill_pid_tree(pid):
                    n += 1
                if OS != "windows":
                    force_kill_pid(pid)
        if n:
            self.on_log(f"🧹 Cleaned {n} leftover tunnel(s) before connecting.")
        # فهرست ردیابی را به فرایند زنده محدود کن
        self.cfg["tracked_pids"] = [live_pid] if live_pid else []
        self.save_config()

    def t(self, key):
        return TR[self.lang][key]

    # ───────── ساخت رابط ─────────
    def _build_ui(self):
        shell = QtWidgets.QHBoxLayout(self)
        shell.setContentsMargins(14, 14, 14, 14);
        shell.setSpacing(0)

        # تنها یک کارت بیرونی با یک سایه (یکپارچه)
        self.root = QtWidgets.QFrame();
        self.root.setObjectName("root")
        eff = QtWidgets.QGraphicsDropShadowEffect(blurRadius=40, xOffset=0, yOffset=12)
        eff.setColor(QtGui.QColor(0, 0, 0, 60));
        self.root.setGraphicsEffect(eff)
        shell.addWidget(self.root)

        body = QtWidgets.QHBoxLayout(self.root)
        body.setContentsMargins(0, 0, 0, 0);
        body.setSpacing(0)
        # ترتیب ثابت چپ‌به‌راست تا کشوی لاگ همیشه سمت چپ بماند (حتی در RTL)
        body.setDirection(QtWidgets.QBoxLayout.LeftToRight)

        # کشوی لاگ (داخل همان کارت، سمت چپ)
        self.drawer = LogDrawer(self.t("logs_title"))
        self.drawer.close_btn.clicked.connect(self.toggle_logs)
        self.drawer.anim.finished.connect(self._log_anim_done)
        body.addWidget(self.drawer)

        # دستهٔ باریک باز/بست
        self.handle = QtWidgets.QPushButton("‹")
        self.handle.setObjectName("logHandle")
        self.handle.setCursor(QtCore.Qt.PointingHandCursor)
        self.handle.setFixedWidth(18)
        self.handle.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        self.handle.clicked.connect(self.toggle_logs)
        body.addWidget(self.handle)

        # ستون محتوای اصلی (سمت راست)
        content = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(content);
        v.setContentsMargins(18, 14, 18, 16);
        v.setSpacing(14)
        body.addWidget(content, 1)

        header = QtWidgets.QWidget();
        header.setObjectName("header")
        hl = QtWidgets.QHBoxLayout(header);
        hl.setContentsMargins(0, 0, 0, 0)
        title = QtWidgets.QLabel("SSH Tunnel Manager");
        title.setObjectName("titleLbl")
        self.theme_btn = QtWidgets.QPushButton("🌙");
        self.theme_btn.setObjectName("winBtn")
        self.theme_btn.setCursor(QtCore.Qt.PointingHandCursor);
        self.theme_btn.clicked.connect(self.toggle_theme)
        mn = QtWidgets.QPushButton("—");
        mn.setObjectName("winBtn");
        mn.clicked.connect(self.showMinimized)
        cl = QtWidgets.QPushButton("✕");
        cl.setObjectName("closeBtn");
        cl.clicked.connect(self.close)
        header.mousePressEvent = self._header_press
        header.mouseMoveEvent = self._header_move
        header.mouseDoubleClickEvent = lambda e: self.toggle_max()
        hl.addWidget(title);
        hl.addStretch(1)
        hl.addWidget(self.theme_btn);
        hl.addWidget(mn);
        hl.addWidget(cl)
        v.addWidget(header)

        self.stack = QtWidgets.QStackedWidget()
        self.home_page = self._page_home()
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self._wrap_scroll(self._page_servers()))
        self.stack.addWidget(self._wrap_scroll(self._page_settings()))
        v.addWidget(self.stack, 1)

        v.addWidget(self._tabbar())
        self.grip = QtWidgets.QSizeGrip(self.root)
        # نشانگر دست (pointer) برای همهٔ کنترل‌های قابل‌کلیک
        self._apply_pointer_cursors()

    def _apply_pointer_cursors(self):
        """نشانگر موس را روی همهٔ ویجت‌های تعاملی به حالت دست تنظیم می‌کند."""
        types = (QtWidgets.QPushButton, QtWidgets.QCheckBox,
                 QtWidgets.QRadioButton, QtWidgets.QComboBox,
                 QtWidgets.QSlider, QtWidgets.QToolButton)
        for w in self.findChildren(QtWidgets.QWidget):
            if isinstance(w, types):
                w.setCursor(QtCore.Qt.PointingHandCursor)
        # دکمهٔ پاور و برچسب‌های کلیک‌پذیرِ چک‌باکس‌ها
        if hasattr(self, "power"):
            self.power.setCursor(QtCore.Qt.PointingHandCursor)
        for lbl in (getattr(self, "autostart_lbl", None),
                    getattr(self, "autoconnect_lbl", None),
                    getattr(self, "term_proxy_lbl", None)):
            if lbl is not None:
                lbl.setCursor(QtCore.Qt.PointingHandCursor)

    # ───────── باز/بستن کشوی لاگ ─────────
    def toggle_logs(self):
        opening = not self.drawer._open
        self.drawer._open = opening
        dw = self.drawer._w
        self.drawer.anim.stop()
        if opening:
            self.resize(self.width() + dw, self.height())
            self.drawer.anim.setStartValue(self.drawer.maximumWidth())
            self.drawer.anim.setEndValue(dw)
        else:
            self.drawer.anim.setStartValue(self.drawer.maximumWidth())
            self.drawer.anim.setEndValue(0)
        self.drawer.anim.start()
        self.handle.setText("›" if opening else "‹")
        self.handle.setToolTip(self.t("logs_title"))

    def _log_anim_done(self):
        # پس از بسته‌شدن کامل، پهنای پنجره را به حالت اولیه برگردان
        if not self.drawer._open:
            self.resize(max(self.width() - self.drawer._w, 430), self.height())

    def _tabbar(self):
        bar = QtWidgets.QFrame()
        bar.setObjectName("tabbar")
        bl = QtWidgets.QHBoxLayout(bar)
        bl.setContentsMargins(8, 6, 8, 6)
        bl.setSpacing(6)
        self.tabs = []
        self._tab_icons = ["🔘", "📡", "⚙️"]
        self._tab_keys = ["tab_home", "tab_servers", "tab_settings"]
        for i, icon in enumerate(self._tab_icons):
            b = QtWidgets.QPushButton(f"{icon}\n")
            b.setStyleSheet("""
                QPushButton {
                    font-size: 15px;
                }
            """)
            b.setObjectName("tabBtn")
            b.setCheckable(True)
            b.setCursor(QtCore.Qt.PointingHandCursor)
            b.clicked.connect(lambda _, n=i: self.switch_tab(n))
            bl.addWidget(b)
            self.tabs.append(b)
        self.tabs[0].setChecked(True)
        return bar

    def switch_tab(self, n):
        for i, b in enumerate(self.tabs):
            b.setChecked(i == n)
        self.stack.setCurrentIndex(n)
        if n == 1:
            self.refresh_servers()

    def _wrap_scroll(self, inner):
        """قراردادن یک صفحه داخل ناحیهٔ اسکرول‌شونده (برای تب‌های سرورها و تنظیمات).

        فقط اسکرول عمودی؛ محتوا با عرض پنجره هم‌اندازه می‌شود (ریسپانسیو) و
        افقی اسکرول نمی‌شود.
        """
        # اجازه بده محتوا تا عرض کم جمع شود تا کلیپ/اسکرول افقی رخ ندهد
        inner.setMinimumWidth(0)
        inner.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                            QtWidgets.QSizePolicy.Preferred)
        sa = QtWidgets.QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QtWidgets.QFrame.NoFrame)
        sa.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        sa.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        sa.setMinimumWidth(0)
        sa.setWidget(inner)
        return sa

    def _wrap_checkbox(self, on_toggled, checked=False, enabled=True):
        """چک‌باکس با متنِ کنارِ آن که سطرشکن (word-wrap) است تا در عرض کم
        به‌جای کلیپ‌شدن، به خط بعد برود. متن بعداً در retranslate ست می‌شود.
        برمی‌گرداند: (container_layout, checkbox, label)
        """
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        cb = QtWidgets.QCheckBox("")
        cb.setChecked(checked)
        cb.setEnabled(enabled)
        cb.toggled.connect(on_toggled)
        lbl = QtWidgets.QLabel("")
        lbl.setWordWrap(True)
        lbl.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                          QtWidgets.QSizePolicy.Preferred)
        # کلیک روی متن هم چک‌باکس را تغییر دهد (اگر فعال باشد)
        lbl.mousePressEvent = lambda e, c=cb: (c.toggle() if c.isEnabled() else None)
        row.addWidget(cb, 0, QtCore.Qt.AlignTop)
        row.addWidget(lbl, 1)
        return row, cb, lbl

    # ───────── صفحهٔ خانه ─────────
    def _page_home(self):
        page = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout(page);
        l.setContentsMargins(2, 4, 2, 2);
        l.setSpacing(14)
        pill = QtWidgets.QFrame();
        pill.setObjectName("pill")
        pl = QtWidgets.QHBoxLayout(pill);
        pl.setContentsMargins(14, 8, 10, 8);
        pl.setSpacing(10)
        self.dot = QtWidgets.QLabel("●");
        self.dot.setStyleSheet("color:#9aa3b5; font-size:14px;")
        col = QtWidgets.QVBoxLayout();
        col.setSpacing(0)
        self.pill_name = QtWidgets.QLabel("");
        self.pill_name.setObjectName("pillName")
        self.pill_sub = QtWidgets.QLabel("—");
        self.pill_sub.setObjectName("pillSub")
        col.addWidget(self.pill_name);
        col.addWidget(self.pill_sub)
        self.server_combo = QtWidgets.QComboBox();
        self.server_combo.setMinimumWidth(150)
        self.server_combo.currentIndexChanged.connect(self.on_pick_server)
        pl.addWidget(self.dot);
        pl.addLayout(col);
        pl.addStretch(1);
        pl.addWidget(self.server_combo)
        l.addWidget(pill)

        center = QtWidgets.QFrame();
        center.setObjectName("card")
        cv = QtWidgets.QVBoxLayout(center);
        cv.setContentsMargins(20, 26, 20, 26);
        cv.setSpacing(12)
        self.power = PowerButton();
        self.power.clicked.connect(self.toggle_tunnel)
        cv.addWidget(self.power, 0, QtCore.Qt.AlignHCenter)
        self.status_lbl = QtWidgets.QLabel("");
        self.status_lbl.setObjectName("status")
        self.status_lbl.setAlignment(QtCore.Qt.AlignCenter)
        cv.addWidget(self.status_lbl)
        l.addWidget(center)

        info = QtWidgets.QFrame();
        info.setObjectName("card")
        il = QtWidgets.QVBoxLayout(info);
        il.setContentsMargins(16, 14, 16, 14);
        il.setSpacing(10)
        self.row_server = self._inforow("—")
        self.row_tunnel = self._inforow("—")
        self.row_socks = self._inforow("—")
        for r in (self.row_server, self.row_tunnel, self.row_socks):
            il.addLayout(r)
        sl = QtWidgets.QHBoxLayout()
        self.socks_set_btn = QtWidgets.QPushButton();
        self.socks_set_btn.clicked.connect(self.manual_set_socks)
        self.socks_auto_btn = QtWidgets.QPushButton();
        self.socks_auto_btn.clicked.connect(self.manual_auto_proxy)
        sl.addWidget(self.socks_set_btn);
        sl.addWidget(self.socks_auto_btn)
        il.addLayout(sl)
        l.addWidget(info);
        l.addStretch(1)
        return page

    def _inforow(self, value):
        h = QtWidgets.QHBoxLayout()
        a = QtWidgets.QLabel("");
        a.setObjectName("muted")
        b = QtWidgets.QLabel(value);
        b.setObjectName("h2")
        b.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        h.addWidget(a);
        h.addStretch(1);
        h.addWidget(b)
        h._label = a;
        h._value = b
        return h

    # ───────── صفحهٔ سرورها ─────────
    def _page_servers(self):
        page = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout(page);
        l.setContentsMargins(2, 4, 2, 2);
        l.setSpacing(12)
        top = QtWidgets.QHBoxLayout()
        self.servers_title = QtWidgets.QLabel("");
        self.servers_title.setObjectName("h1")
        self.add_btn = QtWidgets.QPushButton("");
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.clicked.connect(self.add_server)
        top.addWidget(self.servers_title);
        top.addStretch(1);
        top.addWidget(self.add_btn)
        l.addLayout(top)
        self.server_list = QtWidgets.QListWidget()
        self.server_list.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        l.addWidget(self.server_list, 1)
        return page

    # ───────── صفحهٔ تنظیمات ─────────
    def _page_settings(self):
        page = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout(page);
        l.setContentsMargins(2, 4, 2, 2);
        l.setSpacing(14)
        self.settings_title = QtWidgets.QLabel("");
        self.settings_title.setObjectName("h1")
        l.addWidget(self.settings_title)

        # autossh
        c1 = QtWidgets.QFrame();
        c1.setObjectName("card")
        c1l = QtWidgets.QVBoxLayout(c1);
        c1l.setContentsMargins(16, 14, 16, 14);
        c1l.setSpacing(8)
        row = QtWidgets.QHBoxLayout()
        self.autossh_label = QtWidgets.QLabel("");
        self.autossh_label.setObjectName("muted")
        self.autossh_status = QtWidgets.QLabel("");
        self.autossh_status.setObjectName("h2")
        row.addWidget(self.autossh_label);
        row.addStretch(1);
        row.addWidget(self.autossh_status)
        c1l.addLayout(row)
        self.install_cmd = QtWidgets.QLineEdit(install_primary_command())
        self.install_cmd.setReadOnly(True);
        self.install_cmd.setMinimumWidth(0)
        self.install_cmd.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                                       QtWidgets.QSizePolicy.Fixed)
        self.install_cmd.setCursorPosition(0)
        c1l.addWidget(self.install_cmd)
        ib = QtWidgets.QHBoxLayout()
        self.copy_btn = QtWidgets.QPushButton("")
        self.copy_btn.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(self.install_cmd.text()))
        self.recheck_btn = QtWidgets.QPushButton("");
        self.recheck_btn.clicked.connect(self.check_autossh_installed)
        ib.addWidget(self.copy_btn);
        ib.addWidget(self.recheck_btn)
        c1l.addLayout(ib)
        l.addWidget(c1)

        # language + scale + theme
        c2 = QtWidgets.QFrame();
        c2.setObjectName("card")
        c2l = QtWidgets.QVBoxLayout(c2);
        c2l.setContentsMargins(16, 14, 16, 14);
        c2l.setSpacing(10)
        lrow = QtWidgets.QHBoxLayout()
        self.lang_label = QtWidgets.QLabel("")
        self.lang_combo = QtWidgets.QComboBox()
        self.lang_combo.addItem(TR["fa"]["fa_name"], "fa")
        self.lang_combo.addItem(TR["en"]["en_name"], "en")
        self.lang_combo.setCurrentIndex(0 if self.lang == "fa" else 1)
        self.lang_combo.currentIndexChanged.connect(self.on_lang_change)
        lrow.addWidget(self.lang_label);
        lrow.addStretch(1);
        lrow.addWidget(self.lang_combo)
        c2l.addLayout(lrow)
        srow = QtWidgets.QHBoxLayout()
        self.scale_label = QtWidgets.QLabel("")
        self.scale_lbl = QtWidgets.QLabel(f"{self.scale}%")
        srow.addWidget(self.scale_label);
        srow.addStretch(1);
        srow.addWidget(self.scale_lbl)
        c2l.addLayout(srow)
        self.scale_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.scale_slider.setRange(80, 160);
        self.scale_slider.setValue(self.scale)
        self.scale_slider.valueChanged.connect(self.on_scale)
        c2l.addWidget(self.scale_slider)
        trow = QtWidgets.QHBoxLayout()
        self.theme_label = QtWidgets.QLabel("")
        self.theme_toggle_btn = QtWidgets.QPushButton("");
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        trow.addWidget(self.theme_label);
        trow.addStretch(1);
        trow.addWidget(self.theme_toggle_btn)
        c2l.addLayout(trow)
        l.addWidget(c2)

        # startup (autostart + auto-connect)
        c_start = QtWidgets.QFrame();
        c_start.setObjectName("card")
        csl = QtWidgets.QVBoxLayout(c_start);
        csl.setContentsMargins(16, 14, 16, 14);
        csl.setSpacing(8)
        self.startup_title = QtWidgets.QLabel("");
        self.startup_title.setObjectName("h2")
        self.startup_title.setWordWrap(True)
        csl.addWidget(self.startup_title)
        as_row, self.autostart_chk, self.autostart_lbl = self._wrap_checkbox(
            self.on_autostart_toggled, checked=bool(self.cfg.get("autostart", False)))
        csl.addLayout(as_row)
        ac_row, self.autoconnect_chk, self.autoconnect_lbl = self._wrap_checkbox(
            self.on_autoconnect_toggled,
            checked=bool(self.cfg.get("autoconnect", False)),
            enabled=self.autostart_chk.isChecked())
        csl.addLayout(ac_row)
        l.addWidget(c_start)

        # terminal / system-wide proxy
        c_term = QtWidgets.QFrame();
        c_term.setObjectName("card")
        ctl = QtWidgets.QVBoxLayout(c_term);
        ctl.setContentsMargins(16, 14, 16, 14);
        ctl.setSpacing(8)
        self.term_proxy_title = QtWidgets.QLabel("");
        self.term_proxy_title.setObjectName("h2")
        self.term_proxy_title.setWordWrap(True)
        ctl.addWidget(self.term_proxy_title)
        tp_row, self.term_proxy_chk, self.term_proxy_lbl = self._wrap_checkbox(
            self.on_term_proxy_toggled, checked=bool(self.cfg.get("term_proxy", False)))
        ctl.addLayout(tp_row)
        self.term_proxy_hint = QtWidgets.QLabel("");
        self.term_proxy_hint.setObjectName("muted")
        self.term_proxy_hint.setWordWrap(True)
        ctl.addWidget(self.term_proxy_hint)
        self.term_proxy_copy_btn = QtWidgets.QPushButton("")
        self.term_proxy_copy_btn.clicked.connect(
            lambda: QtWidgets.QApplication.clipboard().setText("source ~/.bashrc"))
        ctl.addWidget(self.term_proxy_copy_btn)
        l.addWidget(c_term)

        # pkill
        c3 = QtWidgets.QFrame();
        c3.setObjectName("card")
        c3l = QtWidgets.QVBoxLayout(c3);
        c3l.setContentsMargins(16, 14, 16, 14);
        c3l.setSpacing(8)
        self.cleanup_hint = QtWidgets.QLabel("");
        self.cleanup_hint.setObjectName("muted")
        self.cleanup_hint.setWordWrap(True)
        c3l.addWidget(self.cleanup_hint)
        self.pkill_btn = QtWidgets.QPushButton("");
        self.pkill_btn.setObjectName("dangerBtn")
        self.pkill_btn.clicked.connect(self.do_pkill)
        c3l.addWidget(self.pkill_btn)
        l.addWidget(c3);
        l.addStretch(1)
        # نسخهٔ برنامه در پایان لیست
        self.version_lbl = QtWidgets.QLabel(f"{APP_NAME} v{APP_VERSION}")
        self.version_lbl.setObjectName("muted")
        self.version_lbl.setAlignment(QtCore.Qt.AlignCenter)
        l.addWidget(self.version_lbl)
        # دکمه‌ها بتوانند در عرض کم جمع شوند (به‌جای پهن‌نگه‌داشتن کارت)
        for b in (self.copy_btn, self.recheck_btn, self.theme_toggle_btn,
                  self.term_proxy_copy_btn, self.pkill_btn):
            b.setMinimumWidth(0)
            b.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                            QtWidgets.QSizePolicy.Fixed)
        return page

    # ───────── ترجمهٔ کل رابط ─────────
    def retranslate(self):
        rtl = self.lang == "fa"
        QtWidgets.QApplication.instance().setLayoutDirection(
            QtCore.Qt.RightToLeft if rtl else QtCore.Qt.LeftToRight)
        self.setLayoutDirection(QtCore.Qt.RightToLeft if rtl else QtCore.Qt.LeftToRight)
        for i, key in enumerate(self._tab_keys):
            self.tabs[i].setText(f"{self._tab_icons[i]}\n{self.t(key)}")
        self.drawer.set_title(self.t("logs_title"))
        self.handle.setToolTip(self.t("logs_title"))
        self.row_server._label.setText(self.t("info_server"))
        self.row_tunnel._label.setText(self.t("info_tunnel"))
        self.row_socks._label.setText(self.t("info_socks"))
        self.socks_set_btn.setText(self.t("btn_set_socks"))
        self.socks_auto_btn.setText(self.t("btn_auto_proxy"))
        self.servers_title.setText(self.t("servers_title"))
        self.add_btn.setText(self.t("new_server"))
        self.settings_title.setText(self.t("settings_title"))
        self.autossh_label.setText(self.t("autossh_label"))
        self.install_cmd.setText(install_primary_command())
        self.copy_btn.setText(self.t("copy_install"))
        self.recheck_btn.setText(self.t("recheck"))
        self.lang_label.setText(self.t("language"))
        self.scale_label.setText(self.t("ui_scale"))
        self.theme_label.setText(self.t("app_theme"))
        self.theme_toggle_btn.setText(self.t("toggle_theme"))
        self.cleanup_hint.setText(self.t("cleanup_hint"))
        self.pkill_btn.setText(self.t("pkill"))
        self.startup_title.setText(self.t("startup_title"))
        self.autostart_lbl.setText(self.t("autostart_chk"))
        self.autoconnect_lbl.setText(self.t("autoconnect_chk"))
        self.term_proxy_title.setText(self.t("term_proxy_title"))
        self.term_proxy_lbl.setText(self.t("term_proxy_chk"))
        self.term_proxy_hint.setText(self.t("term_proxy_hint"))
        self.term_proxy_copy_btn.setText(self.t("term_proxy_copy"))
        self._refresh_autossh_label()
        self.refresh_servers()
        self.sync_active_pill()
        self.on_state(self.tunnel.state)

    def on_lang_change(self, _):
        self.lang = self.lang_combo.currentData()
        self.cfg["lang"] = self.lang
        self.save_config()
        self.retranslate()
        self._rebuild_tray_menu()

    # ───────── سینی سیستم ─────────
    def _build_tray(self):
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(make_power_icon(THEMES[self.theme_name]["off"]))
        self.tray.activated.connect(self._tray_activated)
        self._rebuild_tray_menu()
        self.tray.show()
        self._update_tray()

    def _rebuild_tray_menu(self):
        if not getattr(self, "tray", None):
            return
        menu = QtWidgets.QMenu()
        self.act_toggle = menu.addAction(self.t("tray_connect"), self.toggle_tunnel)
        menu.addSeparator()
        self.tray_server_menu = menu.addMenu(self.t("tray_pick"))
        menu.addSeparator()
        menu.addAction(self.t("tray_show"), self.show_window)
        menu.addAction(self.t("pkill"), self.do_pkill)
        menu.addSeparator()
        menu.addAction(self.t("tray_quit"), self.quit_app)
        self.tray.setContextMenu(menu)
        self._rebuild_tray_servers()
        self._update_tray()

    def _rebuild_tray_servers(self):
        if not getattr(self, "tray", None):
            return
        self.tray_server_menu.clear()
        group = QtWidgets.QActionGroup(self);
        group.setExclusive(True)
        for p in self.servers():
            a = self.tray_server_menu.addAction(p["name"]);
            a.setCheckable(True)
            a.setChecked(p["id"] == self.cfg.get("active"))
            a.triggered.connect(lambda _, pid=p["id"]: self._tray_pick(pid))
            group.addAction(a)
        if not self.servers():
            e = self.tray_server_menu.addAction(self.t("tray_none"));
            e.setEnabled(False)

    def _tray_pick(self, pid):
        self.cfg["active"] = pid;
        self.save_config()
        idx = self.server_combo.findData(pid)
        if idx >= 0:
            self.server_combo.setCurrentIndex(idx)
        self.sync_active_pill();
        self._update_tray()

    def _tray_activated(self, reason):
        if reason in (QtWidgets.QSystemTrayIcon.Trigger, QtWidgets.QSystemTrayIcon.DoubleClick):
            self.show_window() if not self.isVisible() else self.hide()

    def _update_tray(self):
        if not getattr(self, "tray", None):
            return
        c = THEMES[self.theme_name];
        st = self.tunnel.state
        color = {"on": c["on"], "connecting": c["busy"], "error": c["danger"]}.get(st, c["off"])
        self.tray.setIcon(make_power_icon(color))
        on = st in ("on", "connecting")
        self.act_toggle.setText(self.t("tray_disconnect") if on else self.t("tray_connect"))
        p = self.active_server()
        tip = f"{APP_NAME}\n"
        if p:
            tip += f"{p['name']} — {p['user']}@{p['ip']}\n"
        tip += {"on": "● " + self.t("status_on"), "connecting": "● " + self.t("status_connecting"),
                "reconnecting": "● " + self.t("status_reconnecting"),
                "error": "● " + self.t("status_error")}.get(st, "○ " + self.t("status_off"))
        self.tray.setToolTip(tip)

    def show_window(self):
        self.showNormal();
        self.raise_();
        self.activateWindow()

    def quit_app(self):
        self._really_quit = True
        self.close()
        QtWidgets.QApplication.quit()

    # ───────── سرورها ─────────
    def servers(self):
        return self.cfg.setdefault("profiles", [])

    def refresh_servers(self):
        if not hasattr(self, "server_list"):
            return
        self.server_list.clear()
        for p in self.servers():
            item = QtWidgets.QListWidgetItem()
            row = ServerRow(p, self.t("edit"))
            row.edit.connect(self.edit_server)
            row.remove.connect(self.delete_server)
            item.setSizeHint(QtCore.QSize(0, max(76, row.sizeHint().height())))
            self.server_list.addItem(item)
            self.server_list.setItemWidget(item, row)
        self.server_combo.blockSignals(True)
        self.server_combo.clear()
        for p in self.servers():
            self.server_combo.addItem(p["name"], p["id"])
        active = self.cfg.get("active")
        if active:
            idx = self.server_combo.findData(active)
            if idx >= 0:
                self.server_combo.setCurrentIndex(idx)
        self.server_combo.blockSignals(False)
        self.sync_active_pill()
        self._rebuild_tray_servers()

    def add_server(self):
        dlg = ServerDialog(self, THEMES[self.theme_name], self.lang)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.servers().append(dlg.data())
            if not self.cfg.get("active"):
                self.cfg["active"] = self.servers()[-1]["id"]
            self.save_config();
            self.refresh_servers()

    def edit_server(self, pid):
        prof = next((p for p in self.servers() if p["id"] == pid), None)
        if not prof:
            return
        dlg = ServerDialog(self, THEMES[self.theme_name], self.lang, prof)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            data = dlg.data()
            for i, p in enumerate(self.servers()):
                if p["id"] == pid:
                    self.servers()[i] = data
            self.save_config();
            self.refresh_servers()

    def delete_server(self, pid):
        mb = self._msgbox(
            QtWidgets.QMessageBox.Question,
            self.t("del_title"), self.t("del_q"),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if mb.exec_() != QtWidgets.QMessageBox.Yes:
            return
        self.cfg["profiles"] = [p for p in self.servers() if p["id"] != pid]
        if self.cfg.get("active") == pid:
            self.cfg["active"] = self.servers()[0]["id"] if self.servers() else None
        self.save_config();
        self.refresh_servers()

    def on_pick_server(self, idx):
        pid = self.server_combo.itemData(idx)
        if pid:
            self.cfg["active"] = pid;
            self.save_config();
            self.sync_active_pill();
            self._update_tray()

    def active_server(self):
        pid = self.cfg.get("active")
        return next((p for p in self.servers() if p["id"] == pid), None)

    def sync_active_pill(self):
        p = self.active_server()
        if not p:
            self.pill_name.setText(self.t("no_server"))
            self.pill_sub.setText(self.t("pick_hint"))
            self.row_server._value.setText("—")
            self.row_tunnel._value.setText("—")
            self.update_socks_row()
            return
        self.pill_name.setText(p["name"])
        self.pill_sub.setText(f"{p['user']}@{p['ip']}:{p['ssh_port']}")
        self.row_server._value.setText(f"{p['user']}@{p['ip']}:{p['ssh_port']}")
        self.row_tunnel._value.setText(f"127.0.0.1:{p['dyn_port']}")
        self.update_socks_row()

    def _proxy_msg(self, ok, msg):
        """تبدیل پیام پراکسی به متن قابل‌نمایش (با ترجمهٔ حالت پشتیبانی‌نشده)."""
        if msg.startswith("AUTO_PROXY_UNSUPPORTED"):
            port = msg.split(":", 1)[1] if ":" in msg else ""
            p = self.active_server()
            if not port and p:
                port = str(p.get("dyn_port", "1085"))
            return "ℹ️ " + self.t("proxy_manual").format(p=port or "1085")
        return ("✅ " if ok else "⚠️ ") + msg

    def update_socks_row(self):
        # ویندوز: خواندن وضعیت از رجیستری
        if OS == "windows":
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
                enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
                if enabled:
                    try:
                        server, _ = winreg.QueryValueEx(key, "ProxyServer")
                    except Exception:
                        server = ""
                    port = server.split(":")[-1] if ":" in server else "?"
                    self.row_socks._value.setText(self.t("socks_active").format(p=port))
                else:
                    self.row_socks._value.setText(self.t("socks_off"))
                winreg.CloseKey(key)
            except Exception:
                self.row_socks._value.setText(self.t("socks_off"))
            return
        if not gsettings_available():
            self.row_socks._value.setText(self.t("socks_unknown"));
            return
        try:
            mode = subprocess.run(["gsettings", "get", "org.gnome.system.proxy", "mode"],
                                  capture_output=True, text=True).stdout.strip().strip("'")
            if mode == "manual":
                port = subprocess.run(["gsettings", "get", "org.gnome.system.proxy.socks", "port"],
                                      capture_output=True, text=True).stdout.strip()
                self.row_socks._value.setText(self.t("socks_active").format(p=port))
            elif mode == "auto":
                self.row_socks._value.setText(self.t("socks_auto"))
            else:
                self.row_socks._value.setText(self.t("socks_off"))
        except Exception:
            self.row_socks._value.setText(self.t("socks_unknown"))

    # ───────── اتصال/قطع ─────────
    def toggle_tunnel(self):
        if self.tunnel.state in ("on", "connecting", "reconnecting"):
            self.tunnel.stop()
            # revert از طریق on_state("off") انجام می‌شود
        else:
            p = self.active_server()
            if not p:
                self._msgbox(QtWidgets.QMessageBox.Warning,
                             APP_NAME, self.t("warn_pick")).exec_()
                return
            self._cleanup_orphan_tunnels()
            self.tunnel.start(p)

    def _revert_all_proxy(self):
        """بازگرداندن همهٔ تغییرات پراکسی به حالت اولیه: سیستم → Automatic،
        و پاک‌کردن متغیرهای محیطی ترمینال. این تابع هم هنگام قطعِ دستی و هم
        هنگام خروجِ خودکارِ تونل (شکست/قطع ناگهانی) صدا زده می‌شود."""
        ok, msg = set_system_proxy_auto()
        self.on_log(self._proxy_msg(ok, msg))
        if self.cfg.get("term_proxy", False):
            tok, tmsg = clear_terminal_proxy()
            self.on_log(self._proxy_msg(tok, tmsg))
        self.update_socks_row()

    def _on_tunnel_failed(self, msg_key):
        """نمایش پیام شکستِ واقعیِ اتصال به کاربر و در لاگ."""
        p = self.active_server()
        mon = str(p.get("mon_port", "1086")) if p else "1086"
        try:
            text = self.t(msg_key).format(m=mon)
        except Exception:
            text = self.t(msg_key)
        self.on_log(text)
        self._msgbox(QtWidgets.QMessageBox.Critical, self.t("status_error"), text).exec_()

    def on_autostart_toggled(self, checked):
        ok, err = set_autostart(checked)
        if not ok:
            # اگر اعمال نشد، تیک را برگردان و خطا را نشان بده
            self.autostart_chk.blockSignals(True)
            self.autostart_chk.setChecked(autostart_enabled())
            self.autostart_chk.blockSignals(False)
            if err:
                self.on_log("⚠️ " + err)
        self.cfg["autostart"] = self.autostart_chk.isChecked()
        # اتصال خودکار فقط وقتی معنا دارد که اجرای خودکار فعال باشد
        self.autoconnect_chk.setEnabled(self.autostart_chk.isChecked())
        if not self.autostart_chk.isChecked():
            self.autoconnect_chk.setChecked(False)
            self.cfg["autoconnect"] = False
        self.save_config()

    def on_autoconnect_toggled(self, checked):
        self.cfg["autoconnect"] = bool(checked)
        self.save_config()

    def on_term_proxy_toggled(self, checked):
        self.cfg["term_proxy"] = bool(checked)
        self.save_config()
        # افزودن/حذفِ خودکارِ خط سورس در فایل‌های شِل
        if checked:
            ok, msg = install_rc_hook()
            if msg:
                self.on_log(self._proxy_msg(ok, msg))
            # وضعیت فعلی پراکسی را در proxy.env بنویس (فعال یا خاموش)
            if self.tunnel.state == "on":
                p = self.active_server()
                if p:
                    write_terminal_proxy(int(p["dyn_port"]))
            else:
                clear_terminal_proxy()
            self.on_log("ℹ️ " + self.t("term_proxy_reload_hint"))
        else:
            # هنگام غیرفعال‌کردن: خط سورس و متغیرها را پاک کن
            ok, msg = remove_rc_hook()
            if msg:
                self.on_log(self._proxy_msg(ok, msg))
            clear_terminal_proxy()
        # اگر هم‌اکنون متصل است، وضعیت پراکسیِ ترمینال را همگام کن
        if self.tunnel.state == "on":
            p = self.active_server()
            if checked and p:
                tok, tmsg = write_terminal_proxy(int(p["dyn_port"]))
                self.on_log(self._proxy_msg(tok, tmsg))
                self._proxy_applied = True
            elif not checked:
                tok, tmsg = clear_terminal_proxy()
                self.on_log(self._proxy_msg(tok, tmsg))

    def on_state(self, state):
        c = THEMES[self.theme_name]
        if state == "on":
            self.power.set_state("on", c["on"])
            self.status_lbl.setText(self.t("status_on"))
            self.status_lbl.setStyleSheet(f"color:{c['on']};")
            self.dot.setStyleSheet(f"color:{c['on']}; font-size:14px;")
            p = self.active_server()
            if p and p.get("set_socks", True):
                ok, msg = set_system_socks(int(p["dyn_port"]))
                self.on_log(self._proxy_msg(ok, msg))
                self._proxy_applied = True
            if p and self.cfg.get("term_proxy", False):
                tok, tmsg = write_terminal_proxy(int(p["dyn_port"]))
                self.on_log(self._proxy_msg(tok, tmsg))
                self._proxy_applied = True
            self.update_socks_row()
        elif state == "connecting":
            self.power.set_state("busy", c["busy"])
            self.status_lbl.setText(self.t("status_connecting"))
            self.status_lbl.setStyleSheet(f"color:{c['busy']};")
        elif state == "reconnecting":
            # تونل موقتاً افتاده ولی autossh در حال بازسازی است؛ پراکسی را
            # برنمی‌گردانیم چون انتظار داریم به‌زودی دوباره وصل شود.
            self.power.set_state("busy", c["busy"])
            self.status_lbl.setText(self.t("status_reconnecting"))
            self.status_lbl.setStyleSheet(f"color:{c['busy']};")
            self.dot.setStyleSheet(f"color:{c['busy']}; font-size:14px;")
        elif state == "error":
            self.power.set_state("off", c["danger"])
            self.status_lbl.setText(self.t("status_error"))
            self.status_lbl.setStyleSheet(f"color:{c['danger']};")
            self.dot.setStyleSheet(f"color:{c['off']}; font-size:14px;")
            # هر تغییرِ پراکسیِ احتمالی را برگردان (پوشش قطع/شکستِ خودکار)
            if getattr(self, "_proxy_applied", False):
                self._revert_all_proxy()
                self._proxy_applied = False
            else:
                self.update_socks_row()
        else:
            self.power.set_state("off", c["off"])
            self.status_lbl.setText(self.t("status_off"))
            self.status_lbl.setStyleSheet(f"color:{c['off']};")
            self.dot.setStyleSheet(f"color:{c['off']}; font-size:14px;")
            # هر تغییرِ پراکسیِ احتمالی را برگردان (پوشش قطع/شکستِ خودکار)
            if getattr(self, "_proxy_applied", False):
                self._revert_all_proxy()
                self._proxy_applied = False
            else:
                self.update_socks_row()
        self._update_tray()

    # ───────── ردیابی PID تونل‌های ساخته‌شده توسط برنامه ─────────
    def _tracked_pids(self):
        return self.cfg.setdefault("tracked_pids", [])

    def _track_pid(self, pid):
        pid = int(pid)
        if pid and pid not in self._tracked_pids():
            self._tracked_pids().append(pid)
            self.save_config()

    def _untrack_pid(self, pid):
        pid = int(pid)
        if pid in self._tracked_pids():
            self._tracked_pids().remove(pid)
            self.save_config()

    def do_pkill(self):
        # فقط تونل‌هایی که خودِ این برنامه ساخته است
        pids = set(int(x) for x in self._tracked_pids())
        if self.tunnel.proc is not None:
            live = int(self.tunnel.proc.processId())
            if live:
                pids.add(live)
        # تونلِ زندهٔ مدیریت‌شده را تمیز ببند
        self.tunnel.stop()
        n = 0
        for pid in pids:
            if kill_pid_tree(pid):
                n += 1
        # فرصت کوتاه، سپس kill اجباری برای بازمانده‌ها
        if n and OS != "windows":
            QtCore.QThread.msleep(300)
            for pid in pids:
                force_kill_pid(pid)
        self.cfg["tracked_pids"] = []
        self.save_config()
        if n:
            self.on_log(f"🧹 {n} app tunnel(s) closed.")
        else:
            self.on_log("ℹ️ No app-created tunnel to close.")
        # بازگرداندن پراکسی سیستم و ترمینال به حالت اولیه
        ok, msg = set_system_proxy_auto()
        self.on_log(self._proxy_msg(ok, msg))
        if self.cfg.get("term_proxy", False):
            tok, tmsg = clear_terminal_proxy()
            self.on_log(self._proxy_msg(tok, tmsg))
        self._proxy_applied = False
        self.update_socks_row()
        # پیام مناسب به کاربر (چون ممکن است کشوی لاگ بسته باشد)
        if n:
            self._msgbox(QtWidgets.QMessageBox.Information, self.t("pkill"),
                         self.t("pkill_done").format(n=n)).exec_()
        else:
            self._msgbox(QtWidgets.QMessageBox.Information, self.t("pkill"),
                         self.t("pkill_none")).exec_()

    def manual_set_socks(self):
        p = self.active_server()
        port = int(p["dyn_port"]) if p else 1085
        ok, msg = set_system_socks(port)
        self.on_log(self._proxy_msg(ok, msg));
        self.update_socks_row()

    def manual_auto_proxy(self):
        ok, msg = set_system_proxy_auto()
        self.on_log(self._proxy_msg(ok, msg));
        self.update_socks_row()

    def on_log(self, text):
        self.drawer.append(text)

    # ───────── بررسی autossh ─────────
    def _refresh_autossh_label(self):
        c = THEMES[self.theme_name]
        if self._autossh_installed is None:
            self.autossh_status.setText(self.t("autossh_unchecked"));
            return
        if self._autossh_installed:
            self.autossh_status.setText(self.t("autossh_yes"))
            self.autossh_status.setStyleSheet(f"color:{c['on']};")
        else:
            self.autossh_status.setText(self.t("autossh_no"))
            self.autossh_status.setStyleSheet(f"color:{c['danger']};")

    def check_autossh_installed(self):
        c = THEMES[self.theme_name]
        self._autossh_installed = shutil.which("autossh") is not None
        if hasattr(self, "install_cmd"):
            self.install_cmd.setText(install_primary_command())
        self._refresh_autossh_label()
        if not self._autossh_installed and not self.cfg.get("warned_install"):
            self.cfg["warned_install"] = True;
            self.save_config()
            m = QtWidgets.QMessageBox(self)
            m.setWindowTitle(self.t("inst_title"))
            m.setIcon(QtWidgets.QMessageBox.Warning)
            m.setText(self.t("inst_text"))
            m.setInformativeText(install_note(self.lang))
            m.setStyleSheet(qss(c))
            m.setLayoutDirection(
                QtCore.Qt.RightToLeft if self.lang == "fa" else QtCore.Qt.LeftToRight)
            copy_btn = m.addButton(self.t("copy_install"), QtWidgets.QMessageBox.AcceptRole)
            m.addButton(self.t("ok"), QtWidgets.QMessageBox.RejectRole)
            m.exec_()
            if m.clickedButton() == copy_btn:
                QtWidgets.QApplication.clipboard().setText(install_primary_command())
            self.switch_tab(2)

    # ───────── تم/مقیاس ─────────
    def _msgbox(self, icon, title, text, buttons=QtWidgets.QMessageBox.Ok):
        """ساخت QMessageBox هماهنگ با تم فعلی برنامه."""
        c = THEMES[self.theme_name]
        mb = QtWidgets.QMessageBox(self)
        mb.setIcon(icon)
        mb.setWindowTitle(title)
        mb.setText(text)
        mb.setStandardButtons(buttons)
        mb.setStyleSheet(qss(c))
        mb.setLayoutDirection(
            QtCore.Qt.RightToLeft if self.lang == "fa" else QtCore.Qt.LeftToRight)
        return mb

    def apply_theme(self):
        c = THEMES[self.theme_name]
        base_font = max(8, int(11 * self.scale / 100))
        self.setStyleSheet(qss(c) + f"\n* {{ font-size: {base_font}px; }}")
        self.theme_btn.setText("☀" if self.theme_name == "dark" else "🌙")
        self.on_state(self.tunnel.state)

    def toggle_theme(self):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.cfg["theme"] = self.theme_name;
        self.save_config();
        self.apply_theme()

    def on_scale(self, v):
        self.scale = v;
        self.scale_lbl.setText(f"{v}%")
        self.cfg["scale"] = v;
        self.save_config();
        self.apply_theme()

    # ───────── پنجرهٔ بدون قاب ─────────
    def _header_press(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag = e.globalPos() - self.frameGeometry().topLeft();
            e.accept()

    def _header_move(self, e):
        if self._drag and e.buttons() & QtCore.Qt.LeftButton:
            self.move(e.globalPos() - self._drag);
            e.accept()

    def toggle_max(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def resizeEvent(self, e):
        if hasattr(self, "grip"):
            self.grip.move(self.root.width() - 22, self.root.height() - 22)
        # ذخیرهٔ اندازهٔ پنجره (با کمی تأخیر تا هنگام درگ مدام ذخیره نشود)
        if hasattr(self, "_save_size_timer"):
            self._save_size_timer.start(500)
        super().resizeEvent(e)

    def _persist_window_size(self):
        # هنگام بسته/کمینه‌بودن یا بزرگ‌نمایی، اندازه را ذخیره نکن
        if self.isMaximized() or self.isMinimized() or not self.isVisible():
            return
        # عرض واقعیِ بدون احتساب کشوی لاگِ باز
        w = self.width()
        if getattr(self.drawer, "_open", False):
            w = max(w - self.drawer._w, 430)
        self.cfg["win_w"] = w
        self.cfg["win_h"] = self.height()
        self.save_config()

    # ───────── ذخیره/بارگذاری ─────────
    def load_config(self):
        try:
            if CONFIG_FILE.exists():
                cfg = json.loads(CONFIG_FILE.read_text("utf-8"))
                cfg = self._migrate_config(cfg)
                return cfg
        except Exception:
            pass
        return {"profiles": [], "active": None, "theme": "light", "scale": 100, "lang": "fa"}

    def _migrate_config(self, cfg):
        """مهاجرت یک‌بارهٔ تنظیمات قدیمی: غیرفعال‌کردن پورت مانیتورِ -M که
        باعث خطای «remote port forwarding failed» و حلقهٔ ری‌استارت می‌شد.
        معماری جدید برای تشخیص قطعی به ServerAlive و پایش SOCKS تکیه دارد."""
        try:
            if not cfg.get("_migrated_mon0"):
                for p in cfg.get("profiles", []):
                    # هر مقدار مانیتورِ قدیمی را به 0 (خاموش) ببر
                    if str(p.get("mon_port", "0")).strip() not in ("", "0"):
                        p["mon_port"] = "0"
                cfg["_migrated_mon0"] = True
        except Exception:
            pass
        return cfg

    def save_config(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(json.dumps(self.cfg, ensure_ascii=False, indent=2), "utf-8")
        except Exception as e:
            print("save error:", e)

    def closeEvent(self, e):
        if getattr(self, "tray", None) and not self._really_quit:
            self._persist_window_size()
            e.ignore();
            self.hide()
            if not self.cfg.get("tray_hint_shown"):
                self.cfg["tray_hint_shown"] = True;
                self.save_config()
                self.tray.showMessage(APP_NAME, self.t("tray_hint"),
                                      QtWidgets.QSystemTrayIcon.Information, 4000)
            return
        self._persist_window_size()
        try:
            self.tunnel.stop()
        except Exception:
            pass
        if getattr(self, "tray", None):
            self.tray.hide()
        self.save_config()
        super().closeEvent(e)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    win = MainWindow()
    app.setQuitOnLastWindowClosed(not bool(getattr(win, "tray", None)))
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()