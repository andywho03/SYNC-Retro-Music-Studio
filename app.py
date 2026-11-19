import customtkinter as ctk
from PIL import Image
import subprocess
import threading
import requests
import ctypes
import random
import json
import io
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

app = ctk.CTk()
app.title("SYNC - Retro Music Studio")
app.geometry("1150x690")

MERINO = "#F5EEDD"
ROCK_BLUE = "#84B3CE"
VENICE_BLUE = "#16587B"

app.configure(fg_color=ROCK_BLUE)

reproduciendo = False
archivo_actual = None
mensaje_vacio = None
imagenes_memoria = []

def mci_comando(cmd):
    ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)
def mci_comando(cmd):
    buffer = ctypes.create_unicode_buffer(255)
    ctypes.windll.winmm.mciSendStringW(cmd, buffer, 254, None)
    return buffer.value

def actualizar_barra_tiempo():
    if reproduciendo and archivo_actual:
        try:
            largo_str = mci_comando("status musica length")
            pos_str = mci_comando("status musica position")
            if largo_str.isdigit() and pos_str.isdigit():
                largo = int(largo_str)
                pos = int(pos_str)
                if largo > 1000:
                    progreso = pos / largo
                    barra_tiempo.set(min(progreso, 1.0))
                    # Si la canción terminó sola, reinicia el botón a Play
                    if pos >= largo:
                        if modo_repetir:
                            mci_comando("seek musica to start")
                            mci_comando("play musica")
                            barra_tiempo.set(0.0)
                        else:
                            cambiar_pista(1)

        except Exception:
            pass
    app.after(500, actualizar_barra_tiempo)

def reproducir_archivo(ruta_mp3, titulo, fuente, img_caratula=None):
    global reproduciendo, archivo_actual
    if os.path.exists(ruta_mp3):
        mci_comando("close musica")
        ruta_abs = os.path.abspath(ruta_mp3)
        mci_comando(f'open "{ruta_abs}" type mpegvideo alias musica')
        mci_comando("play musica")
        archivo_actual = ruta_abs
        reproduciendo = True
        btn_play_pausa.configure(text="❚❚")
        lbl_titulo_repro.configure(text=titulo[:40])
        lbl_artista_repro.configure(text=f"Reproduciendo • {fuente}")
        barra_tiempo.set(0.5)

        # Buscar siempre la imagen en la carpeta covers para ponerla abajo
        nombre_sin_ext = os.path.splitext(os.path.basename(ruta_mp3))[:35]
        ruta_foto = os.path.join("covers", f"{nombre_sin_ext}.png")
        if os.path.exists(ruta_foto):
            pil_b = Image.open(ruta_foto)
            img_b = ctk.CTkImage(light_image=pil_b, size=(60, 60))
            imagenes_memoria.append(img_b)
            lbl_caratula_bottom.configure(image=img_b, text="")
        elif img_caratula:
            lbl_caratula_bottom.configure(image=img_caratula, text="")

def alternar_reproduccion():
    global reproduciendo
    if not archivo_actual:
        return
    if reproduciendo:
        mci_comando("pause musica")
        reproduciendo = False
        btn_play_pausa.configure(text="▶")
    else:
        mci_comando("resume musica")
        reproduciendo = True
        btn_play_pausa.configure(text="❚❚")

menu_resultados = None
modo_aleatorio = False
modo_repetir = False

def alternar_aleatorio():
    global modo_aleatorio
    modo_aleatorio = not modo_aleatorio
    btn_shuffle.configure(text_color="#38bdf8" if modo_aleatorio else MERINO)

def alternar_repetir():
    global modo_repetir
    modo_repetir = not modo_repetir
    btn_repeat.configure(text_color="#38bdf8" if modo_repetir else MERINO)

def cambiar_pista(direccion):
    mp3s = [f for f in os.listdir(os.getcwd()) if f.lower().endswith(".mp3")]
    if not mp3s:
        return

    if modo_aleatorio and len(mp3s) > 1:
        elegida = random.choice(mp3s)
    else:
        nombre_actual = os.path.basename(archivo_actual) if archivo_actual else ""
        if nombre_actual in mp3s:
            idx = mp3s.index(nombre_actual)
            nuevo_idx = (idx + direccion) % len(mp3s)
            elegida = mp3s[nuevo_idx]
        else:
            elegida = mp3s[0]

    reproducir_archivo(elegida, os.path.splitext(elegida)[0], "Local Library")

def cerrar_menu_busqueda():
    global menu_resultados
    if menu_resultados and menu_resultados.winfo_exists():
        menu_resultados.destroy()

