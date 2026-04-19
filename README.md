# CURRENCY_TRADER
# 💹 Currency Trader Pro
**A Full-Stack Cybersecurity-Focused Trading Simulation**

Currency Trader Pro is a web-based platform that simulates a real-time currency exchange market. Developed for the BCA Semester 2 DBMS Lab, this project focuses on secure user authentication, atomic database transactions, and real-time data visualization.

---

## 🚀 Deployment Links
- **Live Frontend (Vercel):** [Your-Vercel-Link-Here]
- **API Backend (Render):** [Your-Render-Link-Here]

---

## 🛠️ Technology Stack
- **Frontend:** HTML5, CSS3 (Glassmorphism UI), JavaScript (ES6), Chart.js
- **Backend:** Python (Flask), Flask-CORS, Flask-Session
- **Database:** MySQL (Hosted on Railway.app)
- **Security:** SHA-256 Password Hashing (Werkzeug), Environment Variable Protection

---

## ⚙️ Key Features
- **User Authentication:** Secure registration and login system.
- **New User Bonus:** Newly registered users are automatically credited with a $100.00 USD starting balance.
- **Dynamic Market:** Exchange rates fluctuate +/- 0.5% every 5 seconds to simulate real market volatility.
- **Live Graphing:** Real-time trend analysis using Chart.js based on 5-second polling intervals.
- **Atomic Trading:** Prevents race conditions and debt; the backend validates balances before executing any BUY or SELL orders.
- **Transaction Ledger:** A permanent log of all user trades stored in the MySQL database.

---

## 🔒 Cybersecurity Implementation
As a Cybersecurity specialization student, I have implemented the following security measures:
1. **Password Salting & Hashing:** Passwords are never stored in plain text. We utilize the `PBKDF2` algorithm with SHA-256.
2. **Environment Isolation:** Sensitive database credentials (Host, User, Password) are stored in server-side environment variables, ensuring they never leak into the public version control (GitHub).
3. **CORS Policy:** Restricted Cross-Origin Resource Sharing to ensure only the authorized frontend can communicate with the trading API.
4. **Session Security:** Utilizes cryptographically signed cookies to manage user sessions.

---

## 📂 Project Structure
```text
├── main.py              # Flask REST API & Market Logic
├── index.html           # SPA Frontend (HTML/CSS/JS)
├── requirements.txt     # Python Dependencies for Render
├── setup.sql            # MySQL Database Schema & Seed Data
└── .gitignore           # Prevents sensitive file leakage
