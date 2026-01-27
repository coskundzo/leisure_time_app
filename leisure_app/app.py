from flask import Flask, render_template, request, url_for, jsonify
from werkzeug.utils import secure_filename
import os
import requests
import json
from yt_dlp import YoutubeDL

app = Flask(__name__)

MUSIC_DIR = os.path.join(app.static_folder, "music")
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'flac', 'webm', 'mp4'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/books/read")
def read_books():
    pdf_file = "pdfs/sample.pdf"  # static/pdfs/sample.pdf
    return render_template("read_books.html", pdf_file=pdf_file)


@app.route("/books/listen", methods=["GET"])
def listen_books():
    query = request.args.get("q", "").strip().lower()
    error = None
    
    # Load books from local JSON file
    try:
        json_path = os.path.join(app.static_folder, 'data', 'audiobooks.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            all_books = json.load(f)
    except Exception as e:
        all_books = []
        error = f"Error loading audiobooks database: {str(e)}"

    # Filter books based on query if provided
    if query:
        books = [b for b in all_books if query in b['title'].lower() or query in b['author'].lower()]
    else:
        books = all_books

    return render_template("listen_books.html", query=request.args.get("q", ""), books=books, error=error)


@app.route("/music", methods=["GET", "POST"])
def listen_music():
    audio_url = None
    video_url_display = None
    video_title = None
    error = None
    success = None

    os.makedirs(MUSIC_DIR, exist_ok=True)

    if request.method == "POST":
        # Check if this is a file upload
        if 'music_file' in request.files:
            file = request.files['music_file']
            if file and file.filename:
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(MUSIC_DIR, filename)
                    file.save(filepath)
                    success = f"File '{filename}' uploaded successfully!"
                else:
                    error = "Invalid file type. Allowed: mp3, wav, ogg, m4a, flac, webm, mp4"
            else:
                error = "Please select a file to upload."
        # Check if this is a YouTube URL download
        elif request.form.get("video_url"):
            video_url = request.form.get("video_url", "").strip()
            if video_url:
                try:
                    ydl_opts = {
                        "format": "best",
                        "outtmpl": os.path.join(MUSIC_DIR, "%(title)s.%(ext)s"),
                        "noplaylist": True,
                        "quiet": True,
                    }
                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(video_url, download=True)
                        filename = ydl.prepare_filename(info)
                        video_title = info.get('title', 'Unknown')
                    audio_url = url_for(
                        "static", filename="music/" + os.path.basename(filename)
                    )
                    video_url_display = video_url
                except Exception as e:
                    error = "Error downloading. Please check the URL."
            else:
                error = "Please enter a URL."

    # Get search query
    search_query = request.args.get('search', '').strip().lower()

    # Get list of all music files
    music_files = []
    if os.path.exists(MUSIC_DIR):
        for f in os.listdir(MUSIC_DIR):
            if allowed_file(f):
                # Apply search filter
                if search_query and search_query not in f.lower():
                    continue
                music_files.append({
                    'name': f,
                    'url': url_for('static', filename='music/' + f)
                })
    music_files.sort(key=lambda x: x['name'].lower())

    return render_template("music.html", 
                         audio_url=audio_url, 
                         video_url=video_url_display,
                         video_title=video_title,
                         error=error, 
                         success=success,
                         music_files=music_files,
                         search_query=request.args.get('search', ''))


@app.route("/music/delete/<filename>", methods=["POST"])
def delete_music(filename):
    try:
        filepath = os.path.join(MUSIC_DIR, secure_filename(filename))
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass
    return "", 204


@app.route("/music/search")
def search_youtube_music():
    """Search YouTube Music for tracks"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'results': [], 'error': 'No search query provided'})
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'ytsearch20',
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch20:{query}", download=False)
            
        results = []
        if result and 'entries' in result:
            for entry in result['entries']:
                if entry:
                    results.append({
                        'id': entry.get('id', ''),
                        'title': entry.get('title', 'Unknown'),
                        'channel': entry.get('channel', entry.get('uploader', 'Unknown')),
                        'duration': entry.get('duration', 0),
                        'thumbnail': entry.get('thumbnail', ''),
                        'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                    })
        
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'results': [], 'error': str(e)})


@app.route("/music/download", methods=["POST"])
def download_youtube_music():
    """Download a track from YouTube by video ID"""
    data = request.get_json()
    video_id = data.get('video_id', '').strip()
    download_format = data.get('format', 'mp3')  # 'mp3' or 'video'
    
    if not video_id:
        return jsonify({'success': False, 'error': 'No video ID provided'})
    
    try:
        os.makedirs(MUSIC_DIR, exist_ok=True)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        if download_format == 'video':
            ydl_opts = {
                "format": "best[ext=mp4]/best",
                "outtmpl": os.path.join(MUSIC_DIR, "%(title)s.%(ext)s"),
                "noplaylist": True,
                "quiet": True,
            }
        else:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(MUSIC_DIR, "%(title)s.%(ext)s"),
                "noplaylist": True,
                "quiet": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'Unknown')
        
        format_label = "video" if download_format == 'video' else "MP3"
        return jsonify({
            'success': True, 
            'message': f'"{title}" ({format_label}) downloaded successfully!',
            'title': title
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route("/chess")
def play_chess():
    return render_template("chess.html")


if __name__ == "__main__":
    app.run(debug=True)
