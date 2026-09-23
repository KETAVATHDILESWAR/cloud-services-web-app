# Cloud Services & Web App Deployment

A Flask web application deployed on AWS using multiple cloud services.

## Architecture

User
→ Route 53
→ EC2
→ Flask/Gunicorn
→ RDS PostgreSQL

The application also uses:

- Amazon S3
- Amazon VPC
- IAM
- AWS Secrets Manager
- Amazon CloudWatch

## Technologies

- Python
- Flask
- PostgreSQL
- AWS EC2
- AWS RDS
- AWS S3
- AWS VPC
- AWS IAM
- AWS Secrets Manager
- AWS CloudWatch
- Amazon Route 53
- Nginx
- Gunicorn

## AWS Services Used

### EC2

Hosts the Flask web application.

### RDS

Stores application data using PostgreSQL.

### S3

Provides object storage.

### VPC

Provides network isolation using public and private subnets.

### IAM

Provides controlled AWS permissions for the EC2 instance.

### Secrets Manager

Stores database credentials securely.

### CloudWatch

Collects monitoring metrics and application/server logs.

### Route 53

Provides DNS routing for the live application.

## Security

- Database is not publicly accessible.
- RDS accepts connections only from the EC2 security group.
- SSH access is restricted to the administrator's IP.
- Database credentials are not stored in GitHub.
- Secrets are stored separately from application source code.
- EC2 uses an IAM role instead of hard-coded AWS credentials.
- Environment variables are used for application configuration.

## Application Flow

User
→ Route 53
→ EC2
→ Nginx
→ Gunicorn
→ Flask
→ RDS

## Repository

https://github.com/KETAVATHDILESWAR/cloud-services-web-app

## Live Website

YOUR_LIVE_WEBSITE_URL

## Screenshots

- EC2
- RDS
- S3
- VPC
- IAM
- CloudWatch
- Live Application

## Learning Outcome

This project demonstrates the deployment of a web application using compute,
database, storage, networking, IAM, monitoring, secrets management and DNS
services in AWS.
