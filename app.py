import os
import io
import qrcode
import netifaces
from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'mp4', 'mp3', 'csv', 'xlsx', 'docx'])

app = Flask(__name__)
app.secret_key = 'rainbow-secret-key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML = '''
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rainbow ファイル転送</title>
  <link rel="stylesheet" href="/static/rainbow.css">
  <style>body{background:#fafaff;}</style>
</head>
<body>
  <header style="padding:2rem 1rem 1rem 1rem;">
    <h1 style="color:var(--primary);">Rainbow ファイル転送</h1>
    <p>この端末 ⇔ 他端末（スマホ/PC）でファイルをやり取りできます</p>
    <div style="margin-top:1rem;">
      <span>スマホからアクセス：</span>
      <img src="/qr" alt="QRコード" style="vertical-align:middle;width:120px;height:120px;border:1px solid #ddd;background:#fff;">
      <br>
      <span style="font-size:0.9em;color:#555;">URL: {{ access_url }}</span>
    </div>
  </header>
  <main style="padding:2rem;max-width:700px;margin:auto;">
    <section>
      <h2>ファイルを送信</h2>
      <form method="post" enctype="multipart/form-data">
        <input type="file" name="file" class="input">
        <button class="btn btn-primary" type="submit">アップロード</button>
      </form>
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <div class="alert alert-success">{{ messages[0] }}</div>
        {% endif %}
      {% endwith %}
    </section>
    <section style="margin-top:2rem;">
      <h2>受信ファイル一覧</h2>
      <ul class="list">
        {% for filename in files %}
        <li class="list-item">
          <a href="/download/{{ filename }}" class="btn btn-secondary">{{ filename }}</a>
        </li>
        {% else %}
        <li class="list-item">ファイルなし</li>
        {% endfor %}
      </ul>
    </section>
  </main>
  <footer style="text-align:center;padding:2rem 1rem 1rem 1rem;color:#888;">
    &copy; 2025 Shizuku Tanaka | Rainbow OSS
  </footer>
</body>
</html>
'''

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_local_ip():
    # Wi-Fiや有線LANのローカルIPを自動取得
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addrs:
            for addr in addrs[netifaces.AF_INET]:
                ip = addr.get('addr')
                if ip and not ip.startswith('127.'):
                    return ip
    return '127.0.0.1'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('ファイルが選択されていません')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('ファイルが選択されていません')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash(f'{filename} を受信しました')
            return redirect(url_for('index'))
        else:
            flash('許可されていないファイル形式です')
            return redirect(request.url)
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    local_ip = get_local_ip()
    access_url = f'http://{local_ip}:5000/'
    return render_template_string(HTML, files=files, access_url=access_url)

@app.route('/qr')
def qr():
    local_ip = get_local_ip()
    url = f'http://{local_ip}:5000/'
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
