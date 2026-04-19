from flask import Flask, jsonify, request, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
import os, random

app = Flask(__name__)
# Secret key should be an env variable for security
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_for_dev')

# FIX: Add CORS for Vercel support
CORS(app, supports_credentials=True)

def get_db():
    # Use DATABASE_URL from Railway/Supabase environment
    return psycopg2.connect(os.getenv('DATABASE_URL'), cursor_factory=RealDictCursor)

# ... (Auth routes remain similar, ensure you use psycopg2 syntax)

@app.route('/api/rates')
def get_rates():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT id, rate FROM exchange_rates")
    rates = cur.fetchall()
    for r in rates:
        new_rate = float(r['rate']) * random.uniform(0.995, 1.005)
        # FIX: Ensure parameters are passed correctly for PostgreSQL
        cur.execute("UPDATE exchange_rates SET rate=%s WHERE id=%s", (new_rate, r['id']))
    db.commit()
    
    cur.execute("SELECT from_currency, to_currency, rate FROM exchange_rates")
    res = cur.fetchall(); cur.close(); db.close()
    return jsonify(res)

@app.route('/api/trade', methods=['POST'])
def trade():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    f_curr, t_curr, amt = data['from'], data['to'], float(data['amount'])
    user_id = session['user_id']
    
    db = get_db(); cur = db.cursor()
    
    # Verify balance
    cur.execute("SELECT balance FROM wallets WHERE user_id=%s AND currency_code=%s", (user_id, f_curr))
    bal = cur.fetchone()
    if not bal or float(bal['balance']) < amt: 
        cur.close(); db.close(); return jsonify({'error': 'Insufficient funds!'}), 400

    # Get Rate Logic
    cur.execute("SELECT rate FROM exchange_rates WHERE from_currency=%s AND to_currency=%s", (f_curr, t_curr))
    r = cur.fetchone()
    if r: rate = float(r['rate'])
    else:
        cur.execute("SELECT rate FROM exchange_rates WHERE from_currency=%s AND to_currency=%s", (t_curr, f_curr))
        inv = cur.fetchone()
        if inv: rate = 1.0 / float(inv['rate'])
        else: return jsonify({'error': 'Pair not found'}), 404

    bought = amt * rate

    # FIX: PostgreSQL UPSERT Syntax (ON CONFLICT)
    try:
        cur.execute("UPDATE wallets SET balance = balance - %s WHERE user_id=%s AND currency_code=%s", (amt, user_id, f_curr))
        
        cur.execute("""
            INSERT INTO wallets (user_id, currency_code, balance) VALUES (%s, %s, %s)
            ON CONFLICT (user_id, currency_code) 
            DO UPDATE SET balance = wallets.balance + EXCLUDED.balance
        """, (user_id, t_curr, bought))
        
        cur.execute("""
            INSERT INTO transactions (user_id, from_currency, to_currency, amount, converted_amount, rate)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, f_curr, t_curr, amt, bought, rate))
        
        db.commit()
        return jsonify({'success': True, 'bought': bought})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close(); db.close()
