# ==============================================================================
# Nom du projet : Keychron Battery Monitor
# Auteur        : Jessy JONKISZ
# X (Twitter)   : https://x.com/JNKZJessy
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
from datetime import datetime, timedelta
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont
import pystray
import hid

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

INSTALL_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

DATA_DIR = os.path.join(os.getenv('APPDATA'), 'KeychronBatteryMonitorJJ')
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
HISTORY_PATH = os.path.join(DATA_DIR, "history.json")
STATS_PATH = os.path.join(DATA_DIR, "stats.json")

VENDOR_ID = 0x3434

DEFAULT_CONFIG = {
    "poll_interval": 30,
    "style": "Cercle épuré",
    "color_high": 50,
    "color_low": 20,
    "language": "auto"
}

def get_system_language():
    try:
        import ctypes
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
        "autonomy": "Autonomie",
        "last_full_charge": "Dernière charge 100%",
        "never": "Jamais",
        "record": "Relevé",
        "calculating": "Calcul en cours...",
        "in_progress": "En cours...",
        "insufficient_data": "Données insuffisantes",
        "unavailable": "Estimation indisponible",
        "show_stats": "📊 Afficher les statistiques",
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
        "tooltip_offline": "Keychron M3 : Hors ligne\nDernier relevé : {}"
    },
    "en": {
        "offline": "Mouse: Offline",
        "charging": "Charging (USB)",
        "on_battery": "On battery",
        "battery_label": "Battery",
        "autonomy": "Battery life",
        "last_full_charge": "Last 100% charge",
        "never": "Never",
        "record": "Last update",
        "calculating": "Calculating...",
        "in_progress": "In progress...",
        "insufficient_data": "Insufficient data",
        "unavailable": "Estimate unavailable",
        "show_stats": "📊 Show statistics",
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
        "tooltip_offline": "Keychron M3: Offline\nLast update: {}"
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
        bolt_points = [
            (36, 8),
            (21, 33),
            (31, 33),
            (25, 56),
            (45, 27),
            (34, 27),
            (36, 8)
        ]
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
            fill_h = int(52 * (max(0, min(level, 100)) / 100.0))
            if fill_h > 0:
                draw.pieslice([6, 6, 58, 58], start=0, end=360, fill=main_color)

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
            initial_title = self.get_tooltip_text()
        else:
            initial_icon = create_battery_icon(0, is_connected=False, config=self.config)
            initial_title = self.t("tooltip_offline").format("---")

        self.rebuild_menu()

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

    def show_popup_window(self, icon=None, item=None):
        """Ouvre une fenêtre Tkinter avec stats et graphique (vert continu si consécutif, pointillé orange si saut de %s)"""
        def run_tk():
            root = tk.Tk()
            root.title("Keychron M3 - Stats & Historique")
            root.geometry("580x520")
            root.configure(bg="#1e1e1e")
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

            lbl_title = tk.Label(root, text="Keychron M3", fg="#00e676", bg="#1e1e1e", font=("Segoe UI", 12, "bold"))
            lbl_title.pack(pady=(12, 5))

            info_frame = tk.Frame(root, bg="#1e1e1e")
            info_frame.pack(fill="x", padx=20, pady=5)

            lbl_bat = tk.Label(info_frame, text=f"{self.t('battery_label')} : {self.battery_level}% ({status_text})", fg="#ffffff", bg="#1e1e1e", font=("Segoe UI", 9, "bold"), anchor="w")
            lbl_bat.pack(fill="x")

            lbl_auto = tk.Label(info_frame, text=f"{self.t('autonomy')} : {self.time_remaining_str}", fg="#b0b0b0", bg="#1e1e1e", font=("Segoe UI", 9), anchor="w")
            lbl_auto.pack(fill="x")

            last_charge_display = self.last_full_charge_time if self.last_full_charge_time else self.t("never")
            lbl_charge = tk.Label(info_frame, text=f"{self.t('last_full_charge')} : {last_charge_display}", fg="#b0b0b0", bg="#1e1e1e", font=("Segoe UI", 9), anchor="w")
            lbl_charge.pack(fill="x")

            chart_frame = tk.Frame(root, bg="#1e1e1e")
            chart_frame.pack(fill="both", expand=True, padx=15, pady=5)

            history_data = []
            if os.path.exists(HISTORY_PATH):
                try:
                    with open(HISTORY_PATH, "r") as f:
                        history_data = json.load(f)
                except Exception:
                    pass

            fig, ax = plt.subplots(figsize=(5.5, 2.0), dpi=100)
            fig.patch.set_facecolor('#1e1e1e')
            ax.set_facecolor('#121212')

            if history_data:
                times = [datetime.fromtimestamp(h["time"]) for h in history_data]
                levels = [h["level"] for h in history_data]
                x_nums = matplotlib.dates.date2num(times)

                for i in range(1, len(x_nums)):
                    lvl_prev = levels[i-1]
                    lvl_curr = levels[i]
                    seg_x = [x_nums[i-1], x_nums[i]]
                    seg_y = [lvl_prev, lvl_curr]

                    level_diff = abs(lvl_prev - lvl_curr)

                    if level_diff > 1:
                        ax.plot(seg_x, seg_y, color="#ff9800", linestyle='--', linewidth=2, alpha=0.85)
                    else:
                        ax.plot(seg_x, seg_y, color="#00e676", linewidth=2)

                ax.xaxis_date()
                ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))
                
                xmin = x_nums[0]
                xmax = max(x_nums[-1], xmin + 1.0)
                ax.set_xlim(xmin, xmax)
                ax.xaxis.set_major_locator(matplotlib.dates.HourLocator(interval=2))
            
            ax.set_ylim(-5, 105)
            ax.tick_params(colors='#b0b0b0', labelsize=8)
            fig.autofmt_xdate(rotation=15, ha='center')
            ax.grid(True, color='#2a2a2a', linestyle='--', linewidth=0.5)
            
            for spine in ax.spines.values():
                spine.set_edgecolor('#333333')

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

            # Mention de l'auteur en bas de la fenêtre
            lbl_author = tk.Label(root, text="Développé par Jessy JONKISZ — https://x.com/JNKZJessy", fg="#777777", bg="#1e1e1e", font=("Segoe UI", 8))
            lbl_author.pack(pady=(2, 0))

            btn_close = tk.Button(root, text="Fermer", command=root.destroy, bg="#333333", fg="#ffffff", bd=0, relief="flat", font=("Segoe UI", 9))
            btn_close.pack(pady=8, ipadx=15, ipady=2)

            root.mainloop()

        threading.Thread(target=run_tk, daemon=True).start()

    def rebuild_menu(self):
        last_charge_display = self.last_full_charge_time if self.last_full_charge_time else self.t("never")
        
        menu = pystray.Menu(
            pystray.MenuItem(self.t("show_stats"), self.show_popup_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: f"{self.t('battery_label')} : {self.battery_level}%" if self.is_connected else self.t("offline"), None, enabled=False),
            pystray.MenuItem(lambda item: f"{self.t('autonomy')} : {self.time_remaining_str}", None, enabled=False),
            pystray.MenuItem(lambda item: f"{self.t('last_full_charge')} : {last_charge_display}", None, enabled=False),
            pystray.MenuItem(lambda item: f"{self.t('record')} : {self.last_update}", None, enabled=False),
            pystray.Menu.SEPARATOR,
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
            initial_title = self.get_tooltip_text() if self.is_connected else self.t("tooltip_offline").format("---")
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
        
        if is_charging or (history and level > history[-1]["level"]):
            history = []
        
        if history and history[-1]["level"] == level:
            return

        now = time.time()
        history.append({"time": now, "level": level})
        
        cutoff = now - 86400
        history = [h for h in history if h["time"] > cutoff]
        
        MAX_HISTORY_ITEMS = 100
        if len(history) > MAX_HISTORY_ITEMS:
            history = history[-MAX_HISTORY_ITEMS:]
        
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

    def get_tooltip_text(self):
        status_text = self.t("charging") if self.is_charging else self.t("on_battery")
        last_charge_display = self.last_full_charge_time if self.last_full_charge_time else self.t("never")
        return (f"Keychron M3 : {self.battery_level}% ({status_text})\n"
                f"{self.t('autonomy')} : {self.time_remaining_str}\n"
                f"{self.t('last_full_charge')} : {last_charge_display}\n"
                f"{self.t('record')} : {self.last_update}")

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

            self.icon.title = self.get_tooltip_text()
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
            self.icon.title = self.t("tooltip_offline").format(self.last_update)
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
            time.sleep(self.config.get("poll_interval", 30))
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
