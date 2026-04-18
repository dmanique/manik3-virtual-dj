import customtkinter as ctk
from tkinter import messagebox
import subprocess
import os
import csv
import ctypes
import sys
import json
import logging

# ==========================================
# 1. OBSERVABILITY & LOGGING
# ==========================================
# In SRE, silent failures are the enemy. We log all state changes, 
# subprocess executions, and errors to a local file for auditability.
logging.basicConfig(
    filename='manik3_system.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ==========================================
# 2. PRIVILEGE ESCALATION (Auto-Admin)
# ==========================================
# Manipulating Windows audio endpoints and registry states requires elevated privileges.
# This function ensures the script self-elevates upon execution to prevent access denials.
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        logging.error(f"Failed to check admin status: {e}")
        return False

if not is_admin():
    logging.info("Requesting Administrator privileges to manipulate audio endpoints...")
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
    except Exception as e:
        logging.critical(f"Failed to elevate privileges: {e}")
        sys.exit()

# ==========================================
# 3. CONFIGURATION MANAGEMENT
# ==========================================
# Hardcoding variables is an anti-pattern. We generate and read from a JSON config file
# to allow users to update application targets without modifying the source code.
if getattr(sys, 'frozen', False):
    CURRENT_DIR = os.path.dirname(sys.executable)
else:
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(CURRENT_DIR, "config.json")

# Default configuration template
DEFAULT_CONFIG = {
    "svv_executable": "SoundVolumeView.exe",
    "apps_ch3_media": ["vlc.exe", "vlcportable.exe", "spotify.exe", "wmplayer.exe"],
    "apps_ch4_extra": ["pikaraoke.exe", "msedge.exe", "firefox.exe"],
    "launchpad_paths": {
        "chrome1": "apps/Chrome1/App/Chrome-bin/chrome1.exe",
        "chrome2": "apps/Chrome2/App/Chrome-bin/chrome2.exe",
        "vlc": "apps/VLC/VLCPortable.exe"
    }
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        logging.info("Config file not found. Generating default config.json")
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            logging.info("Loaded external config.json successfully.")
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Corrupted config.json: {e}. Falling back to defaults.")
        return DEFAULT_CONFIG

config = load_config()
SVV_PATH = os.path.join(CURRENT_DIR, config.get("svv_executable", "SoundVolumeView.exe"))

# ==========================================
# 4. APPLICATION STATE & UI ARCHITECTURE
# ==========================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Theme Constants
COLOR_LINE1 = "#1DB954"
COLOR_LINE2 = "#00D1FF"
COLOR_MUTE = "#E01A4F"
COLOR_APP_BG = "#121212"
COLOR_FRAME_BG = "#1E1E1E"
NO_WINDOW = 0x08000000 # Flag to suppress CMD windows during subprocess execution

class Manik3Mixer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MANIK3 VIRTUAL DJ")
        self.geometry("560x900")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_APP_BG)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Desired State Definition (The brain of the matrix)
        self.current_config = {
            "applied": False,
            "ch1": "LINE 1", "ch2": "LINE 2", "ch3": "MUTE", "ch4": "MUTE",
            "app3": "", "app4": "", "line1": "", "line2": ""
        }
        self.update_funcs = {}

        # UI Variables
        self.var_line1 = ctk.StringVar(value="Select sound device...")
        self.var_line2 = ctk.StringVar(value="Select sound device...")
        self.state_ch1 = ctk.StringVar()
        self.state_ch2 = ctk.StringVar()
        self.state_ch3 = ctk.StringVar()
        self.state_ch4 = ctk.StringVar()

        self.config_window = None
        self.build_ui()

        # Bootstrap: Scan system state upon UI initialization
        logging.info("Application UI initialized. Starting initial system scans.")
        self.after(100, self.update_process_lists)
        self.after(200, self.update_live_displays)

    # --- UI BUILDING METHODS ---
    def build_ui(self):
        # Header
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(pady=(25, 15), fill="x")
        ctk.CTkLabel(frame_header, text="DJ MANIK3", font=("Impact", 46), text_color="#FFFFFF").pack()
        ctk.CTkLabel(frame_header, text="V I R T U A L   D J   M I X E R", font=("Segoe UI", 14, "bold"), text_color="#AAAAAA").pack(pady=(0, 15))
        ctk.CTkLabel(frame_header, text='"So as you struggle to catch the rhythm, \nask yourself, \ncan you dance to MANIQUE, \nto my beat"', font=("Segoe UI", 12, "italic", "bold"), text_color="#666666").pack()

        # Launchpad (Application Deployment)
        frame_launch = ctk.CTkFrame(self, fg_color="transparent")
        frame_launch.pack(pady=(5, 15), padx=20)
        btn_style = {"font": ("Segoe UI", 12, "bold"), "fg_color": "#2A2A2A", "hover_color": "#3A3A3A", "height": 38, "width": 120}
        
        ctk.CTkButton(frame_launch, text="🌐 CH1", command=lambda: self.launch_program("chrome1"), **btn_style).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkButton(frame_launch, text="🌐 CH2", command=lambda: self.launch_program("chrome2"), **btn_style).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(frame_launch, text="▶ VLC", command=lambda: self.launch_program("vlc"), **btn_style).grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkButton(frame_launch, text="⚙️ SETUP", text_color="#FFFFFF", fg_color=COLOR_MUTE, hover_color="#B0123C", font=("Segoe UI", 12, "bold"), height=38, width=120, command=self.open_settings).grid(row=0, column=3, padx=5, pady=5)

        # Matrix Frame
        frame_matrix = ctk.CTkFrame(self, fg_color="transparent")
        frame_matrix.pack(padx=20, fill="x")

        # Static Channels
        self.create_channel(frame_matrix, "■ CH 1: YouTube (chrome1)", self.state_ch1, "LINE 1", "ch1")
        self.create_channel(frame_matrix, "■ CH 2: YouTube (chrome2)", self.state_ch2, "LINE 2", "ch2")
        
        # Dynamic Channels (Process Hooking)
        self.combo_app3 = self.create_dynamic_channel(frame_matrix, "■ CH 3: Media Players", self.state_ch3, "MUTE", "ch3")
        self.combo_app4 = self.create_dynamic_channel(frame_matrix, "■ CH 4: Extras / Karaoke", self.state_ch4, "MUTE", "ch4")

        # Telemetry Displays
        frame_displays = ctk.CTkFrame(self, fg_color="transparent")
        frame_displays.pack(padx=20, pady=(5, 10), fill="x")
        frame_displays.grid_columnconfigure(0, weight=1)
        frame_displays.grid_columnconfigure(1, weight=1)

        self.lbl_display_line1 = self.create_display(frame_displays, "🔴 LIVE ON LINE 1", COLOR_LINE1, 0, 0)
        self.lbl_display_line2 = self.create_display(frame_displays, "🔴 LIVE ON LINE 2", COLOR_LINE2, 0, 1)

        # Execution Controls
        frame_buttons = ctk.CTkFrame(self, fg_color="transparent")
        frame_buttons.pack(pady=(5, 20), side="bottom")
        ctk.CTkButton(frame_buttons, text="⟳ RESCAN", font=("Segoe UI", 14, "bold"), fg_color="#333333", hover_color="#555555", width=140, height=45, command=self.update_process_lists).pack(side="left", padx=10)
        self.btn_apply = ctk.CTkButton(frame_buttons, text="▶ APPLY MIX", font=("Segoe UI", 16, "bold"), fg_color=COLOR_MUTE, hover_color="#B0123C", width=250, height=45, command=self.apply_configuration)
        self.btn_apply.pack(side="left", padx=10)

    # --- UI COMPONENT FACTORIES ---
    def create_channel(self, parent, title, var_state, default_state, block_id):
        frame = ctk.CTkFrame(parent, fg_color=COLOR_FRAME_BG, corner_radius=8)
        frame.pack(pady=(0, 15), fill="x")
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=title, font=("Impact", 18), text_color="#FFFFFF").grid(row=0, column=0, padx=15, pady=25, sticky="w")
        btns = self.create_routing_block(frame, var_state, default_state, block_id)
        btns.grid(row=0, column=1, padx=15, pady=25, sticky="e")

    def create_dynamic_channel(self, parent, title, var_state, default_state, block_id):
        frame = ctk.CTkFrame(parent, fg_color=COLOR_FRAME_BG, corner_radius=8)
        frame.pack(pady=(0, 15), fill="x")
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=title, font=("Impact", 18), text_color="#FFFFFF").grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5), sticky="w")
        combo = ctk.CTkComboBox(frame, width=260, height=35, font=("Segoe UI", 12), command=lambda _: self.check_for_changes())
        combo.grid(row=1, column=0, padx=15, pady=(0, 20), sticky="w")
        btns = self.create_routing_block(frame, var_state, default_state, block_id)
        btns.grid(row=1, column=1, padx=15, pady=(0, 20), sticky="e")
        return combo

    def create_display(self, parent, text, color, row, col):
        frame = ctk.CTkFrame(parent, fg_color="#1A1A1A", border_width=2, border_color=color, corner_radius=10)
        frame.grid(row=row, column=col, padx=(0 if col==0 else 8, 8 if col==0 else 0), sticky="nsew")
        ctk.CTkLabel(frame, text=text, font=("Impact", 16), text_color=color).pack(pady=(10, 5))
        lbl = ctk.CTkLabel(frame, text="---", font=("Segoe UI", 12, "bold"), text_color="#FFFFFF", justify="center")
        lbl.pack(pady=(5, 15), padx=10)
        return lbl

    def create_routing_block(self, parent, var_state, default_state, block_id):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_font = ("Segoe UI", 12, "bold")
        
        btn_l1 = ctk.CTkButton(frame, text="LINE 1", font=btn_font, width=75, height=35, corner_radius=6)
        btn_m = ctk.CTkButton(frame, text="MUTE", font=btn_font, width=75, height=35, corner_radius=6)
        btn_l2 = ctk.CTkButton(frame, text="LINE 2", font=btn_font, width=75, height=35, corner_radius=6)

        btn_l1.pack(side="left", padx=2)
        btn_m.pack(side="left", padx=2)
        btn_l2.pack(side="left", padx=2)

        def update_colors(current_state):
            var_state.set(current_state)
            for b in [btn_l1, btn_m, btn_l2]:
                b.configure(fg_color="#333333", text_color="#AAAAAA", hover_color="#444444")

            if current_state == "LINE 1":
                btn_l1.configure(fg_color=COLOR_LINE1, text_color="#000000", hover_color="#179141")
            elif current_state == "LINE 2":
                btn_l2.configure(fg_color=COLOR_LINE2, text_color="#000000", hover_color="#00A8CC")
            elif current_state == "MUTE":
                btn_m.configure(fg_color=COLOR_MUTE, text_color="#FFFFFF", hover_color="#B0123C")
            
            self.check_for_changes()

        btn_l1.configure(command=lambda: update_colors("LINE 1"))
        btn_m.configure(command=lambda: update_colors("MUTE"))
        btn_l2.configure(command=lambda: update_colors("LINE 2"))

        self.update_funcs[block_id] = update_colors
        update_colors(default_state)
        return frame

    # --- ORCHESTRATION & SYSTEM LOGIC ---
    def launch_program(self, app_key):
        rel_path = config.get("launchpad_paths", {}).get(app_key)
        if not rel_path: return
        
        full_path = os.path.join(CURRENT_DIR, rel_path.replace("/", os.sep))
        if not os.path.exists(full_path):
            logging.error(f"Target executable missing: {full_path}")
            messagebox.showerror("File Missing", f"Could not find:\n{full_path}")
            return

        try:
            app_dir = os.path.dirname(full_path)
            args = ""
            # Inject isolation arguments for Chrome to run multiple separate instances
            if "chrome" in app_key.lower():
                data_dir = os.path.abspath(os.path.join(app_dir, "..", "..", "Data", "profile"))
                args = f' --user-data-dir="{data_dir}" --no-first-run --no-default-browser-check "https://www.youtube.com"'

            subprocess.Popen(f'"{full_path}" {args}', shell=True, cwd=app_dir)
            logging.info(f"Successfully launched target: {app_key}.")
            self.after(3000, self.update_process_lists)
        except Exception as e:
            logging.error(f"Failed to launch {app_key}: {e}")
            messagebox.showerror("Execution Error", f"Failed to start {app_key}: {e}")

    def get_raw_processes(self):
        processes = set()
        try:
            # Query Windows for active process list silently
            result = subprocess.run("tasklist /V /FO CSV /NH", shell=True, capture_output=True, text=True, errors='ignore', creationflags=NO_WINDOW)
            for line in result.stdout.splitlines():
                if line.strip() and len(line.split('","')) >= 9:
                    processes.add(line.split('","')[0].strip('"').lower())
        except subprocess.CalledProcessError as e:
            logging.error(f"System tasklist command failed: {e}")
        return processes

    def get_audio_devices(self):
        devices = set()
        temp_file = os.path.join(CURRENT_DIR, "temp_audio.csv")
        
        if not os.path.exists(SVV_PATH):
            logging.error("SoundVolumeView.exe is missing. Cannot fetch audio endpoints.")
            return ["⚠️ ERROR: SVV Missing!"]
            
        try:
            subprocess.run([SVV_PATH, "/scomma", temp_file], shell=False, creationflags=NO_WINDOW, check=True)
            for enc in ['utf-16', 'utf-8-sig', 'utf-8', 'mbcs', 'latin-1']:
                try:
                    with open(temp_file, "r", encoding=enc) as f:
                        rows = list(csv.reader(f))
                    for row in rows:
                        if len(row) >= 3:
                            r_low = [str(i).lower() for i in row]
                            # Filter for output/playback devices specifically
                            if ("device" in r_low or "dispositivo" in r_low) and ("render" in r_low or "playback" in r_low or "reprodução" in r_low or "saída" in r_low):
                                devices.add(row[0])
                    break
                except UnicodeDecodeError:
                    continue
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to export device list from SVV: {e}")
        
        # Cleanup temporary state file
        if os.path.exists(temp_file):
            try: os.remove(temp_file)
            except OSError: pass
            
        return sorted(list(devices)) if devices else ["No audio devices found..."]

    def process_routing(self, target_app, destination, hardware_a, hardware_b):
        if not target_app or "Select" in target_app: return True
        clean_target = target_app.split(" ")[0].strip().lower()
        
        if not os.path.exists(SVV_PATH):
            logging.error(f"Cannot route {clean_target}. SVV engine missing.")
            return False

        try:
            if destination == "MUTE":
                subprocess.run([SVV_PATH, "/Mute", clean_target], shell=False, creationflags=NO_WINDOW, check=True)
                logging.info(f"Muted process: {clean_target}")
                return True
            else:
                target_hardware = hardware_a if destination == "LINE 1" else hardware_b
                if "⚠️" in target_hardware or "Select" in target_hardware or not target_hardware: return False
                
                # Execute routing via Windows Audio API hooks
                subprocess.run([SVV_PATH, "/SetAppDefault", target_hardware.strip(), "all", clean_target], shell=False, creationflags=NO_WINDOW, check=True)
                subprocess.run([SVV_PATH, "/Unmute", clean_target], shell=False, creationflags=NO_WINDOW, check=True)
                logging.info(f"Routed process {clean_target} to endpoint {target_hardware}")
                return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Endpoint routing failed for {clean_target} -> {destination}: {e}")
            return False

    def check_for_changes(self, *args):
        # Determine if current UI state drifts from applied state
        try:
            drift_detected = (
                not self.current_config["applied"] or
                self.state_ch1.get() != self.current_config["ch1"] or
                self.state_ch2.get() != self.current_config["ch2"] or
                self.state_ch3.get() != self.current_config["ch3"] or
                self.state_ch4.get() != self.current_config["ch4"] or
                self.combo_app3.get() != self.current_config["app3"] or
                self.combo_app4.get() != self.current_config["app4"] or
                self.var_line1.get() != self.current_config["line1"] or
                self.var_line2.get() != self.current_config["line2"]
            )
            if drift_detected:
                self.btn_apply.configure(state="normal", text="▶ APPLY MIX", fg_color=COLOR_MUTE, text_color="#FFFFFF")
            else:
                self.btn_apply.configure(state="disabled", text="✅ MIX ACTIVE", fg_color=COLOR_LINE1, text_color_disabled="#000000")
        except AttributeError:
            pass # UI elements not fully instantiated yet

    def update_live_displays(self):
        l1_apps, l2_apps = [], []

        if self.current_config["applied"]:
            st1, st2, st3, st4 = self.current_config["ch1"], self.current_config["ch2"], self.current_config["ch3"], self.current_config["ch4"]

            if st1 == "LINE 1": l1_apps.append("CH 1: YouTube 1")
            elif st1 == "LINE 2": l2_apps.append("CH 1: YouTube 1")

            if st2 == "LINE 1": l1_apps.append("CH 2: YouTube 2")
            elif st2 == "LINE 2": l2_apps.append("CH 2: YouTube 2")

            for app, state in [(self.current_config["app3"], st3), (self.current_config["app4"], st4)]:
                app_clean = app.replace(".exe", "")
                if "Select" not in app_clean and app_clean:
                    if state == "LINE 1": l1_apps.append(f"CH X: {app_clean}")
                    elif state == "LINE 2": l2_apps.append(f"CH X: {app_clean}")

        self.lbl_display_line1.configure(text="\n".join(l1_apps) if l1_apps else "--- SILENCE ---")
        self.lbl_display_line2.configure(text="\n".join(l2_apps) if l2_apps else "--- SILENCE ---")

    def apply_configuration(self):
        hardware_a, hardware_b = self.var_line1.get(), self.var_line2.get()

        if "Select" in hardware_a or "Select" in hardware_b or not hardware_a or not hardware_b:
            logging.warning("Routing aborted: Hardware endpoints not defined.")
            return messagebox.showwarning("Warning", "Open '⚙️ SETUP' and map the sound devices for LINE 1 and LINE 2!")

        st1, st2 = self.state_ch1.get(), self.state_ch2.get()

        # Audio Collision Defense Mechanism
        # Prevents two Chrome instances from fighting over the same audio pipeline
        if st1 != "MUTE" and st1 == st2:
            logging.warning("Defensive action: Audio collision prevented between CH1 and CH2.")
            messagebox.showwarning("Audio Collision 🚫", "Chrome 1 and Chrome 2 are attempting to use the same channel!\n\nButtons have been reverted to the last known safe state.")
            if "ch1" in self.update_funcs: self.update_funcs["ch1"](self.current_config.get("ch1", "LINE 1"))
            if "ch2" in self.update_funcs: self.update_funcs["ch2"](self.current_config.get("ch2", "LINE 2"))
            return

        s1 = self.process_routing("chrome1.exe", st1, hardware_a, hardware_b)
        s2 = self.process_routing("chrome2.exe", st2, hardware_a, hardware_b)
        s3 = self.process_routing(self.combo_app3.get(), self.state_ch3.get(), hardware_a, hardware_b)
        s4 = self.process_routing(self.combo_app4.get(), self.state_ch4.get(), hardware_a, hardware_b)

        if all([s1, s2, s3, s4]):
            logging.info("Matrix routing configuration successfully applied.")
            self.current_config.update({
                "applied": True, "ch1": st1, "ch2": st2, 
                "ch3": self.state_ch3.get(), "ch4": self.state_ch4.get(),
                "app3": self.combo_app3.get(), "app4": self.combo_app4.get(),
                "line1": hardware_a, "line2": hardware_b
            })
            self.update_live_displays()
            self.check_for_changes()
        else:
            logging.error("Failed to apply the complete routing matrix.")
            messagebox.showerror("Error", "Failed to apply the routing matrix. Check your sound devices and ensure the SVV executable is present.")

    def update_process_lists(self):
        procs = self.get_raw_processes()
        l_ch3 = [p for p in procs if p in config.get("apps_ch3_media", [])]
        l_ch4 = [p for p in procs if p in config.get("apps_ch4_extra", [])]

        v_ch3 = self.combo_app3.get()
        self.combo_app3.configure(values=l_ch3 if l_ch3 else ["No Media Apps Detected"])
        self.combo_app3.set(v_ch3 if v_ch3 in l_ch3 else ("Select Media App..." if not l_ch3 else l_ch3[0]))

        v_ch4 = self.combo_app4.get()
        self.combo_app4.configure(values=l_ch4 if l_ch4 else ["No Extra Apps Detected"])
        self.combo_app4.set(v_ch4 if v_ch4 in l_ch4 else ("Select Extra App..." if not l_ch4 else l_ch4[0]))
        self.check_for_changes()

    def open_settings(self):
        if self.config_window is None or not self.config_window.winfo_exists():
            self.config_window = ctk.CTkToplevel(self)
            self.config_window.title("⚙️ Hardware Setup")
            self.config_window.geometry("450x260")
            self.config_window.resizable(False, False)
            self.config_window.configure(fg_color="#1A1A1A")
            self.config_window.attributes("-topmost", True)

            ctk.CTkLabel(self.config_window, text="PHYSICAL ROUTING", font=("Impact", 24), text_color="#FFFFFF").pack(pady=(15, 10))
            l_disp = self.get_audio_devices()

            ctk.CTkLabel(self.config_window, text="Mixer LINE 1 (e.g., Speaker):", font=("Segoe UI", 12, "bold"), text_color=COLOR_LINE1).pack(anchor="w", padx=20)
            ctk.CTkComboBox(self.config_window, variable=self.var_line1, values=l_disp, width=410, height=30, command=lambda _: self.check_for_changes()).pack(pady=(0, 10), padx=20)

            ctk.CTkLabel(self.config_window, text="Mixer LINE 2 (e.g., USB Speaker):", font=("Segoe UI", 12, "bold"), text_color=COLOR_LINE2).pack(anchor="w", padx=20)
            ctk.CTkComboBox(self.config_window, variable=self.var_line2, values=l_disp, width=410, height=30, command=lambda _: self.check_for_changes()).pack(pady=(0, 15), padx=20)

            ctk.CTkButton(self.config_window, text="Save & Close", font=("Segoe UI", 12, "bold"), fg_color="#333333", hover_color="#555555", command=self.config_window.destroy).pack(pady=5)
        else:
            self.config_window.focus()

    def on_close(self):
        logging.info("Application shutdown initiated by user.")
        self.withdraw()
        self.quit()

# ==========================================
# 5. EXECUTION ENTRY POINT
# ==========================================
if __name__ == "__main__":
    app = Manik3Mixer()
    app.mainloop()
 