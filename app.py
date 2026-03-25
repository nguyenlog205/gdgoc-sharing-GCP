import os
import json
import uuid
import yaml
import argparse
from flask import Flask, request, render_template_string, redirect, url_for
from google.cloud import storage

# ==============================================
# CONFIG LOADER 
# ==============================================
parser = argparse.ArgumentParser()
parser.add_argument("--config", type=str, required=True)
args = parser.parse_args()

with open(args.config, 'r') as f:
    cfg = yaml.safe_load(f)

app = Flask(__name__)

# ==============================================
# STORAGE LOGIC
# ==============================================
def get_client():
    return storage.Client(project=cfg.get('project_id'))

def initialize_bucket():
    client = get_client()
    bucket = client.bucket(cfg['bucket_name'])
    if not bucket.exists():
        client.create_bucket(bucket, location=cfg['region'])

def get_keywords():
    bucket = get_client().bucket(cfg['bucket_name'])
    blob = bucket.blob(cfg['keywords_file'])
    return json.loads(blob.download_as_text()) if blob.exists() else {}

def save_keywords(data):
    bucket = get_client().bucket(cfg['bucket_name'])
    blob = bucket.blob(cfg['keywords_file'])
    blob.upload_from_string(json.dumps(data), content_type="application/json")

# ==============================================
# UI TEMPLATE 
# ==============================================
HTML = """
<!doctype html>
<html>
<head>
    <title>{{ service_name }}</title>
    <style>
        :root {
            --google-blue: #4285F4; --google-red: #EA4335;
            --google-yellow: #FBBC05; --google-green: #34A853;
            --bg: #ffffff; --text: #202124; --gray: #f1f3f4;
        }
        body { font-family: 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; display: flex; justify-content: center; }
        .container { width: 100%; max-width: 800px; padding: 60px 20px; }
        
        /* GDGoC Dots */
        .dots { display: flex; gap: 5px; margin-bottom: 10px; }
        .dot { width: 10px; height: 10px; border-radius: 50%; }
        
        h1 { font-size: 28px; font-weight: 500; margin: 0 0 40px 0; letter-spacing: -0.5px; }
        
        /* Minimalist Form */
        .upload-zone { background: var(--gray); padding: 30px; border-radius: 16px; margin-bottom: 40px; }
        input[type="text"], input[type="file"] { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
        
        button { background: var(--google-blue); color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: 0.2s; }
        button:hover { opacity: 0.8; }
        
        .search-bar { display: flex; gap: 10px; margin-bottom: 50px; }
        .search-bar input { flex-grow: 1; margin: 0; }

        /* Grid */
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }
        .card { border-radius: 12px; overflow: hidden; border: 1px solid var(--gray); transition: 0.3s; }
        .card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.05); }
        .card img { width: 100%; height: 200px; object-fit: cover; border-bottom: 1px solid var(--gray); }
        .card-tags { padding: 12px; display: flex; flex-wrap: wrap; gap: 5px; }
        .tag { font-size: 11px; background: var(--gray); padding: 4px 10px; border-radius: 20px; color: #5f6368; }
    </style>
</head>
<body>
    <div class="container">
        <div class="dots">
            <div class="dot" style="background:var(--google-blue)"></div>
            <div class="dot" style="background:var(--google-red)"></div>
            <div class="dot" style="background:var(--google-yellow)"></div>
            <div class="dot" style="background:var(--google-green)"></div>
        </div>
        <h1>{{ service_name }}</h1>

        <div class="upload-zone">
            <form method="post" enctype="multipart/form-data" action="/upload">
                <input type="file" name="file" accept="image/*" required>
                <input type="text" name="keywords" placeholder="Keywords (e.g. AI, UIT, Google)" required>
                <button type="submit">Upload Image</button>
            </form>
        </div>

        <form class="search-bar" method="get" action="/search">
            <input type="text" name="keyword" placeholder="Search by keyword..." required>
            <button type="submit" style="background:#202124">Search</button>
        </form>

        {% if keyword %}
            <div class="grid">
            {% for img in images %}
                <div class="card">
                    <img src="{{ img.url }}">
                    <div class="card-tags">
                        {% for kw in img.keywords %}<span class="tag">#{{ kw }}</span>{% endfor %}
                    </div>
                </div>
            {% endfor %}
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

# ==============================================
# ROUTE
# ==============================================
@app.route('/')
def index():
    return render_template_string(HTML, service_name=cfg['service_name'], keyword=None)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    kws = [k.strip().lower() for k in request.form.get('keywords', '').split(',') if k.strip()]
    
    filename = f"{uuid.uuid4().hex}.{file.filename.split('.')[-1]}"
    blob = get_client().bucket(cfg['bucket_name']).blob(f"{cfg['upload_folder']}{filename}")
    
    blob.upload_from_file(file, content_type=file.content_type)
    blob.make_public()
    
    data = get_keywords()
    for kw in kws:
        if kw not in data: data[kw] = []
        data[kw].append({"url": blob.public_url, "keywords": kws})
    save_keywords(data)
    return redirect(url_for('index'))

@app.route('/search')
def search():
    kw = request.args.get('keyword', '').lower()
    images = get_keywords().get(kw, [])
    return render_template_string(HTML, service_name=cfg['service_name'], keyword=kw, images=images)

if __name__ == '__main__':
    initialize_bucket()
    app.run(host=cfg['host'], port=cfg['port'], debug=cfg['debug'])