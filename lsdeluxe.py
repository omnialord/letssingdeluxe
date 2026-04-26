import os
import sys
import csv
import json
import shutil
import requests
import subprocess
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from tqdm import tqdm

# ==========================================
# VERSION MAP & ARGUMENT PARSING
# ==========================================
VERSION_MAP = {
    "2025": {
        "FR": ("songs_fr", "01001C101ED11002"),
        "AUS": ("songs_aus", "01001C101ED11001"),
        "SPA": ("songs_spa", "01001C101ED11005"),
        "GER": ("songs_ger", "01001C101ED11003"),
        "UK": ("songs_uk", "01001C101ED11006"),
        "INT": ("songs_int", "01001C101ED11004"),
    },
    "2026": {
        "AUS": ("songs_aus", "0100EE4020D19001"),
        "FR": ("songs_fr", "0100EE4020D19002"),
        "SPA": ("songs_spa", "0100EE4020D19004"),
        "UK": ("songs_uk", "0100EE4020D19006"),
        "INT": ("songs_int", "0100EE4020D19003"),
    }
}

MENU_OPTIONS = {
    "1": ("2025", "FR"),
    "2": ("2025", "AUS"),
    "3": ("2025", "SPA"),
    "4": ("2025", "GER"),
    "5": ("2025", "UK"),
    "6": ("2025", "INT"),
    "7": ("2026", "AUS"),
    "8": ("2026", "FR"),
    "9": ("2026", "SPA"),
    "10": ("2026", "UK"),
    "11": ("2026", "INT")
}

NO_VIDEO = False
target_year = "2025"
target_region = "FR"

if len(sys.argv) == 1:
    # Interactive Menu Mode
    print("\nChoose your game version:")
    print("1 - 2025 French Hits")
    print("2 - 2025 Australia and New Zealand Hits")
    print("3 - 2025 Spanish Hits")
    print("4 - 2025 German Hits")
    print("5 - 2025 Hits from UK")
    print("6 - 2025 International Hits")
    print("7 - 2026 Australia and New Zealand Hits")
    print("8 - 2026 French Hits")
    print("9 - 2026 Spanish Hits")
    print("10 - 2026 UK Hits")
    print("11 - 2026 International Hits")
    
    while True:
        choice = input("\nEnter choice (1-11): ").strip()
        if choice in MENU_OPTIONS:
            target_year, target_region = MENU_OPTIONS[choice]
            break
        print("[ERROR] Invalid choice. Please enter a number between 1 and 11.")

    print("\nVideo processing mode:")
    print("1 - Use music videos (default, recommended)")
    print("2 - Use static cover images (lightweight, faster)")
    
    while True:
        vid_choice = input("\nEnter choice (1-2): ").strip()
        if vid_choice == "1":
            NO_VIDEO = False
            break
        elif vid_choice == "2":
            NO_VIDEO = True
            break
        print("[ERROR] Invalid choice. Please enter 1 or 2.")
        
else:
    # CLI Argument Mode
    args = sys.argv[1:]
    if "--no-video" in args:
        NO_VIDEO = True
        args.remove("--no-video")

    if len(args) >= 2:
        target_year = args[0]
        target_region = args[1].upper()
    else:
        print("[WARNING] Incomplete arguments. Using default: 2025 FR")
        print("[INFO] Usage: py lsdeluxe.py [YEAR] [REGION] [--no-video]")
        print("[INFO] Example: py lsdeluxe.py 2026 INT --no-video")

version_data = VERSION_MAP.get(target_year, {}).get(target_region)
if not version_data:
    print("[WARNING] Invalid version combination '{0} {1}'. Falling back to 2025 FR.".format(target_year, target_region))
    version_data = VERSION_MAP["2025"]["FR"]

JSON_NAME, VERSION_ID = version_data

# ==========================================
# CONFIGURATION & PATHS
# ==========================================
ROOT_DIR = Path('.').absolute()
CSV_FILE = ROOT_DIR / "Lets Sing Deluxe DB - CSV.csv"

DIR_VIDEOS = ROOT_DIR / "videos"
DIR_VXLA = ROOT_DIR / "vxla"
DIR_VXLA_DUET = ROOT_DIR / "vxla_duet"
DIR_VXLA_FEAT = ROOT_DIR / "vxla_feat"
DIR_AUDIO = ROOT_DIR / "audio"
DIR_AUDIO_PREVIEW = ROOT_DIR / "audio_preview"
DIR_COVERS = ROOT_DIR / "covers"

