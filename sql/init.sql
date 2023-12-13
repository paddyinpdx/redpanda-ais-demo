-- Create database
CREATE DATABASE ship_voyage;

-- Use the created database 
\c ship_voyage

-- Create user
-- CREATE USER ship_voyage_user WITH PASSWORD 'password123';

-- Create table
CREATE TABLE ship
(
    mmsi SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(255) NOT NULL,
    callsign VARCHAR(255) NOT NULL,
    destination VARCHAR(255),
    receiver_timestamp TIMESTAMPTZ NOT NULL
);

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ship_voyage TO ship_voyage_user;
