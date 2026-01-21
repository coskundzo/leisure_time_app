from flask import Flask, render_template, request, url_for
import os
import requests
import json
from yt_dlp import YoutubeDL

app = Flask(__name__)

MUSIC_DIR = os.path.join(app.static_folder, "music")


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
    error = None

    if request.method == "POST":
        video_url = request.form.get("video_url", "").strip()
        if video_url:
            try:
                os.makedirs(MUSIC_DIR, exist_ok=True)
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": os.path.join(MUSIC_DIR, "%(id)s.%(ext)s"),
                    "noplaylist": True,
                    "quiet": True,
                }
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=True)
                    filename = ydl.prepare_filename(info)
                audio_url = url_for(
                    "static", filename="music/" + os.path.basename(filename)
                )
            except Exception:
                error = "Error downloading audio. Please check the URL."
        else:
            error = "Please enter a URL."

    return render_template("music.html", audio_url=audio_url, error=error)


@app.route("/chess")
def play_chess():
    return render_template("chess.html")


if __name__ == "__main__":
    app.run(debug=True)
