🌿 Landscape Gardening Platform
A backend system for managing landscape gardening services, including appointment scheduling, team management, and a serverless workflow using AWS SAM.


🚀 Features
Create and manage appointments
Assign team members based on availability
Prevent overlapping bookings (time-slot based logic)
Weather-based validation for outdoor work
Rate-limited APIs
Pagination & filtering
Serverless extension using AWS SAM (Lambda + DynamoDB)

🧱 Tech Stack
Backend
Django
Django REST Framework
SQLite (default)
Serverless (Optional Module)
AWS SAM
AWS Lambda
API Gateway
DynamoDB
SNS

📂 Project Structure
Landscape-platform/
│
├── Landscape_Gardening_Platform/ # Django project
│ ├── core/ # Main app (appointments, services, team)
│ ├── Grounds_Management/ # Django settings
│ ├── manage.py
│ ├── requirements.txt
│
├── appointment-scheduler/ # AWS SAM project
│ ├── template.yaml
│ ├── src/
│ └── events/
│
└── Diagram.jpg # Architecture diagram


⚙️ Django Setup
1. Create virtual environment
python3 -m venv venv
source venv/bin/activate


2. Install dependencies
pip install -r requirements.txt


3. Run migrations
python manage.py migrate


4. Create superuser (optional)
python manage.py createsuperuser


5. Run server
python manage.py runserver

App runs at:

http://127.0.0.1:8000/


🔗 API Endpoints
Create Appointment
POST /api/appointments/request/

List Appointments
GET /api/appointments/

Supports:

pagination
filtering by status and date

☁️ AWS SAM Setup (Optional)
Requirements
AWS CLI
AWS SAM CLI
Docker

Configure AWS
aws configure


Build project
cd appointment-scheduler
sam build


Run locally
sam local start-api


Test API
curl -X POST http://127.0.0.1:3000/appointments \
-H "Content-Type: application/json" \
-d '{"client_id":"123","service":"lawn mowing","scheduled_time":"2026-04-05T10:00:00Z","is_outdoor":true}'


⚠️ Notes
Docker must be running for SAM
AWS credentials required for DynamoDB access
Ensure DynamoDB table exists in your region
Do NOT commit venv/ or db.sqlite3
