#!/usr/bin/env python3
"""SA-MP Launcher for Linux / SA-MP лаунчер для Linux.

Нативный Qt-лаунчер: список серверов, избранное, ник, путь к папке GTA SA.
Сам gta_sa.exe — программа для Windows, поэтому игра запускается через Wine
в отдельном окружении (префиксе), которое лаунчер создаёт и настраивает сам.
"""

import json
import os
import shlex
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import PySide6  # noqa: F401
except ImportError:
    _msg = ("PySide6 (Qt for Python) is not installed / не установлен PySide6.\n\n"
            "Run / выполните:  ./install.sh\n"
            "or / или:  pip install --user PySide6")
    print(_msg, file=sys.stderr)
    for _cmd in (["kdialog", "--error", _msg], ["notify-send", "SA-MP Launcher", _msg]):
        if shutil.which(_cmd[0]):
            subprocess.run(_cmd)
            break
    sys.exit(1)

from PySide6.QtCore import (QObject, Qt, QUrl, Signal, QTimer, QSortFilterProxyModel, QRegularExpression,
                            QLocale, QStandardPaths)
from PySide6.QtGui import (QAction, QDesktopServices, QIcon, QImage, QGuiApplication, QStandardItem,
                           QStandardItemModel, QRegularExpressionValidator)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFrame, QDialogButtonBox, QFileDialog, QFormLayout,
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QTableView, QTabWidget, QToolBar, QVBoxLayout, QWidget, QAbstractItemView,
)

APP_NAME = "SA-MP Launcher"
APP_VERSION = "1.5"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "samp-launcher"
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "samp-launcher"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE = DATA_DIR / "wine.log"

DEFAULT_CONFIG = {
    "nickname": "",
    "language": "auto",        # auto | ru | en
    "gta_dir": "",
    "client_exe": "samp.exe",
    "launch_args": "{host}:{port}",
    "password_args": "-z {password}",
    "wine": "wine",
    "prefix": str(DATA_DIR / "prefix"),
    "api_url": "https://api.open.mp/servers",
    "virtual_desktop": False,  # окно-«рабочий стол» Wine (меняет список разрешений — по умолчанию выкл.)
    "vsync": False,            # вертикальная синхронизация (выкл. = FPS не упирается в герцовку)
    "kill_error_dialog": True, # закрывать окно «Runtime Error R6025» при выходе через /q
    "desktop_size": "",       # пусто = размер экрана
    "favorites": [],  # [{host, port, name, password}]
}

NICK_CHARS = r"[A-Za-z0-9_\[\]\.\$=@()]"  # символы, разрешённые SA-MP в нике
GTA_SA_10US_SIZE = 14383616  # размер gta_sa.exe версии 1.0 US


# ---------------------------------------------------------------- i18n
# Исходный язык интерфейса — русский. EN — перевод по ключу (русской строке).

EN = {
    "Название сервера": "Server name", "Игроки": "Players", "Пинг": "Ping", "Режим": "Mode", "Язык": "Language",
    "(нет ответа) {key}": "(no response) {key}",
    "Настройки": "Settings", "Обзор…": "Browse…",
    "Папка GTA San Andreas:": "GTA San Andreas folder:",
    "Файл клиента SA-MP:": "SA-MP client file:",
    "Аргументы запуска:": "Launch arguments:",
    "Подстановки: {host} {port} {nick} {password}": "Placeholders: {host} {port} {nick} {password}",
    "Язык интерфейса:": "Interface language:",
    "Авто (как в системе)": "Auto (system language)",
    "Вертикальная синхронизация (V-Sync)": "Vertical sync (V-Sync)",
    "Закрывать окно ошибки R6025 при выходе (/q)": "Close the R6025 error window on exit (/q)",
    "Виртуальный рабочий стол Wine (после смены — заново выбрать разрешение в игре)":
        "Wine virtual desktop (after changing, re-select the resolution in game)",
    "авто ({size})": "auto ({size})",
    "Размер окна игры:": "Game window size:",
    "Аргументы пароля:": "Password arguments:",
    "Список серверов (API):": "Server list (API):",
    "Совместимость (запуск Windows-игры)": "Compatibility (running the Windows game)",
    "Команда Wine:": "Wine command:",
    "Папка окружения:": "Prefix folder:",
    "Подготовить окружение": "Prepare prefix",
    "Установить DXVK": "Install DXVK",
    "Запустить установщик клиента…": "Run client installer…",
    "Открыть лог": "Open log",
    "Папка GTA San Andreas": "GTA San Andreas folder",
    "В этой папке нет gta_sa.exe.": "There is no gta_sa.exe in this folder.",
    "{name}… (может занять пару минут)": "{name}… (may take a couple of minutes)",
    "Подготовка окружения": "Preparing prefix",
    "Установка DXVK": "Installing DXVK",
    "winetricks не установлен": "winetricks is not installed",
    "Установщик клиента SA-MP": "SA-MP client installer",
    "Программы Windows (*.exe *.msi)": "Windows programs (*.exe *.msi)",
    "Установщик запущен. Путь к игре в нём: диск Z: → ваша папка GTA ({path})":
        "Installer started. In it, choose drive Z: → your GTA folder ({path})",
    "{name}: ошибка — {err}": "{name}: error — {err}",
    "{name}: готово": "{name}: done",
    "Язык изменится после перезапуска лаунчера. Перезапустить сейчас?":
        "The language will change after restarting the launcher. Restart now?",
    "Добавить сервер": "Add server", "В избранное": "Add to favorites", "Удалить": "Remove",
    "Обновить": "Refresh", "Копировать адрес": "Copy address", "Папка GTA": "GTA folder",
    "Открыть папку игры (для модов)": "Open the game folder (for mods)",
    "Ваш ник в игре": "Your in-game nickname",
    "Например: Ivan_Petrov": "For example: John_Smith",
    "  Играть": "  Play",
    "Поиск по названию, адресу, режиму…": "Search by name, address, mode…",
    "Не пустые": "Not empty", "Не полные": "Not full", "Без пароля": "No password",
    "Поиск серверов:": "Search servers:",
    "Избранное": "Favorites", "Интернет": "Internet",
    "Информация о сервере": "Server info",
    "Адрес:": "Address:", "Игроки:": "Players:", "Пинг:": "Ping:", "Режим:": "Mode:", "Язык:": "Language:",
    "Игрок": "Player", "Счёт": "Score",
    "Укажите папку GTA San Andreas в настройках.": "Set the GTA San Andreas folder in Settings.",
    "Не найден gta_sa.exe в {d}": "gta_sa.exe not found in {d}",
    "  (gta_sa.exe не похож на версию 1.0 US — SA-MP может не запуститься)":
        "  (gta_sa.exe does not look like version 1.0 US — SA-MP may not start)",
    "  · нет {exe} — установите клиент SA-MP в папку игры":
        "  · no {exe} — install the SA-MP client into the game folder",
    "Введите ник — под ним вас увидят на сервере.": "Enter a nickname — other players will see you by it.",
    "Слишком короткий: нужно от 3 до 24 символов.": "Too short: 3 to 24 characters required.",
    "Латиница, цифры и символы _ [ ] . $ = @ ( )": "Latin letters, digits and _ [ ] . $ = @ ( )",
    "  ·  На RP-серверах обычно нужен формат Имя_Фамилия":
        "  ·  RP servers usually require the Firstname_Lastname format",
    "✓ Ник сохранён": "✓ Nickname saved",
    "Выберите сервер в списке ниже": "Select a server in the list below",
    "на <b>{name}</b>": "on <b>{name}</b>",
    "(список недоступен — слишком много игроков)": "(list unavailable — too many players)",
    "Загрузка списка серверов…": "Loading server list…",
    "Не удалось загрузить список: {err}": "Failed to load the list: {err}",
    "Серверов: {n}   ·   {status}": "Servers: {n}   ·   {status}",
    "Адрес сервера (ip:порт):": "Server address (ip:port):",
    "Неверный адрес.": "Invalid address.",
    "{key} добавлен в избранное": "{key} added to favorites",
    "Удалить {key} из избранного?": "Remove {key} from favorites?",
    "Скопировано: {key}": "Copied: {key}",
    "Не удалось запустить игру:\n{err}\n\nЛог: {log}": "Failed to start the game:\n{err}\n\nLog: {log}",
    "Игра запускается…": "Starting the game…",
    "Выберите сервер в списке.": "Select a server in the list.",
    "Укажите папку GTA San Andreas (с gta_sa.exe) в настройках.":
        "Set the GTA San Andreas folder (containing gta_sa.exe) in Settings.",
    "В папке игры нет {exe}.\n\nУстановите клиент SA-MP / SAMP Reborn в папку GTA "
    "(Настройки → «Запустить установщик клиента…») или скопируйте его файлы вручную.":
        "{exe} is missing in the game folder.\n\nInstall the SA-MP / SAMP Reborn client into the GTA folder "
        "(Settings → \"Run client installer…\") or copy its files there manually.",
    "Пароль сервера": "Server password",
    "Отмена": "Cancel",
    "Сервер закрыт паролем:": "This server is password protected:",
    "Первый запуск: подготовка окружения, подождите…": "First launch: preparing the Wine prefix, please wait…",
}

