"""
Entry point for the Handmade Creations website.

Run with:
    python run.py
"""

from backend import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
