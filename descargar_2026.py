import os, time, random, subprocess, sys, re
import yt_dlp
from ytmusicapi import YTMusic

BASE_FOLDER = 'C:/DescargadorMusica/Descargas'

def actualizar_motor():
    subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], capture_output=True)

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def extraer_id_limpio(entrada):
    # Si es una URL completa de canción o playlist
    if "v=" in entrada:
        return entrada.split("v=")[1].split("&")[0]
    if "list=" in entrada:
        return entrada.split("list=")[1].split("&")[0]
    # Si es una URL corta de esas de music.youtube.com/watch?v=...
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
    print("=" * 60)
    print("🚀 YT MUSIC PRO (FIX URLS + MODO BUCLE)")
    print("=" * 60)
    
    entrada_usuario = input("👉 Pega el ID o URL (o escribe 'salir'): ").strip()
    if entrada_usuario.lower() in ['salir', 'exit', 'q']:
        return False

    id_objetivo = extraer_id_limpio(entrada_usuario)
    yt = YTMusic()
    
    songs_to_download = []
    final_path = ""

    try:
        # Detectar si es una Playlist real (PL o VL) o una Radio (RD)
        # YTMusic API suele fallar con las Radios (RD), así que las bajamos como canción individual
        if ("list=PL" in entrada_usuario or "list=VL" in entrada_usuario) or (id_objetivo.startswith("PL") or id_objetivo.startswith("VL")):
            try:
                print("📂 Analizando Playlist...")
                data = yt.get_playlist(id_objetivo, limit=150)
                songs_to_download = data['tracks']
                final_path = generar_ruta_segura(BASE_FOLDER, data.get('title', 'Playlist'))
            except:
                print("⚠️ No se pudo leer como Playlist. Intentando como canción individual...")
                songs_to_download = [{'videoId': id_objetivo}]
                final_path = os.path.join(BASE_FOLDER, "Individuales")
        else:
            # Es una canción individual o una Radio (bajamos solo la canción actual)
            songs_to_download = [{'videoId': id_objetivo}]
            final_path = os.path.join(BASE_FOLDER, "Individuales")
    except:
        songs_to_download = [{'videoId': id_objetivo}]
        final_path = os.path.join(BASE_FOLDER, "Individuales")

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
            # Evitamos que se pegue la URL completa si v_id ya es una URL
            link_final = v_id if v_id.startswith("http") else f"https://www.youtube.com/watch?v={v_id}"
            
            print(f"[{i+1}/{len(songs_to_download)}] 🎵 Procesando...")
            try:
                ydl.download([link_final])
                if len(songs_to_download) > 1: time.sleep(random.uniform(0.5, 1.0))
            except Exception as e:
                print(f"⚠️ Error: No se pudo bajar este ID.")
                
    print(f"\n✅ Proceso completado.")
    input("\nPresiona ENTER para continuar descargando...")
    return True

if __name__ == "__main__":
    actualizar_motor()
    while True:
        if not ejecutar_descarga():
            break
