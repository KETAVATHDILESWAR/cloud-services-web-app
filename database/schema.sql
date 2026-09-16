CREATE DATABASE IF NOT EXISTS cloud_weather;

USE cloud_weather;

CREATE TABLE IF NOT EXISTS weather_searches (
    id INT AUTO_INCREMENT PRIMARY KEY,

    city VARCHAR(100) NOT NULL,

    country VARCHAR(100),

    latitude DECIMAL(10, 6),

    longitude DECIMAL(10, 6),

    temperature DECIMAL(5, 2),

    humidity INT,

    weather_condition VARCHAR(100),

    searched_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
);
