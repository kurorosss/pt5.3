--CREATE USER repl_user WITH REPLICATION ENCRYPTED PASSWORD 'repl_user';
--SELECT pg_create_physical_replication_slot('replication_slot');

CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL
);

CREATE TABLE phone_numbers (
    id SERIAL PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL
);