DIR_DECODER = ROOT_DIR / "MoDecoder"
EXE_DECODER = DIR_DECODER / "MobiclipDecoder.exe"

OUT_BASE = ROOT_DIR / "_DeluxeMod" / VERSION_ID
OUT_ROMFS = OUT_BASE / "romfs"
OUT_SONGS = OUT_ROMFS / "Songs"
OUT_VIDEOS = OUT_SONGS / "videos"
OUT_VXLA = OUT_SONGS / "vxla"
OUT_VXLA_FEAT = OUT_SONGS / "vxla_feat"
OUT_AUDIO = OUT_SONGS / "audio"
OUT_AUDIO_PREVIEW = OUT_SONGS / "audio_preview"
OUT_COVERS = OUT_SONGS / "covers"

FFMPEG_PATH = ROOT_DIR / "ffmpeg" / "bin" / "ffmpeg.exe"
FFPROBE_PATH = ROOT_DIR / "ffmpeg" / "bin" / "ffprobe.exe"
TARGET_VIDEO_MB = 50.0

# ==========================================
# UTILS & FOLDER CREATION
# ==========================================
def ensure_directories():
    required_inputs = [DIR_VIDEOS, DIR_VXLA, DIR_AUDIO, DIR_AUDIO_PREVIEW, DIR_COVERS, DIR_DECODER]
    for d in required_inputs:
        d.mkdir(parents=True, exist_ok=True)
    required_outputs = [OUT_VIDEOS, OUT_VXLA, OUT_VXLA_FEAT, OUT_AUDIO, OUT_AUDIO_PREVIEW, OUT_COVERS]
    for d in required_outputs:
        d.mkdir(parents=True, exist_ok=True)

def verify_tools():
    missing = []
    if not FFMPEG_PATH.exists(): missing.append(str(FFMPEG_PATH))
    if not FFPROBE_PATH.exists(): missing.append(str(FFPROBE_PATH))
    
    if missing:
        print("\n[CRITICAL ERROR] External tools not found:")
        for m in missing:
            print("  - {0}".format(m))
        print("Make sure the 'ffmpeg' folder is in the root directory.")
        sys.exit(1)

# ==========================================
# VXLA CONVERSION FUNCTIONS
# ==========================================
def parse_intervals(layer):
    intervals = []
    if layer is not None:
        for interval in layer.findall('Interval'):
            intervals.append({
                't1': float(interval.get('t1')),
                't2': float(interval.get('t2')),
                'value': interval.get('value'),
                'element': interval
            })
    return intervals

def get_layer(root, name):
    for layer in root.findall('IntervalLayer'):
        if layer.get('name') == name:
            return layer
    return None

def extract_golden_blocks(root):
    golden = []
    for suffix in ["", "2"]:
        g_layer = get_layer(root, "notes{0}_golden".format(suffix))
        if g_layer is not None:
            for interval in g_layer.findall('Interval'):
                golden.append({
                    't1': float(interval.get('t1')),
                    't2': float(interval.get('t2')),
                    'value': interval.get('value')
                })
    return golden

def fix_segments(root, all_golden_intervals):
    structure_layer = get_layer(root, "structure")
    segments_layer = get_layer(root, "segments")
    
    target_layer = None
    
    if structure_layer is not None:
        structure_layer.set("name", "segments")
        target_layer = structure_layer
    elif segments_layer is not None:
        target_layer = segments_layer
    else:
        target_layer = ET.Element('IntervalLayer', datatype="STRING", name="segments")
        root.insert(0, target_layer)

    if target_layer is not None:
        for interval in target_layer.findall('Interval'):
            if interval.get('value') == "refrain":
                interval.set('value', 'feat')
        
        existing_feats = [float(iv.get('t1')) for iv in target_layer.findall('Interval') if iv.get('value') == 'feat']
            
        for g in all_golden_intervals:
            is_duplicate = False
            for ef in existing_feats:
                if abs(ef - g['t1']) < 0.2:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                new_feat = ET.Element('Interval', t1="{0:.3f}".format(g['t1']), t2="{0:.3f}".format(g['t2']), value="feat")
                target_layer.append(new_feat)
                existing_feats.append(g['t1']) 
            
        all_elements = target_layer.findall('Interval')
        all_elements.sort(key=lambda x: float(x.get('t1')))
        
        for elem in target_layer.findall('Interval'):
            target_layer.remove(elem)
        for elem in all_elements:
            target_layer.append(elem)

