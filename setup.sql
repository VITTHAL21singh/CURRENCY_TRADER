DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS wallets;
DROP TABLE IF EXISTS exchange_rates;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS currencies;

-- 1. Users Table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Currencies
CREATE TABLE currencies (
    code VARCHAR(3) PRIMARY KEY,
    name VARCHAR(60) NOT NULL,
    symbol VARCHAR(5) NOT NULL,
    flag VARCHAR(10) NOT NULL
);

-- 3. Exchange Rates
CREATE TABLE exchange_rates (
    id SERIAL PRIMARY KEY,
    from_currency VARCHAR(3) NOT NULL REFERENCES currencies(code),
    to_currency VARCHAR(3) NOT NULL REFERENCES currencies(code),
    rate DECIMAL(18,8) NOT NULL
);

-- 4. User Wallets
CREATE TABLE wallets (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    currency_code VARCHAR(3) NOT NULL REFERENCES currencies(code),
    balance DECIMAL(18,4) DEFAULT 0.0000,
    CONSTRAINT unique_wallet UNIQUE (user_id, currency_code)
);

-- 5. Transaction History
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    amount DECIMAL(18,4) NOT NULL,
    converted_amount DECIMAL(18,6) NOT NULL,
    rate DECIMAL(18,8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Initial Data
INSERT INTO currencies (code, name, symbol, flag) VALUES
('USD', 'US Dollar', '$', '🇺🇸'), ('EUR', 'Euro', '€', '🇪🇺'), 
('INR', 'Indian Rupee', '₹', '🇮🇳'), ('GBP', 'British Pound', '£', '🇬🇧'), 
('JPY', 'Japanese Yen', '¥', '🇯🇵');

INSERT INTO exchange_rates (from_currency, to_currency, rate) VALUES
('USD', 'INR', 83.50), ('USD', 'EUR', 0.92), 
('USD', 'GBP', 0.78), ('USD', 'JPY', 154.00);
