import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Security: Fetch Secret Key and DB URL from Render Environment Variables
app.secret_key = os.getenv('SECRET_KEY', 'default_fallback_key_123')
DATABASE_URL = os.getenv('DATABASE_URL')

# Enable CORS: Allows your Vercel frontend to communicate with this Render API
CORS(app, supports_credentials=True)

# --- DATABASE CONNECTION ---
def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Database Connection Error: {e}")
        return None

# --- AUTHENTICATION ROUTES ---

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing fields"}), 400

    hashed_password = generate_password_hash(password)
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Create User
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id", 
                    (username, hashed_password))
        user_id = cur.fetchone()['id']
        
        # BCA Bonus: Credit $100.00 USD to new user
        cur.execute("INSERT INTO wallets (user_id, currency_code, balance) VALUES (%s, 'USD', 100.00)", 
                    (user_id,))
        
        conn.commit()
        return jsonify({"message": "Registration successful"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "User already exists"}), 400
    finally:
        cur.close()
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (data.get('username'),))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user and check_password_hash(user['password'], data.get('password')):
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({"username": user['username']}), 200
    
    return jsonify({"error": "Invalid username or password"}), 401

@app.route('/api/auth/me', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({"username": session['username']}), 200
    return jsonify({"error": "Not logged in"}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200

# --- TRADING & MARKET ROUTES ---

@app.route('/api/wallet', methods=['GET'])
def get_wallet():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT currency_code, balance FROM wallets WHERE user_id = %s", (session['user_id'],))
    wallet = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(wallet)

@app.route('/api/rates', methods=['GET'])
def get_rates():
    conn = get_db_connection()
    cur = conn.cursor()
    # Fetch rates and simulate a small fluctuation for the "Live Market" feel
    cur.execute("SELECT from_currency, to_currency, rate FROM rates")
    rates = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rates)

@app.route('/api/trade', methods=['POST'])
def execute_trade():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    user_id = session['user_id']
    from_curr = data.get('from')
    to_curr = data.get('to')
    amount = float(data.get('amount'))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1. Verify Balance
        cur.execute("SELECT balance FROM wallets WHERE user_id = %s AND currency_code = %s", (user_id, from_curr))
        balance_row = cur.fetchone()
        
        if not balance_row or float(balance_row['balance']) < amount:
            return jsonify({"error": "Insufficient balance"}), 400

        # 2. Get Exchange Rate
        cur.execute("SELECT rate FROM rates WHERE from_currency = %s AND to_currency = %s", (from_curr, to_curr))
        rate_row = cur.fetchone()
        rate = float(rate_row['rate']) if rate_row else 1.0
        
        converted_amount = amount * rate

        # 3. Deduct from 'From' Wallet
        cur.execute("UPDATE wallets SET balance = balance - %s WHERE user_id = %s AND currency_code = %s", 
                    (amount, user_id, from_curr))

        # 4. Add to 'To' Wallet (UPSERT logic for PostgreSQL)
        cur.execute("""
            INSERT INTO wallets (user_id, currency_code, balance) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (user_id, currency_code) 
            DO UPDATE SET balance = wallets.balance + EXCLUDED.balance
        """, (user_id, to_curr, converted_amount))

        # 5. Log Transaction
        cur.execute("""
            INSERT INTO transactions (user_id, from_currency, to_currency, amount, converted_amount, rate)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, from_curr, to_curr, amount, converted_amount, rate))

        conn.commit()
        return jsonify({"message": "Trade successful"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/history', methods=['GET'])
def get_history():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE user_id = %s ORDER BY created_at DESC LIMIT 10", (session['user_id'],))
    history = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(history)

if __name__ == '__main__':
    # Render requires the app to listen on the port provided by the environment
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
