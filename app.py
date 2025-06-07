import os
from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for, flash
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
    return render_template_string(HTML, files=files)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