def iniciar_descarga_directa(consulta_o_url):
    cerrar_menu_busqueda()
    caja_busqueda.delete(0, "end")
    if mensaje_vacio and mensaje_vacio.winfo_exists():
        mensaje_vacio.destroy()

    es_spotify = "spotify.com" in consulta_o_url.lower()
    fuente = "Spotify" if es_spotify else "YouTube"
    consulta = consulta_o_url

    fila = ctk.CTkFrame(lista_transferencias, height=52, corner_radius=0, fg_color=MERINO, border_width=1, border_color="#e5dec9")
    fila.pack(fill="x", pady=0)
    fila.pack_propagate(False)

    lbl_mini_cover = ctk.CTkLabel(fila, text="🎵", width=36, height=36, fg_color="#d6cfc0", corner_radius=4, text_color=VENICE_BLUE)
    lbl_mini_cover.pack(side="left", padx=(8, 4))

    lbl_archivo = ctk.CTkLabel(fila, text=f"Buscando: {consulta[:32]}...", width=260, font=("Segoe UI", 11, "bold"), text_color="#374151", anchor="w")
    lbl_archivo.pack(side="left", padx=4)

    badge_frame = ctk.CTkFrame(fila, width=95, height=40, fg_color="transparent")
    badge_frame.pack(side="left", padx=8)
    badge_frame.pack_propagate(False)
    ctk.CTkLabel(badge_frame, text=fuente, width=72, height=22, corner_radius=11,
                 fg_color=VENICE_BLUE, text_color="white", font=("Segoe UI", 10, "bold")).place(relx=0.5, rely=0.5, anchor="center")

    lbl_estado = ctk.CTkLabel(fila, text="Connecting...", width=105, font=("Segoe UI", 11), text_color="#0284c7", anchor="w")
    lbl_estado.pack(side="left", padx=8)

    prog_frame = ctk.CTkFrame(fila, width=145, height=40, fg_color="transparent")
    prog_frame.pack(side="left", padx=8)
    prog_frame.pack_propagate(False)
    barra_fila = ctk.CTkProgressBar(prog_frame, width=130, height=6, progress_color=VENICE_BLUE, fg_color="#d6cfc0")
    barra_fila.set(0.15)
    barra_fila.place(relx=0.5, rely=0.5, anchor="center")

    lbl_vel = ctk.CTkLabel(fila, text="-- KB/s", width=95, font=("Segoe UI", 11), text_color="#6b7280", anchor="w")
    lbl_vel.pack(side="left", padx=8)

    lbl_tiempo = ctk.CTkLabel(fila, text="--:--", width=95, font=("Segoe UI", 11), text_color="#6b7280", anchor="w")
    lbl_tiempo.pack(side="left", padx=8)

    btn_play_fila = ctk.CTkButton(fila, text="▶ Play", width=85, height=26, corner_radius=6,
                                  fg_color="#d6cfc0", hover_color=ROCK_BLUE, text_color="#374151",
                                  font=("Segoe UI", 10, "bold"), state="disabled")
    btn_play_fila.pack(side="left", padx=8)

    def tarea_descarga():
        try:
            img_pequena = None
            img_grande = None

            if es_spotify:
                app.after(0, lambda: lbl_archivo.configure(text="Downloading from Spotify..."))
                app.after(0, lambda: lbl_estado.configure(text="Downloading"))
                app.after(0, lambda: barra_fila.set(0.5))
                antes = set(os.listdir(os.getcwd()))
                comando = ["py", "-m", "spotdl", "download", consulta, "--bitrate", "320k", "--format", "mp3"]
                res = subprocess.run(comando, creationflags=subprocess.CREATE_NO_WINDOW)
                despues = set(os.listdir(os.getcwd()))
                nuevos = [f for f in (despues - antes) if f.endswith(".mp3")]
                ruta_final = next(iter(nuevos), "")
                titulo_real = os.path.splitext(ruta_final) if ruta_final else "Canción Spotify"
            else:
                objetivo = consulta if consulta.startswith("http") else f"ytsearch1:{consulta}"
                info_proc = subprocess.run(
                    ["yt-dlp", objetivo, "--dump-json", "--no-playlist"],
                    capture_output=True, text=True, encoding="utf-8",
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                lineas_json = info_proc.stdout.strip().splitlines()
                datos = json.loads(next(iter(lineas_json)))
                titulo_real = datos.get("title", consulta)
                url_real = datos.get("webpage_url", objetivo)
                url_thumb = datos.get("thumbnail", "")
                dur = datos.get("duration", 0)
                mins, segs = divmod(int(dur), 60)
                duracion_str = f"{mins}:{segs:02d} min"

                if url_thumb:
                    try:
                        resp_img = requests.get(url_thumb, timeout=5)
                        pil_img = Image.open(io.BytesIO(resp_img.content))
                        os.makedirs("covers", exist_ok=True)
                        ruta_cover = os.path.join("covers", f"{titulo_real[:35]}.png")
                        pil_img.save(ruta_cover)
                        img_pequena = ctk.CTkImage(light_image=pil_img, size=(36, 36))
                        img_grande = ctk.CTkImage(light_image=pil_img, size=(60, 60))
                        imagenes_memoria.extend([img_pequena, img_grande])
                        app.after(0, lambda: lbl_mini_cover.configure(image=img_pequena, text=""))
                    except Exception:
                        pass

                app.after(0, lambda: lbl_archivo.configure(text=f"{titulo_real[:35]}.mp3"))
                app.after(0, lambda: lbl_estado.configure(text="Downloading"))
                app.after(0, lambda: lbl_tiempo.configure(text=duracion_str))
                app.after(0, lambda: lbl_vel.configure(text="320 KB/s"))
                app.after(0, lambda: barra_fila.set(0.6))

                antes = set(os.listdir(os.getcwd()))
                comando = [
                    "yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
                    "--no-playlist", "--postprocessor-args", "-ar 44100 -b:a 320k",
                    "-o", "%(title)s.%(ext)s", url_real
                ]
                res = subprocess.run(comando, creationflags=subprocess.CREATE_NO_WINDOW)
                despues = set(os.listdir(os.getcwd()))
                nuevos = [f for f in (despues - antes) if f.endswith(".mp3")]
                ruta_final = next(iter(nuevos), "")

            if res.returncode == 0 and ruta_final:
                app.after(0, lambda: barra_fila.set(1.0))
                app.after(0, lambda: lbl_estado.configure(text="Completed", text_color="#15803d"))
                app.after(0, lambda: lbl_vel.configure(text="Listo"))
                app.after(0, lambda: btn_play_fila.configure(
                    state="normal", fg_color=VENICE_BLUE, text_color="white",
                    command=lambda r=ruta_final, t=titulo_real, f=fuente, ig=img_grande: reproducir_archivo(r, t, f, ig)
                ))
                if not reproduciendo:
                    app.after(0, lambda: reproducir_archivo(ruta_final, titulo_real, fuente, img_grande))
            else:
                app.after(0, lambda: lbl_estado.configure(text="Error", text_color="#dc2626"))
        except Exception:
            app.after(0, lambda: lbl_estado.configure(text="Error de red", text_color="#dc2626"))

    threading.Thread(target=tarea_descarga, daemon=True).start()

# --- 1. BARRA SUPERIOR ---
barra_superior = ctk.CTkFrame(app, fg_color=ROCK_BLUE, height=90, corner_radius=0)
barra_superior.pack(side="top", fill="x")
barra_superior.pack_propagate(False)

barra_nav = ctk.CTkFrame(barra_superior, fg_color="transparent", height=38)
barra_nav.pack(fill="x", padx=15, pady=(6, 2))

if os.path.exists("assets/logo_sync.png"):
    img_logo = ctk.CTkImage(light_image=Image.open("assets/logo_sync.png"), size=(115, 28))
    ctk.CTkLabel(barra_nav, image=img_logo, text="").pack(side="left", padx=(0, 20))
else:
    ctk.CTkLabel(barra_nav, text="SYNC", font=("Segoe UI", 22, "bold"), text_color=VENICE_BLUE).pack(side="left", padx=(0, 20))
botones_pestanas = {}
descargas_activas = []  # Guarda el historial de descargas de esta sesión

def cambiar_pestana(nombre_sel):
    # 1. Iluminar la pestaña seleccionada en Venice Blue y apagar las demás
    for nom, boton in botones_pestanas.items():
        activo = (nom == nombre_sel)
        boton.configure(
            fg_color=VENICE_BLUE if activo else "transparent",
            text_color="white" if activo else "#0f293a"
        )
    
    # 2. Ejecutar la acción correspondiente a cada pestaña
    if nombre_sel == "Library":
        # Muestra todas las canciones MP3 guardadas en tu carpeta
        for w in lista_transferencias.winfo_children():
            w.destroy()
        cargar_biblioteca_local()

    elif nombre_sel == "Search":
        # Enfoca el buscador superior y selecciona el texto para escribir rápido
        caja_busqueda.focus()
        caja_busqueda.select_range(0, "end")

    elif nombre_sel == "Player":
        # Pausa o reanuda la canción actual; si no hay ninguna sonando, reproduce la primera de tu carpeta
        if archivo_actual:
            alternar_reproduccion()
        else:
            mp3s = [f for f in os.listdir(os.getcwd()) if f.lower().endswith(".mp3")]
            if mp3s:
                primer_mp3 = mp3s[0]
                reproducir_archivo(primer_mp3, os.path.splitext(primer_mp3)[0], "Biblioteca Local")

    elif nombre_sel == "Transfers":
        # Muestra el aviso o lista de descargas activas de la sesión
        for w in lista_transferencias.winfo_children():
            w.destroy()
        lbl_info_tr = ctk.CTkLabel(
            lista_transferencias,
            text="No active transfers. Type a song name above to download or click 'Library' to view your music.",
            font=("Segoe UI", 12), text_color="#78716c"
        )
        lbl_info_tr.pack(pady=80)

for nombre in ["Library", "Player", "Search", "Transfers"]:
    es_activa = (nombre == "Library")
    btn_tab = ctk.CTkButton(
        barra_nav, text=nombre, width=85, height=28, corner_radius=14,
        fg_color=VENICE_BLUE if es_activa else "transparent",
        text_color="white" if es_activa else "#0f293a",
        hover_color="#236b91", font=("Segoe UI", 12, "bold"),
        command=lambda n=nombre: cambiar_pestana(n)
    )
    btn_tab.pack(side="left", padx=5)
    botones_pestanas[nombre] = btn_tab
def procesar_busqueda(event=None):
    texto = caja_busqueda.get().strip()
    if not texto:
        return

    # Si es un enlace directo (YouTube o Spotify), descargar al instante
    if texto.startswith("http"):
        iniciar_descarga_directa(texto)
        return

    # Si es texto (nombre de artista o canción), buscar 6 opciones y desplegarlas
    cerrar_menu_busqueda()
    global menu_resultados
    menu_resultados = ctk.CTkFrame(app, width=540, height=230, corner_radius=12, fg_color=MERINO, border_width=2, border_color=VENICE_BLUE)
    menu_resultados.place(x=100, y=85)
    menu_resultados.pack_propagate(False)

    lbl_cargando = ctk.CTkLabel(menu_resultados, text=f"🔍 Searching songs for '{texto}'...", font=("Segoe UI", 12, "bold"), text_color=VENICE_BLUE)
    lbl_cargando.pack(pady=80)

    def buscar_opciones():
        try:
            proc = subprocess.run(
                ["yt-dlp", f"ytsearch6:{texto}", "--dump-json", "--flat-playlist", "--no-playlist"],
                capture_output=True, text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW
            )
            lineas = proc.stdout.strip().splitlines()
            opciones = []
            for lin in lineas:
                d = json.loads(lin)
                t = d.get("title", "Unknown")
                u = d.get("url") or f"https://youtube.com{d.get('id')}"
                dur = d.get("duration")
                if dur:
                    m, s = divmod(int(dur), 60)
                    t_str = f"{m}:{s:02d}"
                else:
                    t_str = "--:--"
                opciones.append((t, u, t_str))

            def dibujar_opciones():
                if not menu_resultados or not menu_resultados.winfo_exists():
                    return
                lbl_cargando.destroy()

                # Encabezado del desplegable con botón cerrar (X)
                top_menu = ctk.CTkFrame(menu_resultados, height=28, fg_color=VENICE_BLUE, corner_radius=0)
                top_menu.pack(fill="x")
                ctk.CTkLabel(top_menu, text=f" Results for: {texto}", font=("Segoe UI", 11, "bold"), text_color="white").pack(side="left", padx=8)
                ctk.CTkButton(top_menu, text="✕", width=26, height=22, fg_color="transparent", hover_color="#dc2626", text_color="white", command=cerrar_menu_busqueda).pack(side="right", padx=4)

                scroll_ops = ctk.CTkScrollableFrame(menu_resultados, fg_color=MERINO, corner_radius=0)
                scroll_ops.pack(fill="both", expand=True, padx=2, pady=2)

                if not opciones:
                    ctk.CTkLabel(scroll_ops, text="No results found.", text_color="#6b7280").pack(pady=30)
                    return

                for tit, link, tiempo in opciones:
                    btn_op = ctk.CTkButton(
                        scroll_ops, text=f"🎵  {tit[:52]}   ({tiempo})", anchor="w",
                        height=30, corner_radius=6, fg_color="transparent",
                        hover_color=ROCK_BLUE, text_color="#1f2937", font=("Segoe UI", 11, "bold"),
                        command=lambda url_elegida=link: iniciar_descarga_directa(url_elegida)
                    )
                    btn_op.pack(fill="x", pady=1, padx=4)

            app.after(0, dibujar_opciones)
        except Exception:
            app.after(0, cerrar_menu_busqueda)

    threading.Thread(target=buscar_opciones, daemon=True).start()

barra_busqueda = ctk.CTkFrame(barra_superior, fg_color="transparent", height=38)
barra_busqueda.pack(fill="x", padx=(100, 15), pady=(2, 6))

# Contenedor redondeado color Merino que agrupa el texto y el botón circular de lupa
caja_busqueda = ctk.CTkEntry(
    barra_busqueda, placeholder_text="🔗 Search song or paste link",
    width=420, height=34, corner_radius=17, fg_color=MERINO, bg_color=ROCK_BLUE,
    border_width=0, text_color="#1f2937", font=("Segoe UI", 12)
)
caja_busqueda.pack(side="left", padx=(0, 6))
caja_busqueda.bind("<Return>", procesar_busqueda)

img_lupa = ctk.CTkImage(light_image=Image.open("assets/lupa.png"), size=(14, 14)) if os.path.exists("assets/lupa.png") else None

btn_lupa = ctk.CTkButton(
    barra_busqueda, text="" if img_lupa else "⌕", image=img_lupa,
    width=34, height=34, corner_radius=17,
    fg_color=VENICE_BLUE, bg_color=ROCK_BLUE, hover_color="#236b91", text_color="white",
    font=("Segoe UI", 16, "bold"), command=procesar_busqueda
)
btn_lupa.pack(side="left", padx=(0, 12))

botones_top = [
    ("⬇ Download", procesar_busqueda),
("📁 Folder", lambda: os.startfile(os.getcwd())),
("🗑 Clear", lambda: [w.destroy() for w in lista_transferencias.winfo_children()])
]
for texto_btn, accion_btn in botones_top:
    ctk.CTkButton(
    barra_busqueda, text=texto_btn, width=90, height=30, corner_radius=8,
    fg_color=VENICE_BLUE, hover_color="#236b91", text_color="white",
    font=("Segoe UI", 11, "bold"), command=accion_btn
    ).pack(side="left", padx=4)

    #--- 2. REPRODUCTOR INFERIOR ---
contenedor_bottom = ctk.CTkFrame(app, height=92, corner_radius=0, fg_color=MERINO)
contenedor_bottom.pack(side="bottom", fill="x")

# Fondo izquierdo Rock Blue para continuar el panel lateral sin cortes
ctk.CTkFrame(contenedor_bottom, width=100, height=92, corner_radius=0, fg_color=ROCK_BLUE).place(x=0, y=0)

# Cuerpo del reproductor en Venice Blue con esquinas superiores redondeadas
barra_bottom = ctk.CTkFrame(contenedor_bottom, height=92, corner_radius=24, fg_color=VENICE_BLUE)
barra_bottom.pack(fill="both", expand=True)

# Tapamos la esquina superior izquierda (para que sea recta) y las dos inferiores
ctk.CTkFrame(barra_bottom, width=30, height=30, corner_radius=0, fg_color=VENICE_BLUE).place(x=0, y=0)
ctk.CTkFrame(barra_bottom, width=30, height=30, corner_radius=0, fg_color=VENICE_BLUE).place(relx=0.0, rely=1.0, anchor="sw")
ctk.CTkFrame(barra_bottom, width=30, height=30, corner_radius=0, fg_color=VENICE_BLUE).place(relx=1.0, rely=1.0, anchor="se")

frame_repro = ctk.CTkFrame(barra_bottom, fg_color=VENICE_BLUE, height=74, corner_radius=0)
frame_repro.place(x=15, rely=0.5, anchor="w", relwidth=0.95)
frame_repro.pack_propagate(False)

caratula = ctk.CTkFrame(frame_repro, width=60, height=60, corner_radius=8, fg_color="#0f3c54")
caratula.pack(side="left", padx=(4, 14), pady=7)
caratula.pack_propagate(False)
lbl_caratula_bottom = ctk.CTkLabel(caratula, text="🎵", font=("Segoe UI", 24), text_color=ROCK_BLUE)
lbl_caratula_bottom.place(relx=0.5, rely=0.5, anchor="center")
info_cancion = ctk.CTkFrame(frame_repro, fg_color="transparent")
info_cancion.pack(side="left", pady=12)
lbl_titulo_repro = ctk.CTkLabel(info_cancion, text="No active playback", font=("Segoe UI", 13, "bold"), text_color="white", anchor="w")
lbl_titulo_repro.pack(fill="x")
lbl_artista_repro = ctk.CTkLabel(info_cancion, text="Download a song to listen to it here", font=("Segoe UI", 11), text_color=ROCK_BLUE, anchor="w")
lbl_artista_repro.pack(fill="x")
centro_repro = ctk.CTkFrame(frame_repro, fg_color="transparent")
centro_repro.place(relx=0.55, rely=0.5, anchor="center")
barra_tiempo = ctk.CTkProgressBar(centro_repro, width=460, height=5, progress_color=MERINO, fg_color="#3b7796")
barra_tiempo.set(0.0)
barra_tiempo.pack(pady=(2, 8))
botones_media = ctk.CTkFrame(centro_repro, fg_color="transparent")
botones_media.pack()
estilo_ctrl = {"width": 34, "height": 30, "fg_color": "transparent", "hover_color": "#236b91", "text_color": MERINO, "font": ("Segoe UI", 14, "bold")}

btn_shuffle = ctk.CTkButton(botones_media, text="🔀", command=alternar_aleatorio, **estilo_ctrl)
btn_shuffle.pack(side="left", padx=6)

ctk.CTkButton(botones_media, text="⏮", command=lambda: cambiar_pista(-1), **estilo_ctrl).pack(side="left", padx=6)

btn_play_pausa = ctk.CTkButton(
    botones_media, text="❚❚", width=36, height=36, corner_radius=18,
    fg_color=MERINO, hover_color="#e6dec8", text_color=VENICE_BLUE,
    font=("Segoe UI", 13, "bold"), command=alternar_reproduccion
)
btn_play_pausa.pack(side="left", padx=10)

ctk.CTkButton(botones_media, text="⏭", command=lambda: cambiar_pista(1), **estilo_ctrl).pack(side="left", padx=6)

btn_repeat = ctk.CTkButton(botones_media, text="🔁", command=alternar_repetir, **estilo_ctrl)
btn_repeat.pack(side="left", padx=6)

#--- 3. PANEL LATERAL IZQUIERDO ---

panel_izq = ctk.CTkFrame(app, fg_color=ROCK_BLUE, width=100, corner_radius=0, border_width=0)
panel_izq.pack(side="left", fill="y")
panel_izq.pack_propagate(False)
frame_onda = ctk.CTkFrame(panel_izq, width=78, height=56, fg_color="transparent")
frame_onda.pack(pady=(150, 25), anchor="center")
frame_onda.pack_propagate(False)

alturas_base = tuple(14 + (i % 5) * 8 for i in range(15))
barras_onda = []

for i in range(15):
    b = ctk.CTkFrame(frame_onda, width=3, height=alturas_base[i], corner_radius=2, fg_color=VENICE_BLUE)
    b.place(x=2 + i * 5, rely=0.5, anchor="w")
    barras_onda.append(b)

def animar_onda():
    for i, b in enumerate(barras_onda):
        base = alturas_base[i]
        alto_actual = max(6, min(52, base + random.randint(-12, 14))) if reproduciendo else base
        b.configure(height=alto_actual)
    app.after(90, animar_onda)

animar_onda()
# --- INDICADOR ONLINE / OFFLINE EN VIVO ---
lbl_online = ctk.CTkLabel(
    panel_izq, text="● Online", font=("Segoe UI", 11, "bold"),
    text_color="#065f46"
)
lbl_online.pack(pady=(5, 10), anchor="center")

def verificar_conexion():
    try:
        # Revisa si hay conexión real a internet de forma rápida
        requests.get("https://google.com", timeout=3)
        lbl_online.configure(text="● Online", text_color="#065f46")
    except Exception:
        lbl_online.configure(text="● Offline", text_color="#991b1b")
    app.after(15000, verificar_conexion)

threading.Thread(target=verificar_conexion, daemon=True).start()

# --- ACCIÓN BOTE DE BASURA (Limpiar lista visual) ---
def limpiar_lista_visual():
    for widget in lista_transferencias.winfo_children():
        widget.destroy()
    lbl_vacio_nuevo = ctk.CTkLabel(
        lista_transferencias,
        text="List cleared. Click 'Library' above to view your saved songs again.",
        font=("Segoe UI", 12), text_color="#78716c"
    )
    lbl_vacio_nuevo.pack(pady=80)

ctk.CTkButton(
    panel_izq, text="🗑", width=40, height=35, corner_radius=8,
    fg_color="transparent", hover_color="#73a1bd", text_color=VENICE_BLUE,
    font=("Segoe UI", 18, "bold"), command=limpiar_lista_visual
).pack(pady=4, anchor="center")

# --- ACCIÓN ENGRANE DE AJUSTES (Ventana flotante de configuración) ---
def abrir_ajustes():
    ventana_cfg = ctk.CTkToplevel(app)
    ventana_cfg.title("Ajustes - SYNC Studio")
    ventana_cfg.geometry("420x250")
    ventana_cfg.configure(fg_color=MERINO)
    ventana_cfg.resizable(False, False)
    ventana_cfg.attributes("-topmost", True)

    ctk.CTkLabel(ventana_cfg, text="⚙ CONFIGURATION", font=("Segoe UI", 15, "bold"), text_color=VENICE_BLUE).pack(pady=(18, 6))
    ctk.CTkLabel(ventana_cfg, text="Audio quality: MP3 • 44.1 kHz • 320 kbps CBR", font=("Segoe UI", 11, "bold"), text_color="#374151").pack(pady=2)
    ctk.CTkLabel(ventana_cfg, text=f"Current folder:\n{os.getcwd()}", font=("Segoe UI", 10), text_color="#6b7280", wraplength=380).pack(pady=10)

    def cambiar_carpeta():
        nueva_ruta = ctk.filedialog.askdirectory()
        if nueva_ruta:
            os.chdir(nueva_ruta)
            ventana_cfg.destroy()
            for w in lista_transferencias.winfo_children():
                w.destroy()
            cargar_biblioteca_local()

    ctk.CTkButton(
        ventana_cfg, text="📁 Change download folder", width=220, height=34, corner_radius=8,
        fg_color=VENICE_BLUE, hover_color="#236b91", text_color="white", font=("Segoe UI", 11, "bold"),
        command=cambiar_carpeta
    ).pack(pady=10)

ctk.CTkButton(
    panel_izq, text="⚙", width=40, height=35, corner_radius=8,
    fg_color="transparent", hover_color="#73a1bd", text_color=VENICE_BLUE,
    font=("Segoe UI", 18, "bold"), command=abrir_ajustes
).pack(pady=4, anchor="center")

#--- 4. ÁREA CENTRAL DE TRANSFERENCIAS ---

area_central = ctk.CTkFrame(app, corner_radius=0, border_width=0, fg_color=MERINO)
area_central.pack(side="right", fill="both", expand=True)
header_tabla = ctk.CTkFrame(area_central, height=34, corner_radius=0, fg_color=VENICE_BLUE)
header_tabla.pack(fill="x", padx=0, pady=0)
header_tabla.pack_propagate(False)
columnas = [
    ("File", 310, "w"), ("Source", 105, "center"), ("Status", 105, "center"),
    ("Progress", 150, "center"), ("Size", 95, "center"), ("Duration", 95, "center"), ("Play", 95, "center")
]

for titulo_col, ancho_col, alineacion in columnas:
    ctk.CTkLabel(
        header_tabla, text=titulo_col, width=ancho_col,
        font=("Segoe UI", 11, "bold"), text_color="white", anchor=alineacion
    ).pack(side="left", padx=6)
lista_transferencias = ctk.CTkScrollableFrame(area_central, fg_color=MERINO, corner_radius=0)
lista_transferencias.pack(fill="both", expand=True)
mensaje_vacio = ctk.CTkLabel(
lista_transferencias,
text="Type the name of a song or paste a link in the top bar and press Enter...",
font=("Segoe UI", 12), text_color="#78716c"
)
mensaje_vacio.pack(pady=80)
# --- 5. CARGAR AUTOMÁTICAMENTE LAS CANCIONES YA DESCARGADAS ---
def cargar_biblioteca_local():
    archivos_mp3 = [f for f in os.listdir(os.getcwd()) if f.lower().endswith(".mp3")]
    if not archivos_mp3:
        return

    if mensaje_vacio and mensaje_vacio.winfo_exists():
        mensaje_vacio.destroy()

    os.makedirs("covers", exist_ok=True)

    for archivo in archivos_mp3:
        titulo_limpio = os.path.splitext(archivo)
        
        fila = ctk.CTkFrame(lista_transferencias, height=52, corner_radius=0, fg_color=MERINO, border_width=1, border_color="#e5dec9")
        fila.pack(fill="x", pady=0)
        fila.pack_propagate(False)

        img_pequena = None
        img_grande = None
        posible_cover = os.path.join("covers", f"{titulo_limpio[:35]}.png")

        if os.path.exists(posible_cover):
            try:
                pil_img = Image.open(posible_cover)
                img_pequena = ctk.CTkImage(light_image=pil_img, size=(36, 36))
                img_grande = ctk.CTkImage(light_image=pil_img, size=(60, 60))
                imagenes_memoria.extend([img_pequena, img_grande])
            except Exception:
                pass

        lbl_mini_cover = ctk.CTkLabel(
            fila, text="" if img_pequena else "🎵", image=img_pequena,
            width=36, height=36, fg_color="#d6cfc0", corner_radius=4, text_color=VENICE_BLUE
        )
        lbl_mini_cover.pack(side="left", padx=(8, 4))

        ctk.CTkLabel(fila, text=archivo[:38], width=260, font=("Segoe UI", 11, "bold"), text_color="#374151", anchor="w").pack(side="left", padx=4)

        badge_frame = ctk.CTkFrame(fila, width=95, height=40, fg_color="transparent")
        badge_frame.pack(side="left", padx=8)
        badge_frame.pack_propagate(False)
        ctk.CTkLabel(badge_frame, text="Local MP3", width=72, height=22, corner_radius=11,
                     fg_color=VENICE_BLUE, text_color="white", font=("Segoe UI", 10, "bold")).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(fila, text="Completed", width=105, font=("Segoe UI", 11), text_color="#15803d", anchor="w").pack(side="left", padx=8)

        prog_frame = ctk.CTkFrame(fila, width=145, height=40, fg_color="transparent")
        prog_frame.pack(side="left", padx=8)
        prog_frame.pack_propagate(False)
        barra_fila = ctk.CTkProgressBar(prog_frame, width=130, height=6, progress_color=VENICE_BLUE, fg_color="#d6cfc0")
        barra_fila.set(1.0)
        barra_fila.place(relx=0.5, rely=0.5, anchor="center")
# Calcular peso real en MB
        peso_mb = os.path.getsize(archivo) / (1024 * 1024)
        texto_peso = f"{peso_mb:.2f} MB"

        # Leer duración real del MP3 en minutos:segundos
        alias_temp = f"temp_{hash(archivo)}"
        ruta_abs = os.path.abspath(archivo)
        mci_comando(f'open "{ruta_abs}" type mpegvideo alias {alias_temp}')
        ms_str = mci_comando(f"status {alias_temp} length")
        mci_comando(f"close {alias_temp}")
        if ms_str.isdigit() and int(ms_str) > 0:
            segs_tot = int(ms_str) // 1000
            m, s = divmod(segs_tot, 60)
            texto_duracion = f"{m}:{s:02d} min"
        else:
            texto_duracion = "MP3 320k"
        ctk.CTkLabel(fila, text=texto_peso, width=95, font=("Segoe UI", 11), text_color="#6b7280", anchor="center").pack(side="left", padx=6)
        ctk.CTkLabel(fila, text=texto_duracion, width=95, font=("Segoe UI", 11), text_color="#6b7280", anchor="center").pack(side="left", padx=6)
        btn_play_fila = ctk.CTkButton(
            fila, text="▶ Play", width=85, height=26, corner_radius=6,
            fg_color=VENICE_BLUE, hover_color="#236b91", text_color="white",
            font=("Segoe UI", 10, "bold"),
            command=lambda r=archivo, t=titulo_limpio, ig=img_grande: reproducir_archivo(r, t, "Biblioteca Local", ig)
        )
        btn_play_fila.pack(side="left", padx=8)

        # Si no tenía carátula guardada, buscarla automáticamente en segundo plano
        if not img_pequena:
            def recuperar_foto(t_limpio=titulo_limpio, r_cover=posible_cover, lbl_c=lbl_mini_cover, btn_p=btn_play_fila, arch=archivo):
                try:
                    info = subprocess.run(
                        ["yt-dlp", f"ytsearch1:{t_limpio}", "--dump-json", "--no-playlist"],
                        capture_output=True, text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    datos = json.loads(next(iter(info.stdout.strip().splitlines())))
                    url_t = datos.get("thumbnail", "")
                    if url_t:
                        resp = requests.get(url_t, timeout=5)
                        p_img = Image.open(io.BytesIO(resp.content))
                        p_img.save(r_cover)
                        im_p = ctk.CTkImage(light_image=p_img, size=(36, 36))
                        im_g = ctk.CTkImage(light_image=p_img, size=(60, 60))
                        imagenes_memoria.extend([im_p, im_g])
                        app.after(0, lambda: lbl_c.configure(image=im_p, text=""))
                        app.after(0, lambda: btn_p.configure(command=lambda: reproducir_archivo(arch, t_limpio, "Biblioteca Local", im_g)))
                except Exception:
                    pass
            threading.Thread(target=recuperar_foto, daemon=True).start()

actualizar_barra_tiempo()
cargar_biblioteca_local()
app.update_idletasks()

app.mainloop()