LANG = "ru"


def set_language(cfg):
    global LANG
    lang = cfg.get("language", "auto")
    if lang not in ("ru", "en"):
        lang = "ru" if QLocale.system().name().startswith(("ru", "uk", "be", "kk")) else "en"
    LANG = lang


def T(text, **kw):
    """Перевод строки интерфейса (+ подстановка {имя}, если переданы kw)."""
    if LANG == "en":
        text = EN.get(text, text)
    return text.format(**kw) if kw else text


# ---------------------------------------------------------------- config

def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_FILE)


def split_addr(addr):
    addr = addr.strip()
    for prefix in ("samp://", "omp://"):
        if addr.startswith(prefix):
            addr = addr[len(prefix):]
    addr = addr.rstrip("/")
    if ":" in addr:
        host, port = addr.rsplit(":", 1)
        return host.strip(), int(port)
    return addr, 7777


# ---------------------------------------------------------------- SA-MP query protocol

class _Reader:
    def __init__(self, data):
        self.d, self.i = data, 0

    def take(self, n):
        if self.i + n > len(self.d):
            raise ValueError("short packet")
        v = self.d[self.i:self.i + n]
        self.i += n
        return v

    def u8(self):
        return self.take(1)[0]

    def u16(self):
        return struct.unpack("<H", self.take(2))[0]

    def i32(self):
        return struct.unpack("<i", self.take(4))[0]

    def str8(self):
        return _decode(self.take(self.u8()))

    def str32(self):
        return _decode(self.take(struct.unpack("<I", self.take(4))[0]))


def _decode(b):
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        pass
    # русские названия идут подряд идущими «высокими» байтами (cp1251),
    # одиночные ñ/é — это западная кодировка cp1252
    high_run = any(a >= 0xC0 and c >= 0xC0 for a, c in zip(b, b[1:]))
    return b.decode("cp1251" if high_run else "cp1252", errors="replace")


def samp_query(host, port, opcode, timeout=2.0):
    ip = socket.gethostbyname(host)
    packet = b"SAMP" + socket.inet_aton(ip) + struct.pack("<H", port) + opcode.encode()
    if opcode == "p":
        packet += os.urandom(4)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        t0 = time.monotonic()
        s.sendto(packet, (ip, port))
        while True:
            data, _ = s.recvfrom(65535)
            if data[:4] == b"SAMP" and data[10:11] == opcode.encode():
                return data[11:], int((time.monotonic() - t0) * 1000)


def query_info(host, port):
    data, ping = samp_query(host, port, "i")
    r = _Reader(data)
    return {
        "password": bool(r.u8()),
        "players": r.u16(),
        "max_players": r.u16(),
        "name": r.str32(),
        "mode": r.str32(),
        "language": r.str32(),
        "ping": ping,
    }


def query_players(host, port):
    data, _ = samp_query(host, port, "c")
    r = _Reader(data)
    return [(r.str8(), r.i32()) for _ in range(r.u16())]


# ---------------------------------------------------------------- background work

ICON_NAME = "samp-launcher"
ORIGINAL_ICON = "samp-launcher-original"   # иконка из samp.exe пользователя
XDG_DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
ICON_SIZES = (256, 128, 64, 48, 32, 16)


