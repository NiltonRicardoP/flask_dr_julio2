#!/usr/bin/env python3
import os

from app import create_app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", 5000))
    app.run(debug=app.config.get("DEBUG", False), host=host, port=port)
