import customtkinter as ctk
from tkinter import messagebox
import subprocess
import os
import csv
import ctypes
import sys
import threading
import urllib.request
import zipfile
import tempfile

# ==========================================
# GITHUB DEPENDENCY URL (STATIC ASSET)
# ==========================================
DEPENDENCY_URL = "https://github.com/dmanique/manik3-virtual-dj/releases/download/dependencies-v1/MANIK3_Dependencies.zip"


# ==========================================
# ADMINISTRATOR PRIVILEGE CHECK
# ==========================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

# ==========================================
# DESIGN CONFIGURATION
# ==========================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

COLOR_LINE1 = "#1DB954"  # Vibrant Green
COLOR_LINE2 = "#00D1FF"  # Vibrant Cyan
COLOR_MUTE = "#E01A4F"  # Alert Red
COLOR_BG_APP = "#121212"  # Deep Background
COLOR_BG_FRAME = "#1E1E1E"  # Elevated Card Background
COLOR_BTN_LAUNCH = "#2A2A2A"

NO_WINDOW = 0x08000000

# ==========================================
# PATH CONFIGURATION
# ==========================================
if getattr(sys, 'frozen', False):
    CURRENT_PATH = os.path.dirname(sys.executable)
else:
    CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

SVV_PATH = os.path.join(CURRENT_PATH, "SoundVolumeView.exe")
APPS_PATH = os.path.join(CURRENT_PATH, "apps")

APPS_INFO = {
    "chrome1": {"path": os.path.join(APPS_PATH, "Chrome1", "App", "Chrome-bin", "chrome1.exe")},
    "chrome2": {"path": os.path.join(APPS_PATH, "Chrome2", "App", "Chrome-bin", "chrome2.exe")},
    "vlc": {"path": os.path.join(APPS_PATH, "VLC", "VLCPortable.exe")}
}

APPS_CH3 = ["vlc.exe", "vlcportable.exe", "spotify.exe", "wmplayer.exe"]
APPS_CH4 = ["pikaraoke.exe", "msedge.exe", "firefox.exe"]

update_funcs = {}


