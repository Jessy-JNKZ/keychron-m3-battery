import subprocess
import sys

# --- VÉRIFICATION ET INSTALLATION AUTOMATIQUE DES DÉPENDANCES ---
required_packages = {
    "hidapi": "hid",
    "Pillow": "PIL",
    "pystray": "pystray"
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
from PIL import Image, ImageDraw, ImageFont
import pystray
import hid

INSTALL_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

DATA_DIR = os.path.join(os.getenv('APPDATA'), 'KeychronBatteryMonitorJJ')
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
HISTORY_PATH = os.path.join(DATA_DIR, "history.json")

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
        "record": "Relevé",
        "calculating": "Calcul en cours...",
        "in_progress": "En cours...",
        "insufficient_data": "Données insuffisantes",
        "unavailable": "Estimation indisponible",
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
        "low_battery_title": "Keychron M3 JJ",
        "low_battery_msg": "Batterie faible : {}% restant.\nPensez à rebrancher votre souris !",
        "tooltip_offline": "Keychron M3 : Hors ligne\nDernier relevé : {}"
    },
    "en": {
        "offline": "Mouse: Offline",
        "charging": "Charging (USB)",
        "on_battery": "On battery",
        "battery_label": "Battery",
        "autonomy": "Battery life",
        "record": "Last update",
        "calculating": "Calculating...",
        "in_progress": "In progress...",
        "insufficient_data": "Insufficient data",
        "unavailable": "Estimate unavailable",
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
        "mins": "minutes",
        "startup": "Launch at startup",
        "refresh": "Refresh",
        "quit": "Quit",
        "low_battery_title": "Keychron M3 JJ",
        "low_battery_msg": "Low battery: {}% remaining.\nConsider plugging in your mouse!",
        "tooltip_offline": "Keychron M3: Offline\nLast update: {}"
    }
}

FONT_CACHE = {}

def get_cached_font(size):
    if size not in FONT_CACHE:
        try:
            FONT_CACHE[size] = ImageFont.truetype("arialbd.ttf", size)
        except IOError:
            FONT_CACHE[size] = ImageFont.load_default()
    return FONT_CACHE[size]

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
            (36, 10),
            (22, 34),
            (32, 34),
            (26, 54),
            (44, 28),
            (34, 28),
            (36, 10)
        ]
        draw.polygon(bolt_points, fill=(0, 230, 118))
        return image

    if style in ["Cercle épuré", "Clean circle"]:
        draw.ellipse([6, 6, 58, 58], outline=(40, 40, 40), width=8)
        if is_connected and level > 0:
            angle = int(360.0 * (max(0, min(level, 100)) / 100.0))
            if angle > 0:
                draw.arc([6, 6, 58, 58], start=-90, end=-90 + angle, fill=main_color, width=8)

    elif style in ["Cercle plein", "Solid circle"]:
        draw.ellipse([8, 8, 56, 56], fill=(40, 40, 40))
        if is_connected and level > 0:
            fill_h = int(48 * (max(0, min(level, 100)) / 100.0))
            if fill_h > 0:
                draw.pieslice([8, 8, 56, 56], start=0, end=360, fill=main_color)

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

class KeychronBatteryMonitorJJ:
    def __init__(self):
        self.config = self.load_config()
        self.battery_level = 0
        self.is_charging = False
        self.is_connected = False
        self.running = True
        self.alert_sent = False
        self.last_update = self.t("in_progress")
        self.time_remaining_str = self.t("calculating")
        
        self.startup_folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        self.shortcut_path = os.path.join(self.startup_folder, 'KeychronBatteryMonitorJJ.lnk')

        level, charging, connected = self.read_battery()
        if connected and level is not None:
            self.battery_level = level
            self.is_charging = charging
            self.is_connected = True
            self.last_update = datetime.now().strftime("%H:%M:%S")
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

    def rebuild_menu(self):
        menu = pystray.Menu(
            pystray.MenuItem(lambda item: f"{self.t('battery_label')} : {self.battery_level}%" if self.is_connected else self.t("offline"), None, enabled=False),
            pystray.MenuItem(lambda item: f"{self.t('autonomy')} : {self.time_remaining_str}", None, enabled=False),
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
            self.icon = pystray.Icon("Keychron M3 JJ", icon=initial_icon, title=initial_title, menu=menu)

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
        return f"Keychron M3 : {self.battery_level}% ({status_text})\n{self.t('autonomy')} : {self.time_remaining_str}\n{self.t('record')} : {self.last_update}"

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
    app = KeychronBatteryMonitorJJ()
    app.run()
