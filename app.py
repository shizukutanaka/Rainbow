import os
import io
import qrcode
import netifaces
import threading
import webbrowser
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
  <style>
    body { background: #fafaff; }
    .main-wrap { padding: 2rem 1rem; max-width: 520px; margin: auto; }
    .qr-block { margin: 1.5rem 0 2rem 0; text-align: center; }
    .qr-block img { width: 120px; height: 120px; border: 1px solid #ddd; background: #fff; }
    .file-list { margin-top: 1.5rem; }
    .alert { margin: 1em 0; }
    @media (max-width: 600px) { .main-wrap { padding: 1rem 0.5rem; } }
  </style>
</head>
<body>
  <header style="padding:2rem 1rem 0.5rem 1rem;text-align:center;">
    <h1 style="color:var(--primary);font-size:2.2em;">Rainbow ファイル転送</h1>
    <div class="qr-block">
      <div style="margin-bottom:0.5em;">スマホからアクセス：</div>
      <img src="/qr" alt="QRコード">
      <div style="font-size:0.95em;color:#555;margin-top:0.5em;">URL: <span style="user-select:all;">{{ access_url }}</span></div>
    </div>
  </header>
  <main class="main-wrap">
    <section style="margin-bottom:2.2em;">
      <h2>ファイルを送信</h2>
      <form id="uploadForm" enctype="multipart/form-data" style="display:flex;gap:0.7em;align-items:center;flex-wrap:wrap;">
        <input type="file" name="file" class="input" multiple style="flex:1;min-width:180px;">
        <button class="btn btn-primary" type="submit">アップロード</button>
      </form>
      <div style="font-size:0.95em;color:#888;margin-top:0.3em;">※ 複数ファイル選択・ドラッグ＆ドロップ対応</div>
      <div id="progress-container" style="width:100%;background:#eee;border-radius:6px;display:none;margin:1em 0;">
        <div id="progress-bar" style="height:12px;width:0;background:var(--primary);border-radius:6px;"></div>
      </div>
      <script>
      // ドラッグ＆ドロップ対応
      const input = document.querySelector('input[type=file]');
      input.addEventListener('dragover', e => { e.preventDefault(); });
      input.addEventListener('drop', e => {
        e.preventDefault();
        input.files = e.dataTransfer.files;
      });
      // アップロード進捗バー
      document.getElementById('uploadForm').onsubmit = function(e) {
        e.preventDefault();
        const form = e.target;
        const data = new FormData(form);
        const xhr = new XMLHttpRequest();
        const bar = document.getElementById('progress-bar');
        const container = document.getElementById('progress-container');
        bar.style.width = '0';
        container.style.display = 'block';
        xhr.upload.onprogress = function(evt) {
          if (evt.lengthComputable) {
            const percent = (evt.loaded / evt.total) * 100;
            bar.style.width = percent + '%';
          }
        };
        xhr.onload = function() {
          container.style.display = 'none';
          location.reload();
        };
        xhr.open('POST', '/', true);
        xhr.send(data);
      };
      </script>
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <div class="alert alert-success">{{ messages[0] }}</div>
        {% endif %}
      {% endwith %}
    </section>
    <section class="file-list">
      <h2 style="margin-bottom:0.7em;">受信ファイル一覧</h2>
      <ul class="list">
        {% for filename in files %}
        <li class="list-item" style="display:flex;align-items:center;gap:1em;justify-content:space-between;">
          <span style="flex:1;overflow-wrap:anywhere;">{{ filename }}</span>
          <a href="/download/{{ filename }}" class="btn btn-secondary" download>ダウンロード</a>
          <form method="post" action="/delete/{{ filename }}" style="display:inline;">
            <button class="btn btn-error" type="submit" onclick="return confirm('本当に削除しますか？');">削除</button>
          </form>
        </li>
        {% else %}
        <li class="list-item">ファイルなし</li>
        {% endfor %}
      </ul>
    </section>
    <section style="margin-top:2rem;">
      <h2>転送履歴（直近10件）</h2>
      <ul class="list">
        {% for item in history %}
        <li class="list-item">{{ item }}</li>
        {% else %}
        <li class="list-item">履歴なし</li>
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
                ip = addr['addr']
                if ip != '127.0.0.1' and not ip.startswith('169.'):
                    return ip
    return '127.0.0.1'

def open_browser():
    ip = get_local_ip()
    url = f'http://{ip}:5000/'
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('ファイルが選択されていません')
            return redirect(request.url)
        files = request.files.getlist('file')
        if not files or files[0].filename == '':
            flash('ファイルが選択されていません')
            return redirect(request.url)
        saved = 0
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                base, ext = os.path.splitext(filename)
                count = 1
                # 同名ファイルがあれば _1, _2... で回避
                while os.path.exists(save_path):
                    filename = f"{base}_{count}{ext}"
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    count += 1
                file.save(save_path)
                saved += 1
        if saved:
            flash(f'{saved} ファイルを受信しました')
        else:
            flash('許可されていないファイル形式です')
        return redirect(url_for('index'))
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

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(path):
        os.remove(path)
        del_pin(filename)
        flash(f'{filename} を削除しました')
    else:
        flash('ファイルが見つかりません')
    return redirect(url_for('index'))

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    open_browser()
    app.run(host='0.0.0.0', port=5000, debug=False)
