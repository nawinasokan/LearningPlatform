-- SQL Sandbox schema initialization
-- Creates a separate sandbox schema with realistic datasets for the SQL Lab

CREATE DATABASE interview_sandbox;

\c interview_sandbox;

CREATE SCHEMA IF NOT EXISTS sandbox;

-- ─── Employees Dataset ─────────────────────────────────────────────
CREATE TABLE sandbox.departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    budget NUMERIC(12,2)
);

CREATE TABLE sandbox.employees (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    department_id INT REFERENCES sandbox.departments(id),
    salary NUMERIC(10,2) NOT NULL,
    hire_date DATE NOT NULL,
    job_title VARCHAR(100),
    manager_id INT REFERENCES sandbox.employees(id),
    is_active BOOLEAN DEFAULT TRUE
);

-- ─── Orders Dataset ────────────────────────────────────────────────
CREATE TABLE sandbox.customers (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    city VARCHAR(100),
    country VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sandbox.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    price NUMERIC(10,2) NOT NULL,
    stock_quantity INT DEFAULT 0
);

CREATE TABLE sandbox.orders (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES sandbox.customers(id),
    order_date TIMESTAMP DEFAULT NOW(),
    total_amount NUMERIC(12,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    shipping_city VARCHAR(100)
);

CREATE TABLE sandbox.order_items (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES sandbox.orders(id),
    product_id INT REFERENCES sandbox.products(id),
    quantity INT NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL
);

-- ─── Banking Dataset ───────────────────────────────────────────────
CREATE TABLE sandbox.accounts (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    balance NUMERIC(14,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sandbox.transactions (
    id SERIAL PRIMARY KEY,
    account_id INT REFERENCES sandbox.accounts(id),
    transaction_type VARCHAR(50) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    description VARCHAR(255),
    transaction_date TIMESTAMP DEFAULT NOW()
);

-- ─── Seed Departments ──────────────────────────────────────────────
INSERT INTO sandbox.departments (name, location, budget) VALUES
('Engineering', 'Chennai', 5000000),
('Product', 'Bangalore', 3000000),
('Marketing', 'Mumbai', 2000000),
('HR', 'Chennai', 1000000),
('Finance', 'Delhi', 1500000),
('DevOps', 'Hyderabad', 2500000);

-- ─── Seed Employees ────────────────────────────────────────────────
INSERT INTO sandbox.employees (first_name, last_name, email, department_id, salary, hire_date, job_title, manager_id) VALUES
('Nawin', 'Asokan', 'nawin@example.com', 1, 85000, '2024-08-01', 'Software Developer', NULL),
('Priya', 'Sharma', 'priya@example.com', 1, 95000, '2022-03-15', 'Senior Developer', NULL),
('Arjun', 'Kumar', 'arjun@example.com', 2, 90000, '2023-01-10', 'Product Manager', NULL),
('Divya', 'Nair', 'divya@example.com', 1, 75000, '2024-01-20', 'Backend Developer', 2),
('Rahul', 'Singh', 'rahul@example.com', 3, 70000, '2023-06-01', 'Marketing Analyst', NULL),
('Anjali', 'Patel', 'anjali@example.com', 4, 65000, '2022-11-15', 'HR Manager', NULL),
('Vikram', 'Reddy', 'vikram@example.com', 6, 88000, '2023-08-01', 'DevOps Engineer', NULL),
('Meera', 'Krishnan', 'meera@example.com', 1, 92000, '2021-09-01', 'Lead Developer', NULL),
('Suresh', 'Babu', 'suresh@example.com', 5, 78000, '2023-04-01', 'Finance Analyst', NULL),
('Lakshmi', 'Iyer', 'lakshmi@example.com', 2, 85000, '2022-07-01', 'Product Designer', NULL);

-- ─── Seed Customers ────────────────────────────────────────────────
INSERT INTO sandbox.customers (full_name, email, city, country) VALUES
('Alice Johnson', 'alice@test.com', 'Mumbai', 'India'),
('Bob Smith', 'bob@test.com', 'Chennai', 'India'),
('Carol White', 'carol@test.com', 'Bangalore', 'India'),
('David Brown', 'david@test.com', 'Delhi', 'India'),
('Emma Wilson', 'emma@test.com', 'Hyderabad', 'India'),
('Frank Davis', 'frank@test.com', 'Pune', 'India'),
('Grace Martinez', 'grace@test.com', 'Kolkata', 'India'),
('Henry Taylor', 'henry@test.com', 'Chennai', 'India');

-- ─── Seed Products ─────────────────────────────────────────────────
INSERT INTO sandbox.products (name, category, price, stock_quantity) VALUES
('Python Handbook', 'Books', 599.00, 100),
('Django Course', 'Courses', 1999.00, 50),
('FastAPI Bundle', 'Courses', 2499.00, 30),
('PostgreSQL Guide', 'Books', 799.00, 75),
('Docker Masterclass', 'Courses', 1499.00, 60),
('AWS Certification Prep', 'Courses', 3999.00, 25),
('Redis in Action', 'Books', 699.00, 80),
('System Design Book', 'Books', 999.00, 40);

-- ─── Seed Orders ───────────────────────────────────────────────────
INSERT INTO sandbox.orders (customer_id, total_amount, status, shipping_city) VALUES
(1, 2598.00, 'delivered', 'Mumbai'),
(2, 1999.00, 'delivered', 'Chennai'),
(3, 599.00, 'shipped', 'Bangalore'),
(4, 4598.00, 'processing', 'Delhi'),
(1, 799.00, 'delivered', 'Mumbai'),
(5, 2499.00, 'delivered', 'Hyderabad'),
(6, 1499.00, 'shipped', 'Pune'),
(7, 3999.00, 'pending', 'Kolkata');

INSERT INTO sandbox.order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 599.00), (1, 3, 1, 2499.00),
(2, 2, 1, 1999.00),
(3, 1, 1, 599.00),
(4, 6, 1, 3999.00), (4, 2, 1, 1999.00),  -- corrected total approximation
(5, 4, 1, 799.00),
(6, 3, 1, 2499.00),
(7, 5, 1, 1499.00),
(8, 6, 1, 3999.00);

-- ─── Seed Accounts ─────────────────────────────────────────────────
INSERT INTO sandbox.accounts (customer_name, account_type, balance) VALUES
('Nawin Asokan', 'savings', 125000.00),
('Priya Sharma', 'checking', 45000.00),
('Arjun Kumar', 'savings', 280000.00),
('Divya Nair', 'checking', 32000.00),
('Rahul Singh', 'savings', 95000.00);

INSERT INTO sandbox.transactions (account_id, transaction_type, amount, description, transaction_date) VALUES
(1, 'credit', 85000.00, 'Salary - August 2024', '2024-08-31'),
(1, 'debit', 15000.00, 'Rent payment', '2024-09-01'),
(1, 'credit', 85000.00, 'Salary - September 2024', '2024-09-30'),
(2, 'credit', 95000.00, 'Salary', '2024-09-30'),
(2, 'debit', 25000.00, 'Shopping', '2024-10-05'),
(3, 'credit', 90000.00, 'Salary', '2024-09-30'),
(3, 'credit', 50000.00, 'Freelance payment', '2024-10-10'),
(4, 'credit', 75000.00, 'Salary', '2024-09-30'),
(4, 'debit', 10000.00, 'Utilities', '2024-10-02');
