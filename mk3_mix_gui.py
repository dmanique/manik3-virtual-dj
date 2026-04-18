import customtkinter as ctk
from tkinter import messagebox
import subprocess
import os
import csv
import re
import ctypes
import sys
import threading
import time
import urllib.request
import zipfile
import tempfile

# ==========================================
# GITHUB DEPENDENCY URL (STATIC ASSET)
# ==========================================
# Este link transferirá apenas as apps pesadas (Chrome e VLC)
DEPENDENCY_URL = "https://github.com/dmanique/manik3-virtual-dj/releases/download/dependencies-v1/MANIK3_Dependencies.zip"

# ==========================================
# VERIFICAÇÃO DE ADMINISTRADOR (MODO DEUS)
# ==========================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    print("A pedir privilégios de Administrador...")
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

# ==========================================
# CONFIGURAÇÕES DE DESIGN
# ==========================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

COR_LINE1 = "#1DB954"  # Verde
COR_LINE2 = "#00D1FF"  # Ciano
COR_MUTE = "#E01A4F"  # Vermelho
COR_FUNDO_APP = "#121212"
COR_FUNDO_FRAME = "#1E1E1E"
COR_BTN_LAUNCH = "#2A2A2A"

NO_WINDOW = 0x08000000

# ==========================================
# GESTOR DE ESTADO (A MEMÓRIA DA MESA)
# ==========================================
current_config = {
    "applied": False,
    "ch1": "LINE 1", "ch2": "LINE 2", "ch3": "MUTE", "ch4": "MUTE",
    "app3": "", "app4": "", "line1": "", "line2": ""
}

update_funcs = {}

# ==========================================
# CONFIGURAÇÃO DE CAMINHOS & CATEGORIAS
# ==========================================
if getattr(sys, 'frozen', False):
    PASTA_ATUAL = os.path.dirname(sys.executable)
else:
    PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))

CAMINHO_SVV = os.path.join(PASTA_ATUAL, "SoundVolumeView.exe")
PASTA_APPS = os.path.join(PASTA_ATUAL, "apps")

APPS_INFO = {
    "chrome1": {"caminho": os.path.join(PASTA_APPS, "Chrome1", "App", "Chrome-bin", "chrome1.exe")},
    "chrome2": {"caminho": os.path.join(PASTA_APPS, "Chrome2", "App", "Chrome-bin", "chrome2.exe")},
    "vlc": {"caminho": os.path.join(PASTA_APPS, "VLC", "VLCPortable.exe")}
}

APPS_CH3 = ["vlc.exe", "vlcportable.exe", "spotify.exe", "wmplayer.exe"]
APPS_CH4 = ["pikaraoke.exe", "msedge.exe", "firefox.exe"]

