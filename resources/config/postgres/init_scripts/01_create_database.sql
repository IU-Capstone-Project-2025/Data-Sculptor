-- Create database if it doesn't exist
SELECT 'CREATE DATABASE datasculptor'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'datasculptor'); 