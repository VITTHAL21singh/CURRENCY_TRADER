DROP DATABASE IF EXISTS currency_db;
CREATE DATABASE currency_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE currency_db;

-- 1. Users Table (Authentication)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
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
    id INT AUTO_INCREMENT PRIMARY KEY,
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    rate DECIMAL(18,8) NOT NULL,
    FOREIGN KEY (from_currency) REFERENCES currencies(code),
    FOREIGN KEY (to_currency) REFERENCES currencies(code)
);

-- 4. User Wallets (Tied to user_id)
CREATE TABLE wallets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    currency_code VARCHAR(3) NOT NULL,
    balance DECIMAL(18,4) DEFAULT 0.0000,
    UNIQUE KEY unique_wallet (user_id, currency_code),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (currency_code) REFERENCES currencies(code)
);

-- 5. Transaction History (Tied to user_id)
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    amount DECIMAL(18,4) NOT NULL,
    converted_amount DECIMAL(18,6) NOT NULL,
    rate DECIMAL(18,8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Seed Initial Data
INSERT INTO currencies (code, name, symbol, flag) VALUES
('USD', 'US Dollar', '$', '🇺🇸'), ('EUR', 'Euro', '€', '🇪🇺'), 
('INR', 'Indian Rupee', '₹', '🇮🇳'), ('GBP', 'British Pound', '£', '🇬🇧'), 
('JPY', 'Japanese Yen', '¥', '🇯🇵');

INSERT INTO exchange_rates (from_currency, to_currency, rate) VALUES
('USD', 'INR', 83.50), ('USD', 'EUR', 0.92), 
('USD', 'GBP', 0.78), ('USD', 'JPY', 154.00);