import os
import json
import uuid
from flask import Flask, request, render_template_string, redirect, url_for
from google.cloud import storage

app = Flask(__name__)
BUCKET_NAME = os.environ.get("BUCKET_NAME")

# HTML template embedded for simplicity
HTML = """
<!doctype html>
<html>
<head>
    <title>Image Search</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        .upload-form { border: 1px solid #ccc; padding: 20px; margin-bottom: 20px; }
        .image-grid { display: flex; flex-wrap: wrap; gap: 20px; }
        .image-card { border: 1px solid #ddd; padding: 10px; text-align: center; }
        img { max-width: 200px; max-height: 200px; }
        .keyword-badge { background: #eee; padding: 2px 6px; border-radius: 4px; margin: 2px; display: inline-block; }
        a { text-decoration: none; color: #0066cc; }
    </style>
</head>
<body>
    <h1>🔍 Image Search</h1>

    <div class="upload-form">
        <h2>Upload an Image</h2>
        <form method="post" enctype="multipart/form-data" action="/upload">
            <input type="file" name="file" accept="image/*" required><br><br>
            Keywords (comma separated): <input type="text" name="keywords" placeholder="e.g., cat, funny, meme" required><br><br>
            <button type="submit">Upload</button>
        </form>
    </div>

    <div>
        <h2>Search by Keyword</h2>
        <form method="get" action="/search">
            <input type="text" name="keyword" placeholder="Enter keyword" required>
            <button type="submit">Search</button>
        </form>
    </div>

    {% if keyword %}
        <h2>Results for "{{ keyword }}"</h2>
        {% if images %}
            <div class="image-grid">
            {% for img in images %}
                <div class="image-card">
                    <img src="{{ img.url }}" alt="{{ img.filename }}">
                    <p>{{ img.filename }}</p>
                    <div>
                        {% for kw in img.keywords %}
                            <span class="keyword-badge">{{ kw }}</span>
                        {% endfor %}
                    </div>
                </div>
            {% endfor %}
            </div>
        {% else %}
            <p>No images found for "{{ keyword }}".</p>
        {% endif %}
    {% endif %}
</body>
</html>
"""

def read_keywords():
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob("keywords.json")
    if not blob.exists():
        return {}
    content = blob.download_as_text()
    return json.loads(content)

def write_keywords(data):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob("keywords.json")
    blob.upload_from_string(json.dumps(data), content_type="application/json")

@app.route('/')
def index():
    return render_template_string(HTML, keyword=None, images=None)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    keywords_str = request.form.get('keywords', '')
    keywords = [kw.strip().lower() for kw in keywords_str.split(',') if kw.strip()]

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png', 'gif']:
        return "Unsupported file type", 400
    filename = f"{uuid.uuid4().hex}.{ext}"
    blob_path = f"images/{filename}"

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_path)
    blob.upload_from_file(file, content_type=file.content_type)
    blob.make_public()
    image_url = blob.public_url

    keywords_data = read_keywords()
    for kw in keywords:
        if kw not in keywords_data:
            keywords_data[kw] = []
        keywords_data[kw].append({
            "url": image_url,
            "filename": filename,
            "keywords": keywords
        })
    write_keywords(keywords_data)

    return redirect(url_for('index'))

@app.route('/search')
def search():
    keyword = request.args.get('keyword', '').strip().lower()
    if not keyword:
        return redirect(url_for('index'))
    keywords_data = read_keywords()
    images = keywords_data.get(keyword, [])
    return render_template_string(HTML, keyword=keyword, images=images)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)