def process_track(root, track_suffix=""):
    notes_layer = get_layer(root, "notes{0}".format(track_suffix))
    lyrics_layer = get_layer(root, "lyrics{0}".format(track_suffix))
    lyrics_cut_layer = get_layer(root, "lyrics{0}_cut".format(track_suffix))
    golden_layer = get_layer(root, "notes{0}_golden".format(track_suffix))
    
    if notes_layer is None: return [] 

    notes = parse_intervals(notes_layer)
    golden_intervals = parse_intervals(golden_layer)
    new_notes_full_intervals = []

    if lyrics_cut_layer is not None:
        lyrics_cut = parse_intervals(lyrics_cut_layer)
        cut_map = {}
        for lc in lyrics_cut:
            tempo_str = "{:.3f}".format(lc['t1'])
            cut_map[tempo_str] = lc['value'].strip()
            
        for note in notes:
            tempo_str = "{:.3f}".format(note['t1'])
            note_val = note['value']
            syllable = cut_map.get(tempo_str, '-')
            new_value = "#p{0}#.{1}".format(note_val, syllable)
            
            new_notes_full_intervals.append({
                't1': note['t1'], 't2': note['t2'], 'value': new_value, 
                't1_str': note['element'].get('t1'), 't2_str': note['element'].get('t2')
            })
            
    elif lyrics_layer is not None:
        lyrics = parse_intervals(lyrics_layer)
        for note in notes:
            syllable = "-"
            note_time = note['t1']
            note_val = note['value']
            for lyric in lyrics:
                if abs(note_time - lyric['t1']) < 0.01: 
                    syllable = lyric['value'].strip()
                    break
            new_value = "#p{0}#.{1}".format(note_val, syllable)
            new_notes_full_intervals.append({
                't1': note['t1'], 't2': note['t2'], 'value': new_value, 
                't1_str': note['element'].get('t1'), 't2_str': note['element'].get('t2')
            })
    else:
        for note in notes:
            note_val = note['value']
            new_value = "#p{0}#.-".format(note_val)
            new_notes_full_intervals.append({
                't1': note['t1'], 't2': note['t2'], 'value': new_value, 
                't1_str': note['element'].get('t1'), 't2_str': note['element'].get('t2')
            })

    for note in new_notes_full_intervals:
        for golden in golden_intervals:
            if note['t1'] >= golden['t1'] - 0.01 and note['t2'] <= golden['t2'] + 0.01:
                note['value'] += "#g5"
                break
    return new_notes_full_intervals

def convert_vxla(input_path, output_path):
    try:
        tree = ET.parse(input_path)
        root = tree.getroot()
    except ET.ParseError:
        return False
        
    if root.get('version') == "3.0" and get_layer(root, "segments") is not None:
        shutil.copy2(input_path, output_path)
        tqdm.write("  > [INFO] Copied without changes (already 3.0 with segments): {0}".format(output_path.name))
        return True
        
    root.set('version', '3.0')
    
    notes_full_data = process_track(root, "")
    notes2_full_data = process_track(root, "2")
    
    full_layer = get_layer(root, "notes_full")
    if full_layer is None:
        full_layer = ET.SubElement(root, 'IntervalLayer', name="notes_full")
    else:
        for child in list(full_layer): full_layer.remove(child)
    for nf in notes_full_data:
        ET.SubElement(full_layer, 'Interval', t1=str(nf['t1_str']), t2=str(nf['t2_str']), value=nf['value'])

    if notes2_full_data:
        full_layer2 = get_layer(root, "notes2_full")
        if full_layer2 is None:
            full_layer2 = ET.SubElement(root, 'IntervalLayer', name="notes2_full")
        else:
            for child in list(full_layer2): full_layer2.remove(child)
        for nf in notes2_full_data:
            ET.SubElement(full_layer2, 'Interval', t1=str(nf['t1_str']), t2=str(nf['t2_str']), value=nf['value'])
            
    all_golden = extract_golden_blocks(root)
    fix_segments(root, all_golden)
    
    layers_to_keep = ['segments', 'pages', 'lyrics', 'notes_full', 'pages2', 'lyrics2', 'notes2_full']
    for layer in root.findall('IntervalLayer'):
        name = layer.get('name')
        if name not in layers_to_keep:
            root.remove(layer)
        else:
            layer.attrib.pop('units', None)
            layer.attrib.pop('description', None)

    if hasattr(ET, 'indent'):
        ET.indent(root, space="\t", level=0)
    
    xml_str = ET.tostring(root, encoding="UTF-8", xml_declaration=False).decode("utf-8")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(xml_str)
    return True

