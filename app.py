"""Entry point for the ACEest Fitness & Gym service.

Development:  python app.py
Production:   gunicorn --bind 0.0.0.0:5000 app:app
"""
import os

from aceest import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
