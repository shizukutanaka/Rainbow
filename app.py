import os
import io
import qrcode
import netifaces
import secrets
from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for, flash, send_file, jsonify, abort
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
      <form id="uploadForm" enctype="multipart/form-data">
        <input type="file" name="file" class="input" multiple>
        <button class="btn btn-primary" type="submit">アップロード</button>
      </form>
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
    <section style="margin-top:2rem;">
      <h2>受信ファイル一覧</h2>
      <ul class="list">
        {% for filename in files %}
        <li class="list-item">
          <a href="#" class="btn btn-secondary" onclick="showPinDialog('{{ filename }}', '{{ pins[filename] }}')">{{ filename }}</a>
          <span style="margin-left:0.5em;font-size:0.9em;color:#888;">PIN: <span style="user-select:all;">{{ pins[filename] }}</span></span>
          <form method="post" action="/delete/{{ filename }}" style="display:inline;margin-left:1em;">
            <button class="btn btn-error" type="submit" onclick="return confirm('本当に削除しますか？');">削除</button>
          </form>
        </li>
        {% else %}
        <li class="list-item">ファイルなし</li>
        {% endfor %}
      </ul>
      <div id="dl-progress-container" style="width:100%;background:#eee;border-radius:6px;display:none;margin:1em 0;">
        <div id="dl-progress-bar" style="height:12px;width:0;background:var(--success);border-radius:6px;"></div>
      </div>
      <div id="pin-dialog" style="display:none;position:fixed;left:0;top:0;width:100vw;height:100vh;background:rgba(0,0,0,0.3);z-index:1000;align-items:center;justify-content:center;">
        <div style="background:#fff;padding:2em;border-radius:12px;min-width:280px;box-shadow:0 2px 16px #0002;">
          <h3>PINを入力してください</h3>
          <input id="pin-input" type="text" maxlength="6" style="font-size:1.5em;text-align:center;width:100px;">
          <input id="pin-filename" type="hidden">
          <div style="margin-top:1em;text-align:right;">
            <button onclick="closePinDialog()" class="btn btn-secondary">キャンセル</button>
            <button onclick="submitPin()" class="btn btn-primary">ダウンロード</button>
          </div>
          <div id="pin-error" style="color:red;margin-top:0.5em;display:none;"></div>
        </div>
      </div>
      <script>
      // PINダイアログ
      function showPinDialog(filename, pin) {
        document.getElementById('pin-dialog').style.display = 'flex';
        document.getElementById('pin-input').value = '';
        document.getElementById('pin-filename').value = filename;
        document.getElementById('pin-error').style.display = 'none';
      }
      function closePinDialog() {
        document.getElementById('pin-dialog').style.display = 'none';
      }
      function submitPin() {
        const filename = document.getElementById('pin-filename').value;
        const pin = document.getElementById('pin-input').value;
        const bar = document.getElementById('dl-progress-bar');
        const container = document.getElementById('dl-progress-container');
        bar.style.width = '0';
        container.style.display = 'block';
        fetch(`/download/${filename}?pin=${pin}`).then(resp => {
          if (resp.status === 403) {
            document.getElementById('pin-error').textContent = 'PINが違います';
            document.getElementById('pin-error').style.display = 'block';
            container.style.display = 'none';
            return;
          }
          if (!resp.ok) {
            document.getElementById('pin-error').textContent = 'ダウンロード失敗';
            document.getElementById('pin-error').style.display = 'block';
            container.style.display = 'none';
            return;
          }
          const reader = resp.body.getReader();
          const contentLength = +resp.headers.get('Content-Length');
          let received = 0;
          let chunks = [];
          function pump() {
            return reader.read().then(({done, value}) => {
              if (done) {
                container.style.display = 'none';
                // ダウンロード保存
                const blob = new Blob(chunks);
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = filename;
                a.click();
                closePinDialog();
                return;
              }
              received += value.length;
              chunks.push(value);
              bar.style.width = (received / contentLength * 100) + '%';
              return pump();
            });
          }
          return pump();
        });
      }
      </script>
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
                ip = addr.get('addr')
                if ip and not ip.startswith('127.'):
                    return ip
    return '127.0.0.1'

HISTORY_FILE = 'transfer_history.json'
PIN_FILE = 'file_pins.json'

# 転送履歴の保存
import json
def add_history(entry):
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                hist = json.load(f)
        else:
            hist = []
    except Exception:
        hist = []
    hist.insert(0, entry)
    hist = hist[:10]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(hist, f, ensure_ascii=False)

def load_history():
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

# ファイルごとのPIN管理

def get_pins():
    try:
        with open(PIN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def set_pin(filename, pin):
    pins = get_pins()
    pins[filename] = pin
    with open(PIN_FILE, 'w', encoding='utf-8') as f:
        json.dump(pins, f, ensure_ascii=False)

def get_pin(filename):
    pins = get_pins()
    return pins.get(filename)

def del_pin(filename):
    pins = get_pins()
    if filename in pins:
        del pins[filename]
        with open(PIN_FILE, 'w', encoding='utf-8') as f:
            json.dump(pins, f, ensure_ascii=False)

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
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                pin = str(secrets.randbelow(900000) + 100000)  # 6桁PIN
                set_pin(filename, pin)
                add_history(f"受信: {filename} (PIN: {pin})")
                saved += 1
        if saved:
            flash(f'{saved} ファイルを受信しました')
        else:
            flash('許可されていないファイル形式です')
        return redirect(url_for('index'))
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    local_ip = get_local_ip()
    access_url = f'http://{local_ip}:5000/'
    history = load_history()
    pins = {f: get_pin(f) for f in files}
    return render_template_string(HTML, files=files, access_url=access_url, history=history, pins=pins)


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
    pin = request.args.get('pin')
    expected = get_pin(filename)
    if expected is None or pin != expected:
        return ('', 403)
    add_history(f"ダウンロード: {filename} (PIN: {pin})")
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
    app.run(host='0.0.0.0', port=5000, debug=False)