# ==========================================
# AUTO-SETUP WIZARD
# ==========================================
def run_auto_setup():
    setup_win = ctk.CTkToplevel(janela)
    setup_win.title("⚙️ Workspace Setup")
    setup_win.geometry("450x220")
    setup_win.attributes("-topmost", True)
    setup_win.protocol("WM_DELETE_WINDOW", lambda: None)

    ctk.CTkLabel(setup_win, text="INITIALIZING WORKSPACE", font=("Impact", 22), text_color="#FFFFFF").pack(pady=(20, 5))
    lbl_status = ctk.CTkLabel(setup_win, text="Downloading Portable Apps (Chrome, VLC)...", font=("Segoe UI", 12))
    lbl_status.pack(pady=5)

    progress = ctk.CTkProgressBar(setup_win, width=350, fg_color="#333333", progress_color=COLOR_LINE1)
    progress.pack(pady=10);
    progress.set(0)

    def download_thread():
        temp_zip = os.path.join(tempfile.gettempdir(), "manik3_deps.zip")
        try:
            req = urllib.request.Request(DEPENDENCY_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(temp_zip, 'wb') as out_file:
                total_size = int(response.info().get('Content-Length', -1))
                downloaded = 0
                while True:
                    buffer = response.read(8192)
                    if not buffer: break
                    downloaded += len(buffer)
                    out_file.write(buffer)
                    if total_size > 0: progress.set(downloaded / total_size)

            lbl_status.configure(text="Extracting Files...")
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(CURRENT_PATH)
            os.remove(temp_zip)

            lbl_status.configure(text="Setup Complete!", text_color=COLOR_LINE1)
            janela.after(1000, update_lists);
            janela.after(1500, setup_win.destroy)
        except Exception as e:
            lbl_status.configure(text=f"Error: {e}", text_color=COLOR_MUTE)

    threading.Thread(target=download_thread, daemon=True).start()


# ==========================================
# CORE LOGIC: LAUNCH, PROCESS & AUDIO
# ==========================================
def launch_program(key, args=""):
    info = APPS_INFO.get(key)
    if not info: return
    if os.path.exists(info["path"]):
        try:
            app_dir = os.path.dirname(info["path"])
            if "chrome" in key:
                data_dir = os.path.abspath(os.path.join(app_dir, "..", "..", "Data", "profile"))
                args += f' --user-data-dir="{data_dir}" --no-first-run --no-default-browser-check "https://www.youtube.com"'
            subprocess.Popen(f'"{info["path"]}" {args}', shell=True, cwd=app_dir, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            janela.after(3000, update_lists)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start {key}: {e}")
    else:
        messagebox.showerror("File Missing", f"Could not find:\n{info['path']}")


def get_raw_processes():
    try:
        result = subprocess.run("tasklist /V /FO CSV /NH", shell=True, capture_output=True, text=True, errors='ignore',
                                creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
        return {line.split('","')[0].strip('"').lower() for line in result.stdout.splitlines() if line.strip()}
    except:
        return set()


def get_audio_devices():
    devices = set()
    temp_file = os.path.join(tempfile.gettempdir(), "manik3_audio.csv")
    if not os.path.exists(SVV_PATH): return ["⚠️ ERROR: SVV Missing!"]
    try:
        subprocess.run([SVV_PATH, "/scomma", temp_file], shell=False, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL)
        for enc in ['utf-16', 'utf-8-sig', 'utf-8', 'mbcs', 'latin-1']:
            try:
                with open(temp_file, "r", encoding=enc) as f:
                    for row in csv.reader(f):
                        if len(row) >= 3:
                            r_low = [str(i).lower() for i in row]
                            if ("device" in r_low or "dispositivo" in r_low) and (
                                    "render" in r_low or "playback" in r_low or "reprodução" in r_low or "saída" in r_low):
                                devices.add(row[0])
                break
            except:
                continue
    except:
        pass

    if os.path.exists(temp_file):
        try:
            os.remove(temp_file)
        except:
            pass
    return sorted(list(devices)) if devices else ["No devices found..."]


def process_routing(app_name, destination, card_a, card_b):
    if not app_name or "Select" in app_name or "None" in app_name: return True
    clean_app = app_name.split(" ")[0].strip().lower()
    try:
        if destination == "MUTE":
            subprocess.run([SVV_PATH, "/Mute", clean_app], shell=False, creationflags=NO_WINDOW,
                           stdin=subprocess.DEVNULL)
        else:
            target_card = card_a if destination == "LINE 1" else card_b
            if not target_card or "Select" in target_card: return False
            subprocess.run([SVV_PATH, "/SetAppDefault", target_card, "all", clean_app], shell=False,
                           creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
            subprocess.run([SVV_PATH, "/Unmute", clean_app], shell=False, creationflags=NO_WINDOW,
                           stdin=subprocess.DEVNULL)
        return True
    except:
        return False


def mute_other_apps():
    """Mutes all applications EXCEPT the ones currently selected in the matrix."""
    protected = ["chrome1.exe", "chrome2.exe"]
    app3 = combo_app3.get().split(" ")[0].strip().lower()
    app4 = combo_app4.get().split(" ")[0].strip().lower()
    if "select" not in app3 and "none" not in app3: protected.append(app3)
    if "select" not in app4 and "none" not in app4: protected.append(app4)

    temp_file = os.path.join(tempfile.gettempdir(), "manik3_apps.csv")
    try:
        subprocess.run([SVV_PATH, "/scomma", temp_file], shell=False, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL)
        apps_to_mute = set()
        for enc in ['utf-16', 'utf-8-sig', 'utf-8', 'mbcs', 'latin-1']:
            try:
                with open(temp_file, "r", encoding=enc) as f:
                    for row in csv.reader(f):
                        if len(row) >= 1:
                            name = str(row[0]).strip().lower()
                            # Only target .exe files to avoid muting the Master Hardware Volumes
                            if name.endswith(".exe") and name not in protected:
                                apps_to_mute.add(name)
                break
            except:
                continue

        # Mute all unprotected background apps
        for app in apps_to_mute:
            subprocess.run([SVV_PATH, "/Mute", app], shell=False, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
    except:
        pass

    if os.path.exists(temp_file):
        try:
            os.remove(temp_file)
        except:
            pass


# ==========================================
# EXCLUSIVE AUTO-ROUTING ENGINE
# ==========================================
def handle_routing_request(ch_id, requested_state):
    card_a = var_line1.get()
    card_b = var_line2.get()

    if requested_state != "MUTE" and ("Select" in card_a or "Select" in card_b):
        messagebox.showwarning("Setup Required", "Please map LINE 1 and LINE 2 in '⚙️ SETUP' first.")
        if ch_id in update_funcs: update_funcs[ch_id]("MUTE", trigger=False)
        return

    state_vars = {1: state_ch1, 2: state_ch2, 3: state_ch3, 4: state_ch4}
    apps = {1: "chrome1.exe", 2: "chrome2.exe", 3: combo_app3.get(), 4: combo_app4.get()}

    # Exclusive Filtering
    if requested_state in ["LINE 1", "LINE 2"]:
        for other_id, s_var in state_vars.items():
            if other_id != ch_id and s_var.get() == requested_state:
                s_var.set("MUTE")
                if other_id in update_funcs: update_funcs[other_id]("MUTE", trigger=False)
                process_routing(apps[other_id], "MUTE", card_a, card_b)

    state_vars[ch_id].set(requested_state)
    if ch_id in update_funcs: update_funcs[ch_id](requested_state, trigger=False)
    process_routing(apps[ch_id], requested_state, card_a, card_b)

    update_live_displays()


def on_combobox_change(ch_id, new_val):
    state = state_ch3.get() if ch_id == 3 else state_ch4.get()
    if state != "MUTE":
        handle_routing_request(ch_id, state)
    else:
        update_live_displays()


def update_live_displays():
    l1_apps, l2_apps = [], []
    st1, st2, st3, st4 = state_ch1.get(), state_ch2.get(), state_ch3.get(), state_ch4.get()

    if st1 == "LINE 1":
        l1_apps.append("CH 1: YouTube 1")
    elif st1 == "LINE 2":
        l2_apps.append("CH 1: YouTube 1")

    if st2 == "LINE 1":
        l1_apps.append("CH 2: YouTube 2")
    elif st2 == "LINE 2":
        l2_apps.append("CH 2: YouTube 2")

    app3 = combo_app3.get().replace(".exe", "")
    if "Select" not in app3 and app3 != "None Found":
        if st3 == "LINE 1":
            l1_apps.append(f"CH 3: {app3}")
        elif st3 == "LINE 2":
            l2_apps.append(f"CH 3: {app3}")

    app4 = combo_app4.get().replace(".exe", "")
    if "Select" not in app4 and app4 != "None Found":
        if st4 == "LINE 1":
            l1_apps.append(f"CH 4: {app4}")
        elif st4 == "LINE 2":
            l2_apps.append(f"CH 4: {app4}")

    lbl_display_line1.configure(text="\n".join(l1_apps) if l1_apps else "--- SILENCE ---")
    lbl_display_line2.configure(text="\n".join(l2_apps) if l2_apps else "--- SILENCE ---")


def update_lists():
    p = get_raw_processes()
    for c, l in [(combo_app3, APPS_CH3), (combo_app4, APPS_CH4)]:
        current_val = c.get()
        vals = [x for x in p if x in l]
        c.configure(values=vals if vals else ["None Found"])

        if current_val not in vals and current_val not in ["Select App...", "None Found"]:
            c.set(vals[0] if vals else "Select App...")
        elif current_val in ["Select App...", "None Found"]:
            c.set(vals[0] if vals else "Select App...")


def auto_update_lists():
    update_lists()
    janela.after(5000, auto_update_lists)


# ==========================================
# ASYNCHRONOUS SETUP WINDOW
# ==========================================
janela_config = None


def open_settings():
    global janela_config
    if janela_config is None or not janela_config.winfo_exists():
        janela_config = ctk.CTkToplevel(janela)
        janela_config.title("⚙️ Hardware Setup")
        janela_config.geometry("450x260")
        janela_config.resizable(False, False)
        janela_config.configure(fg_color="#1A1A1A")
        janela_config.attributes("-topmost", True)

        ctk.CTkLabel(janela_config, text="PHYSICAL ROUTING", font=("Impact", 24), text_color="#FFFFFF").pack(
            pady=(15, 10))

        ctk.CTkLabel(janela_config, text="Mixer LINE 1 (ex: Speaker):", font=("Segoe UI", 12, "bold"),
                     text_color=COLOR_LINE1).pack(anchor="w", padx=20)
        cb1 = ctk.CTkComboBox(janela_config, variable=var_line1, values=["Loading devices..."], width=410, height=30)
        cb1.pack(pady=(0, 10), padx=20)

        ctk.CTkLabel(janela_config, text="Mixer LINE 2 (ex: USB Speaker):", font=("Segoe UI", 12, "bold"),
                     text_color=COLOR_LINE2).pack(anchor="w", padx=20)
        cb2 = ctk.CTkComboBox(janela_config, variable=var_line2, values=["Loading devices..."], width=410, height=30)
        cb2.pack(pady=(0, 15), padx=20)

        def save_and_close():
            v1 = var_line1.get()
            v2 = var_line2.get()
            # If successfully configured, turn the main SETUP button Green and execute App Mute Lockdown
            if "Select" not in v1 and "Loading" not in v1 and "Select" not in v2 and "Loading" not in v2:
                btn_setup.configure(fg_color=COLOR_LINE1)
                threading.Thread(target=mute_other_apps, daemon=True).start()
            janela_config.destroy()

        ctk.CTkButton(janela_config, text="Save & Close", font=("Segoe UI", 12, "bold"), fg_color="#333333",
                      hover_color="#555555", command=save_and_close).pack(pady=5)

        def fetch_devices():
            l_disp = get_audio_devices()
            cb1.configure(values=l_disp)
            cb2.configure(values=l_disp)
            if l_disp and var_line1.get() == "Select sound card...": var_line1.set(l_disp[0])
            if l_disp and var_line2.get() == "Select sound card...": var_line2.set(
                l_disp[0] if len(l_disp) == 1 else l_disp[1])

        janela_config.after(100, fetch_devices)
    else:
        janela_config.focus()


# ==========================================
# GUI BUILDER (FUSED GRID SYSTEM WITH CONTROL ZONES)
# ==========================================
def create_routing_block(parent, var_state, default, bid):
    # The distinct visual "Control Zone" panel requested by user
    frame = ctk.CTkFrame(parent, fg_color="#121212", corner_radius=8, border_width=1, border_color="#2A2A2A")
    btn_style = {"height": 32, "font": ("Segoe UI", 12, "bold")}

    def update_colors(s, trigger=True):
        var_state.set(s)
        for b, st in [(b1, "LINE 1"), (bm, "MUTE"), (b2, "LINE 2")]:
            active = (s == st)
            b.configure(
                fg_color=COLOR_LINE1 if active and st == "LINE 1" else COLOR_LINE2 if active and st == "LINE 2" else COLOR_MUTE if active and st == "MUTE" else "#333",
                text_color="#000" if active and st != "MUTE" else "#FFF")
        if trigger:
            handle_routing_request(bid, s)

    # Completely Fused Buttons with Explicit Widths
    b1 = ctk.CTkButton(frame, text="LINE 1", width=70, corner_radius=6, command=lambda: update_colors("LINE 1"),
                       **btn_style)
    bm = ctk.CTkButton(frame, text="MUTE", width=60, corner_radius=0, command=lambda: update_colors("MUTE"),
                       **btn_style)
    b2 = ctk.CTkButton(frame, text="LINE 2", width=70, corner_radius=6, command=lambda: update_colors("LINE 2"),
                       **btn_style)

    # Internal padding to make the dark box frame visible around the buttons
    b1.pack(side="left", padx=(4, 0), pady=4)
    bm.pack(side="left", padx=0, pady=4)
    b2.pack(side="left", padx=(0, 4), pady=4)

    update_funcs[bid] = update_colors
    update_colors(default, trigger=False)
    return frame


# Main Window
janela = ctk.CTk()
janela.title("MANIK3 VIRTUAL DJ")
janela.geometry("400x620")  # Adjusted height to fit flawlessly
janela.resizable(False, False)
janela.configure(fg_color=COLOR_BG_APP)

var_line1, var_line2 = ctk.StringVar(value="Select sound card..."), ctk.StringVar(value="Select sound card...")
state_ch1, state_ch2, state_ch3, state_ch4 = ctk.StringVar(), ctk.StringVar(), ctk.StringVar(), ctk.StringVar()

# Header
header_frame = ctk.CTkFrame(janela, fg_color="transparent")
header_frame.pack(pady=(15, 5), fill="x")
ctk.CTkLabel(header_frame, text="DJ MANIK3", font=("Impact", 44), text_color="#FFF").pack()
ctk.CTkLabel(header_frame, text="V I R T U A L   D J   M I X E R", font=("Segoe UI", 12, "bold"),
             text_color="#AAA").pack()

# Full 4-line Slogan Restored
slogan = '"So as you struggle to catch the rhythm, \nask yourself, \ncan you dance to MANIQUE, \nto my beat"'
ctk.CTkLabel(header_frame, text=slogan, font=("Segoe UI", 12, "italic", "bold"), text_color="#666",
             justify="center").pack(pady=(5, 0))

# Launchpad
launch_frame = ctk.CTkFrame(janela, fg_color="transparent")
launch_frame.pack(pady=(8, 4))
base_btn_style = {"font": ("Segoe UI", 11, "bold"), "height": 28, "width": 90}
ctk.CTkButton(launch_frame, text="🌐 CH1", fg_color=COLOR_BTN_LAUNCH, command=lambda: launch_program("chrome1"),
              **base_btn_style).grid(row=0, column=0, padx=4)
ctk.CTkButton(launch_frame, text="🌐 CH2", fg_color=COLOR_BTN_LAUNCH, command=lambda: launch_program("chrome2"),
              **base_btn_style).grid(row=0, column=1, padx=4)
ctk.CTkButton(launch_frame, text="▶ VLC", fg_color=COLOR_BTN_LAUNCH, command=lambda: launch_program("vlc"),
              **base_btn_style).grid(row=0, column=2, padx=4)
btn_setup = ctk.CTkButton(launch_frame, text="⚙️ SETUP", fg_color=COLOR_MUTE, command=open_settings, **base_btn_style)
btn_setup.grid(row=0, column=3, padx=4)

# ==========================================
# UNIFIED MATRIX CONTAINER
# ==========================================
matrix_container = ctk.CTkFrame(janela, fg_color=COLOR_BG_FRAME, corner_radius=12, border_width=2,
                                border_color="#2A2A2A")
matrix_container.pack(padx=20, pady=10, fill="x")


def add_static_row(ch_title, sub_title, var, default, bid, is_last=False):
    f = ctk.CTkFrame(matrix_container, fg_color="transparent")
    f.pack(fill="x", pady=6)
    f.grid_columnconfigure(0, weight=1)
    f.grid_columnconfigure(1, weight=0)

    left_cont = ctk.CTkFrame(f, fg_color="transparent")
    left_cont.grid(row=0, column=0, sticky="w", padx=15)
    ctk.CTkLabel(left_cont, text=ch_title, font=("Impact", 22), text_color="#FFF").pack(side="left", padx=(0, 6))
    ctk.CTkLabel(left_cont, text=sub_title, font=("Segoe UI", 12, "bold"), text_color="#AAA").pack(side="left")

    create_routing_block(f, var, default, bid).grid(row=0, column=1, sticky="e", padx=10)

    if not is_last:
        ctk.CTkFrame(matrix_container, height=2, fg_color="#2A2A2A").pack(fill="x", padx=15)


def add_dynamic_row(ch_title, var, default, bid, is_last=False):
    f = ctk.CTkFrame(matrix_container, fg_color="transparent")
    f.pack(fill="x", pady=6)
    f.grid_columnconfigure(0, weight=1)
    f.grid_columnconfigure(1, weight=0)

    left_cont = ctk.CTkFrame(f, fg_color="transparent")
    left_cont.grid(row=0, column=0, sticky="w", padx=15)
    ctk.CTkLabel(left_cont, text=ch_title, font=("Impact", 22), text_color="#FFF").pack(side="left", padx=(0, 6))

    cb = ctk.CTkComboBox(left_cont, width=125, height=32, font=("Segoe UI", 12, "bold"),
                         command=lambda val: on_combobox_change(bid, val))
    cb.pack(side="left")

    create_routing_block(f, var, default, bid).grid(row=0, column=1, sticky="e", padx=10)

    if not is_last:
        ctk.CTkFrame(matrix_container, height=2, fg_color="#2A2A2A").pack(fill="x", padx=15)
    return cb


add_static_row("■ CH 1:", "YT1", state_ch1, "MUTE", 1)
add_static_row("■ CH 2:", "YT2", state_ch2, "MUTE", 2)
combo_app3 = add_dynamic_row("■ CH 3:", state_ch3, "MUTE", 3)
combo_app4 = add_dynamic_row("■ CH 4:", state_ch4, "MUTE", 4, is_last=True)

# Live Monitors
display_frame = ctk.CTkFrame(janela, fg_color="transparent")
display_frame.pack(padx=20, pady=(5, 0), fill="x")
display_frame.grid_columnconfigure(0, weight=1)
display_frame.grid_columnconfigure(1, weight=1)


def create_monitor(parent, title, color, col):
    f = ctk.CTkFrame(parent, fg_color="#1A1A1A", border_width=3, border_color=color, corner_radius=12)
    f.grid(row=0, column=col, padx=6, sticky="nsew")

    ctk.CTkLabel(f, text=title, font=("Impact", 22), text_color=color).pack(pady=(16, 8))
    lbl = ctk.CTkLabel(f, text="--- SILENCE ---", font=("Segoe UI", 14, "bold"), text_color="#FFF")
    lbl.pack(pady=(0, 24))

    return lbl


lbl_display_line1 = create_monitor(display_frame, "LIVE LINE 1", COLOR_LINE1, 0)
lbl_display_line2 = create_monitor(display_frame, "LIVE LINE 2", COLOR_LINE2, 1)

# Initialize App
if __name__ == "__main__":
    missing_c1 = not os.path.exists(APPS_INFO["chrome1"]["path"])
    missing_vlc = not os.path.exists(APPS_INFO["vlc"]["path"])

    if missing_c1 or missing_vlc:
        janela.after(500, run_auto_setup)
    else:
        janela.after(100, update_lists)
        janela.after(200, update_live_displays)
        janela.after(5000, auto_update_lists)

    janela.mainloop()
