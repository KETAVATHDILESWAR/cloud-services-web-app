# Cloud Weather Dashboard

A Flask-based cloud web application demonstrating AWS compute,
object storage, managed database, networking, IAM and monitoring.

## Project

Cloud Services & Web App Deployment

## Architecture

User
  ↓
Route 53
  ↓
Nginx
  ↓
Gunicorn
  ↓
Flask Application on EC2
  ├── Open-Meteo API
  ├── Amazon RDS MySQL
  ├── Amazon S3
  └── Amazon CloudWatch

## AWS Services

### Amazon EC2

Hosts the Flask application.

### Amazon RDS

MySQL database stores weather search history.

### Amazon S3

Private object storage for application assets.

### Amazon VPC

Provides cloud networking and security groups.

### IAM

Provides controlled permissions to the EC2 application.

### CloudWatch

Provides:

- Application logs
- Nginx logs
- System logs
- CPU metrics
- Memory metrics
- Disk metrics
- CloudWatch alarms

### Route 53

Used for custom DNS during the final deployment stage.

## Application Features

- Search weather by city
- Current weather
- 7-day forecast
- Temperature
- Humidity
- Wind speed
- Weather condition
- RDS search history
- S3 connectivity
- Application health endpoint
- AWS service status cards

## API

The application uses Open-Meteo for weather and geocoding data.

## Endpoints

/
    Weather dashboard

/health
    Application health

/db-test
    RDS connectivity test

/s3-test
    S3 connectivity test

/s3-upload-test
    S3 upload test

## Local Installation

Create a virtual environment:

```bash
python3 -m venv venv
