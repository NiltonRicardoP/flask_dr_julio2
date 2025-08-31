#!/usr/bin/env python3
from app import app, create_initial_data
import os

if __name__ == '__main__':
    # Ensure upload directory exists
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    courses_dir = os.path.join(uploads_dir, 'courses')
    if not os.path.exists(courses_dir):
        os.makedirs(courses_dir)
    content_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'course_content')
    if not os.path.exists(content_dir):
        os.makedirs(content_dir)
        
    # Initialize default data (admin user and settings)
    create_initial_data()

    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
