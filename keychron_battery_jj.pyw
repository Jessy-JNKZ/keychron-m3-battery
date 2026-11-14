# ==============================================================================
# Nom du projet : Keychron Battery Monitor
# Auteur        : Jessy JONKISZ
# X (Twitter)   : https://x.com/JNKZJessy
# GitHub        : https://github.com/Jessy-JNKZ/keychron-m3-battery
# ==============================================================================

import subprocess
import sys

# --- VÉRIFICATION ET INSTALLATION AUTOMATIQUE DES DÉPENDANCES ---
required_packages = {
    "hidapi": "hid",
    "Pillow": "PIL",
    "pystray": "pystray",
    "matplotlib": "matplotlib"
}

for package_name, import_name in required_packages.items():
    try:
        __import__(import_name)
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name], creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        except Exception:
            sys.exit(1)
# -------------------------------------------------------------

import os
import json
import time
import threading
import ctypes
from ctypes import wintypes
import shutil
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw
import pystray
import hid
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

CURRENT_VERSION = "v1.4.0"
SCRIPT_PATH = os.path.abspath(__file__)
INSTALL_DIR = os.path.dirname(SCRIPT_PATH)

DATA_DIR = os.path.join(os.getenv('APPDATA'), 'KeychronBatteryMonitorJJ')
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
HISTORY_PATH = os.path.join(DATA_DIR, "history.json")
STATS_PATH = os.path.join(DATA_DIR, "stats.json")
DEBUG_LOG_PATH = os.path.join(DATA_DIR, "update_debug.log")

VENDOR_ID = 0x3434

DEFAULT_CONFIG = {
    "poll_interval": 30,
    "style": "Cercle épuré",
    "color_high": 50,
    "color_low": 20,
    "language": "auto"
}

class _SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR), ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY), ("dwHotKey", wintypes.DWORD),
        ("hIconOrMonitor", wintypes.HANDLE), ("hProcess", wintypes.HANDLE),
    ]

def elevated_copy(src_file, dst_file, timeout_ms=60000):
    """Copie src -> dst avec élévation UAC et ATTEND la fin. Retourne (ok, message)."""
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(_SHELLEXECUTEINFOW)]
    shell32.ShellExecuteExW.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    sei = _SHELLEXECUTEINFOW()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS : on récupère le handle du process
    sei.lpVerb = "runas"
    sei.lpFile = "cmd.exe"
    sei.lpParameters = f'/c copy /y "{src_file}" "{dst_file}"'
    sei.lpDirectory = None
    sei.nShow = 0  # SW_HIDE

    write_debug_log(f"ShellExecuteExW runas : cmd.exe {sei.lpParameters}")
    if not shell32.ShellExecuteExW(ctypes.byref(sei)):
        err = ctypes.get_last_error()
        if err == 1223:
            return False, "Élévation refusée par l'utilisateur (UAC annulé)"
        return False, f"ShellExecuteExW a échoué (erreur {err})"

    if not sei.hProcess:
        return False, "Aucun handle de process retourné"
    try:
        wait = kernel32.WaitForSingleObject(sei.hProcess, timeout_ms)
        if wait != 0:
            return False, f"Timeout/erreur en attendant la copie (WaitForSingleObject={wait})"
        code = wintypes.DWORD(1)
        kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(code))
        write_debug_log(f"Process élevé terminé, code retour = {code.value}")
        return code.value == 0, f"code retour {code.value}"
    finally:
        kernel32.CloseHandle(sei.hProcess)

def get_pythonw():
    exe = sys.executable
    if os.path.basename(exe).lower() == "python.exe":
        candidate = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.exists(candidate):
            return candidate
    return exe

def write_debug_log(msg):
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

def get_system_language():
    try:
        windll = ctypes.windll.kernel32
        lang_id = windll.GetUserDefaultUILanguage()
        if lang_id & 0x3FF == 0x09:
            return "en"
    except Exception:
        pass
    return "fr"

