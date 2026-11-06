import os
import sys
import json
import time
import threading
import subprocess
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import pystray

INSTALL_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(INSTALL_DIR, "config.json")
HISTORY_PATH = os.path.join(INSTALL_DIR, "history.json")

VENDOR_ID = 0x3434
PRODUCT_ID = 0xD030

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
hid_dll = ctypes.WinDLL('hid', use_last_error=True)

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = -1

def get_hid_function(name):
    try:
        fn = getattr(hid_dll, name)
        fn.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.ULONG]
        fn.restype = wintypes.BOOL
        return fn
    except AttributeError:
        return None

HidD_SetFeature = get_hid_function('HidD_SetFeature') or get_hid_function('HidD_SetFeatureReport')
HidD_GetFeature = get_hid_function('HidD_GetFeature') or get_hid_function('HidD_GetFeatureReport')

TARGET_PATHS = [
    r"\\?\hid#vid_3434&pid_d030&mi_01&col01#8&2c14466c&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}",
    r"\\?\hid#vid_3434&pid_d030&mi_01&col02#8&2c14466c&0&0001#{4d1e55b2-f16f-11cf-88cb-001111000030}"
]

REPORT_ID = 0x51
STATUS_CMD = 0x06
LEVEL_INDEX = 11

DEFAULT_CONFIG = {
    "poll_interval": 30,
    "style": "Cercle épuré",
    "color_high": 50,
    "color_low": 20
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
        return (46, 125, 50)  # Vert
    elif level > config["color_low"]:
        return (255, 160, 0)  # Orange
    else:
        return (229, 57, 53)  # Rouge

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
        font = get_cached_font(42)
        text = "+"
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (size - (bbox[2] - bbox[0])) // 2
        y = (size - (bbox[3] - bbox[1])) // 2 - 4
        draw.text((x, y), text, fill=(0, 230, 118), font=font)
        return image

    if style == "Cercle épuré":
        draw.ellipse([6, 6, 58, 58], outline=(40, 40, 40), width=8)
        if is_connected and level > 0:
            angle = int(360.0 * (max(0, min(level, 100)) / 100.0))
            if angle > 0:
                draw.arc([6, 6, 58, 58], start=-90, end=-90 + angle, fill=main_color, width=8)

    elif style == "Cercle plein":
        draw.ellipse([8, 8, 56, 56], fill=(40, 40, 40))
        if is_connected and level > 0:
            fill_h = int(48 * (max(0, min(level, 100)) / 100.0))
            if fill_h > 0:
                draw.pieslice([8, 8, 56, 56], start=0, end=360, fill=main_color)

    elif style == "Batterie horizontale":
        draw.rounded_rectangle([4, 16, 52, 48], radius=6, outline=(180, 180, 180), width=4)
        draw.rounded_rectangle([52, 26, 58, 38], radius=2, fill=(180, 180, 180))
        if is_connected and level > 0:
            fill_w = int(40 * (max(0, min(level, 100)) / 100.0))
            if fill_w > 0:
                draw.rounded_rectangle([8, 20, 8 + fill_w, 44], radius=4, fill=main_color)

    elif style == "Batterie verticale":
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
        self.last_update = "En cours..."
        self.time_remaining_str = "Calcul en cours..."
        
        self.startup_folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        self.shortcut_path = os.path.join(self.startup_folder, 'KeychronBatteryMonitorJJ.lnk')

        level, charging, connected = self.read_battery()
        if connected and level is not None:
            self.battery_level = level
            self.is_charging = charging
            self.is_connected = True
            self.last_update = datetime.now().strftime("%H:%M:%S")
            self.record_history(level)
            self.update_time_remaining()
            initial_icon = create_battery_icon(level, charging, is_connected=True, config=self.config)
            initial_title = self.get_tooltip_text()
        else:
            initial_icon = create_battery_icon(0, is_connected=False, config=self.config)
            initial_title = "Keychron M3 : Hors ligne"

        self.icon = pystray.Icon(
            "Keychron M3 JJ",
            icon=initial_icon,
            title=initial_title,
            menu=pystray.Menu(
                pystray.MenuItem(lambda item: f"Batterie : {self.battery_level}%" if self.is_connected else "Souris : Hors ligne", None, enabled=False),
                pystray.MenuItem(lambda item: f"Autonomie : {self.time_remaining_str}", None, enabled=False),
                pystray.MenuItem(lambda item: f"Relevé : {self.last_update}", None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Style d'affichage", pystray.Menu(
                    pystray.MenuItem("Cercle épuré", self.set_style("Cercle épuré"), checked=lambda item: self.config["style"] == "Cercle épuré"),
                    pystray.MenuItem("Cercle plein", self.set_style("Cercle plein"), checked=lambda item: self.config["style"] == "Cercle plein"),
                    pystray.MenuItem("Batterie horizontale", self.set_style("Batterie horizontale"), checked=lambda item: self.config["style"] == "Batterie horizontale"),
                    pystray.MenuItem("Batterie verticale", self.set_style("Batterie verticale"), checked=lambda item: self.config["style"] == "Batterie verticale"),
                )),
                pystray.MenuItem("Limites de couleur", pystray.Menu(
                    pystray.MenuItem(lambda item: f"Seuil Orange (Actuel: <{self.config['color_high']}%)", None, enabled=False),
                    pystray.MenuItem("Passer seuil orange à 60%", self.set_color_limits(60, 20)),
                    pystray.MenuItem("Passer seuil orange à 50%", self.set_color_limits(50, 20)),
                    pystray.MenuItem("Passer seuil orange à 40%", self.set_color_limits(40, 15)),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem(lambda item: f"Seuil Rouge (Actuel: <{self.config['color_low']}%)", None, enabled=False),
                    pystray.MenuItem("Passer seuil rouge à 25%", self.set_color_limits(self.config["color_high"], 25)),
                    pystray.MenuItem("Passer seuil rouge à 20%", self.set_color_limits(self.config["color_high"], 20)),
                    pystray.MenuItem("Passer seuil rouge à 10%", self.set_color_limits(self.config["color_high"], 10)),
                )),
                pystray.MenuItem("Fréquence de rafraîchissement", pystray.Menu(
                    pystray.MenuItem("15 secondes", self.set_interval(15), checked=lambda item: self.config["poll_interval"] == 15),
                    pystray.MenuItem("30 secondes", self.set_interval(30), checked=lambda item: self.config["poll_interval"] == 30),
                    pystray.MenuItem("1 minute", self.set_interval(60), checked=lambda item: self.config["poll_interval"] == 60),
                    pystray.MenuItem("5 minutes", self.set_interval(300), checked=lambda item: self.config["poll_interval"] == 300),
                )),
                pystray.MenuItem("Lancer au démarrage", self.toggle_startup, checked=lambda item: os.path.exists(self.shortcut_path)),
                pystray.MenuItem("Rafraîchir", self.update_status),
                pystray.MenuItem("Quitter", self.quit)
            )
        )

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

    def record_history(self, level):
        history = []
        if os.path.exists(HISTORY_PATH):
            try:
                with open(HISTORY_PATH, "r") as f:
                    history = json.load(f)
            except Exception:
                pass
        
        now = time.time()
        history.append({"time": now, "level": level})
        
        # Filtre temporel (24h) et limite stricte de quantité (100 points max)
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
        if not os.path.exists(HISTORY_PATH):
            self.time_remaining_str = "Données insuffisantes"
            return

        try:
            with open(HISTORY_PATH, "r") as f:
                history = json.load(f)
            if len(history) < 2:
                self.time_remaining_str = "Calcul en cours..."
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
                    self.time_remaining_str = f"~{h}h {m}min restantes"
                    return
        except Exception:
            pass
        self.time_remaining_str = "Estimation indisponible"

    def set_style(self, style_name):
        def inner(icon, item):
            self.config["style"] = style_name
            self.save_config()
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
        status_text = "En charge" if self.is_charging else "Sur batterie"
        return f"Keychron M3 : {self.battery_level}% ({status_text})\nAutonomie : {self.time_remaining_str}\nDernier relevé : {self.last_update}"

    def read_battery(self):
        for path in TARGET_PATHS:
            handle = INVALID_HANDLE_VALUE
            try:
                handle = kernel32.CreateFileW(
                    path, GENERIC_READ | GENERIC_WRITE,
                    FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None
                )
                if handle == INVALID_HANDLE_VALUE or handle == 0:
                    continue

                req_buffer = (ctypes.c_ubyte * 65)()
                req_buffer[0] = REPORT_ID
                req_buffer[1] = STATUS_CMD

                if HidD_SetFeature:
                    HidD_SetFeature(handle, ctypes.byref(req_buffer), 65)

                time.sleep(0.04)
                resp_buffer = (ctypes.c_ubyte * 65)()
                resp_buffer[0] = REPORT_ID

                res_get = False
                if HidD_GetFeature:
                    res_get = HidD_GetFeature(handle, ctypes.byref(resp_buffer), 65)

                if res_get:
                    data = list(resp_buffer)
                    if len(data) > LEVEL_INDEX:
                        val = data[LEVEL_INDEX]
                        is_connected = bool(data[9] == 1) if len(data) > 9 else True
                        is_charging = bool(data[2] == 0x02) if len(data) > 2 else False

                        if 1 <= val <= 100 and is_connected:
                            return val, is_charging, True
            except Exception:
                pass
            finally:
                if handle != INVALID_HANDLE_VALUE and handle != 0:
                    kernel32.CloseHandle(handle)
        return None, False, False

    def update_status(self):
        level, charging, connected = self.read_battery()
        self.last_update = datetime.now().strftime("%H:%M:%S")

        if connected and level is not None:
            self.battery_level = level
            self.is_charging = charging
            self.is_connected = True
            self.record_history(level)
            self.update_time_remaining()

            self.icon.title = self.get_tooltip_text()
            self.icon.icon = create_battery_icon(level, charging, is_connected=True, config=self.config)

            if level <= 15 and not charging:
                if not self.alert_sent:
                    self.icon.notify(
                        f"Batterie faible : {level}% restant.\nPensez à rebrancher votre souris !",
                        "Keychron M3 JJ"
                    )
                    self.alert_sent = True
            else:
                self.alert_sent = False
        else:
            self.is_connected = False
            self.icon.title = f"Keychron M3 : Hors ligne\nDernier relevé : {self.last_update}"
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