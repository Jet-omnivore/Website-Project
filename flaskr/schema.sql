DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS user_data;
DROP TABLE IF EXISTS lease;
DROP TABLE IF EXISTS withdrawal_record;
DROP TABLE IF EXISTS user_order;

CREATE TABLE user (
        id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
        gmail TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );

CREATE TABLE user_data (
        id INTEGER PRIMARY KEY,
        availabe_coins INTEGER NOT NULL,
        balance INTEGER NOT NULL,
        daily_income INTEGER NOT NULL,
        total_income INTEGER NOT NULL,
        withdrawable_amount INTEGER NOT NULL,
        withdrawn_amount INTEGER NOT NULL
    );    

CREATE TABLE lease (
    user_id INTEGER NOT NULL,
    daily_income INTEGER NOT NULL,
    total_income INTEGER NOT NULL,
    leased_days INTEGER NOT NULL,
    accumulated_income INTEGER NOT NULL,
    bought_date DATE NOT NULL,
    status TEXT NOT NULL
    );

CREATE TABLE withdrawal_record (
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    bought_date DATE NOT NULL,
    status TEXT NOT NULL
    );

CREATE TABLE user_order (
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    order_id TEXT NOT NULL,
    respcode TEXT NOT NULL,
    order_date DATE NOT NULL
    );