translations = {
    "fr": {
        "offline": "Souris : Hors ligne",
        "charging": "En charge (USB)",
        "on_battery": "Sur batterie",
        "battery_label": "Batterie",
        "autonomy": "Autonomie estimée",
        "last_full_charge": "Dernière charge 100%",
        "never": "Jamais",
        "record": "Dernier relevé",
        "calculating": "Calcul en cours...",
        "in_progress": "En cours...",
        "insufficient_data": "Données insuffisantes",
        "unavailable": "Estimation indisponible",
        "show_stats": "📊 Afficher les statistiques",
        "update_available": "🚀 Mise à jour disponible !",
        "update_msg": "Une nouvelle version ({}) est disponible.\nSouhaitez-vous l'installer maintenant ?",
        "up_to_date": "Votre application est à jour.",
        "menu_update": "Vérifier les mises à jour",
        "downloading": "Téléchargement de la mise à jour...",
        "installing": "Installation et redémarrage...",
        "update_success": "Mise à jour réussie !",
        "asset_missing": "Mise à jour détectée, mais le fichier .pyw est introuvable dans les assets de la release GitHub.",
        "menu_style": "Style d'affichage",
        "style_circle": "Cercle épuré",
        "style_solid": "Cercle plein",
        "style_h_bat": "Batterie horizontale",
        "style_v_bat": "Batterie verticale",
        "menu_lang": "Langue / Language",
        "lang_auto": "Automatique (Système)",
        "lang_fr": "Français",
        "lang_en": "English",
        "menu_colors": "Limites de couleur",
        "orange_threshold": "Seuil Orange (Actuel: <{}%)",
        "set_orange": "Passer seuil orange à {}%",
        "red_threshold": "Seuil Rouge (Actuel: <{}%)",
        "set_red": "Passer seuil rouge à {}%",
        "menu_interval": "Fréquence de rafraîchissement",
        "sec": "secondes",
        "min": "minute",
        "mins": "minutes",
        "startup": "Lancer au démarrage",
        "refresh": "Rafraîchir",
        "quit": "Quitter",
        "low_battery_title": "Keychron M3",
        "low_battery_msg": "Batterie faible : {}% restant.\nPensez à rebrancher votre souris !",
        "full_battery_title": "Keychron M3",
        "full_battery_msg": "Souris chargée à 100% !\nVous pouvez la débrancher pour préserver la batterie.",
        "tooltip_offline": "Keychron M3 : Hors ligne"
    },
    "en": {
        "offline": "Mouse: Offline",
        "charging": "Charging (USB)",
        "on_battery": "On battery",
        "battery_label": "Battery",
        "autonomy": "Estimated battery life",
        "last_full_charge": "Last 100% charge",
        "never": "Never",
        "record": "Last update",
        "calculating": "Calculating...",
        "in_progress": "In progress...",
        "insufficient_data": "Insufficient data",
        "unavailable": "Estimate unavailable",
        "show_stats": "📊 Show statistics",
        "update_available": "🚀 Update available!",
        "update_msg": "A new version ({}) is available.\nWould you like to install it now?",
        "up_to_date": "Your application is up to date.",
        "menu_update": "Check for updates",
        "downloading": "Downloading update...",
        "installing": "Installing and restarting...",
        "update_success": "Update successful!",
        "asset_missing": "Update found, but the .pyw file is missing from the GitHub release assets.",
        "menu_style": "Display style",
        "style_circle": "Clean circle",
        "style_solid": "Solid circle",
        "style_h_bat": "Horizontal battery",
        "style_v_bat": "Vertical battery",
        "menu_lang": "Language / Langue",
        "lang_auto": "Automatic (System)",
        "lang_fr": "Français",
        "lang_en": "English",
        "menu_colors": "Color thresholds",
        "orange_threshold": "Orange threshold (Current: <{}%)",
        "set_orange": "Set orange threshold to {}%",
        "red_threshold": "Red threshold (Current: <{}%)",
        "set_red": "Set red threshold to {}%",
        "menu_interval": "Polling interval",
        "sec": "seconds",
        "min": "minute",
        "minutes": "minutes",
        "startup": "Launch at startup",
        "refresh": "Refresh",
        "quit": "Quit",
        "low_battery_title": "Keychron M3",
        "low_battery_msg": "Low battery: {}% remaining.\nConsider plugging in your mouse!",
        "full_battery_title": "Keychron M3",
        "full_battery_msg": "Mouse charged to 100%!\nYou can unplug it to preserve battery health.",
        "tooltip_offline": "Keychron M3: Offline"
    }
}

def get_dynamic_color(level, config):
    if level > config["color_high"]:
        return (46, 125, 50)
    elif level > config["color_low"]:
        return (255, 160, 0)
    else:
        return (229, 57, 53)

def create_battery_icon(level, is_charging=False, is_connected=True, config=None):
    if config is None:
        config = DEFAULT_CONFIG

    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    if not is_connected:
        main_color = (110, 110, 110)
    elif is_charging:
        main_color = (0, 230, 118)
    else:
        main_color = get_dynamic_color(level, config)

    style = config.get("style", "Cercle épuré")

    if is_charging:
        bolt_points = [(36, 8), (21, 33), (31, 33), (25, 56), (45, 27), (34, 27), (36, 8)]
        draw.polygon(bolt_points, fill=(0, 230, 118))
        return image

    if style in ["Cercle épuré", "Clean circle"]:
        draw.ellipse([4, 4, 60, 60], outline=(50, 50, 50), width=7)
        if is_connected and level > 0:
            angle = int(360.0 * (max(0, min(level, 100)) / 100.0))
            if angle > 0:
                draw.arc([4, 4, 60, 60], start=-90, end=-90 + angle, fill=main_color, width=7)

    elif style in ["Cercle plein", "Solid circle"]:
        draw.ellipse([6, 6, 58, 58], fill=(40, 40, 40))
        if is_connected and level > 0:
            angle = int(360.0 * (max(0, min(level, 100)) / 100.0))
            if angle > 0:
                draw.pieslice([6, 6, 58, 58], start=-90, end=-90 + angle, fill=main_color)

    elif style in ["Batterie horizontale", "Horizontal battery"]:
        draw.rounded_rectangle([4, 16, 52, 48], radius=6, outline=(180, 180, 180), width=4)
        draw.rounded_rectangle([52, 26, 58, 38], radius=2, fill=(180, 180, 180))
        if is_connected and level > 0:
            fill_w = int(40 * (max(0, min(level, 100)) / 100.0))
            if fill_w > 0:
                draw.rounded_rectangle([8, 20, 8 + fill_w, 44], radius=4, fill=main_color)

    elif style in ["Batterie verticale", "Vertical battery"]:
        draw.rounded_rectangle([18, 4, 46, 54], radius=6, outline=(180, 180, 180), width=4)
        draw.rounded_rectangle([26, 1, 38, 4], radius=2, fill=(180, 180, 180))
        if is_connected and level > 0:
            fill_h = int(46 * (max(0, min(level, 100)) / 100.0))
            if fill_h > 0:
                draw.rounded_rectangle([22, 50 - fill_h, 42, 50], radius=4, fill=main_color)

    return image

