import os, subprocess, httpx, re
from mutagen.mp4 import MP4

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def p_clean(nome):
    return re.sub(r'[^a-zA-Z0-9._-]', '_', nome)

def carica_su_catbox(filepath):
    try:
        with open(filepath, 'rb') as f:
            files = {'reqtype': (None, 'fileupload'), 'fileToUpload': (os.path.basename(filepath), f)}
            res = httpx.post("https://catbox.moe/user/api.php", files=files, timeout=120.0)
            if res.status_code == 200 and res.text.startswith("http"):
                return res.text
    except Exception as e:
        print(f"Errore Catbox: {e}")
    return ""

print("Controllo coda su Supabase...")
res = httpx.get(f"{SUPABASE_URL}/rest/v1/richieste_download?select=*", headers=headers)

if res.status_code == 200 and len(res.json()) > 0:
    richieste = res.json()
    print(f"Trovate {len(richieste)} canzoni da processare.")
    
    os.makedirs("temp_music", exist_ok=True)
    os.chdir("temp_music")
    
    for req in richieste:
        url_spotify = req['spotify_url']
        id_richiesta = req['id']
        print(f"\n[!] Scarico: {url_spotify}")
        
        for f in os.listdir("."): os.remove(f)
            
        subprocess.run(["spotdl", url_spotify, "--format", "m4a", "--bitrate", "128k"])
        
        file_audio = next((f for f in os.listdir(".") if f.endswith(".m4a")), None)
        
        if file_audio:
            title = file_audio[:-4]
            artist, album, has_cover = "Sconosciuto", "Singolo", False
            cover_filename = f"cover_{p_clean(title)}.jpg"

            try:
                audio = MP4(file_audio)
                if '\xa9nam' in audio.tags: title = audio.tags['\xa9nam'][0]
                if '\xa9ART' in audio.tags: artist = audio.tags['\xa9ART'][0]
                if '\xa9alb' in audio.tags: album = audio.tags['\xa9alb'][0]
                if 'covr' in audio.tags:
                    with open(cover_filename, 'wb') as img: img.write(audio.tags['covr'][0])
                    has_cover = True
            except Exception: pass

            print(f" -> Carico '{title}' su Catbox.moe...")
            
            audio_url = carica_su_catbox(file_audio)
            cover_url = carica_su_catbox(cover_filename) if has_cover else ""

            if audio_url:
                dati = {"title": title, "artist": artist, "album": album, "audio_url": audio_url, "cover_url": cover_url}
                httpx.post(f"{SUPABASE_URL}/rest/v1/songs", headers=headers, json=dati)
                print(f" -> [OK] Finito! Link Audio: {audio_url}")
            else:
                print(" -> [ERRORE] Impossibile ottenere il link da Catbox.")
                
        httpx.delete(f"{SUPABASE_URL}/rest/v1/richieste_download?id=eq.{id_richiesta}", headers=headers)
        
else:
    print("Nessuna nuova richiesta in coda.")