# ==========================================
# VIDEO CONVERSION FUNCTIONS
# ==========================================
def get_duration(media_path):
    try:
        result = subprocess.run(
            [str(FFPROBE_PATH), '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(media_path)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, text=True
        )
        return float(result.stdout)
    except Exception:
        return 60.0

def get_framerate(video_path):
    try:
        result = subprocess.run(
            [str(FFPROBE_PATH), '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=r_frame_rate', '-of',
             'default=noprint_wrappers=1:nokey=1', str(video_path)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, text=True
        )
        r_frame_rate = result.stdout.strip()
        if '/' in r_frame_rate:
            num, den = map(int, r_frame_rate.split('/'))
            return num / den if den != 0 else 0.0
        return float(r_frame_rate)
    except Exception:
        return 0.0

def create_temp_mp4_25fps(input_file, temp_output_file, duration):
    original_size_bytes = input_file.stat().st_size
    original_size_mb = original_size_bytes / (1024 * 1024)
    target_bitrate_kbs = int((original_size_mb * 8192) / duration) if duration > 0 else 2000
    
    ffmpegCmd = [
        str(FFMPEG_PATH), '-y', '-i', str(input_file),
        '-c:v', 'libx264', '-preset', 'medium',
        '-vf', 'scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=25',
        '-an', '-b:v', str(target_bitrate_kbs) + 'k',
        str(temp_output_file)
    ]
    subprocess.run(ffmpegCmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def convert_mo_to_mp4(mo_file, mp4_output):
    if not EXE_DECODER.exists():
        raise Exception("MobiclipDecoder not found at {0}".format(EXE_DECODER))

    destino_mo = DIR_DECODER / mo_file.name
    shutil.copy2(mo_file, destino_mo)
    for f in DIR_DECODER.glob("*.png"): f.unlink(missing_ok=True)
    
    try:
        subprocess.run([str(EXE_DECODER)], cwd=str(DIR_DECODER), check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        frames = sorted([f for f in DIR_DECODER.glob("*.png") if f.stem.isdigit()], key=lambda x: int(x.stem))
        if not frames: return False
        
        with open(DIR_DECODER / "frames.txt", "w") as f:
            for fr in frames: f.write("file '{0}'\nduration {1}\n".format(fr.name, 1/25.0))
            
        ffmpeg_cmd = [str(FFMPEG_PATH), '-y', '-f', 'concat', '-safe', '0', '-i', 'frames.txt', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', '25', str(mp4_output.absolute())]
        subprocess.run(ffmpeg_cmd, cwd=str(DIR_DECODER), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False
    finally:
        for f in DIR_DECODER.glob("*.png"): f.unlink(missing_ok=True)
        if destino_mo.exists(): destino_mo.unlink()

def create_still_video_from_cover(cover_path, output_mp4, duration):
    target_size_mb = 10
    target_bitrate_kbps = int((target_size_mb * 8192) / max(duration, 1))
    complex_filter = (
        "split[bg][fg];"
        "[bg]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,gblur=sigma=10[bg_blurred];"
        "[fg]scale='if(gt(iw/ih,1280/720),min(iw,1280),-1)':'if(gt(iw/ih,1280/720),-1,min(ih,720))':force_original_aspect_ratio=decrease[fg_scaled];"
        "[bg_blurred][fg_scaled]overlay=(W-w)/2:(H-h)/2,fps=25"
    )
    ffmpeg_cmd = [
        str(FFMPEG_PATH), '-y', '-loop', '1',
        '-i', str(cover_path),
        '-c:v', 'libx264', '-t', str(duration),
        '-preset', 'medium', '-tune', 'stillimage',
        '-b:v', "{0}k".format(target_bitrate_kbps),
        '-vf', complex_filter,
        '-pix_fmt', 'yuv420p',
        '-an', str(output_mp4)
    ]
    try:
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False

def create_video_bink(input_path, output_path, compression_percentage):
    binkconv_path = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'RADVideo' / 'radvideo64.exe'
    
    if not binkconv_path.exists():
         raise Exception("RADVideo (Bink) not found at {0}".format(binkconv_path))

    binkArgs = [
        str(binkconv_path), 'binkc', str(input_path.absolute()), str(output_path.absolute()), 
        '/V200', '/(1280', '/)720', '/L-1', 
        '/D' + str(compression_percentage), '/#'
    ]
    
    subprocess.run(binkArgs, capture_output=True, text=True, check=True)
    return output_path.exists()

# ==========================================
# AUDIO & PREVIEW FUNCTIONS
# ==========================================
def generate_audio_preview(audio_in, audio_out):
    ffmpeg_cmd = [
        str(FFMPEG_PATH), '-y', '-ss', '60', '-i', str(audio_in),
        '-vn', '-t', '30', '-ar', '48000', '-af', 'loudnorm=I=-16:LRA=11:TP=-1.5', str(audio_out)
    ]
    subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
    return True

# ==========================================
# COVER FUNCTIONS
# ==========================================
def download_deezer_cover(album_id, output_path):
    url_api = "https://api.deezer.com/album/{0}/image?size=512".format(album_id)
    try:
        req = requests.get(url_api, stream=True)
        url_final = req.url.replace('.jpg', '.png')
        req.close()
        
        img_req = requests.get(url_final)
        img_req.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(img_req.content)
        return True
    except Exception:
        return False

def generate_video_thumbnail(video_path, output_path):
    ffmpeg_cmd = [
        str(FFMPEG_PATH), '-y', '-i', str(video_path),
        '-ss', '00:00:10', '-vframes', '1', '-vf', 'scale=256:256', str(output_path)
    ]
    subprocess.run(ffmpeg_cmd, capture_output=True, check=False)
    return output_path.exists()

# ==========================================
# JSON EXPORT
# ==========================================
def append_to_json(processed_songs):
    json_filename = "{0}.json".format(JSON_NAME)
    json_source_path = ROOT_DIR / json_filename
    json_output_path = OUT_ROMFS / json_filename
    
    data = {"name": "deluxe", "songs": []}
    
    if json_source_path.exists():
        try:
            with open(json_source_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    existing_ids = set()
    for s in data.get("songs", []):
        if "id" in s:
            existing_ids.add(s["id"])

    for song in processed_songs:
        if song["id"] not in existing_ids:
            data["songs"].append(song)
    
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ==========================================
# MAIN ORCHESTRATOR
# ==========================================
def load_csv_safe(file_path):
    songs = []
    with open(file_path, mode='r', encoding='utf-8-sig') as f:
        content = f.read()
        
    lines = content.splitlines()
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith('"') and line.endswith('"') and '","' not in line:
            line = line[1:-1]
            line = line.replace('""', '"')
        clean_lines.append(line)
        
    reader = csv.DictReader(clean_lines)
    id_key = None
    if reader.fieldnames:
        for fn in reader.fieldnames:
            if fn and fn.strip().lower() == 'id':
                id_key = fn
                break
                
    for row in reader:
        if id_key and row.get(id_key):
            row['id'] = row[id_key].strip()
            songs.append(row)
    return songs

def main():
    ensure_directories()
    verify_tools()
    
    if not CSV_FILE.exists():
        print("[ERROR] CSV file not found: {0}".format(CSV_FILE))
        return

    songs_to_process = load_csv_safe(CSV_FILE)
    valid_songs = []
    missing_log = []

    print("[INFO] Pre-scanning directories to identify valid songs...")

    for song in songs_to_process:
        song_id = song.get('id', '').strip()
        if not song_id: continue
        
        ogg_file = DIR_AUDIO / "{0}.ogg".format(song_id)
        
        vxla_files = []
        for d in [DIR_VXLA, DIR_VXLA_DUET, DIR_VXLA_FEAT]:
            temp_path = d / "{0}.vxla".format(song_id)
            if temp_path.exists():
                vxla_files.append(temp_path)
                break
                
        for d in [DIR_VXLA, DIR_VXLA_DUET, DIR_VXLA_FEAT]:
            found_duet = False
            for suffix in ["_DUET", "_duet", "_FEAT", "_feat"]:
                temp_path = d / "{0}{1}.vxla".format(song_id, suffix)
                if temp_path.exists():
                    vxla_files.append(temp_path)
                    found_duet = True
                    break
            if found_duet: break
        
        video_file = None
        for ext in ['.mp4', '.bk2', '.mo']:
            temp_path = DIR_VIDEOS / "{0}{1}".format(song_id, ext)
            if temp_path.exists():
                video_file = temp_path
                break
                
        # If --no-video is enabled, tolerate missing video file during scan
        if not ogg_file.exists() or not vxla_files or (not video_file and not NO_VIDEO):
            missing = []
            if not ogg_file.exists(): missing.append("Audio")
            if not vxla_files: missing.append("VXLA")
            if not video_file and not NO_VIDEO: missing.append("Video")
            missing_log.append("[{0}] -> Missing: {1}".format(song_id, ", ".join(missing)))
        else:
            song['ogg_file'] = ogg_file
            song['vxla_files'] = vxla_files
            song['video_file'] = video_file
            valid_songs.append(song)

    if missing_log:
        with open("_Missing_Log.txt", "w", encoding="utf-8") as f:
            f.write("=== MISSING FILES LOG ===\n")
            f.write("\n".join(missing_log))
        print("[INFO] Found {0} invalid entries. Details saved in '_Missing_Log.txt'.".format(len(missing_log)))

    if not valid_songs:
        print("[WARNING] No valid songs found with all required files to process.")
        return

    processed_success = []

    for song in tqdm(valid_songs, desc="Processing Songs", unit="song"):
        song_id = song['id']
        ogg_file = song['ogg_file']
        vxla_files = song['vxla_files']
        video_file = song['video_file']

        try:
            tqdm.write("\n--- Processing ID: {0} ---".format(song_id))
            
            # === AUDIO ===
            tqdm.write("[{0}] Step 1/5: Processing audio...".format(song_id))
            final_audio_path = OUT_AUDIO / "{0}.ogg".format(song_id)
            if not final_audio_path.exists() and "_instru" not in ogg_file.name.lower():
                shutil.copy2(ogg_file, final_audio_path)

            # === PREVIEW ===
            tqdm.write("[{0}] Step 2/5: Processing audio preview...".format(song_id))
            preview_in = DIR_AUDIO_PREVIEW / "{0}_preview.ogg".format(song_id)
            preview_out = OUT_AUDIO_PREVIEW / "{0}_preview.ogg".format(song_id)
            
            if not preview_out.exists():
                if preview_in.exists():
                    shutil.copy2(preview_in, preview_out)
                else:
                    tqdm.write("  > Generating preview with FFmpeg...")
                    generate_audio_preview(ogg_file, preview_out)

            # === COVER ===
            tqdm.write("[{0}] Step 3/5: Processing cover...".format(song_id))
            final_cover_name = "{0}.png".format(song_id)
            cover_out = OUT_COVERS / final_cover_name
            cover_success = False
            
            if not cover_out.exists():
                cover_in = DIR_COVERS / "{0}.png".format(song_id)
                if cover_in.exists():
                    shutil.copy2(cover_in, cover_out)
                    cover_success = True
                else:
                    deezer_id = song.get('cover', '').strip()
                    if deezer_id and deezer_id.isdigit():
                        tqdm.write("  > Downloading cover from Deezer...")
                        cover_success = download_deezer_cover(deezer_id, cover_out)
                        
                    if not cover_success and video_file and video_file.suffix == '.mp4':
                        tqdm.write("  > Deezer failed/missing, generating thumbnail from video...")
                        cover_success = generate_video_thumbnail(video_file, cover_out)
            else:
                cover_success = True

            # === VIDEO ===
            tqdm.write("[{0}] Step 4/5: Processing video...".format(song_id))
            final_video_name = "{0}.bk2".format(song_id)
            final_video_path = OUT_VIDEOS / final_video_name
            
            if not final_video_path.exists():
                if video_file:
                    if video_file.suffix == '.bk2':
                        shutil.copy2(video_file, final_video_path)
                    else:
                        target_mp4 = video_file
                        is_temp_mo = False
                        
                        if video_file.suffix == '.mo':
                            target_mp4 = DIR_VIDEOS / "{0}_temp.mp4".format(song_id)
                            is_temp_mo = True
                            if not convert_mo_to_mp4(video_file, target_mp4):
                                raise Exception("Mobiclip conversion failed.")
                        
                        duration = get_duration(target_mp4)
                        current_fps = get_framerate(target_mp4)
                        file_to_process = target_mp4
                        temp_fps_file = DIR_VIDEOS / "TEMP_FPS_{0}.mp4".format(song_id)
                        
                        if abs(current_fps - 25.0) > 0.1:
                            tqdm.write("  > Converting video to 25 FPS...")
                            create_temp_mp4_25fps(target_mp4, temp_fps_file, duration)
                            if temp_fps_file.exists():
                                file_to_process = temp_fps_file
                        
                        temp_size_mb = file_to_process.stat().st_size / (1024 * 1024)
                        if temp_size_mb <= TARGET_VIDEO_MB:
                            compression_percentage = 100
                        else:
                            percentage = (TARGET_VIDEO_MB / temp_size_mb) * 100
                            compression_percentage = max(1, min(200, int(round(percentage))))

                        tqdm.write("  > Converting to Bink (.bk2) format...")
                        if not create_video_bink(file_to_process, final_video_path, compression_percentage):
                            raise Exception("Bink conversion failed.")
                            
                        if temp_fps_file.exists():
                            temp_fps_file.unlink()
                        if is_temp_mo and target_mp4.exists():
                            target_mp4.unlink()
                elif NO_VIDEO:
                    if not cover_success:
                        raise Exception("Missing video and failed to obtain cover image for static video generation.")
                        
                    tqdm.write("  > Missing video file. Generating static video from cover...")
                    song_duration = get_duration(final_audio_path)
                    temp_static_mp4 = DIR_VIDEOS / "{0}_static.mp4".format(song_id)
                    
                    if not create_still_video_from_cover(cover_out, temp_static_mp4, song_duration):
                        raise Exception("Static video generation failed.")
                        
                    tqdm.write("  > Converting static video to Bink (.bk2) format...")
                    if not create_video_bink(temp_static_mp4, final_video_path, 100):
                        raise Exception("Bink conversion failed for static video.")
                        
                    if temp_static_mp4.exists():
                        temp_static_mp4.unlink()
                else:
                    raise Exception("Unexpected Error: No video found and --no-video was not set.")
            else:
                tqdm.write("  > Video already exists, skipping.")

            # === VXLA ===
            tqdm.write("[{0}] Step 5/5: Converting {1} VXLA structure(s)...".format(song_id, len(vxla_files)))
            
            for vxla_file in vxla_files:
                vxla_parents = [p.name.lower() for p in vxla_file.parents]
                is_file_duet = ('vxla_duet' in vxla_parents or 'vxla_feat' in vxla_parents or 
                                '_duet' in vxla_file.name.lower() or '_feat' in vxla_file.name.lower())
                
                final_vxla_name = "{0}_feat.vxla".format(song_id) if is_file_duet else "{0}.vxla".format(song_id)
                final_vxla_dir = OUT_VXLA_FEAT if is_file_duet else OUT_VXLA
                final_vxla_path = final_vxla_dir / final_vxla_name
                
                if not final_vxla_path.exists():
                    if not convert_vxla(vxla_file, final_vxla_path):
                        raise Exception("VXLA conversion failed for {0}.".format(vxla_file.name))
                else:
                    tqdm.write("  > VXLA ({0}) already exists, skipping.".format(final_vxla_name))

            # Prepare dict for JSON export
            song_to_save = dict(song)
            song_to_save.pop('ogg_file', None)
            song_to_save.pop('vxla_files', None)
            song_to_save.pop('video_file', None)
            
            processed_success.append(song_to_save)
            tqdm.write("[{0}] [SUCCESS] Finished processing.".format(song_id))

        except Exception as e:
            tqdm.write("[{0}] [ERROR] Process failed: {1}".format(song_id, str(e)))

    if processed_success:
        append_to_json(processed_success)
        print("\n[SUCCESS] Completed! {0} valid songs were fully processed and appended to JSON.".format(len(processed_success)))

if __name__ == "__main__":
    main()
