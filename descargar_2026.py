import os, time, random, subprocess, sys, re, urllib.request, json, zipfile

# ── Colores ANSI ──────────────────────────────────────────────
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def p(color, texto):
    """Imprime con color ANSI, con fallback seguro si la consola no lo soporta."""
    try:
        print(f"{color}{texto}{RESET}")
    except:
        print(texto)

# ─────────────────────────────────────────────────────────────

def descargar_con_progreso(url, path, descripcion):
    """Descarga un archivo mostrando una barra de progreso en consola."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            total_size = int(response.info().get('Content-Length', 0))
            block_size = 1024 * 8
            downloaded = 0
            with open(path, 'wb') as f:
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    f.write(buffer)
                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        bar = ('#' * (percent // 2)).ljust(50)
                        try:
                            print(f"\r{CYAN}{descripcion}{RESET}: [{GREEN}{bar}{RESET}] {percent}% ({downloaded//1024} KB)", end='', flush=True)
                        except:
                            print(f"\r{descripcion}: [{bar}] {percent}% ({downloaded//1024} KB)", end='', flush=True)
            print("\n")
        return True
    except Exception as e:
        p(RED, f"\n[ERROR] Durante la descarga: {e}")
        return False

def buscar_ffmpeg_universal():
    """Busca FFmpeg en todas las unidades del sistema con profundidad limitada."""
    import string
    p(CYAN, "[INFO] Buscando FFmpeg en el sistema (esto puede tardar unos segundos)...")
    drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
    for drive in drives:
        try:
            if os.path.exists(os.path.join(drive, 'ffmpeg.exe')):
                return os.path.join(drive, 'ffmpeg.exe')
            with os.scandir(drive) as it:
                for entry in it:
                    if entry.is_dir() and 'ffmpeg' in entry.name.lower():
                        p_root = os.path.join(entry.path, 'ffmpeg.exe')
                        p_bin  = os.path.join(entry.path, 'bin', 'ffmpeg.exe')
                        if os.path.exists(p_root): return p_root
                        if os.path.exists(p_bin):  return p_bin
        except:
            continue
    return None

def obtener_internal_dir():
    """Obtiene la ruta en AppData/Local para guardar binarios y config de forma discreta."""
    path = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'YT_Music_Pro_Data')
    os.makedirs(path, exist_ok=True)
    return path

def cargar_config():
    config_path = os.path.join(obtener_internal_dir(), 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except: pass
    return {}

def guardar_config(data):
    internal_dir = obtener_internal_dir()
    config_path = os.path.join(internal_dir, 'config.json')
    try:
        with open(config_path, 'w') as f:
            json.dump(data, f)
    except: pass

def asegurar_ffmpeg():
    """Verifica si FFmpeg existe; busca universalmente antes de descargar."""
    internal_dir = obtener_internal_dir()

    config = cargar_config()
    ffmpeg_path = config.get('ffmpeg_path')

    if ffmpeg_path and os.path.exists(ffmpeg_path):
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        if ffmpeg_dir not in os.environ['PATH']:
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ['PATH']
        return True

    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except: pass

    local_ffmpeg = os.path.join(internal_dir, 'ffmpeg.exe')
    if os.path.exists(local_ffmpeg):
        os.environ['PATH'] = internal_dir + os.pathsep + os.environ['PATH']
        return True

    path_encontrado = buscar_ffmpeg_universal()
    if path_encontrado:
        p(GREEN, f"[OK] FFmpeg encontrado en: {path_encontrado}")
        config['ffmpeg_path'] = path_encontrado
        guardar_config(config)
        ffmpeg_dir = os.path.dirname(path_encontrado)
        os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ['PATH']
        return True

    p(YELLOW, "[INFO] No se encontro FFmpeg en ningun lado. Iniciando descarga...")
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = os.path.join(internal_dir, 'ffmpeg.zip')

    if descargar_con_progreso(url, zip_path, "Descargando FFmpeg"):
        try:
            p(CYAN, "[INFO] Extrayendo...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith('ffmpeg.exe') or file.endswith('ffprobe.exe'):
                        filename = os.path.basename(file)
                        with zip_ref.open(file) as source, open(os.path.join(internal_dir, filename), 'wb') as target:
                            target.write(source.read())
            os.remove(zip_path)
            config['ffmpeg_path'] = os.path.join(internal_dir, 'ffmpeg.exe')
            guardar_config(config)
            os.environ['PATH'] = internal_dir + os.pathsep + os.environ['PATH']
            p(GREEN, "[OK] FFmpeg configurado correctamente.")
            return True
        except Exception as e:
            p(RED, f"[ERROR] No se pudo extraer FFmpeg: {e}")
    return False

def actualizar_ytdlp_portable():
    """Descarga la ultima version de yt-dlp desde GitHub si es necesario."""
    try:
        internal_dir = obtener_internal_dir()
        update_file = os.path.join(internal_dir, 'yt-dlp.zip')

        p(CYAN, "[INFO] Comprobando actualizaciones de motor...")

        api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(api_url, headers=headers)

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            latest_version = data['tag_name']

            config = cargar_config()
            current_version = config.get('ytdlp_version', '')

            if current_version == latest_version and os.path.exists(update_file):
                p(GREEN, f"[OK] Motor al dia (version {latest_version}).")
                sys.path.insert(0, update_file)
                return

            download_url = next((asset['browser_download_url'] for asset in data['assets'] if asset['name'] == 'yt-dlp'), None)

            if download_url:
                if descargar_con_progreso(download_url, update_file, f"Actualizando motor a {latest_version}"):
                    config['ytdlp_version'] = latest_version
                    guardar_config(config)

        if os.path.exists(update_file):
            sys.path.insert(0, update_file)

    except Exception as e:
        p(YELLOW, f"[WARN] No se pudo comprobar actualizaciones: {e}")
        update_file = os.path.join(obtener_internal_dir(), 'yt-dlp.zip')
        if os.path.exists(update_file):
            sys.path.insert(0, update_file)

import yt_dlp
from ytmusicapi import YTMusic

DEFAULT_FOLDER = 'C:/DescargadorMusica/Descargas'

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def obtener_ruta_sistema(nombre):
    """Obtiene la ruta real de carpetas de sistema, considerando OneDrive."""
    try:
        home = os.path.expanduser("~")
        standard = os.path.join(home, nombre)
        onedrive = os.path.join(home, "OneDrive", nombre)
        
        if os.path.exists(onedrive):
            return onedrive
        return standard
    except:
        return "." # Fallback a ruta actual si falla todo

def elegir_carpeta():
    """Muestra carpetas recomendadas y permite elegir o escribir una ruta."""
    config = cargar_config()
    ultima = config.get('ultima_carpeta_musica', DEFAULT_FOLDER)

    recomendaciones = [
        ("Escritorio",    obtener_ruta_sistema("Desktop")),
        ("Descargas",     obtener_ruta_sistema("Downloads")),
        ("Documentos",    obtener_ruta_sistema("Documents")),
        ("Musica",        obtener_ruta_sistema("Music")),
        ("Ultima usada",  ultima),
    ]

    print("")
    p(CYAN,  "=" * 60)
    p(BOLD,  "   CARPETA DE DESTINO")
    p(CYAN,  "=" * 60)
    for i, (nombre, ruta) in enumerate(recomendaciones, 1):
        print(f"  {BOLD}{i}.{RESET} {nombre:<14} {YELLOW}{ruta}{RESET}")
    print(f"  {BOLD}{len(recomendaciones)+1}.{RESET} Escribir ruta personalizada")
    print("")

    try:
        sel = input("  >> Opcion (ENTER = ultima usada): ").strip()
    except:
        sel = ""

    if sel.isdigit():
        idx = int(sel) - 1
        if 0 <= idx < len(recomendaciones):
            carpeta = recomendaciones[idx][1]
        else:
            # Opcion "personalizada"
            try:
                carpeta = input("  >> Ruta: ").strip() or ultima
            except:
                carpeta = ultima
    elif sel == "":
        carpeta = ultima
    else:
        # Escribio una ruta directamente
        carpeta = sel

    config['ultima_carpeta_musica'] = carpeta
    guardar_config(config)
    os.makedirs(carpeta, exist_ok=True)
    p(GREEN, f"  [OK] Guardando en: {carpeta}")
    print("")
    return carpeta

def extraer_id_limpio(entrada):
    if "v=" in entrada:
        return entrada.split("v=")[1].split("&")[0]
    if "list=" in entrada:
        return entrada.split("list=")[1].split("&")[0]
    if "watch?v=" in entrada:
        return entrada.split("watch?v=")[1].split("&")[0]
    return entrada.strip()

def generar_ruta_segura(base_path, nombre_sugerido):
    clean_name = "".join([c for c in nombre_sugerido if c.isalnum() or c in (' ', '-', '_')]).strip()
    if not clean_name: clean_name = "Playlist"
    i = 1
    final_name = clean_name
    while True:
        full_path = os.path.join(base_path, "Playlists", final_name)
        if not os.path.exists(full_path): return full_path
        final_name = f"{clean_name} ({i})"; i += 1

def ejecutar_descarga():
    limpiar_pantalla()
    p(CYAN, "=" * 60)
    p(BOLD, "   YT MUSIC PRO")
    p(CYAN, "=" * 60)

    # Elegir carpeta ANTES de pedir la URL (vale para toda la playlist)
    base_folder = elegir_carpeta()

    entrada_usuario = input(">> Pega el ID o URL (o escribe 'salir'): ").strip()
    if entrada_usuario.lower() in ['salir', 'exit', 'q']:
        return False

    id_objetivo = extraer_id_limpio(entrada_usuario)
    yt = YTMusic()

    songs_to_download = []
    final_path = ""

    try:
        if (("list=PL" in entrada_usuario or "list=VL" in entrada_usuario) or
                (id_objetivo.startswith("PL") or id_objetivo.startswith("VL"))):
            try:
                p(CYAN, "[INFO] Analizando Playlist...")
                data = yt.get_playlist(id_objetivo, limit=150)
                songs_to_download = data['tracks']
                final_path = generar_ruta_segura(base_folder, data.get('title', 'Playlist'))
            except:
                p(YELLOW, "[WARN] No se pudo leer como Playlist. Intentando como cancion individual...")
                songs_to_download = [{'videoId': id_objetivo}]
                final_path = os.path.join(base_folder, "Individuales")
        else:
            songs_to_download = [{'videoId': id_objetivo}]
            final_path = os.path.join(base_folder, "Individuales")
    except:
        songs_to_download = [{'videoId': id_objetivo}]
        final_path = os.path.join(base_folder, "Individuales")

    os.makedirs(final_path, exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"{final_path}/%(title)s.%(ext)s",
        'writethumbnail': True,
        'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'},
            {'key': 'EmbedThumbnail'}, {'key': 'FFmpegMetadata'}
        ],
        'noplaylist': True, 'quiet': True, 'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, song in enumerate(songs_to_download):
            v_id = song['videoId']
            link_final = v_id if v_id.startswith("http") else f"https://www.youtube.com/watch?v={v_id}"
            p(CYAN, f"[{i+1}/{len(songs_to_download)}] Procesando...")
            try:
                ydl.download([link_final])
                if len(songs_to_download) > 1: time.sleep(random.uniform(0.5, 1.0))
            except Exception as e:
                p(RED, "[ERROR] No se pudo bajar este ID.")

    p(GREEN, f"\n[OK] Proceso completado. Guardado en: {final_path}")
    input("\nPresiona ENTER para continuar descargando...")
    return True

if __name__ == "__main__":
    try:
        # Asegurar que el motor y las herramientas existan
        asegurar_ffmpeg()
        actualizar_ytdlp_portable()
        
        while True:
            if not ejecutar_descarga():
                break
    except Exception as e:
        import traceback
        p(RED, "\n" + "="*60)
        p(RED, "   CRITICAL ERROR / ERROR CRÍTICO")
        p(RED, "="*60)
        p(YELLOW, f"Detalles: {e}")
        print("\nTraza del error:")
        print(traceback.format_exc())
        p(RED, "="*60)
        input("\nPresiona ENTER para cerrar...")
