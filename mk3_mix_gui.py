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
# 1. SETUP LOGGING (Observability)
# ==========================================
logging.basicConfig(
    filename='manik3_system.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ==========================================
# 2. VERIFICAÇÃO DE ADMINISTRADOR
# ==========================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        logging.error(f"Failed to check admin status: {e}")
        return False

if not is_admin():
    logging.info("Requesting Administrator privileges...")
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
    except Exception as e:
        logging.critical(f"Failed to elevate privileges: {e}")
        sys.exit()

# ==========================================
# 3. GESTÃO DE CONFIGURAÇÃO (Config Management)
# ==========================================
if getattr(sys, 'frozen', False):
    PASTA_ATUAL = os.path.dirname(sys.executable)
else:
    PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(PASTA_ATUAL, "config.json")

# Default configuration if file doesn't exist
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
CAMINHO_SVV = os.path.join(PASTA_ATUAL, config.get("svv_executable", "SoundVolumeView.exe"))

# ==========================================
# 4. CLASSES & DESIGN DA APLICAÇÃO
# ==========================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Cores Constants
COR_LINE1 = "#1DB954"
COR_LINE2 = "#00D1FF"
COR_MUTE = "#E01A4F"
COR_FUNDO_APP = "#121212"
COR_FUNDO_FRAME = "#1E1E1E"
NO_WINDOW = 0x08000000

class Manik3Mixer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MANIK3 VIRTUAL DJ")
        self.geometry("560x900")
        self.resizable(False, False)
        self.configure(fg_color=COR_FUNDO_APP)
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar)

        # Estado (A Memória da Mesa)
        self.current_config = {
            "applied": False,
            "ch1": "LINE 1", "ch2": "LINE 2", "ch3": "MUTE", "ch4": "MUTE",
            "app3": "", "app4": "", "line1": "", "line2": ""
        }
        self.update_funcs = {}

        # Variáveis da UI
        self.var_line1 = ctk.StringVar(value="Selecionar placa de som...")
        self.var_line2 = ctk.StringVar(value="Selecionar placa de som...")
        self.state_ch1 = ctk.StringVar()
        self.state_ch2 = ctk.StringVar()
        self.state_ch3 = ctk.StringVar()
        self.state_ch4 = ctk.StringVar()

        self.janela_config = None
        self.build_ui()

        # Arranque
        logging.info("Application UI initialized. Starting initial scans.")
        self.after(100, self.atualizar_listas)
        self.after(200, self.atualizar_displays_ao_vivo)

    # --- UI BUILDING METHODS ---
    def build_ui(self):
        # Cabeçalho
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(pady=(25, 15), fill="x")
        ctk.CTkLabel(frame_header, text="DJ MANIK3", font=("Impact", 46), text_color="#FFFFFF").pack()
        ctk.CTkLabel(frame_header, text="V I R T U A L   D J   M I X E R", font=("Segoe UI", 14, "bold"), text_color="#AAAAAA").pack(pady=(0, 15))
        ctk.CTkLabel(frame_header, text='"So as you struggle to catch the rhythm, \nask yourself, \ncan you dance to MANIQUE, \nto my beat"', font=("Segoe UI", 12, "italic", "bold"), text_color="#666666").pack()

        # Launchpad
        frame_launch = ctk.CTkFrame(self, fg_color="transparent")
        frame_launch.pack(pady=(5, 15), padx=20)
        btn_style = {"font": ("Segoe UI", 12, "bold"), "fg_color": "#2A2A2A", "hover_color": "#3A3A3A", "height": 38, "width": 120}
        
        ctk.CTkButton(frame_launch, text="🌐 CH1", command=lambda: self.abrir_programa("chrome1"), **btn_style).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkButton(frame_launch, text="🌐 CH2", command=lambda: self.abrir_programa("chrome2"), **btn_style).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(frame_launch, text="▶ VLC", command=lambda: self.abrir_programa("vlc"), **btn_style).grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkButton(frame_launch, text="⚙️ SETUP", text_color="#FFFFFF", fg_color=COR_MUTE, hover_color="#B0123C", font=("Segoe UI", 12, "bold"), height=38, width=120, command=self.abrir_configuracoes).grid(row=0, column=3, padx=5, pady=5)

        # Matrix
        frame_matrix = ctk.CTkFrame(self, fg_color="transparent")
        frame_matrix.pack(padx=20, fill="x")

        # Channels
        self.criar_canal(frame_matrix, "■ CH 1: YouTube (chrome1)", self.state_ch1, "LINE 1", "ch1")
        self.criar_canal(frame_matrix, "■ CH 2: YouTube (chrome2)", self.state_ch2, "LINE 2", "ch2")
        
        self.combo_app3 = self.criar_canal_dinamico(frame_matrix, "■ CH 3: Media Players", self.state_ch3, "MUTE", "ch3")
        self.combo_app4 = self.criar_canal_dinamico(frame_matrix, "■ CH 4: Extras / Karaoke", self.state_ch4, "MUTE", "ch4")

        # Displays
        frame_displays = ctk.CTkFrame(self, fg_color="transparent")
        frame_displays.pack(padx=20, pady=(5, 10), fill="x")
        frame_displays.grid_columnconfigure(0, weight=1)
        frame_displays.grid_columnconfigure(1, weight=1)

        self.lbl_display_line1 = self.criar_display(frame_displays, "🔴 LIVE ON LINE 1", COR_LINE1, 0, 0)
        self.lbl_display_line2 = self.criar_display(frame_displays, "🔴 LIVE ON LINE 2", COR_LINE2, 0, 1)

        # Bottom Buttons
        frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        frame_botoes.pack(pady=(5, 20), side="bottom")
        ctk.CTkButton(frame_botoes, text="⟳ RESCAN", font=("Segoe UI", 14, "bold"), fg_color="#333333", hover_color="#555555", width=140, height=45, command=self.atualizar_listas).pack(side="left", padx=10)
        self.btn_aplicar = ctk.CTkButton(frame_botoes, text="▶ APPLY MIX", font=("Segoe UI", 16, "bold"), fg_color=COR_MUTE, hover_color="#B0123C", width=250, height=45, command=self.aplicar_configuracoes)
        self.btn_aplicar.pack(side="left", padx=10)

    # --- UI HELPERS ---
    def criar_canal(self, parent, titulo, var_state, default_state, block_id):
        frame = ctk.CTkFrame(parent, fg_color=COR_FUNDO_FRAME, corner_radius=8)
        frame.pack(pady=(0, 15), fill="x")
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=titulo, font=("Impact", 18), text_color="#FFFFFF").grid(row=0, column=0, padx=15, pady=25, sticky="w")
        btns = self.criar_bloco_roteamento(frame, var_state, default_state, block_id)
        btns.grid(row=0, column=1, padx=15, pady=25, sticky="e")

    def criar_canal_dinamico(self, parent, titulo, var_state, default_state, block_id):
        frame = ctk.CTkFrame(parent, fg_color=COR_FUNDO_FRAME, corner_radius=8)
        frame.pack(pady=(0, 15), fill="x")
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=titulo, font=("Impact", 18), text_color="#FFFFFF").grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5), sticky="w")
        combo = ctk.CTkComboBox(frame, width=260, height=35, font=("Segoe UI", 12), command=lambda _: self.verificar_alteracoes())
        combo.grid(row=1, column=0, padx=15, pady=(0, 20), sticky="w")
        btns = self.criar_bloco_roteamento(frame, var_state, default_state, block_id)
        btns.grid(row=1, column=1, padx=15, pady=(0, 20), sticky="e")
        return combo

    def criar_display(self, parent, text, color, row, col):
        frame = ctk.CTkFrame(parent, fg_color="#1A1A1A", border_width=2, border_color=color, corner_radius=10)
        frame.grid(row=row, column=col, padx=(0 if col==0 else 8, 8 if col==0 else 0), sticky="nsew")
        ctk.CTkLabel(frame, text=text, font=("Impact", 16), text_color=color).pack(pady=(10, 5))
        lbl = ctk.CTkLabel(frame, text="---", font=("Segoe UI", 12, "bold"), text_color="#FFFFFF", justify="center")
        lbl.pack(pady=(5, 15), padx=10)
        return lbl

    def criar_bloco_roteamento(self, parent, var_state, default_state, block_id):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_font = ("Segoe UI", 12, "bold")
        
        btn_l1 = ctk.CTkButton(frame, text="LINE 1", font=btn_font, width=75, height=35, corner_radius=6)
        btn_m = ctk.CTkButton(frame, text="MUTE", font=btn_font, width=75, height=35, corner_radius=6)
        btn_l2 = ctk.CTkButton(frame, text="LINE 2", font=btn_font, width=75, height=35, corner_radius=6)

        btn_l1.pack(side="left", padx=2)
        btn_m.pack(side="left", padx=2)
        btn_l2.pack(side="left", padx=2)

        def atualizar_cores(estado_atual):
            var_state.set(estado_atual)
            for b in [btn_l1, btn_m, btn_l2]:
                b.configure(fg_color="#333333", text_color="#AAAAAA", hover_color="#444444")

            if estado_atual == "LINE 1":
                btn_l1.configure(fg_color=COR_LINE1, text_color="#000000", hover_color="#179141")
            elif estado_atual == "LINE 2":
                btn_l2.configure(fg_color=COR_LINE2, text_color="#000000", hover_color="#00A8CC")
            elif estado_atual == "MUTE":
                btn_m.configure(fg_color=COR_MUTE, text_color="#FFFFFF", hover_color="#B0123C")
            
            self.verificar_alteracoes()

        btn_l1.configure(command=lambda: atualizar_cores("LINE 1"))
        btn_m.configure(command=lambda: atualizar_cores("MUTE"))
        btn_l2.configure(command=lambda: atualizar_cores("LINE 2"))

        self.update_funcs[block_id] = atualizar_cores
        atualizar_cores(default_state)
        return frame

    # --- CORE LOGIC ---
    def abrir_programa(self, chave):
        rel_path = config.get("launchpad_paths", {}).get(chave)
        if not rel_path: return
        
        full_path = os.path.join(PASTA_ATUAL, rel_path.replace("/", os.sep))
        if not os.path.exists(full_path):
            logging.error(f"Application missing: {full_path}")
            messagebox.showerror("File Missing", f"Could not find:\n{full_path}")
            return

        try:
            pasta_do_programa = os.path.dirname(full_path)
            args = ""
            if "chrome" in chave.lower():
                pasta_dados = os.path.abspath(os.path.join(pasta_do_programa, "..", "..", "Data", "profile"))
                args = f' --user-data-dir="{pasta_dados}" --no-first-run --no-default-browser-check "https://www.youtube.com"'

            subprocess.Popen(f'"{full_path}" {args}', shell=True, cwd=pasta_do_programa)
            logging.info(f"Launched {chave} successfully.")
            self.after(3000, self.atualizar_listas)
        except Exception as e:
            logging.error(f"Failed to launch {chave}: {e}")
            messagebox.showerror("Error", f"Failed to start {chave}: {e}")

    def obter_processos_brutos(self):
        processos = set()
        try:
            resultado = subprocess.run("tasklist /V /FO CSV /NH", shell=True, capture_output=True, text=True, errors='ignore', creationflags=NO_WINDOW)
            for linha in resultado.stdout.splitlines():
                if linha.strip() and len(linha.split('","')) >= 9:
                    processos.add(linha.split('","')[0].strip('"').lower())
        except subprocess.CalledProcessError as e:
            logging.error(f"Tasklist command failed: {e}")
        return processos

    def obter_dispositivos(self):
        dispositivos = set()
        arq_temp = os.path.join(PASTA_ATUAL, "temp_audio.csv")
        
        if not os.path.exists(CAMINHO_SVV):
            logging.error("SoundVolumeView.exe is missing from root directory.")
            return ["⚠️ ERRO: SVV em falta!"]
            
        try:
            subprocess.run([CAMINHO_SVV, "/scomma", arq_temp], shell=False, creationflags=NO_WINDOW, check=True)
            for enc in ['utf-16', 'utf-8-sig', 'utf-8', 'mbcs', 'latin-1']:
                try:
                    with open(arq_temp, "r", encoding=enc) as f:
                        linhas = list(csv.reader(f))
                    for linha in linhas:
                        if len(linha) >= 3:
                            l_low = [str(i).lower() for i in linha]
                            if ("device" in l_low or "dispositivo" in l_low) and ("render" in l_low or "reprodução" in l_low or "saída" in l_low):
                                dispositivos.add(linha[0])
                    break
                except UnicodeDecodeError:
                    continue
        except subprocess.CalledProcessError as e:
            logging.error(f"SVV failed to export devices: {e}")
        
        if os.path.exists(arq_temp):
            try: os.remove(arq_temp)
            except OSError: pass
            
        return sorted(list(dispositivos)) if dispositivos else ["Nenhum dispositivo encontrado..."]

    def processar_roteamento(self, alvo_app, selecao_destino, placa_a, placa_b):
        if not alvo_app or "Selecionar" in alvo_app: return True
        alvo_limpo = alvo_app.split(" ")[0].strip().lower()
        
        if not os.path.exists(CAMINHO_SVV):
            logging.error("Cannot route audio. SVV missing.")
            return False

        try:
            if selecao_destino == "MUTE":
                subprocess.run([CAMINHO_SVV, "/Mute", alvo_limpo], shell=False, creationflags=NO_WINDOW, check=True)
                logging.info(f"Muted application: {alvo_limpo}")
                return True
            else:
                placa_alvo = placa_a if selecao_destino == "LINE 1" else placa_b
                if "⚠️" in placa_alvo or "Selecionar" in placa_alvo or not placa_alvo: return False
                
                subprocess.run([CAMINHO_SVV, "/SetAppDefault", placa_alvo.strip(), "all", alvo_limpo], shell=False, creationflags=NO_WINDOW, check=True)
                subprocess.run([CAMINHO_SVV, "/Unmute", alvo_limpo], shell=False, creationflags=NO_WINDOW, check=True)
                logging.info(f"Routed {alvo_limpo} to {placa_alvo}")
                return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Routing failed for {alvo_limpo} to {selecao_destino}: {e}")
            return False

    def verificar_alteracoes(self, *args):
        try:
            mudou = (
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
            if mudou:
                self.btn_aplicar.configure(state="normal", text="▶ APPLY MIX", fg_color=COR_MUTE, text_color="#FFFFFF")
            else:
                self.btn_aplicar.configure(state="disabled", text="✅ MIX ATIVO", fg_color=COR_LINE1, text_color_disabled="#000000")
        except AttributeError:
            pass # UI not fully drawn yet

    def atualizar_displays_ao_vivo(self):
        l1_apps, l2_apps = [], []

        if self.current_config["applied"]:
            st1, st2, st3, st4 = self.current_config["ch1"], self.current_config["ch2"], self.current_config["ch3"], self.current_config["ch4"]

            if st1 == "LINE 1": l1_apps.append("CH 1: YouTube 1")
            elif st1 == "LINE 2": l2_apps.append("CH 1: YouTube 1")

            if st2 == "LINE 1": l1_apps.append("CH 2: YouTube 2")
            elif st2 == "LINE 2": l2_apps.append("CH 2: YouTube 2")

            for app, state in [(self.current_config["app3"], st3), (self.current_config["app4"], st4)]:
                app_clean = app.replace(".exe", "")
                if "Selecionar" not in app_clean and app_clean:
                    if state == "LINE 1": l1_apps.append(f"CH X: {app_clean}")
                    elif state == "LINE 2": l2_apps.append(f"CH X: {app_clean}")

        self.lbl_display_line1.configure(text="\n".join(l1_apps) if l1_apps else "--- SILÊNCIO ---")
        self.lbl_display_line2.configure(text="\n".join(l2_apps) if l2_apps else "--- SILÊNCIO ---")

    def aplicar_configuracoes(self):
        placa_a, placa_b = self.var_line1.get(), self.var_line2.get()

        if "Selecionar" in placa_a or "Selecionar" in placa_b or not placa_a or not placa_b:
            logging.warning("Attempted to apply mix without selecting hardware devices.")
            return messagebox.showwarning("Atenção", "Abre o '⚙️ SETUP' e define as placas para o LINE 1 e LINE 2!")

        st1, st2 = self.state_ch1.get(), self.state_ch2.get()

        # Reversão Anti-Colisão
        if st1 != "MUTE" and st1 == st2:
            logging.warning("Audio collision prevented between CH1 and CH2.")
            messagebox.showwarning("Colisão de Áudio 🚫", "O Chrome 1 e o Chrome 2 estão a tentar usar o mesmo canal!\n\nOs botões foram revertidos para a última posição segura.")
            if "ch1" in self.update_funcs: self.update_funcs["ch1"](self.current_config.get("ch1", "LINE 1"))
            if "ch2" in self.update_funcs: self.update_funcs["ch2"](self.current_config.get("ch2", "LINE 2"))
            return

        s1 = self.processar_roteamento("chrome1.exe", st1, placa_a, placa_b)
        s2 = self.processar_roteamento("chrome2.exe", st2, placa_a, placa_b)
        s3 = self.processar_roteamento(self.combo_app3.get(), self.state_ch3.get(), placa_a, placa_b)
        s4 = self.processar_roteamento(self.combo_app4.get(), self.state_ch4.get(), placa_a, placa_b)

        if all([s1, s2, s3, s4]):
            logging.info("Matrix routing applied successfully.")
            self.current_config.update({
                "applied": True, "ch1": st1, "ch2": st2, 
                "ch3": self.state_ch3.get(), "ch4": self.state_ch4.get(),
                "app3": self.combo_app3.get(), "app4": self.combo_app4.get(),
                "line1": placa_a, "line2": placa_b
            })
            self.atualizar_displays_ao_vivo()
            self.verificar_alteracoes()
        else:
            logging.error("Failed to apply full matrix routing.")
            messagebox.showerror("Erro", "Falha ao aplicar a matriz. Verifica as placas e o ficheiro SVV.")

    def atualizar_listas(self):
        procs = self.obter_processos_brutos()
        l_ch3 = [p for p in procs if p in config.get("apps_ch3_media", [])]
        l_ch4 = [p for p in procs if p in config.get("apps_ch4_extra", [])]

        v_ch3 = self.combo_app3.get()
        self.combo_app3.configure(values=l_ch3 if l_ch3 else ["Nenhuma Media detetada"])
        self.combo_app3.set(v_ch3 if v_ch3 in l_ch3 else ("Selecionar Media..." if not l_ch3 else l_ch3[0]))

        v_ch4 = self.combo_app4.get()
        self.combo_app4.configure(values=l_ch4 if l_ch4 else ["Nenhuma Extra detetada"])
        self.combo_app4.set(v_ch4 if v_ch4 in l_ch4 else ("Selecionar Extra..." if not l_ch4 else l_ch4[0]))
        self.verificar_alteracoes()

    def abrir_configuracoes(self):
        if self.janela_config is None or not self.janela_config.winfo_exists():
            self.janela_config = ctk.CTkToplevel(self)
            self.janela_config.title("⚙️ Setup de Hardware")
            self.janela_config.geometry("450x260")
            self.janela_config.resizable(False, False)
            self.janela_config.configure(fg_color="#1A1A1A")
            self.janela_config.attributes("-topmost", True)

            ctk.CTkLabel(self.janela_config, text="ROTEAMENTO FÍSICO", font=("Impact", 24), text_color="#FFFFFF").pack(pady=(15, 10))
            l_disp = self.obter_dispositivos()

            ctk.CTkLabel(self.janela_config, text="Mesa LINE 1 (ex: Speaker):", font=("Segoe UI", 12, "bold"), text_color=COR_LINE1).pack(anchor="w", padx=20)
            ctk.CTkComboBox(self.janela_config, variable=self.var_line1, values=l_disp, width=410, height=30, command=lambda _: self.verificar_alteracoes()).pack(pady=(0, 10), padx=20)

            ctk.CTkLabel(self.janela_config, text="Mesa LINE 2 (ex: USB Speaker):", font=("Segoe UI", 12, "bold"), text_color=COR_LINE2).pack(anchor="w", padx=20)
            ctk.CTkComboBox(self.janela_config, variable=self.var_line2, values=l_disp, width=410, height=30, command=lambda _: self.verificar_alteracoes()).pack(pady=(0, 15), padx=20)

            ctk.CTkButton(self.janela_config, text="Guardar & Fechar", font=("Segoe UI", 12, "bold"), fg_color="#333333", hover_color="#555555", command=self.janela_config.destroy).pack(pady=5)
        else:
            self.janela_config.focus()

    def ao_fechar(self):
        logging.info("Application closed by user.")
        self.withdraw()
        self.quit()

# ==========================================
# 5. EXECUÇÃO DO PROGRAMA
# ==========================================
if __name__ == "__main__":
    app = Manik3Mixer()
    app.mainloop()