class KeychronBatteryMonitor:
    def __init__(self):
        self.config = self.load_config()
        self.battery_level = 0
        self.is_charging = False
        self.is_connected = False
        self.running = True
        self.alert_sent = False
        self.full_charge_notified = False
        self.last_update = self.t("in_progress")
        self.time_remaining_str = self.t("calculating")
        self.last_full_charge_time = self.load_last_full_charge()
        
        self.startup_folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        self.shortcut_path = os.path.join(self.startup_folder, 'KeychronBatteryMonitor.lnk')

        level, charging, connected = self.read_battery()
        if connected and level is not None:
            self.battery_level = level
            self.is_charging = charging
            self.is_connected = True
            self.last_update = datetime.now().strftime("%H:%M:%S")
            self.check_full_charge(level, charging)
            self.record_history(level, charging)
            self.update_time_remaining()
            initial_icon = create_battery_icon(level, charging, is_connected=True, config=self.config)
            initial_title = self.get_safe_tooltip()
        else:
            initial_icon = create_battery_icon(0, is_connected=False, config=self.config)
            initial_title = self.get_safe_tooltip()

        self.rebuild_menu()
        
        threading.Thread(target=self.background_check_update, daemon=True).start()

    def get_current_lang(self):
        lang_pref = self.config.get("language", "auto")
        if lang_pref in ["fr", "en"]:
            return lang_pref
        return get_system_language()

    def t(self, key):
        lang = self.get_current_lang()
        return translations[lang].get(key, key)

    def load_last_full_charge(self):
        if os.path.exists(STATS_PATH):
            try:
                with open(STATS_PATH, "r") as f:
                    data = json.load(f)
                    return data.get("last_full_charge", None)
            except Exception:
                pass
        return None

    def save_last_full_charge(self, time_str):
        self.last_full_charge_time = time_str
        try:
            with open(STATS_PATH, "w") as f:
                json.dump({"last_full_charge": time_str}, f)
        except Exception:
            pass

    def check_full_charge(self, level, is_charging):
        if is_charging and level >= 99:
            current_time = datetime.now().strftime("%d/%m/%Y à %H:%M")
            if self.last_full_charge_time != current_time:
                self.save_last_full_charge(current_time)
                if not self.full_charge_notified and hasattr(self, 'icon'):
                    try:
                        self.icon.notify(
                            self.t("full_battery_msg"),
                            self.t("full_battery_title")
                        )
                        self.full_charge_notified = True
                    except Exception:
                        pass
        else:
            self.full_charge_notified = False

    def get_safe_tooltip(self):
        if not self.is_connected:
            text = self.t("tooltip_offline")
        else:
            status_text = self.t("charging") if self.is_charging else self.t("on_battery")
            text = (f"Keychron M3 : {self.battery_level}% ({status_text})\n"
                    f"{self.t('autonomy')} : {self.time_remaining_str}")
        
        if len(text) > 127:
            text = text[:124] + "..."
        return text

    def check_for_updates(self, manual=False):
        api_url = "https://api.github.com/repos/Jessy-JNKZ/keychron-m3-battery/releases/latest"
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "KeychronBatteryMonitor-App"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                latest_tag = data.get("tag_name", "").strip()
                
                download_url = None
                for asset in data.get("assets", []):
                    if asset.get("name") == "keychron_battery_jj.pyw":
                        download_url = asset.get("browser_download_url")
                        break
                
                clean_latest = latest_tag.lstrip('v')
                clean_current = CURRENT_VERSION.lstrip('v')
                
                if clean_latest > clean_current:
                    if not download_url and manual:
                        self.show_popup_msg(self.t("asset_missing"))
                    return True, latest_tag, download_url
                else:
                    if manual and hasattr(self, 'icon'):
                        self.show_popup_msg(self.t("up_to_date"))
                    return False, latest_tag, None
        except Exception:
            if manual and hasattr(self, 'icon'):
                self.show_popup_msg("Impossible de vérifier les mises à jour.")
        return False, "", None

    def show_popup_msg(self, message):
        def run():
            win = tk.Tk()
            win.withdraw()
            from tkinter import messagebox
            messagebox.showinfo("Keychron M3", message)
            win.destroy()
        threading.Thread(target=run, daemon=True).start()

    def show_update_dialog(self, tag, download_url):
        def run():
            root = tk.Tk()
            root.title("Keychron M3 - Mise à jour")
            root.geometry("400x180")
            root.configure(bg="#0D0E12")
            root.attributes("-topmost", True)
            root.resizable(False, False)

            root.update_idletasks()
            x = (root.winfo_screenwidth() // 2) - 200
            y = (root.winfo_screenheight() // 2) - 90
            root.geometry(f'400x180+{x}+{y}')

            tk.Label(root, text=self.t("update_available"), fg="#00E676", bg="#0D0E12", font=("Segoe UI", 12, "bold")).pack(pady=(15, 5))
            tk.Label(root, text=self.t("update_msg").format(tag), fg="#D4D4D8", bg="#0D0E12", font=("Segoe UI", 9), justify="center").pack(pady=5)

            btn_frame = tk.Frame(root, bg="#0D0E12")
            btn_frame.pack(pady=15)

            def on_accept():
                root.destroy()
                self.perform_update(download_url)

            btn_style = {"bd": 0, "relief": "flat", "font": ("Segoe UI", 9, "bold"), "padx": 14, "pady": 6}
            tk.Button(btn_frame, text="Installer", command=on_accept, bg="#00E676", fg="#000000", **btn_style).pack(side="left", padx=8)
            tk.Button(btn_frame, text="Plus tard", command=root.destroy, bg="#27272A", fg="#FFFFFF", **btn_style).pack(side="left", padx=8)

            root.mainloop()
        threading.Thread(target=run, daemon=True).start()

    def perform_update(self, download_url):
        if not download_url:
            self.show_popup_msg(self.t("asset_missing"))
            return

        if os.path.exists(DEBUG_LOG_PATH):
            try:
                os.remove(DEBUG_LOG_PATH)
            except Exception:
                pass

        write_debug_log(f"Début mise à jour. SCRIPT_PATH={SCRIPT_PATH}, INSTALL_DIR={INSTALL_DIR}")

        def run_progress():
            root = tk.Tk()
            root.title("Keychron M3")
            root.geometry("380x130")
            root.configure(bg="#0D0E12")
            root.attributes("-topmost", True)
            root.resizable(False, False)

            root.update_idletasks()
            x = (root.winfo_screenwidth() // 2) - 190
            y = (root.winfo_screenheight() // 2) - 65
            root.geometry(f'380x130+{x}+{y}')

            lbl_status = tk.Label(root, text=self.t("downloading"), fg="#FFFFFF", bg="#0D0E12", font=("Segoe UI", 9, "bold"))
            lbl_status.pack(pady=(15, 8))

            progress = ttk.Progressbar(root, orient="horizontal", length=320, mode="determinate")
            progress.pack(pady=5)

            def download_task():
                try:
                    write_debug_log(f"Téléchargement depuis {download_url}")
                    req = urllib.request.Request(download_url, headers={"User-Agent": "KeychronBatteryMonitor-App"})
                    with urllib.request.urlopen(req) as response:
                        total_size = int(response.headers.get('Content-Length', 0))
                        downloaded = 0
                        chunk_size = 8192
                        
                        temp_file = os.path.join(DATA_DIR, "keychron_battery_jj.pyw.tmp")
                        with open(temp_file, "wb") as f:
                            while True:
                                chunk = response.read(chunk_size)
                                if not chunk:
                                    break
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    percent = int((downloaded / total_size) * 100)
                                    root.after(0, lambda p=percent: progress.configure(value=p))

                    write_debug_log(f"Téléchargement terminé ({downloaded} octets) -> {temp_file}")
                    root.after(0, lambda: lbl_status.configure(text=self.t("installing")))
                    time.sleep(0.5)

                    # Vérification de sécurité : le fichier téléchargé doit être du Python valide
                    with open(temp_file, "rb") as tf:
                        data = tf.read()
                    try:
                        compile(data, "keychron_battery_jj.pyw", "exec")
                    except SyntaxError as se:
                        raise RuntimeError(f"Fichier téléchargé invalide : {se}")

                    root.after(0, root.destroy)

                    # Test d'écriture dans le dossier d'installation
                    needs_admin = False
                    try:
                        test_file = os.path.join(INSTALL_DIR, ".write_test")
                        with open(test_file, "w") as tf:
                            tf.write("1")
                        os.remove(test_file)
                        write_debug_log("Test écriture INSTALL_DIR: OK")
                    except Exception as e:
                        needs_admin = True
                        write_debug_log(f"Test écriture INSTALL_DIR: ÉCHEC ({e}) -> UAC requis")

                    # IMPORTANT : on reste vivant (l'icône tourne toujours) pendant toute la copie.
                    if needs_admin:
                        ok, msg = elevated_copy(temp_file, SCRIPT_PATH)
                    else:
                        try:
                            shutil.copyfile(temp_file, SCRIPT_PATH)
                            ok, msg = True, "copie directe OK"
                        except Exception as ce:
                            ok, msg = False, f"copie directe échouée : {ce}"

                    # Vérification réelle du résultat
                    if ok:
                        ok = os.path.exists(SCRIPT_PATH) and os.path.getsize(SCRIPT_PATH) == len(data)
                        if not ok:
                            msg = "taille du fichier installé différente du fichier téléchargé"

                    if not ok:
                        write_debug_log(f"ÉCHEC mise à jour : {msg}")
                        self.show_popup_msg(f"Échec de la mise à jour : {msg}")
                        return

                    write_debug_log("Copie réussie, relance de l'application")
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass

                    # Relance (non élevée) puis fermeture de cette instance
                    self.running = False
                    if hasattr(self, 'icon') and self.icon:
                        try:
                            self.icon.stop()
                        except Exception:
                            pass
                    time.sleep(0.5)
                    subprocess.Popen(
                        [get_pythonw(), SCRIPT_PATH],
                        cwd=INSTALL_DIR,
                        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                        close_fds=True
                    )
                    write_debug_log("Nouvelle instance lancée, fermeture de l'ancienne")
                    os._exit(0)

                except Exception as e:
                    write_debug_log(f"Exception dans download_task : {e}")
                    root.after(0, root.destroy)
                    self.show_popup_msg(f"Échec de la mise à jour : {e}")

            threading.Thread(target=download_task, daemon=True).start()
            root.mainloop()

        threading.Thread(target=run_progress, daemon=True).start()

    def background_check_update(self):
        time.sleep(15)
        has_update, tag, url = self.check_for_updates(manual=False)
        if has_update and url:
            self.show_update_dialog(tag, url)

    def menu_check_update_action(self, icon, item):
        has_update, tag, url = self.check_for_updates(manual=True)
        if has_update and url:
            self.show_update_dialog(tag, url)

    def show_popup_window(self, icon=None, item=None):
        def run_tk():
            root = tk.Tk()
            root.title("Keychron M3 — Dashboard Batterie")
            root.geometry("620x600")
            root.configure(bg="#0D0E12")
            root.attributes("-topmost", True)
            root.resizable(False, False)

            root.update_idletasks()
            width = root.winfo_width()
            height = root.winfo_height()
            x = (root.winfo_screenwidth() // 2) - (width // 2)
            y = (root.winfo_screenheight() // 2) - (height // 2)
            root.geometry(f'{width}x{height}+{x}+{y}')

            status_text = self.t("charging") if self.is_charging else self.t("on_battery")
            if not self.is_connected:
                status_text = self.t("offline")

            header_frame = tk.Frame(root, bg="#0D0E12")
            header_frame.pack(fill="x", padx=24, pady=(20, 10))

            lbl_title = tk.Label(header_frame, text="Keychron M3", fg="#00E676", bg="#0D0E12", font=("Segoe UI", 16, "bold"))
            lbl_title.pack(anchor="w")

            lbl_subtitle = tk.Label(header_frame, text="Centre de télémétrie et d'historique de la batterie", fg="#71717A", bg="#0D0E12", font=("Segoe UI", 9))
            lbl_subtitle.pack(anchor="w", pady=(2, 0))

            card_frame = tk.Frame(root, bg="#16181D", bd=0)
            card_frame.pack(fill="x", padx=24, pady=8)

            inner_card = tk.Frame(card_frame, bg="#16181D")
            inner_card.pack(fill="x", padx=16, pady=16)

            row_bat = tk.Frame(inner_card, bg="#16181D")
            row_bat.pack(fill="x", pady=3)
            tk.Label(row_bat, text=self.t('battery_label'), fg="#9CA3AF", bg="#16181D", font=("Segoe UI", 10)).pack(side="left")
            tk.Label(row_bat, text=f"{self.battery_level}%  •  {status_text}", fg="#FFFFFF", bg="#16181D", font=("Segoe UI", 10, "bold")).pack(side="right")

            row_auto = tk.Frame(inner_card, bg="#16181D")
            row_auto.pack(fill="x", pady=3)
            tk.Label(row_auto, text=self.t('autonomy'), fg="#9CA3AF", bg="#16181D", font=("Segoe UI", 10)).pack(side="left")
            tk.Label(row_auto, text=self.time_remaining_str, fg="#E4E4E7", bg="#16181D", font=("Segoe UI", 10)).pack(side="right")

            last_charge_display = self.last_full_charge_time if self.last_full_charge_time else self.t("never")
            row_charge = tk.Frame(inner_card, bg="#16181D")
            row_charge.pack(fill="x", pady=3)
            tk.Label(row_charge, text=self.t('last_full_charge'), fg="#9CA3AF", bg="#16181D", font=("Segoe UI", 10)).pack(side="left")
            tk.Label(row_charge, text=last_charge_display, fg="#E4E4E7", bg="#16181D", font=("Segoe UI", 10)).pack(side="right")

            control_frame = tk.Frame(root, bg="#0D0E12")
            control_frame.pack(fill="x", padx=24, pady=(12, 4))

            tk.Label(control_frame, text="Période d'affichage :", fg="#9CA3AF", bg="#0D0E12", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 10))

            history_data = []
            if os.path.exists(HISTORY_PATH):
                try:
                    with open(HISTORY_PATH, "r") as f:
                        history_data = json.load(f)
                except Exception:
                    pass

            fig, ax = plt.subplots(figsize=(5.7, 2.3), dpi=100)
            fig.patch.set_facecolor('#16181D')
            ax.set_facecolor('#101115')
            fig.subplots_adjust(left=0.08, right=0.96, top=0.92, bottom=0.22)

            scatter_points = None
            tooltip_texts = []

            def plot_data(days_filter=None):
                nonlocal scatter_points, tooltip_texts
                ax.clear()
                ax.set_facecolor('#101115')
                
                if history_data:
                    times_all = [datetime.fromtimestamp(h["time"]) for h in history_data]
                    levels_all = [h["level"] for h in history_data]
                    x_nums_all = mdates.date2num(times_all)

                    for i in range(1, len(x_nums_all)):
                        lvl_prev = levels_all[i-1]
                        lvl_curr = levels_all[i]
                        seg_x = [x_nums_all[i-1], x_nums_all[i]]
                        seg_y = [lvl_prev, lvl_curr]

                        level_diff = abs(lvl_prev - lvl_curr)
                        if level_diff > 1:
                            ax.plot(seg_x, seg_y, color="#FF9800", linestyle='--', linewidth=2, alpha=0.9)
                        else:
                            ax.plot(seg_x, seg_y, color="#00E676", linewidth=2)

                    scatter_points = ax.scatter(x_nums_all, levels_all, color="#00E676", s=22, zorder=5, picker=5)
                    tooltip_texts = [f"{t.strftime('%d/%m à %H:%M')} — {l}%" for t, l in zip(times_all, levels_all)]

                    ax.xaxis_date()
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
                    
                    now_num = mdates.date2num(datetime.now())
                    if days_filter == 1:
                        xmin = now_num - 1.0
                        xmax = now_num
                    elif days_filter == 7:
                        xmin = now_num - 7.0
                        xmax = now_num
                    else:
                        xmin = x_nums_all[0]
                        xmax = max(x_nums_all[-1], xmin + 0.5)

                    ax.set_xlim(xmin, xmax)
                    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

                ax.set_ylim(-5, 105)
                ax.tick_params(colors='#71717A', labelsize=8)
                ax.grid(True, color='#27272A', linestyle='--', linewidth=0.5)
                for spine in ax.spines.values():
                    spine.set_edgecolor('#27272A')
                canvas.draw()

            btn_style = {"bg": "#27272A", "fg": "#FFFFFF", "activebackground": "#3F3F46", "activeforeground": "#FFFFFF", "bd": 0, "relief": "flat", "font": ("Segoe UI", 8, "bold"), "padx": 10, "pady": 4}
            
            btn_all = tk.Button(control_frame, text="Tout", command=lambda: plot_data(None), **btn_style)
            btn_all.pack(side="right", padx=2)
            btn_7d = tk.Button(control_frame, text="7 jours", command=lambda: plot_data(7), **btn_style)
            btn_7d.pack(side="right", padx=2)
            btn_24h = tk.Button(control_frame, text="24h", command=lambda: plot_data(1), **btn_style)
            btn_24h.pack(side="right", padx=2)

            chart_frame = tk.Frame(root, bg="#16181D", width=572, height=226)
            chart_frame.pack(fill="none", expand=False, padx=24, pady=6)
            chart_frame.pack_propagate(False)

            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

            plot_data(None)

            legend_frame = tk.Frame(root, bg="#0D0E12")
            legend_frame.pack(fill="x", padx=24, pady=(2, 8))
            tk.Label(legend_frame, text="🟢 Décharge normale", fg="#00E676", bg="#0D0E12", font=("Segoe UI", 8)).pack(side="left", padx=(0, 16))
            tk.Label(legend_frame, text="🟠 Estimation / Saut de %", fg="#FF9800", bg="#0D0E12", font=("Segoe UI", 8)).pack(side="left")

            annot = ax.annotate("", xy=(0,0), xytext=(-20,20), textcoords="offset points",
                                bbox=dict(boxstyle="round,pad=0.4", fc="#18181B", ec="#3F3F46", alpha=0.95),
                                color="#FFFFFF", fontsize=8)
            annot.set_visible(False)

            def on_hover(event):
                if scatter_points is None:
                    return
                if event.inaxes == ax:
                    cont, ind = scatter_points.contains(event)
                    if cont:
                        idx = ind["ind"][0]
                        pos = scatter_points.get_offsets()[idx]
                        annot.xy = pos
                        annot.set_text(tooltip_texts[idx])
                        annot.set_visible(True)
                        canvas.draw_idle()
                    else:
                        if annot.get_visible():
                            annot.set_visible(False)
                            canvas.draw_idle()

            fig.canvas.mpl_connect("motion_notify_event", on_hover)

            pressed = {'val': False, 'x': 0}

            def on_press(event):
                if event.inaxes != ax or event.button != 1:
                    return
                pressed['val'] = True
                pressed['x'] = event.xdata

            def on_motion(event):
                if not pressed['val'] or event.inaxes != ax:
                    return
                if event.xdata is None:
                    return
                dx = pressed['x'] - event.xdata
                cur_xlim = ax.get_xlim()
                ax.set_xlim(cur_xlim[0] + dx, cur_xlim[1] + dx)
                canvas.draw_idle()

            def on_release(event):
                pressed['val'] = False

            def on_scroll(event):
                if event.inaxes != ax:
                    return
                cur_xlim = ax.get_xlim()
                xdata = event.xdata
                if xdata is None:
                    return
                scale_factor = 0.8 if event.button == 'up' else 1.25
                new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
                rel = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
                ax.set_xlim([xdata - new_width * (1 - rel), xdata + new_width * rel])
                canvas.draw_idle()

            fig.canvas.mpl_connect('button_press_event', on_press)
            fig.canvas.mpl_connect('motion_notify_event', on_motion)
            fig.canvas.mpl_connect('button_release_event', on_release)
            fig.canvas.mpl_connect('scroll_event', on_scroll)

            footer_frame = tk.Frame(root, bg="#0D0E12")
            footer_frame.pack(fill="x", padx=24, pady=(4, 16))

            lbl_author = tk.Label(footer_frame, text=f"Développé par Jessy JONKISZ ({CURRENT_VERSION})", fg="#52525B", bg="#0D0E12", font=("Segoe UI", 8))
            lbl_author.pack(side="left")

            btn_close = tk.Button(footer_frame, text="Fermer", command=root.destroy, bg="#27272A", fg="#FFFFFF", activebackground="#3F3F46", activeforeground="#FFFFFF", bd=0, relief="flat", font=("Segoe UI", 9, "bold"), padx=16, pady=4)
            btn_close.pack(side="right")

            root.mainloop()

        threading.Thread(target=run_tk, daemon=True).start()

    def rebuild_menu(self):
        last_charge_display = self.last_full_charge_time if self.last_full_charge_time else self.t("never")
        
        menu = pystray.Menu(
            pystray.MenuItem(f"Keychron M3 — {CURRENT_VERSION}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self.t("show_stats"), self.show_popup_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: f"{self.t('battery_label')} : {self.battery_level}%" if self.is_connected else self.t("offline"), None, enabled=False),
            pystray.MenuItem(lambda item: f"{self.t('autonomy')} : {self.time_remaining_str}", None, enabled=False),
            pystray.MenuItem(lambda item: f"{self.t('last_full_charge')} : {last_charge_display}", None, enabled=False),
            pystray.MenuItem(lambda item: f"{self.t('record')} : {self.last_update}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self.t("menu_update"), self.menu_check_update_action),
            pystray.MenuItem(self.t("menu_style"), pystray.Menu(
                pystray.MenuItem(self.t("style_circle"), self.set_style("Cercle épuré"), checked=lambda item: self.config["style"] in ["Cercle épuré", "Clean circle"]),
                pystray.MenuItem(self.t("style_solid"), self.set_style("Cercle plein"), checked=lambda item: self.config["style"] in ["Cercle plein", "Solid circle"]),
                pystray.MenuItem(self.t("style_h_bat"), self.set_style("Batterie horizontale"), checked=lambda item: self.config["style"] in ["Batterie horizontale", "Horizontal battery"]),
                pystray.MenuItem(self.t("style_v_bat"), self.set_style("Batterie verticale"), checked=lambda item: self.config["style"] in ["Batterie verticale", "Vertical battery"]),
            )),
            pystray.MenuItem(self.t("menu_lang"), pystray.Menu(
                pystray.MenuItem(self.t("lang_auto"), self.set_language("auto"), checked=lambda item: self.config.get("language", "auto") == "auto"),
                pystray.MenuItem(self.t("lang_fr"), self.set_language("fr"), checked=lambda item: self.config.get("language") == "fr"),
                pystray.MenuItem(self.t("lang_en"), self.set_language("en"), checked=lambda item: self.config.get("language") == "en"),
            )),
            pystray.MenuItem(self.t("menu_colors"), pystray.Menu(
                pystray.MenuItem(lambda item: self.t("orange_threshold").format(self.config['color_high']), None, enabled=False),
                pystray.MenuItem(self.t("set_orange").format(60), self.set_color_limits(60, 20)),
                pystray.MenuItem(self.t("set_orange").format(50), self.set_color_limits(50, 20)),
                pystray.MenuItem(self.t("set_orange").format(40), self.set_color_limits(40, 15)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(lambda item: self.t("red_threshold").format(self.config['color_low']), None, enabled=False),
                pystray.MenuItem(self.t("set_red").format(25), self.set_color_limits(self.config["color_high"], 25)),
                pystray.MenuItem(self.t("set_red").format(20), self.set_color_limits(self.config["color_high"], 20)),
                pystray.MenuItem(self.t("set_red").format(10), self.set_color_limits(self.config["color_high"], 10)),
            )),
            pystray.MenuItem(self.t("menu_interval"), pystray.Menu(
                pystray.MenuItem(f"15 {self.t('sec')}", self.set_interval(15), checked=lambda item: self.config["poll_interval"] == 15),
                pystray.MenuItem(f"30 {self.t('sec')}", self.set_interval(30), checked=lambda item: self.config["poll_interval"] == 30),
                pystray.MenuItem(f"1 {self.t('min')}", self.set_interval(60), checked=lambda item: self.config["poll_interval"] == 60),
                pystray.MenuItem(f"5 {self.t('mins')}", self.set_interval(300), checked=lambda item: self.config["poll_interval"] == 300),
            )),
            pystray.MenuItem(self.t("startup"), self.toggle_startup, checked=lambda item: os.path.exists(self.shortcut_path)),
            pystray.MenuItem(self.t("refresh"), self.update_status),
            pystray.MenuItem(self.t("quit"), self.quit)
        )
        if hasattr(self, 'icon') and self.icon:
            self.icon.menu = menu
        else:
            initial_icon = create_battery_icon(self.battery_level, self.is_charging, self.is_connected, config=self.config)
            initial_title = self.get_safe_tooltip()
            self.icon = pystray.Icon("Keychron M3", icon=initial_icon, title=initial_title, menu=menu)

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except Exception:
                pass
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception:
            pass

    def record_history(self, level, is_charging):
        history = []
        if os.path.exists(HISTORY_PATH):
            try:
                with open(HISTORY_PATH, "r") as f:
                    history = json.load(f)
            except Exception:
                pass
        
        if is_charging:
            if history and history[-1]["level"] != 100:
                history.append({"time": time.time(), "level": 100})
            else:
                return
        
        if history and history[-1]["level"] == level:
            return

        now = time.time()
        history.append({"time": now, "level": level})
        
        cycles = []
        current_cycle = []
        for h in history:
            if current_cycle and h["level"] > current_cycle[-1]["level"]:
                cycles.append(current_cycle)
                current_cycle = [h]
            else:
                current_cycle.append(h)
        if current_cycle:
            cycles.append(current_cycle)

        if len(cycles) > 5:
            cycles = cycles[-5:]

        history = [item for cycle in cycles for item in cycle]
        
        try:
            with open(HISTORY_PATH, "w") as f:
                json.dump(history, f)
        except Exception:
            pass

    def update_time_remaining(self):
        if self.is_charging:
            self.time_remaining_str = self.t("charging")
            return

        if not os.path.exists(HISTORY_PATH):
            self.time_remaining_str = self.t("insufficient_data")
            return

        try:
            with open(HISTORY_PATH, "r") as f:
                history = json.load(f)
            if len(history) < 2:
                self.time_remaining_str = self.t("calculating")
                return

            oldest = history[0]
            newest = history[-1]
            time_diff_hours = (newest["time"] - oldest["time"]) / 3600.0
            level_diff = oldest["level"] - newest["level"]

            if time_diff_hours > 0.05 and level_diff > 0:
                drain_rate = level_diff / time_diff_hours
                if drain_rate > 0:
                    hours_left = self.battery_level / drain_rate
                    td = timedelta(hours=hours_left)
                    h = int(td.total_seconds() // 3600)
                    m = int((td.total_seconds() % 3600) // 60)
                    lang = self.get_current_lang()
                    self.time_remaining_str = f"~{h}h {m}min" if lang == "en" else f"~{h}h {m}min restantes"
                    return
        except Exception:
            pass
        self.time_remaining_str = self.t("unavailable")

    def set_style(self, style_name):
        def inner(icon, item):
            self.config["style"] = style_name
            self.save_config()
            self.update_status()
        return inner

    def set_language(self, lang_code):
        def inner(icon, item):
            self.config["language"] = lang_code
            self.save_config()
            self.rebuild_menu()
            self.update_status()
        return inner

    def set_color_limits(self, high, low):
        def inner(icon, item):
            self.config["color_high"] = high
            self.config["color_low"] = low
            self.save_config()
            self.update_status()
        return inner

    def set_interval(self, seconds):
        def inner(icon, item):
            self.config["poll_interval"] = seconds
            self.save_config()
            self.update_status()
        return inner

    def read_battery(self):
        try:
            devices = hid.enumerate(VENDOR_ID)
            if not devices:
                return None, False, False

            sorted_devices = sorted(devices, key=lambda x: 0 if x['product_id'] == 0xD033 else 1)

            for d in sorted_devices:
                pid = d['product_id']
                if pid not in [0xD033, 0xD030]:
                    continue

                path = d['path']
                try:
                    h = hid.device()
                    h.open_path(path)
                    
                    report_data = [0x00] * 65
                    report_data[0] = 0x51
                    report_data[1] = 0x06
                    h.send_feature_report(report_data)

                    time.sleep(0.03)
                    resp = h.get_feature_report(0x51, 65)
                    h.close()

                    if resp and len(resp) > 11:
                        val = resp[11]
                        if 1 <= val <= 100:
                            is_charging = (pid == 0xD033)
                            return val, is_charging, True
                except Exception:
                    try:
                        h.close()
                    except Exception:
                        pass
                    continue

        except Exception:
            pass

        return None, False, False

    def update_status(self):
        level, charging, connected = self.read_battery()
        
        if connected and level is not None:
            self.check_full_charge(level, charging)
            if os.path.exists(HISTORY_PATH):
                try:
                    with open(HISTORY_PATH, "r") as f:
                        history = json.load(f)
                    if history and level > history[-1]["level"]:
                        charging = True
                except Exception:
                    pass

        self.last_update = datetime.now().strftime("%H:%M:%S")

        if connected and level is not None:
            self.battery_level = level
            self.is_charging = charging
            self.is_connected = True
            self.record_history(level, charging)
            self.update_time_remaining()

            self.icon.title = self.get_safe_tooltip()
            self.icon.icon = create_battery_icon(level, charging, is_connected=True, config=self.config)

            if level <= 15 and not charging:
                if not self.alert_sent:
                    self.icon.notify(
                        self.t("low_battery_msg").format(level),
                        self.t("low_battery_title")
                    )
                    self.alert_sent = True
            else:
                self.alert_sent = False
        else:
            self.is_connected = False
            self.icon.title = self.get_safe_tooltip()
            self.icon.icon = create_battery_icon(0, is_connected=False, config=self.config)

    def toggle_startup(self, icon, item):
        script_path = os.path.join(INSTALL_DIR, "keychron_battery_jj.pyw")
        
        if os.path.exists(self.shortcut_path):
            try:
                os.remove(self.shortcut_path)
            except Exception:
                pass
        else:
            try:
                ps_command = (
                    f"$ws = New-Object -ComObject WScript.Shell; "
                    f"$sc = $ws.CreateShortcut('{self.shortcut_path}'); "
                    f"$sc.TargetPath = 'pythonw.exe'; "
                    f"$sc.Arguments = '\"{script_path}\"'; "
                    f"$sc.WorkingDirectory = '{INSTALL_DIR}'; "
                    f"$sc.Save()"
                )
                subprocess.run(
                    ["powershell", "-WindowStyle", "Hidden", "-Command", ps_command],
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception:
                pass

    def background_loop(self):
        while self.running:
            poll_interval = self.config.get("poll_interval", 30)
            sleep_time = 5 if not self.is_connected else poll_interval
            time.sleep(sleep_time)
            self.update_status()

    def run(self):
        thread = threading.Thread(target=self.background_loop, daemon=True)
        thread.start()
        self.icon.run()

    def quit(self, icon, item):
        self.running = False
        self.icon.stop()

if __name__ == "__main__":
    app = KeychronBatteryMonitor()
    app.run()
