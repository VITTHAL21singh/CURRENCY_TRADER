from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os, random

app = Flask(__name__)
app.secret_key = 'super_secret_trading_key_for_bca' # Required for sessions
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root', # Leave empty '' if no password
    'database': 'currency_db',
    'charset': 'utf8mb4'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# ─── FRONTEND ROUTES ───
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

# ─── AUTHENTICATION API ───
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username, password = data.get('username'), data.get('password')
    if not username or not password: return jsonify({'error': 'Missing fields'}), 400

    hashed_pw = generate_password_hash(password)
    db = get_db(); cur = db.cursor()
    try:
        # Create User
        cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed_pw))
        user_id = cur.lastrowid
        # Grant $100 starting balance
        cur.execute("INSERT INTO wallets (user_id, currency_code, balance) VALUES (%s, 'USD', 100.00)", (user_id,))
        db.commit()
        return jsonify({'message': 'Registration successful'})
    except mysql.connector.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        cur.close(); db.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username=%s", (data.get('username'),))
    user = cur.fetchone()
    cur.close(); db.close()

    if user and check_password_hash(user['password_hash'], data.get('password')):
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({'message': 'Logged in', 'username': user['username']})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/api/auth/me', methods=['GET'])
def me():
    if 'user_id' in session: return jsonify({'logged_in': True, 'username': session['username']})
    return jsonify({'logged_in': False}), 401

# ─── TRADING API ───
@app.route('/api/rates')
def get_rates():
    db = get_db(); cur = db.cursor(dictionary=True)
    # Market Volatility: Fluctuate rates +/- 0.5% every time they are fetched
    cur.execute("SELECT id, rate FROM exchange_rates")
    for r in cur.fetchall():
        new_rate = float(r['rate']) * random.uniform(0.995, 1.005)
        cur.execute("UPDATE exchange_rates SET rate=%s WHERE id=%s", (new_rate, r['id']))
    db.commit()
    
    cur.execute("SELECT from_currency, to_currency, rate FROM exchange_rates")
    res = cur.fetchall(); cur.close(); db.close()
    return jsonify(res)

@app.route('/api/wallet')
def get_wallet():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT w.currency_code, w.balance, c.flag 
        FROM wallets w JOIN currencies c ON w.currency_code = c.code 
        WHERE w.user_id=%s AND w.balance > 0
    """, (session['user_id'],))
    res = cur.fetchall(); cur.close(); db.close()
    return jsonify(res)

@app.route('/api/history')
def get_history():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM transactions WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (session['user_id'],))
    res = cur.fetchall()
    for r in res: r['created_at'] = r['created_at'].strftime('%H:%M:%S')
    cur.close(); db.close()
    return jsonify(res)

@app.route('/api/trade', methods=['POST'])
def trade():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    f_curr, t_curr, amt = data['from'], data['to'], float(data['amount'])
    user_id = session['user_id']
    
    db = get_db(); cur = db.cursor(dictionary=True)
    
    # Verify balance
    cur.execute("SELECT balance FROM wallets WHERE user_id=%s AND currency_code=%s", (user_id, f_curr))
    bal = cur.fetchone()
    if not bal or float(bal['balance']) < amt: 
        cur.close(); db.close(); return jsonify({'error': 'Insufficient funds!'}), 400

    # Get Rate
    cur.execute("SELECT rate FROM exchange_rates WHERE from_currency=%s AND to_currency=%s", (f_curr, t_curr))
    r = cur.fetchone()
    if r: rate = float(r['rate'])
    else:
        cur.execute("SELECT rate FROM exchange_rates WHERE from_currency=%s AND to_currency=%s", (t_curr, f_curr))
        inv = cur.fetchone()
        if inv: rate = 1.0 / float(inv['rate'])
        else: return jsonify({'error': 'Pair not found'}), 404

    bought = amt * rate

    # Process Transaction
    cur.execute("UPDATE wallets SET balance = balance - %s WHERE user_id=%s AND currency_code=%s", (amt, user_id, f_curr))
    cur.execute("""
        INSERT INTO wallets (user_id, currency_code, balance) VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE balance = balance + %s
    """, (user_id, t_curr, bought, bought))
    cur.execute("""
        INSERT INTO transactions (user_id, from_currency, to_currency, amount, converted_amount, rate)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, f_curr, t_curr, amt, bought, rate))
    
    db.commit(); cur.close(); db.close()
    return jsonify({'success': True, 'bought': bought})

if __name__ == '__main__':
    app.run(debug=True, port=5000)