def exe_icon_image(exe):
    """Достать самую крупную иконку из ресурсов Windows-программы (.exe). QImage или None.

    Логотип не входит в репозиторий: берётся из samp.exe, который уже есть у пользователя.
    """
    try:
        d = Path(exe).read_bytes()
        u16 = lambda o: struct.unpack_from("<H", d, o)[0]   # noqa: E731
        u32 = lambda o: struct.unpack_from("<I", d, o)[0]   # noqa: E731
        pe = u32(0x3C)
        if d[pe:pe + 4] != b"PE\0\0":
            return None
        nsec, opt_size = u16(pe + 6), u16(pe + 20)
        opt = pe + 24
        ddir = opt + (96 if u16(opt) == 0x10B else 112)          # PE32 / PE32+
        rsrc_rva = u32(ddir + 2 * 8)
        secs = [(u32(o + 12), max(u32(o + 8), u32(o + 16)), u32(o + 20))
                for o in (opt + opt_size + i * 40 for i in range(nsec))]

        def off(rva):
            for va, size, raw in secs:
                if va <= rva < va + size:
                    return rva - va + raw
            raise ValueError("rva")
        base = off(rsrc_rva)

        def entries(o):
            n = u16(o + 12) + u16(o + 14)
            return [(u32(o + 16 + i * 8), u32(o + 20 + i * 8)) for i in range(n)]

        def find(o, key):   # подкаталог/данные для числового id (None — первый)
            for name, target in entries(o):
                if key is None or (not name & 0x80000000 and name == key):
                    return target
            return None

        def leaf(target):   # спуститься до данных (первый язык)
            while target & 0x80000000:
                target = entries(base + (target & 0x7FFFFFFF))[0][1]
            e = base + target
            return d[off(u32(e)):off(u32(e)) + u32(e + 4)]

        types = base
        groups = find(types, 14)    # RT_GROUP_ICON
        icons = find(types, 3)      # RT_ICON
        if groups is None or icons is None:
            return None
        grp = leaf(entries(base + (groups & 0x7FFFFFFF))[0][1])
        best = None
        for i in range(struct.unpack_from("<H", grp, 4)[0]):
            w, h, colors, _, planes, bits, size, iid = struct.unpack_from("<BBBBHHIH", grp, 6 + i * 14)
            score = ((w or 256) * (h or 256), bits)
            if best is None or score > best[0]:
                best = (score, (w, h, colors, planes, bits, iid))
        w, h, colors, planes, bits, iid = best[1]
        sub = find(base + (icons & 0x7FFFFFFF), iid)
        if sub is None:
            return None
        img = leaf(sub)
        if not img.startswith(b"\x89PNG"):   # BMP-иконка: обернуть в формат .ico
            img = (struct.pack("<HHH", 0, 1, 1)
                   + struct.pack("<BBBBHHII", w, h, colors, 0, planes, bits, len(img), 22) + img)
        q = QImage.fromData(img)
        return None if q.isNull() else q
    except (OSError, ValueError, struct.error, IndexError, TypeError):
        return None


def _desktop_file():
    """Ярлык лаунчера: пользовательский, а если его нет (установка пакетом) — системный."""
    user = XDG_DATA / "applications" / "samp-launcher.desktop"
    if user.exists():
        return user, user
    for d in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":"):
        f = Path(d) / "applications" / "samp-launcher.desktop"
        if f.exists():
            return f, user     # системный не трогаем — кладём копию в ~/.local (она главнее)
    return None, user


