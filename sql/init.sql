CREATE DATABASE ship_voyage;

-- Use the created database
\c ship_voyage

CREATE TABLE ship
(
    mmsi SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(255) NOT NULL,
    callsign VARCHAR(255) NOT NULL,
    destination VARCHAR(255),
    timestamp BIGINT NOT NULL
);

-- This user has already been created by setting the POSTGRES_USER
-- and POSTGRES_PASSWORD environment variables in the docker compose file.
GRANT ALL PRIVILEGES ON DATABASE ship_voyage TO ship_voyage_producer_user;

CREATE USER clickhouse_consumer_user WITH PASSWORD 'password456';
GRANT CONNECT ON DATABASE ship_voyage TO clickhouse_consumer_user;
GRANT SELECT ON ship TO clickhouse_consumer_user;
