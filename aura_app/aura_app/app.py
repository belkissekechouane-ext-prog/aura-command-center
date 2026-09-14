import os, sqlite3, hashlib, hmac, base64
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-render')
DB_PATH = os.environ.get('DB_PATH', 'aura.db')

USERS = {
    
    'nesrine': {'display': 'Nesrine', 'salt': 'YkJ+IC4c+50Q/z2fy1YomA==', 'hash': 'M8D/K0eEGU3GMi9vz1hfXGOKN4tZdX7Nbv5cQ4AFBCU='},
    'adel': {'display': 'Adel', 'salt': 'rkrm0MQy2tEsScpRU2TmiQ==', 'hash': 'aNy0apF27DHhFZwcybh6rbHaH1DeO3myVyMXjtEROwg='},
    'alix': {'display': 'Alix', 'salt': 'Uv2TMHtO11TwxejaeUIdEA==', 'hash': 'JEuHg8qIGcVmLwBsk098KDXnlKdrGINN+4vc47e7GGQ='},
    'ahmed': {'display': 'Ahmed', 'salt': 'pnn1/1FsZFeVMfAtZ7QhWg==', 'hash': '1L7mmUKyKvwNBm4OkNwUjMk0KsTbQ6IvBo7Nbhdd27k='},
    'cyrin': {'display': 'Cyrin', 'salt': 'idSPDKKk86GNV79qznvKeg==', 'hash': 'B0XRKgYF459SGJ4N8UAn31NvJGae6goUUaaYnSln78U='},
    'ahlam': {'display': 'Ahlam', 'salt': 'CaGZQWaot6fM7dZ7/cmAHQ==', 'hash': 'YSTaje9F3DUINpG4xgZNRFFLngQCzM673tTWuVee3Kw='},
}


def verify_password(password, salt_b64, hash_b64):
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(hash_b64)
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 240000)
    return hmac.compare_digest(actual, expected)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS stats (
        username TEXT PRIMARY KEY,
        calls INTEGER NOT NULL DEFAULT 0,
        appointments INTEGER NOT NULL DEFAULT 0,
        sales INTEGER NOT NULL DEFAULT 0,
        target INTEGER NOT NULL DEFAULT 10
    )''')
    for username in USERS:
        conn.execute('INSERT OR IGNORE INTO stats(username, calls, appointments, sales, target) VALUES (?,0,0,0,10)', (username,))
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET','POST'])
def login():
    if session.get('username'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username','').strip().lower()
        password = request.form.get('password','')
        user = USERS.get(username)
        if user and verify_password(password, user['salt'], user['hash']):
            session['username'] = username
            return redirect(url_for('dashboard'))
        flash('Identifiant ou mot de passe incorrect.')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
    conn = get_db()
    rows = conn.execute('SELECT * FROM stats').fetchall()
    conn.close()
    stats = {r['username']: dict(r) for r in rows}
    me = stats[username]
    leaderboard = sorted(
        [{'username': u, 'display': USERS[u]['display'], **stats[u]} for u in USERS],
        key=lambda x: (x['sales'], x['appointments'], x['calls']), reverse=True
    )
    totals = {
        'calls': sum(x['calls'] for x in leaderboard),
        'appointments': sum(x['appointments'] for x in leaderboard),
        'sales': sum(x['sales'] for x in leaderboard),
    }
    progress = min(100, round((me['sales'] / max(me['target'], 1)) * 100))
    return render_template('dashboard.html', me=me, display=USERS[username]['display'], leaderboard=leaderboard, totals=totals, progress=progress)

@app.post('/update')
def update():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
    def num(name, default=0):
        try:
            return max(0, int(request.form.get(name, default)))
        except Exception:
            return default
    calls = num('calls')
    appointments = num('appointments')
    sales = num('sales')
    target = max(1, num('target', 10))
    conn = get_db()
    conn.execute('UPDATE stats SET calls=?, appointments=?, sales=?, target=? WHERE username=?',
                 (calls, appointments, sales, target, username))
    conn.commit(); conn.close()
    flash('Tes statistiques ont été mises à jour ✨')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/health')
def health():
    return {'status': 'ok'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
