"""
app.py – local development entry point only.

For production (Railway) gunicorn uses the app factory:
    web: gunicorn "app:create_app()"
"""
import os

from app import create_app

application = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    application.run(host="127.0.0.1", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")

