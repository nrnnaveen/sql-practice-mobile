# SQL Practice Mobile

A mobile-friendly SQL practice web application built with Flask.

## Features

- User authentication (signup / login / logout)
- SQL editor with Monaco Editor integration
- Support for MySQL and PostgreSQL databases
- Query history tracking per session
- Table explorer sidebar

## Project Structure

```
sql-practice-mobile/
├── app.py                  # Application entry point
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── Procfile                # Deployment process file
│
├── app/                    # Main application package
│   ├── __init__.py         # Flask app factory
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py         # User model (SQLite)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py         # Login / signup / logout routes
│   │   ├── dashboard.py    # Dashboard route
│   │   └── editor.py       # SQL editor route
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py     # Authentication business logic
│   │   ├── mysql_service.py    # MySQL operations
│   │   └── postgres_service.py # PostgreSQL operations
│   ├── utils/
│   │   ├── __init__.py
│   │   └── db_engines.py   # Database engine helpers
│   ├── templates/
│   │   ├── base.html       # Base layout template
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── signup.html
│   │   ├── dashboard.html
│   │   └── editor.html
│   └── static/
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── editor.js
│
└── tests/
    ├── __init__.py
    └── test_auth.py        # Unit tests for authentication
```

## Setup

### Prerequisites

- Python 3.8+
- MySQL or PostgreSQL (optional, for DB practice)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/nrnnaveen/sql-practice-mobile.git
   cd sql-practice-mobile
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables (optional):
   ```bash
   export SECRET_KEY=your_secret_key
   export MYSQL_HOST=localhost
   export MYSQL_USER=root
   export MYSQL_PASSWORD=yourpassword
   export MYSQL_DATABASE=test_db
   export POSTGRES_HOST=localhost
   export POSTGRES_USER=postgres
   export POSTGRES_PASSWORD=yourpassword
   export POSTGRES_DATABASE=test_db
   ```

4. Run the application:
   ```bash
   python app.py
   ```

   The app will be available at `http://localhost:5000`.

## Running Tests

```bash
python -m pytest tests/
```

## Deployment

The application includes a `Procfile` for deployment on platforms like Heroku:

```
web: gunicorn app:app
```