def install_original_icon(gta_dir):
    """Если в папке игры есть samp.exe — поставить его иконку лаунчеру (ярлык, док, окно).

    Делается один раз для каждой версии samp.exe. Возвращает True, если иконка есть.
    """
    exe = Path(gta_dir) / "samp.exe" if gta_dir else None
    icons = XDG_DATA / "icons" / "hicolor"
    marker = DATA_DIR / "icon-source"
    if not exe or not exe.is_file():
        return (icons / "256x256" / "apps" / f"{ORIGINAL_ICON}.png").exists()
    st = exe.stat()
    stamp = f"{exe.resolve()}:{st.st_size}:{int(st.st_mtime)}"
    try:
        if marker.read_text() == stamp and (icons / "256x256/apps" / f"{ORIGINAL_ICON}.png").exists():
            return True
    except OSError:
        pass
    img = exe_icon_image(exe)
    if img is None:
        return False
    for sz in ICON_SIZES:
        dst = icons / f"{sz}x{sz}" / "apps" / f"{ORIGINAL_ICON}.png"
        dst.parent.mkdir(parents=True, exist_ok=True)
        img.scaled(sz, sz, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(str(dst), "PNG")
    src, dst = _desktop_file()
    if src:
        lines = src.read_text(encoding="utf-8").splitlines()
        new = [f"Icon={ORIGINAL_ICON}" if ln.startswith("Icon=") else ln for ln in lines]
        if new != lines or src != dst:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text("\n".join(new) + "\n", encoding="utf-8")
    for cmd in (["gtk-update-icon-cache", "-f", "-t", str(icons)],
                ["update-desktop-database", str(XDG_DATA / "applications")], ["kbuildsycoca6"]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    marker.write_text(stamp)
    return True


def app_icon():
    """Иконка окна: из samp.exe пользователя, если есть, иначе своя из репозитория."""
    for name in (ORIGINAL_ICON, ICON_NAME):
        icon = QIcon()
        for sz in ICON_SIZES:
            f = XDG_DATA / "icons/hicolor" / f"{sz}x{sz}/apps/{name}.png"
            if f.exists():
                icon.addFile(str(f))
        if icon.isNull():
            icon = QIcon.fromTheme(name)
        if not icon.isNull():
            return icon
    return QIcon.fromTheme("applications-games")


class Bridge(QObject):
    info = Signal(str, object)       # key, dict | None
    players = Signal(str, object)    # key, list | None
    internet = Signal(object, str)   # list, error
    task_done = Signal(str, str)     # name, error ("" = ok)


POOL = ThreadPoolExecutor(max_workers=24)


# ---------------------------------------------------------------- game runner (Wine внутри)

class GameRunner:
    def __init__(self, cfg):
        self.cfg = cfg
        self.screen_size = "1920x1080"

    def env(self):
        e = dict(os.environ)
        e["WINEPREFIX"] = self.cfg["prefix"]
        # в лог пишутся только ошибки и предупреждения звука — для диагностики
        # trace+dialog нужен, чтобы заметить окно ошибки R6025 после /q
        e["WINEDEBUG"] = self.cfg.get("wine_debug", "err+all,fixme-all,trace+dialog")
        e["DXVK_LOG_LEVEL"] = "none"
        e["DXVK_CONFIG_FILE"] = str(DATA_DIR / "dxvk.conf")
        if not self.cfg.get("vsync", False):
            e["MESA_VK_WSI_PRESENT_MODE"] = "immediate"  # Vulkan (DXVK) на Mesa/RADV
            e["vblank_mode"] = "0"                       # OpenGL на Mesa
            e["__GL_SYNC_TO_VBLANK"] = "0"               # OpenGL на NVIDIA
        # без окон установки Mono/Gecko — они игре не нужны
        e.setdefault("WINEDLLOVERRIDES", "mscoree,mshtml=")
        return e

    def wine(self):
        w = shutil.which(self.cfg["wine"]) or self.cfg["wine"]
        return w

    def prefix_ready(self):
        return (Path(self.cfg["prefix"]) / "system.reg").exists()

    def _run(self, args, **kw):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"\n=== {time.strftime('%F %T')} {' '.join(map(str, args))}\n")
            log.flush()
            subprocess.run(args, env=self.env(), stdout=log, stderr=subprocess.STDOUT, check=True, **kw)

    def setup_prefix(self):
        Path(self.cfg["prefix"]).mkdir(parents=True, exist_ok=True)
        self._run([self.wine(), "wineboot", "-i"])
        self._run([shutil.which("wineserver") or "wineserver", "-w"])

    def install_dxvk(self):
        if not shutil.which("winetricks"):
            raise RuntimeError(T("winetricks не установлен"))
        if not self.prefix_ready():
            self.setup_prefix()
        self._run(["winetricks", "-q", "dxvk"])

    @staticmethod
    def win_path(p):
        return "Z:" + str(Path(p).resolve()).replace("/", "\\")

    def write_registry(self, nickname):
        """Ник и путь к игре для SA-MP + отключение окна ошибки Wine.

        Без окна ошибки выход через /q просто закрывает игру: SA-MP завершает
        процесс «жёстко», и Wine иначе показывает диалог «программа вызвала ошибку».
        """
        def q(v):
            return v.replace("\\", "\\\\").replace('"', '\\"')
        gta_exe = Path(self.cfg["gta_dir"]) / "gta_sa.exe"
        reg = (
            "Windows Registry Editor Version 5.00\r\n\r\n"
            "[HKEY_CURRENT_USER\\Software\\SAMP]\r\n"
            f'"PlayerName"="{q(nickname)}"\r\n'
            f'"gta_sa_exe"="{q(self.win_path(gta_exe))}"\r\n\r\n'
            "[HKEY_CURRENT_USER\\Software\\Wine\\WineDbg]\r\n"
            '"ShowCrashDialog"=dword:00000000\r\n\r\n'
        )
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        f = DATA_DIR / "launcher.reg"
        f.write_bytes(b"\xff\xfe" + reg.encode("utf-16-le"))
        self._run([self.wine(), "regedit", "/S", self.win_path(f)])

    def launch(self, host, port, nickname, password=""):
        gta_dir = Path(self.cfg["gta_dir"])
        exe = gta_dir / self.cfg["client_exe"]
        fmt = {"host": host, "port": port, "nick": nickname, "password": password}
        args = shlex.split(self.cfg["launch_args"].format(**fmt))
        if password and self.cfg.get("password_args"):
            args += shlex.split(self.cfg["password_args"].format(**fmt))
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        log = open(LOG_FILE, "a", encoding="utf-8")
        log.write(f"\n=== {time.strftime('%F %T')} launch {exe.name} {args}\n")
        log.flush()
        vsync = self.cfg.get("vsync", False)
        (DATA_DIR / "dxvk.conf").write_text(
            "# создаётся лаунчером при каждом запуске\n"
            f"d3d9.presentInterval = {-1 if vsync else 0}\n"
            f"dxgi.syncInterval = {-1 if vsync else 0}\n", encoding="utf-8")
        log_start = LOG_FILE.stat().st_size
        cmd = [self.wine(), str(exe), *args]
        if self.cfg.get("virtual_desktop", False):
            size = self.cfg.get("desktop_size") or self.screen_size
            cmd = [self.wine(), "explorer", f"/desktop=SAMP,{size}", str(exe), *args]
        subprocess.Popen(cmd, cwd=gta_dir, env=self.env(),
                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        log.close()
        if self.cfg.get("kill_error_dialog", True):
            POOL.submit(self.watch_exit_error, log_start)

    def watch_exit_error(self, log_start, grace=20):
        """Следит за логом: если игра (проработав дольше grace секунд) показала окно
        ошибки — это R6025 при выходе через /q. Тогда тихо завершаем все процессы игры.
        Окна в первые секунды не трогаем — там могут быть обычные сообщения модов."""
        wait = subprocess.Popen([shutil.which("wineserver") or "wineserver", "-w"], env=self.env())
        t0 = time.monotonic()
        pos = log_start
        try:
            while wait.poll() is None:
                time.sleep(0.5)
                with open(LOG_FILE, "rb") as f:
                    f.seek(pos)
                    chunk = f.read()
                pos += len(chunk)
                if b"MSGBOX_DlgProc" in chunk and time.monotonic() - t0 > grace:
                    with open(LOG_FILE, "a", encoding="utf-8") as log:
                        log.write(f"=== {time.strftime('%F %T')} окно ошибки после выхода — закрываю игру\n")
                    subprocess.run([shutil.which("wineserver") or "wineserver", "-k"], env=self.env())
                    break
        finally:
            if wait.poll() is None:
                wait.wait(timeout=10)

    def run_exe(self, exe_path):
        """Запустить произвольный .exe (например, установщик клиента) в префиксе."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        log = open(LOG_FILE, "a", encoding="utf-8")
        subprocess.Popen([self.wine(), str(exe_path)], cwd=Path(exe_path).parent, env=self.env(),
                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        log.close()

    def winecfg(self):
        subprocess.Popen([self.wine(), "winecfg"], env=self.env(), start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------- server table

SORT_ROLE = Qt.UserRole + 1
KEY_ROLE = Qt.UserRole
TAG_ROLE = Qt.UserRole + 2

COLS = ["", "Название сервера", "Игроки", "Пинг", "Режим", "Язык"]


class ServerTable(QTableView):
    """Таблица серверов. Сортировка и фильтры работают внутри Qt (без Python-сравнений)."""

    def __init__(self):
        super().__init__()
        self.model_ = QStandardItemModel(0, len(COLS), self)
        self.model_.setHorizontalHeaderLabels([T(c) if c else c for c in COLS])
        # 1-й фильтр: флажки «не пустые / не полные / без пароля» (по скрытым меткам)
        self.tag_proxy = QSortFilterProxyModel(self)
        self.tag_proxy.setSourceModel(self.model_)
        self.tag_proxy.setFilterKeyColumn(0)
        self.tag_proxy.setFilterRole(TAG_ROLE)
        # 2-й фильтр: поиск по тексту + сортировка
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.tag_proxy)
        self.proxy.setFilterKeyColumn(-1)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy.setSortRole(SORT_ROLE)
        self.setModel(self.proxy)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(24)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        h = self.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        for c, w in ((0, 28), (2, 90), (3, 60), (4, 170), (5, 110)):
            self.setColumnWidth(c, w)
        self.setSortingEnabled(True)
        self.sortByColumn(2, Qt.DescendingOrder)
        self.rows = {}  # key -> QStandardItem колонки 0

    def set_servers(self, servers):
        self.model_.removeRows(0, self.model_.rowCount())
        self.rows.clear()
        for s in servers:
            self.add(s)

    def add(self, s):
        key = f"{s['host']}:{s['port']}"
        if key in self.rows:
            return
        items = [QStandardItem() for _ in COLS]
        items[0].setData(key, KEY_ROLE)
        items[1].setData(key, Qt.ToolTipRole)
        items[2].setData(-1, SORT_ROLE)
        items[3].setData(99999, SORT_ROLE)
        for c in (0, 1, 4, 5):
            items[c].setData("", SORT_ROLE)
        items[0].setData("", TAG_ROLE)
        self.model_.appendRow(items)
        self.rows[key] = items[0]
        self.update_info(key, s)

    def _set(self, row, col, text, sort):
        it = self.model_.item(row, col)
        it.setText(text)
        it.setData(sort, SORT_ROLE)

    def update_info(self, key, info):
        it0 = self.rows.get(key)
        if it0 is None:
            return
        r = it0.row()
        if info is None:
            self._set(r, 3, "—", 99999)
            if not self.model_.item(r, 1).text():
                self._set(r, 1, T("(нет ответа) {key}", key=key), key.lower())
            return
        if "password" in info:
            self._set(r, 0, "🔒" if info["password"] else "", "1" if info["password"] else "0")
        name = info.get("name") or self.model_.item(r, 1).text() or key
        self._set(r, 1, name, name.lower())
        if "players" in info:
            self._set(r, 2, f"{info['players']} / {info.get('max_players', '?')}", int(info["players"]))
        if "ping" in info:
            self._set(r, 3, str(info["ping"]), int(info["ping"]))
        if info.get("mode"):
            self._set(r, 4, info["mode"], info["mode"].lower())
        if info.get("language"):
            self._set(r, 5, info["language"], info["language"].lower())
        # скрытые метки для фильтров
        tags = ""
        p, mp = info.get("players"), info.get("max_players")
        if p == 0:
            tags += "E"
        if p is not None and mp and p >= mp:
            tags += "F"
        if info.get("password"):
            tags += "L"
        it0.setData(tags, TAG_ROLE)

    def current_key(self):
        idx = self.currentIndex()
        if not idx.isValid():
            return None
        return self.proxy.index(idx.row(), 0).data(KEY_ROLE)

    def remove_key(self, key):
        it = self.rows.pop(key, None)
        if it is not None:
            self.model_.removeRow(it.row())

    def apply_filter(self, text, hide_empty, hide_full, hide_locked):
        bad = ("E" if hide_empty else "") + ("F" if hide_full else "") + ("L" if hide_locked else "")
        self.tag_proxy.setFilterRegularExpression(QRegularExpression(f"^[^{bad}]*$" if bad else ""))
        self.proxy.setFilterFixedString(text)


# ---------------------------------------------------------------- settings dialog

class SettingsDialog(QDialog):
    def __init__(self, cfg, runner, bridge, parent=None):
        super().__init__(parent)
        self.cfg, self.runner, self.bridge = cfg, runner, bridge
        self.setWindowTitle(T("Настройки"))
        self.setMinimumWidth(620)

        form = QFormLayout()
        self.gta = QLineEdit(cfg["gta_dir"])
        b = QPushButton(T("Обзор…"))
        b.clicked.connect(self.browse_gta)
        row = QHBoxLayout()
        row.addWidget(self.gta)
        row.addWidget(b)
        form.addRow(T("Папка GTA San Andreas:"), row)

        self.exe = QLineEdit(cfg["client_exe"])
        form.addRow(T("Файл клиента SA-MP:"), self.exe)
        self.args = QLineEdit(cfg["launch_args"])
        self.args.setToolTip(T("Подстановки: {host} {port} {nick} {password}"))
        form.addRow(T("Аргументы запуска:"), self.args)
        self.vsync = QCheckBox(T("Вертикальная синхронизация (V-Sync)"))
        self.vsync.setChecked(cfg.get("vsync", False))
        form.addRow(self.vsync)
        self.killerr = QCheckBox(T("Закрывать окно ошибки R6025 при выходе (/q)"))
        self.killerr.setChecked(cfg.get("kill_error_dialog", True))
        form.addRow(self.killerr)
        self.vdesk = QCheckBox(T("Виртуальный рабочий стол Wine (после смены — заново выбрать разрешение в игре)"))
        self.vdesk.setChecked(cfg.get("virtual_desktop", False))
        form.addRow(self.vdesk)
        self.dsize = QLineEdit(cfg.get("desktop_size", ""))
        self.dsize.setPlaceholderText(T("авто ({size})", size=runner.screen_size))
        form.addRow(T("Размер окна игры:"), self.dsize)
        self.lang = QComboBox()
        for code, label in (("auto", T("Авто (как в системе)")), ("ru", "Русский"), ("en", "English")):
            self.lang.addItem(label, code)
        self.lang.setCurrentIndex(max(0, self.lang.findData(cfg.get("language", "auto"))))
        form.insertRow(0, T("Язык интерфейса:"), self.lang)
        self.pargs = QLineEdit(cfg["password_args"])
        form.addRow(T("Аргументы пароля:"), self.pargs)
        self.api = QLineEdit(cfg["api_url"])
        form.addRow(T("Список серверов (API):"), self.api)

        adv = QGroupBox(T("Совместимость (запуск Windows-игры)"))
        af = QFormLayout(adv)
        self.wine = QLineEdit(cfg["wine"])
        af.addRow(T("Команда Wine:"), self.wine)
        self.prefix = QLineEdit(cfg["prefix"])
        af.addRow(T("Папка окружения:"), self.prefix)
        btns = QGridLayout()
        for text, fn in ((T("Подготовить окружение"), self.do_setup),
                         (T("Установить DXVK"), self.do_dxvk),
                         (T("Запустить установщик клиента…"), self.do_installer),
                         ("winecfg", lambda: self._apply() or self.runner.winecfg()),
                         (T("Открыть лог"), lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_FILE))))):
            pb = QPushButton(text)
            pb.clicked.connect(fn)
            n = btns.count()
            btns.addWidget(pb, n // 3, n % 3)  # 3 кнопки в ряд — длинные русские подписи не обрезаются
        af.addRow(btns)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        af.addRow(self.status)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("OK")
        bb.button(QDialogButtonBox.Cancel).setText(T("Отмена"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(adv)
        lay.addWidget(bb)
        self.bridge.task_done.connect(self.on_task_done)

    def browse_gta(self):
        d = QFileDialog.getExistingDirectory(self, T("Папка GTA San Andreas"), self.gta.text() or str(Path.home()))
        if d:
            self.gta.setText(d)
            if not (Path(d) / "gta_sa.exe").exists():
                QMessageBox.warning(self, APP_NAME, T("В этой папке нет gta_sa.exe."))

    def _apply(self):
        self.cfg.update(gta_dir=self.gta.text().strip(), client_exe=self.exe.text().strip(),
                        launch_args=self.args.text(), password_args=self.pargs.text(),
                        virtual_desktop=self.vdesk.isChecked(), desktop_size=self.dsize.text().strip(),
                        vsync=self.vsync.isChecked(), kill_error_dialog=self.killerr.isChecked(),
                        api_url=self.api.text().strip(), wine=self.wine.text().strip(),
                        prefix=self.prefix.text().strip(), language=self.lang.currentData())

    def _bg(self, name, fn):
        self._apply()
        self.status.setText(T("{name}… (может занять пару минут)", name=name))

        def job():
            try:
                fn()
                self.bridge.task_done.emit(name, "")
            except Exception as e:  # noqa: BLE001
                self.bridge.task_done.emit(name, str(e))
        POOL.submit(job)

    def do_setup(self):
        self._bg(T("Подготовка окружения"), self.runner.setup_prefix)

    def do_dxvk(self):
        self._bg(T("Установка DXVK"), self.runner.install_dxvk)

    def do_installer(self):
        self._apply()
        downloads = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or str(Path.home())
        f, _ = QFileDialog.getOpenFileName(self, T("Установщик клиента SA-MP"), downloads,
                                           T("Программы Windows (*.exe *.msi)"))
        if f:
            if not self.runner.prefix_ready():
                self.runner.setup_prefix()
            self.status.setText(T("Установщик запущен. Путь к игре в нём: диск Z: → ваша папка GTA ({path})",
                                  path=self.runner.win_path(self.gta.text() or Path.home())))
            self.runner.run_exe(f)

    def on_task_done(self, name, err):
        self.status.setText(T("{name}: ошибка — {err}", name=name, err=err) if err
                            else T("{name}: готово", name=name))

    def accept(self):
        old_lang = self.cfg.get("language", "auto")
        self._apply()
        save_config(self.cfg)
        super().accept()
        if self.cfg["language"] != old_lang:
            answer = QMessageBox.question(self.parent(), APP_NAME,
                                          T("Язык изменится после перезапуска лаунчера. Перезапустить сейчас?"))
            if answer == QMessageBox.Yes:
                os.execv(sys.executable, [sys.executable, *sys.argv])


# ---------------------------------------------------------------- main window

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        set_language(self.cfg)
        self.runner = GameRunner(self.cfg)
        scr = QGuiApplication.primaryScreen()
        if scr is not None:
            g, dpr = scr.geometry(), scr.devicePixelRatio()
            self.runner.screen_size = f"{round(g.width() * dpr)}x{round(g.height() * dpr)}"
        self.bridge = Bridge()
        self.info_cache = {}
        self.internet_list = []

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        install_original_icon(self.cfg.get("gta_dir"))
        self.setWindowIcon(app_icon())
        self.resize(1000, 680)

        # toolbar
        tb = QToolBar()
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        def act(icon, text, fn, tip=None):
            a = QAction(QIcon.fromTheme(icon), text, self)
            a.triggered.connect(fn)
            if tip:
                a.setToolTip(tip)
            tb.addAction(a)
            return a

        act("list-add", T("Добавить сервер"), self.add_server)
        act("bookmark-new", T("В избранное"), self.to_favorites)
        act("list-remove", T("Удалить"), self.remove_favorite)
        act("view-refresh", T("Обновить"), self.refresh)
        act("edit-copy", T("Копировать адрес"), self.copy_addr)
        tb.addSeparator()
        act("folder-open", T("Папка GTA"), self.open_gta_dir, T("Открыть папку игры (для модов)"))
        act("configure", T("Настройки"), self.open_settings)

        # ---- панель «ник + Играть» — самое заметное место окна
        panel = QFrame()
        panel.setObjectName("nickPanel")
        panel.setStyleSheet(
            "QFrame#nickPanel { background: palette(alternate-base); border: 1px solid palette(mid);"
            " border-radius: 10px; }"
            "QFrame#nickPanel QLabel { background: transparent; border: none; }")
        title = QLabel(T("Ваш ник в игре"))
        title.setStyleSheet("font-size: 15pt; font-weight: 600;")
        self.nick = QLineEdit(self.cfg["nickname"])
        self.nick.setMaxLength(24)
        self.nick.setMinimumWidth(320)
        self.nick.setMinimumHeight(42)
        self.nick.setPlaceholderText(T("Например: Ivan_Petrov"))
        self.nick.setClearButtonEnabled(True)
        self.nick.setValidator(QRegularExpressionValidator(QRegularExpression(NICK_CHARS + "{0,24}"), self))
        self.nick_style = "font-size: 14pt; padding: 4px 10px; border-radius: 6px; border: 2px solid {};"
        self.nick.textChanged.connect(self.on_nick_changed)
        self.nick.returnPressed.connect(self.connect_selected)
        self.nick_hint = QLabel()
        self.nick_hint.setWordWrap(True)
        nick_col = QVBoxLayout()
        nick_col.setSpacing(6)
        nick_col.addWidget(title)
        nick_col.addWidget(self.nick)
        nick_col.addWidget(self.nick_hint)

        self.play_btn = QPushButton(QIcon.fromTheme("media-playback-start"), T("  Играть"))
        self.play_btn.setMinimumSize(200, 64)
        self.play_btn.setStyleSheet(
            "QPushButton { font-size: 16pt; font-weight: 600; color: palette(highlighted-text);"
            " background: palette(highlight); border: none; border-radius: 8px; padding: 6px 18px; }"
            "QPushButton:hover { background: palette(link); }"
            "QPushButton:disabled { background: palette(mid); }")
        self.play_btn.clicked.connect(self.connect_selected)
        self.server_lbl = QLabel()
        self.server_lbl.setAlignment(Qt.AlignCenter)
        self.server_lbl.setWordWrap(True)
        self.server_lbl.setMaximumWidth(260)
        play_col = QVBoxLayout()
        play_col.addWidget(self.play_btn)
        play_col.addWidget(self.server_lbl)

        pl = QHBoxLayout(panel)
        pl.setContentsMargins(16, 12, 16, 12)
        pl.addLayout(nick_col, 1)
        pl.addSpacing(16)
        pl.addLayout(play_col)
        self.nick_save_timer = QTimer(self, singleShot=True, interval=600, timeout=self.save_nick)

        # filter row
        self.search = QLineEdit()
        self.search.setPlaceholderText(T("Поиск по названию, адресу, режиму…"))
        self.search.setClearButtonEnabled(True)
        self.f_empty = QCheckBox(T("Не пустые"))
        self.f_full = QCheckBox(T("Не полные"))
        self.f_lock = QCheckBox(T("Без пароля"))
        for w in (self.f_empty, self.f_full, self.f_lock):
            w.toggled.connect(self.apply_filter)
        self.search.textChanged.connect(lambda: self.filter_timer.start(200))
        self.filter_timer = QTimer(self, singleShot=True, timeout=self.apply_filter)
        frow = QHBoxLayout()
        frow.addWidget(QLabel(T("Поиск серверов:")))
        frow.addWidget(self.search, 1)
        for w in (self.f_empty, self.f_full, self.f_lock):
            frow.addWidget(w)

        # tables
        self.fav = ServerTable()
        self.net = ServerTable()
        self.tabs = QTabWidget()
        self.tabs.addTab(self.fav, T("Избранное"))
        self.tabs.addTab(self.net, T("Интернет"))
        self.tabs.currentChanged.connect(self.on_tab)
        for t in (self.fav, self.net):
            t.selectionModel().currentRowChanged.connect(lambda *_: self.on_select())
            t.doubleClicked.connect(lambda *_: self.connect_selected())

        # info panel
        self.lbl = {k: QLabel("—") for k in ("addr", "players", "ping", "mode", "lang")}
        for l in self.lbl.values():
            l.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_box = QGroupBox(T("Информация о сервере"))
        il = QFormLayout(info_box)
        for k, t in (("addr", "Адрес:"), ("players", "Игроки:"), ("ping", "Пинг:"),
                     ("mode", "Режим:"), ("lang", "Язык:")):
            il.addRow(T(t), self.lbl[k])
        self.plist = QTableWidget(0, 2)
        self.plist.setHorizontalHeaderLabels([T("Игрок"), T("Счёт")])
        self.plist.verticalHeader().hide()
        self.plist.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.plist.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        bottom = QSplitter()
        bottom.addWidget(info_box)
        bottom.addWidget(self.plist)
        bottom.setSizes([600, 400])

        split = QSplitter(Qt.Vertical)
        split.addWidget(self.tabs)
        split.addWidget(bottom)
        split.setSizes([460, 200])

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.addWidget(panel)
        lay.addLayout(frow)
        lay.addWidget(split)
        self.setCentralWidget(central)

        self.bridge.info.connect(self.on_info)
        self.bridge.players.connect(self.on_players)
        self.bridge.internet.connect(self.on_internet)
        self.bridge.task_done.connect(self.on_task_done)

        self.load_favorites()
        self.statusBar().showMessage(self.gta_status())
        self.on_nick_changed(self.nick.text(), save=False)
        self.update_server_label()
        if not self.cfg["nickname"]:
            self.nick.setFocus()
            self.nick.selectAll()

        self.ping_timer = QTimer(self, interval=5000, timeout=self.ping_selected)
        self.ping_timer.start()

    # ---- helpers
    def table(self):
        return self.tabs.currentWidget()

    def gta_status(self):
        d = self.cfg["gta_dir"]
        if not d:
            return T("Укажите папку GTA San Andreas в настройках.")
        exe = Path(d) / "gta_sa.exe"
        if not exe.exists():
            return T("Не найден gta_sa.exe в {d}", d=d)
        msg = f"GTA: {d}"
        if exe.stat().st_size != GTA_SA_10US_SIZE:
            msg += T("  (gta_sa.exe не похож на версию 1.0 US — SA-MP может не запуститься)")
        if not (Path(d) / self.cfg["client_exe"]).exists():
            msg += T("  · нет {exe} — установите клиент SA-MP в папку игры", exe=self.cfg["client_exe"])
        return msg

    def nick_problem(self, nick):
        if not nick:
            return T("Введите ник — под ним вас увидят на сервере.")
        if len(nick) < 3:
            return T("Слишком короткий: нужно от 3 до 24 символов.")
        return ""

    def on_nick_changed(self, text, save=True):
        problem = self.nick_problem(text.strip())
        if problem:
            self.nick.setStyleSheet(self.nick_style.format("#da4453"))
            self.nick_hint.setText(f"<span style='color:#da4453'>⚠ {problem}</span>  "
                                   + T("Латиница, цифры и символы _ [ ] . $ = @ ( )"))
        else:
            self.nick.setStyleSheet(self.nick_style.format("palette(highlight)"))
            rp = "" if "_" in text else T("  ·  На RP-серверах обычно нужен формат Имя_Фамилия")
            self.nick_hint.setText(f"<span style='color:#27ae60'>{T('✓ Ник сохранён')}</span>"
                                   f"<span style='color:palette(placeholder-text)'>{rp}</span>")
            if save:
                self.nick_save_timer.start()

    def save_nick(self):
        nick = self.nick.text().strip()
        if not self.nick_problem(nick):
            self.cfg["nickname"] = nick
            save_config(self.cfg)

    def update_server_label(self):
        key = self.table().current_key()
        if not key:
            self.server_lbl.setText(T("Выберите сервер в списке ниже"))
            return
        name = self.info_cache.get(key, {}).get("name") or key
        if len(name) > 40:
            name = name[:38] + "…"
        self.server_lbl.setText(T("на <b>{name}</b>", name=name))

    def fav_entry(self, key):
        for f in self.cfg["favorites"]:
            if f"{f['host']}:{f['port']}" == key:
                return f
        return None

    # ---- queries
    def query_async(self, key, players=False):
        if not key:
            return
        host, port = split_addr(key)

        def job():
            try:
                self.bridge.info.emit(key, query_info(host, port))
            except Exception:  # noqa: BLE001
                self.bridge.info.emit(key, None)
                return
            if players:
                try:
                    self.bridge.players.emit(key, query_players(host, port))
                except Exception:  # noqa: BLE001
                    self.bridge.players.emit(key, None)
        POOL.submit(job)

    def on_info(self, key, info):
        if info is not None:
            self.info_cache[key] = info
            f = self.fav_entry(key)
            if f is not None and f.get("name") != info["name"]:
                f["name"] = info["name"]
                save_config(self.cfg)
        for t in (self.fav, self.net):
            t.update_info(key, info)
        if key == self.table().current_key():
            self.show_info(key)

    def on_players(self, key, players):
        if key != self.table().current_key():
            return
        self.plist.setRowCount(0)
        if players is None:
            self.plist.setRowCount(1)
            self.plist.setItem(0, 0, QTableWidgetItem(T("(список недоступен — слишком много игроков)")))
            return
        self.plist.setRowCount(len(players))
        for i, (n, s) in enumerate(players):
            self.plist.setItem(i, 0, QTableWidgetItem(n))
            self.plist.setItem(i, 1, QTableWidgetItem(str(s)))

    def show_info(self, key):
        info = self.info_cache.get(key, {})
        self.lbl["addr"].setText(key)
        if "players" in info:
            self.lbl["players"].setText(f"{info['players']} / {info.get('max_players', '?')}")
        else:
            self.lbl["players"].setText("—")
        self.lbl["ping"].setText(str(info.get("ping", "—")))
        self.lbl["mode"].setText(info.get("mode") or "—")
        self.lbl["lang"].setText(info.get("language") or "—")

    def on_select(self):
        self.update_server_label()
        key = self.table().current_key()
        if not key:
            return
        self.show_info(key)
        self.plist.setRowCount(0)
        self.query_async(key, players=True)

    def ping_selected(self):
        if not self.isActiveWindow():
            return
        key = self.table().current_key()
        if key:
            self.query_async(key)

    # ---- lists
    def load_favorites(self):
        self.fav.set_servers([dict(f, name=f.get("name", "")) for f in self.cfg["favorites"]])
        for f in self.cfg["favorites"]:
            self.query_async(f"{f['host']}:{f['port']}")

    def on_tab(self, idx):
        if idx == 1 and not self.internet_list:
            self.load_internet()
        self.apply_filter()
        self.update_server_label()

    def load_internet(self):
        self.statusBar().showMessage(T("Загрузка списка серверов…"))
        url = self.cfg["api_url"]

        def job():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "samp-launcher-linux"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = json.load(r)
                out = []
                for s in data:
                    host, port = split_addr(s.get("ip") or s.get("address") or "")
                    out.append({"host": host, "port": port, "name": s.get("hn", ""),
                                "players": s.get("pc", 0), "max_players": s.get("pm", 0),
                                "mode": s.get("gm", ""), "language": s.get("la", ""),
                                "password": bool(s.get("pa", False))})
                self.bridge.internet.emit(out, "")
            except Exception as e:  # noqa: BLE001
                self.bridge.internet.emit([], str(e))
        POOL.submit(job)

    def on_internet(self, servers, err):
        if err:
            self.statusBar().showMessage(T("Не удалось загрузить список: {err}", err=err))
            return
        servers.sort(key=lambda s: -s["players"])
        self.internet_list = servers
        for s in servers:
            self.info_cache.setdefault(f"{s['host']}:{s['port']}", {k: s[k] for k in
                                       ("players", "max_players", "name", "mode", "language", "password")})
        self.net.set_servers(servers)
        self.apply_filter()
        self.statusBar().showMessage(T("Серверов: {n}   ·   {status}", n=len(servers), status=self.gta_status()))

    def apply_filter(self):
        for t in (self.fav, self.net):
            t.apply_filter(self.search.text(), self.f_empty.isChecked(),
                           self.f_full.isChecked(), self.f_lock.isChecked())

    def refresh(self):
        if self.tabs.currentIndex() == 1:
            self.load_internet()
        else:
            self.load_favorites()

    # ---- actions
    def add_server(self):
        text, ok = QInputDialog.getText(self, T("Добавить сервер"), T("Адрес сервера (ip:порт):"))
        if not ok or not text.strip():
            return
        try:
            host, port = split_addr(text)
        except ValueError:
            QMessageBox.warning(self, APP_NAME, T("Неверный адрес."))
            return
        self._add_fav(host, port, "")
        self.tabs.setCurrentIndex(0)

    def _add_fav(self, host, port, name):
        key = f"{host}:{port}"
        if self.fav_entry(key):
            return
        self.cfg["favorites"].append({"host": host, "port": port, "name": name, "password": ""})
        save_config(self.cfg)
        self.fav.add({"host": host, "port": port, "name": name, **self.info_cache.get(key, {})})
        self.query_async(key)

    def to_favorites(self):
        key = self.table().current_key()
        if key:
            host, port = split_addr(key)
            self._add_fav(host, port, self.info_cache.get(key, {}).get("name", ""))
            self.statusBar().showMessage(T("{key} добавлен в избранное", key=key), 3000)

    def remove_favorite(self):
        if self.tabs.currentIndex() != 0:
            return
        key = self.fav.current_key()
        if key and QMessageBox.question(self, APP_NAME, T("Удалить {key} из избранного?", key=key)) == QMessageBox.Yes:
            self.cfg["favorites"] = [f for f in self.cfg["favorites"] if f"{f['host']}:{f['port']}" != key]
            save_config(self.cfg)
            self.fav.remove_key(key)

    def copy_addr(self):
        key = self.table().current_key()
        if key:
            QGuiApplication.clipboard().setText(key)
            self.statusBar().showMessage(T("Скопировано: {key}", key=key), 3000)

    def open_gta_dir(self):
        if self.cfg["gta_dir"] and Path(self.cfg["gta_dir"]).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.cfg["gta_dir"]))
        else:
            self.open_settings()

    def open_settings(self):
        SettingsDialog(self.cfg, self.runner, self.bridge, self).exec()
        if install_original_icon(self.cfg.get("gta_dir")):   # папку GTA могли поменять
            self.setWindowIcon(app_icon())
        self.statusBar().showMessage(self.gta_status())

    def on_task_done(self, name, err):
        if name == "launch":
            if err:
                QMessageBox.critical(self, APP_NAME, T("Не удалось запустить игру:\n{err}\n\nЛог: {log}", err=err, log=LOG_FILE))
            else:
                self.statusBar().showMessage(T("Игра запускается…"), 8000)

    def connect_selected(self):
        key = self.table().current_key()
        if not key:
            QMessageBox.information(self, APP_NAME, T("Выберите сервер в списке."))
            return
        problem = self.nick_problem(self.nick.text().strip())
        if problem:
            QMessageBox.warning(self, APP_NAME, problem)
            self.nick.setFocus()
            return
        self.save_nick()
        gta = Path(self.cfg["gta_dir"]) if self.cfg["gta_dir"] else None
        if not gta or not (gta / "gta_sa.exe").exists():
            QMessageBox.warning(self, APP_NAME, T("Укажите папку GTA San Andreas (с gta_sa.exe) в настройках."))
            self.open_settings()
            return
        if not (gta / self.cfg["client_exe"]).exists():
            QMessageBox.warning(self, APP_NAME, T(
                "В папке игры нет {exe}.\n\nУстановите клиент SA-MP / SAMP Reborn в папку GTA "
                "(Настройки → «Запустить установщик клиента…») или скопируйте его файлы вручную.",
                exe=self.cfg["client_exe"]))
            return
        host, port = split_addr(key)
        fav = self.fav_entry(key) or {}
        password = fav.get("password", "")
        if self.info_cache.get(key, {}).get("password") and not password:
            password, ok = QInputDialog.getText(self, T("Пароль сервера"), T("Сервер закрыт паролем:"), QLineEdit.Password)
            if not ok:
                return
        nick = self.cfg["nickname"]
        first = not self.runner.prefix_ready()
        if first:
            self.statusBar().showMessage(T("Первый запуск: подготовка окружения, подождите…"))

        def job():
            try:
                if first:
                    self.runner.setup_prefix()
                self.runner.write_registry(nick)
                self.runner.launch(host, port, nick, password)
                self.bridge.task_done.emit("launch", "")
            except Exception as e:  # noqa: BLE001
                self.bridge.task_done.emit("launch", str(e))
        POOL.submit(job)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("samp-launcher")
    app.setApplicationDisplayName(APP_NAME)
    app.setDesktopFileName("samp-launcher")
    w = MainWindow()
    w.show()
    # samp://ip:port из браузера/ярлыка → сразу добавить в избранное
    for a in sys.argv[1:]:
        if a.startswith(("samp://", "omp://")):
            host, port = split_addr(a)
            w._add_fav(host, port, "")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