# ==========================================
# AUTO-SETUP WIZARD (DOWNLOADER DAS APPS)
# ==========================================
def iniciar_auto_setup():
    setup_win = ctk.CTkToplevel(janela)
    setup_win.title("⚙️ MANIK3 Auto-Setup")
    setup_win.geometry("450x220")
    setup_win.resizable(False, False)
    setup_win.attributes("-topmost", True)
    setup_win.protocol("WM_DELETE_WINDOW", lambda: None) # Impede fechar a meio

    ctk.CTkLabel(setup_win, text="A INICIALIZAR WORKSPACE", font=("Impact", 20), text_color="#FFFFFF").pack(pady=(20, 5))
    
    # Texto Atualizado: Apenas avisa sobre Chrome e VLC
    lbl_status = ctk.CTkLabel(setup_win, text="A transferir dependências (Chrome, VLC)...", font=("Segoe UI", 12))
    lbl_status.pack(pady=5)

    progress = ctk.CTkProgressBar(setup_win, width=350, fg_color="#333333", progress_color=COR_LINE1)
    progress.pack(pady=10)
    progress.set(0)

    def download_thread():
        temp_zip = os.path.join(tempfile.gettempdir(), "manik3_deps.zip")
        try:
            req = urllib.request.Request(DEPENDENCY_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(temp_zip, 'wb') as out_file:
                total_size = int(response.info().get('Content-Length', -1))
                downloaded = 0
                block_size = 8192
                while True:
                    buffer = response.read(block_size)
                    if not buffer: break
                    downloaded += len(buffer)
                    out_file.write(buffer)
                    if total_size > 0:
                        progress.set(min(downloaded / total_size, 1.0))

            lbl_status.configure(text="A extrair ficheiros...")
            progress.configure(mode="indeterminate", progress_color=COR_LINE2)
            progress.start()

            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(PASTA_ATUAL)

            if os.path.exists(temp_zip):
                os.remove(temp_zip)

            lbl_status.configure(text="Setup Concluído! A iniciar sistema...", text_color=COR_LINE1)
            progress.stop()

            janela.after(1000, atualizar_listas)
            janela.after(1500, setup_win.destroy)

        except Exception as e:
            lbl_status.configure(text=f"Erro de Transferência:\n{e}", text_color=COR_MUTE)
            progress.stop()
            setup_win.after(6000, setup_win.destroy)

    threading.Thread(target=download_thread, daemon=True).start()

# ==========================================
# FUNÇÕES DE ABERTURA
# ==========================================
def abrir_programa(chave, args=""):
    info = APPS_INFO.get(chave)
    if not info: return
    if os.path.exists(info["caminho"]):
        try:
            pasta_do_programa = os.path.dirname(info["caminho"])
            if "chrome" in chave:
                pasta_dados = os.path.abspath(os.path.join(pasta_do_programa, "..", "..", "Data", "profile"))
                args += f' --user-data-dir="{pasta_dados}" --no-first-run --no-default-browser-check "https://www.youtube.com"'

            subprocess.Popen(f'"{info["caminho"]}" {args}', shell=True, cwd=pasta_do_programa, 
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            janela.after(3000, atualizar_listas)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao iniciar {chave}: {e}")
    else:
        messagebox.showerror("Falta de Ficheiro", f"Não foi encontrado:\n{info['caminho']}")

# ==========================================
# MOTORES DE ÁUDIO & ROTEAMENTO
# ==========================================
def obter_processos_brutos():
    processos = set()
    try:
        resultado = subprocess.run("tasklist /V /FO CSV /NH", shell=True, capture_output=True, text=True,
                                   errors='ignore', creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
        for linha in resultado.stdout.splitlines():
            if linha.strip() and len(linha.split('","')) >= 9:
                processos.add(linha.split('","')[0].strip('"').lower())
    except:
        pass
    return processos

def obter_dispositivos():
    dispositivos = set()
    arq_temp = os.path.join(tempfile.gettempdir(), "manik3_temp_audio.csv")
    if not os.path.exists(CAMINHO_SVV): return ["⚠️ ERRO: SVV em falta!"]
    try:
        subprocess.run([CAMINHO_SVV, "/scomma", arq_temp], shell=False, creationflags=NO_WINDOW, 
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for enc in ['utf-16', 'utf-8-sig', 'utf-8', 'mbcs', 'latin-1']:
            try:
                with open(arq_temp, "r", encoding=enc) as f:
                    linhas = list(csv.reader(f))
                for linha in linhas:
                    if len(linha) >= 3:
                        l_low = [str(i).lower() for i in linha]
                        if ("device" in l_low or "dispositivo" in l_low) and (
                                "render" in l_low or "reprodução" in l_low or "saída" in l_low):
                            dispositivos.add(linha[0])
                break
            except:
                continue
    except:
        pass
    if os.path.exists(arq_temp):
        try: os.remove(arq_temp)
        except: pass
    return sorted(list(dispositivos)) if dispositivos else ["Nenhum dispositivo..."]

def processar_roteamento(alvo_app, selecao_destino, placa_a, placa_b):
    if not alvo_app or "Selecionar" in alvo_app: return True
    alvo_limpo = alvo_app.split(" ")[0].strip().lower()
    try:
        if selecao_destino == "MUTE":
            subprocess.run([CAMINHO_SVV, "/Mute", alvo_limpo], shell=False, creationflags=NO_WINDOW,
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        else:
            placa_alvo = placa_a if selecao_destino == "LINE 1" else placa_b
            if "⚠️" in placa_alvo or "Selecionar" in placa_alvo or not placa_alvo: return False
            subprocess.run([CAMINHO_SVV, "/SetAppDefault", placa_alvo.strip(), "all", alvo_limpo], shell=False,
                           creationflags=NO_WINDOW, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([CAMINHO_SVV, "/Unmute", alvo_limpo], shell=False, creationflags=NO_WINDOW,
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except:
        return False

def verificar_alteracoes(*args):
    mudou = (
            not current_config["applied"] or
            state_ch1.get() != current_config["ch1"] or
            state_ch2.get() != current_config["ch2"] or
            state_ch3.get() != current_config["ch3"] or
            state_ch4.get() != current_config["ch4"] or
            combo_app3.get() != current_config["app3"] or
            combo_app4.get() != current_config["app4"] or
            var_line1.get() != current_config["line1"] or
            var_line2.get() != current_config["line2"]
    )
    try:
        if mudou:
            btn_aplicar.configure(state="normal", text="▶ APPLY MIX", fg_color=COR_MUTE, text_color="#FFFFFF")
        else:
            btn_aplicar.configure(state="disabled", text="✅ MIX ATIVO", fg_color=COR_LINE1, text_color_disabled="#000000")
    except NameError:
        pass 

def atualizar_displays_ao_vivo():
    l1_apps = []
    l2_apps = []

    if current_config["applied"]:
        st1, st2, st3, st4 = current_config["ch1"], current_config["ch2"], current_config["ch3"], current_config["ch4"]

        if st1 == "LINE 1": l1_apps.append("CH 1: YouTube 1")
        elif st1 == "LINE 2": l2_apps.append("CH 1: YouTube 1")

        if st2 == "LINE 1": l1_apps.append("CH 2: YouTube 2")
        elif st2 == "LINE 2": l2_apps.append("CH 2: YouTube 2")

        app3 = current_config["app3"].replace(".exe", "")
        if "Selecionar" not in app3 and app3:
            if st3 == "LINE 1": l1_apps.append(f"CH 3: {app3}")
            elif st3 == "LINE 2": l2_apps.append(f"CH 3: {app3}")

        app4 = current_config["app4"].replace(".exe", "")
        if "Selecionar" not in app4 and app4:
            if st4 == "LINE 1": l1_apps.append(f"CH 4: {app4}")
            elif st4 == "LINE 2": l2_apps.append(f"CH 4: {app4}")

    lbl_display_line1.configure(text="\n".join(l1_apps) if l1_apps else "--- SILÊNCIO ---")
    lbl_display_line2.configure(text="\n".join(l2_apps) if l2_apps else "--- SILÊNCIO ---")

def aplicar_configuracoes():
    placa_a, placa_b = var_line1.get(), var_line2.get()

    if "Selecionar" in placa_a or "Selecionar" in placa_b or not placa_a or not placa_b:
        return messagebox.showwarning("Atenção", "Abre o '⚙️ SETUP' e define as placas para o LINE 1 e LINE 2!")

    st1, st2 = state_ch1.get(), state_ch2.get()

    if st1 != "MUTE" and st1 == st2:
        messagebox.showwarning(
            "Colisão de Áudio 🚫",
            "O Chrome 1 e o Chrome 2 estão a tentar usar o mesmo canal!\n\n"
            "Os botões foram revertidos para a última posição segura."
        )
        if "ch1" in update_funcs: update_funcs["ch1"](current_config.get("ch1", "LINE 1"))
        if "ch2" in update_funcs: update_funcs["ch2"](current_config.get("ch2", "LINE 2"))
        return

    s1 = processar_roteamento("chrome1.exe", st1, placa_a, placa_b)
    s2 = processar_roteamento("chrome2.exe", st2, placa_a, placa_b)
    s3 = processar_roteamento(combo_app3.get(), state_ch3.get(), placa_a, placa_b)
    s4 = processar_roteamento(combo_app4.get(), state_ch4.get(), placa_a, placa_b)

    if all([s1, s2, s3, s4]):
        current_config["applied"] = True
        current_config["ch1"], current_config["ch2"] = st1, st2
        current_config["ch3"], current_config["ch4"] = state_ch3.get(), state_ch4.get()
        current_config["app3"], current_config["app4"] = combo_app3.get(), combo_app4.get()
        current_config["line1"], current_config["line2"] = placa_a, placa_b

        atualizar_displays_ao_vivo()
        verificar_alteracoes()
    else:
        messagebox.showerror("Erro", "Falha ao aplicar a matriz. Verifica as placas e o SVV.")

def atualizar_listas():
    procs = obter_processos_brutos()
    l_ch3 = [p for p in procs if p in APPS_CH3]
    l_ch4 = [p for p in procs if p in APPS_CH4]

    v_ch3 = combo_app3.get()
    combo_app3.configure(values=l_ch3 if l_ch3 else ["Nenhuma Media detetada"])
    combo_app3.set(v_ch3 if v_ch3 in l_ch3 else ("Selecionar Media..." if not l_ch3 else l_ch3[0]))

    v_ch4 = combo_app4.get()
    combo_app4.configure(values=l_ch4 if l_ch4 else ["Nenhuma Extra detetada"])
    combo_app4.set(v_ch4 if v_ch4 in l_ch4 else ("Selecionar Extra..." if not l_ch4 else l_ch4[0]))
    verificar_alteracoes()

# ==========================================
# BUILDER DE BOTÕES DE ROTEAMENTO
# ==========================================
def criar_bloco_roteamento(parent, var_state, default_state, block_id):
    frame = ctk.CTkFrame(parent, fg_color="transparent")

    largura_btn = 75
    altura_btn = 35
    fonte_btn = ("Segoe UI", 12, "bold")

    btn_l1 = ctk.CTkButton(frame, text="LINE 1", font=fonte_btn, width=largura_btn, height=altura_btn, corner_radius=6)
    btn_m = ctk.CTkButton(frame, text="MUTE", font=fonte_btn, width=largura_btn, height=altura_btn, corner_radius=6)
    btn_l2 = ctk.CTkButton(frame, text="LINE 2", font=fonte_btn, width=largura_btn, height=altura_btn, corner_radius=6)

    btn_l1.pack(side="left", padx=2)
    btn_m.pack(side="left", padx=2)
    btn_l2.pack(side="left", padx=2)

    def atualizar_cores(estado_atual):
        var_state.set(estado_atual)
        cor_inativo = "#333333"
        hover_inativo = "#444444"
        texto_inativo = "#AAAAAA"

        btn_l1.configure(fg_color=cor_inativo, text_color=texto_inativo, hover_color=hover_inativo)
        btn_m.configure(fg_color=cor_inativo, text_color=texto_inativo, hover_color=hover_inativo)
        btn_l2.configure(fg_color=cor_inativo, text_color=texto_inativo, hover_color=hover_inativo)

        if estado_atual == "LINE 1":
            btn_l1.configure(fg_color=COR_LINE1, text_color="#000000", hover_color="#179141")
        elif estado_atual == "LINE 2":
            btn_l2.configure(fg_color=COR_LINE2, text_color="#000000", hover_color="#00A8CC")
        elif estado_atual == "MUTE":
            btn_m.configure(fg_color=COR_MUTE, text_color="#FFFFFF", hover_color="#B0123C")

        verificar_alteracoes()

    btn_l1.configure(command=lambda: atualizar_cores("LINE 1"))
    btn_m.configure(command=lambda: atualizar_cores("MUTE"))
    btn_l2.configure(command=lambda: atualizar_cores("LINE 2"))

    update_funcs[block_id] = atualizar_cores
    atualizar_cores(default_state)
    return frame

# ==========================================
# SUB-MENU DE CONFIGURAÇÃO (POP-UP)
# ==========================================
janela_config = None

def abrir_configuracoes():
    global janela_config
    if janela_config is None or not janela_config.winfo_exists():
        janela_config = ctk.CTkToplevel(janela)
        janela_config.title("⚙️ Setup de Hardware")
        janela_config.geometry("450x260")
        janela_config.resizable(False, False)
        janela_config.configure(fg_color="#1A1A1A")
        janela_config.attributes("-topmost", True)

        ctk.CTkLabel(janela_config, text="ROTEAMENTO FÍSICO", font=("Impact", 24), text_color="#FFFFFF").pack(
            pady=(15, 10))

        l_disp = obter_dispositivos()

        ctk.CTkLabel(janela_config, text="Mesa LINE 1 (ex: Speaker):", font=("Segoe UI", 12, "bold"),
                     text_color=COR_LINE1).pack(anchor="w", padx=20)
        combo_a = ctk.CTkComboBox(janela_config, variable=var_line1, values=l_disp, width=410, height=30,
                                  command=lambda _: verificar_alteracoes())
        combo_a.pack(pady=(0, 10), padx=20)

        ctk.CTkLabel(janela_config, text="Mesa LINE 2 (ex: USB Speaker):", font=("Segoe UI", 12, "bold"),
                     text_color=COR_LINE2).pack(anchor="w", padx=20)
        combo_b = ctk.CTkComboBox(janela_config, variable=var_line2, values=l_disp, width=410, height=30,
                                  command=lambda _: verificar_alteracoes())
        combo_b.pack(pady=(0, 15), padx=20)

        ctk.CTkButton(janela_config, text="Guardar & Fechar", font=("Segoe UI", 12, "bold"), fg_color="#333333",
                      hover_color="#555555", command=janela_config.destroy).pack(pady=5)
    else:
        janela_config.focus()

def ao_fechar():
    janela.withdraw()
    janela.quit()

# ==========================================
# DESENHO DA INTERFACE GRÁFICA PRINCIPAL
# ==========================================

janela = ctk.CTk()
janela.title("MANIK3 VIRTUAL DJ")
janela.geometry("560x900")
janela.resizable(False, False)
janela.configure(fg_color=COR_FUNDO_APP)
janela.protocol("WM_DELETE_WINDOW", ao_fechar)

# Variáveis Globais
var_line1 = ctk.StringVar(value="Selecionar placa de som...")
var_line2 = ctk.StringVar(value="Selecionar placa de som...")

state_ch1 = ctk.StringVar()
state_ch2 = ctk.StringVar()
state_ch3 = ctk.StringVar()
state_ch4 = ctk.StringVar()

# --- CABEÇALHO ---
frame_header = ctk.CTkFrame(janela, fg_color="transparent")
frame_header.pack(pady=(25, 15), fill="x")

ctk.CTkLabel(frame_header, text="DJ MANIK3", font=("Impact", 46), text_color="#FFFFFF").pack(anchor="center")
ctk.CTkLabel(frame_header, text="V I R T U A L   D J   M I X E R", font=("Segoe UI", 14, "bold"),
             text_color="#AAAAAA").pack(anchor="center", pady=(0, 15))

slogan = '"So as you struggle to catch the rhythm, \nask yourself, \ncan you dance to MANIQUE, \nto my beat"'
ctk.CTkLabel(frame_header, text=slogan, font=("Segoe UI", 12, "italic", "bold"), text_color="#666666",
             justify="center").pack(anchor="center")

# --- LAUNCHPAD ---
frame_launch = ctk.CTkFrame(janela, fg_color="transparent")
frame_launch.pack(pady=(5, 15), padx=20)
style_launch = {"font": ("Segoe UI", 12, "bold"), "fg_color": COR_BTN_LAUNCH, "hover_color": "#3A3A3A", "height": 38,
                "width": 120}

ctk.CTkButton(frame_launch, text="🌐 CH1", command=lambda: abrir_programa("chrome1"), **style_launch).grid(row=0, column=0, padx=5, pady=5)
ctk.CTkButton(frame_launch, text="🌐 CH2", command=lambda: abrir_programa("chrome2"), **style_launch).grid(row=0, column=1, padx=5, pady=5)
ctk.CTkButton(frame_launch, text="▶ VLC", command=lambda: abrir_programa("vlc"), **style_launch).grid(row=0, column=2, padx=5, pady=5)
ctk.CTkButton(frame_launch, text="⚙️ SETUP", text_color="#FFFFFF", fg_color=COR_MUTE, hover_color="#B0123C",
              font=("Segoe UI", 12, "bold"), height=38, width=120, command=abrir_configuracoes).grid(row=0, column=3, padx=5, pady=5)

# --- MATRIZ DOS CANAIS ---
frame_matrix = ctk.CTkFrame(janela, fg_color="transparent")
frame_matrix.pack(padx=20, fill="x")

frame_ch1 = ctk.CTkFrame(frame_matrix, fg_color=COR_FUNDO_FRAME, corner_radius=8)
frame_ch1.pack(pady=(0, 15), fill="x")
frame_ch1.grid_columnconfigure(0, weight=1)
ctk.CTkLabel(frame_ch1, text="■ CH 1: YouTube (chrome1)", font=("Impact", 18), text_color="#FFFFFF").grid(row=0, column=0, padx=15, pady=25, sticky="w")
btns_ch1 = criar_bloco_roteamento(frame_ch1, state_ch1, "LINE 1", "ch1")
btns_ch1.grid(row=0, column=1, padx=15, pady=25, sticky="e")

frame_ch2 = ctk.CTkFrame(frame_matrix, fg_color=COR_FUNDO_FRAME, corner_radius=8)
frame_ch2.pack(pady=(0, 15), fill="x")
frame_ch2.grid_columnconfigure(0, weight=1)
ctk.CTkLabel(frame_ch2, text="■ CH 2: YouTube (chrome2)", font=("Impact", 18), text_color="#FFFFFF").grid(row=0, column=0, padx=15, pady=25, sticky="w")
btns_ch2 = criar_bloco_roteamento(frame_ch2, state_ch2, "LINE 2", "ch2")
btns_ch2.grid(row=0, column=1, padx=15, pady=25, sticky="e")

frame_ch3 = ctk.CTkFrame(frame_matrix, fg_color=COR_FUNDO_FRAME, corner_radius=8)
frame_ch3.pack(pady=(0, 15), fill="x")
frame_ch3.grid_columnconfigure(0, weight=1)
ctk.CTkLabel(frame_ch3, text="■ CH 3: Media Players (VLC, Spotify)", font=("Impact", 18), text_color="#FFFFFF").grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5), sticky="w")
combo_app3 = ctk.CTkComboBox(frame_ch3, width=260, height=35, font=("Segoe UI", 12), command=lambda _: verificar_alteracoes())
combo_app3.grid(row=1, column=0, padx=15, pady=(0, 20), sticky="w")
btns_ch3 = criar_bloco_roteamento(frame_ch3, state_ch3, "MUTE", "ch3")
btns_ch3.grid(row=1, column=1, padx=15, pady=(0, 20), sticky="e")

frame_ch4 = ctk.CTkFrame(frame_matrix, fg_color=COR_FUNDO_FRAME, corner_radius=8)
frame_ch4.pack(pady=(0, 10), fill="x")
frame_ch4.grid_columnconfigure(0, weight=1)
ctk.CTkLabel(frame_ch4, text="■ CH 4: Extras / Karaoke", font=("Impact", 18), text_color="#FFFFFF").grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 5), sticky="w")
combo_app4 = ctk.CTkComboBox(frame_ch4, width=260, height=35, font=("Segoe UI", 12), command=lambda _: verificar_alteracoes())
combo_app4.grid(row=1, column=0, padx=15, pady=(0, 20), sticky="w")
btns_ch4 = criar_bloco_roteamento(frame_ch4, state_ch4, "MUTE", "ch4")
btns_ch4.grid(row=1, column=1, padx=15, pady=(0, 20), sticky="e")

# --- PAINÉIS DE MONITORIZAÇÃO AO VIVO ---
frame_displays = ctk.CTkFrame(janela, fg_color="transparent")
frame_displays.pack(padx=20, pady=(5, 10), fill="x")
frame_displays.grid_columnconfigure(0, weight=1)
frame_displays.grid_columnconfigure(1, weight=1)

frame_disp_l1 = ctk.CTkFrame(frame_displays, fg_color="#1A1A1A", border_width=2, border_color=COR_LINE1, corner_radius=10)
frame_disp_l1.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
ctk.CTkLabel(frame_disp_l1, text="🔴 LIVE ON LINE 1", font=("Impact", 16), text_color=COR_LINE1).pack(pady=(10, 5))
lbl_display_line1 = ctk.CTkLabel(frame_disp_l1, text="---", font=("Segoe UI", 12, "bold"), text_color="#FFFFFF", justify="center")
lbl_display_line1.pack(pady=(5, 15), padx=10)

frame_disp_l2 = ctk.CTkFrame(frame_displays, fg_color="#1A1A1A", border_width=2, border_color=COR_LINE2, corner_radius=10)
frame_disp_l2.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
ctk.CTkLabel(frame_disp_l2, text="🔴 LIVE ON LINE 2", font=("Impact", 16), text_color=COR_LINE2).pack(pady=(10, 5))
lbl_display_line2 = ctk.CTkLabel(frame_disp_l2, text="---", font=("Segoe UI", 12, "bold"), text_color="#FFFFFF", justify="center")
lbl_display_line2.pack(pady=(5, 15), padx=10)

# --- BOTÕES DE AÇÃO INFERIORES ---
frame_botoes = ctk.CTkFrame(janela, fg_color="transparent")
frame_botoes.pack(pady=(5, 20), side="bottom")

btn_atualizar = ctk.CTkButton(frame_botoes, text="⟳ RESCAN", font=("Segoe UI", 14, "bold"), fg_color="#333333",
                              hover_color="#555555", text_color="#FFFFFF", width=140, height=45, command=atualizar_listas)
btn_atualizar.pack(side="left", padx=10)

btn_aplicar = ctk.CTkButton(frame_botoes, text="▶ APPLY MIX", font=("Segoe UI", 16, "bold"), fg_color=COR_MUTE,
                            hover_color="#B0123C", text_color="#FFFFFF", width=250, height=45, command=aplicar_configuracoes)
btn_aplicar.pack(side="left", padx=10)

# ==========================================
# GATILHO DE ARRANQUE & AUTO-SETUP
# ==========================================
# Se a pasta apps não existir, avança com auto-setup das apps pesadas
if not os.path.exists(PASTA_APPS):
    janela.after(500, iniciar_auto_setup)
else:
    # Se já existir as apps mas faltar o SVV, dá apenas um aviso porque ele deveria vir com o EXE
    if not os.path.exists(CAMINHO_SVV):
        messagebox.showwarning("Aviso de Sistema", "SoundVolumeView.exe não foi encontrado na pasta principal!\nO roteamento de áudio não vai funcionar. Por favor, garante que ele está ao lado do ficheiro EXE.")
    janela.after(100, atualizar_listas)

janela.after(200, atualizar_displays_ao_vivo)
janela.mainloop()
