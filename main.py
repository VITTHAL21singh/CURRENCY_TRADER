import os
import random
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'cyber_trading_key_2026')

# Allow Vercel to communicate with Railway
CORS(app, supports_credentials=True)

def get_db():
    # DATABASE_URL should be set in Railway/Render Env Variables
    db_url = os.getenv('DATABASE_URL')
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username, password = data.get('username'), data.get('password')
    if not username or not password: return jsonify({'error': 'Missing fields'}), 400

    hashed_pw = generate_password_hash(password)
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id", (username, hashed_pw))
        user_id = cur.fetchone()['id']
        cur.execute("INSERT INTO wallets (user_id, currency_code, balance) VALUES (%s, 'USD', 100.00)", (user_id,))
        db.commit()
        return jsonify({'message': 'Registration successful'})
    except Exception as e:
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        cur.close(); db.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE username=%s", (data.get('username'),))
    user = cur.fetchone()
    cur.close(); db.close()

    if user and check_password_hash(user['password_hash'], data.get('password')):
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({'username': user['username']})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/api/auth/me', methods=['GET'])
def me():
    if 'user_id' in session: return jsonify({'username': session['username']})
    return jsonify({'error': 'Not logged in'}), 401

@app.route('/api/rates')
def get_rates():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT id, rate FROM exchange_rates")
    rows = cur.fetchall()
    for r in rows:
        new_rate = float(r['rate']) * random.uniform(0.998, 1.002)
        cur.execute("UPDATE exchange_rates SET rate=%s WHERE id=%s", (new_rate, r['id']))
    db.commit()
    cur.execute("SELECT from_currency, to_currency, rate FROM exchange_rates")
    res = cur.fetchall(); cur.close(); db.close()
    return jsonify(res)

@app.route('/api/wallet')
def get_wallet():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    db = get_db(); cur = db.cursor()
    cur.execute("""
        SELECT w.currency_code, w.balance, c.flag 
        FROM wallets w JOIN currencies c ON w.currency_code = c.code 
        WHERE w.user_id=%s AND w.balance > 0
    """, (session['user_id'],))
    res = cur.fetchall(); cur.close(); db.close()
    return jsonify(res)

@app.route('/api/trade', methods=['POST'])
def trade():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    f_curr, t_curr, amt = data['from'], data['to'], float(data['amount'])
    user_id = session['user_id']
    
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT balance FROM wallets WHERE user_id=%s AND currency_code=%s", (user_id, f_curr))
    bal = cur.fetchone()
    if not bal or float(bal['balance']) < amt: 
        return jsonify({'error': 'Insufficient funds!'}), 400

    cur.execute("SELECT rate FROM exchange_rates WHERE from_currency=%s AND to_currency=%s", (f_curr, t_curr))
    r = cur.fetchone()
    rate = float(r['rate']) if r else 1.0
    bought = amt * rate

    try:
        cur.execute("UPDATE wallets SET balance = balance - %s WHERE user_id=%s AND currency_code=%s", (amt, user_id, f_curr))
        cur.execute("""
            INSERT INTO wallets (user_id, currency_code, balance) VALUES (%s, %s, %s)
            ON CONFLICT (user_id, currency_code) 
            DO UPDATE SET balance = wallets.balance + EXCLUDED.balance
        """, (user_id, t_curr, bought))
        cur.execute("INSERT INTO transactions (user_id, from_currency, to_currency, amount, converted_amount, rate) VALUES (%s, %s, %s, %s, %s, %s)",
                    (user_id, f_curr, t_curr, amt, bought, rate))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback(); return jsonify({'error': str(e)}), 500
    finally:
        cur.close(); db.close()

@app.route('/api/history')
def get_history():
    if 'user_id' not in session: return jsonify([]), 401
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT * FROM transactions WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (session['user_id'],))
    res = cur.fetchall()
    for r in res: r['created_at'] = r['created_at'].strftime('%H:%M:%S')
    cur.close(); db.close()
    return jsonify(res)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
