# PrintEstimation

A Django web application for managing printing jobs, cost estimation, and client relationships in a print shop environment.

## Features

- **Job Management**: Create, track, and manage printing jobs with detailed specifications
- **Cost Estimation**: Automated calculation of printing costs based on materials, operations, and quantities
- **Client Management**: Handle client relationships and job history
- **Operations Management**: Define printing operations, paper types, and sizes
- **PDF Export**: Generate professional estimates and job sheets as PDFs
- **User Authentication**: Role-based access control for different user types
- **Status Tracking**: Monitor job progress from draft to completion

## Tech Stack

- **Framework**: Django 5.2+
- **Database**: PostgreSQL (configurable via environment)
- **Frontend**: Bootstrap 5 with Crispy Forms
- **Authentication**: Custom user model with role-based permissions
- **Styling**: CSS3 with responsive design

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements/development.txt
   ```

2. **Set Environment Variables**
   Create a `.env` file with:
   ```
   DB_NAME=printing_estimation
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   ```

3. **Database Setup**
   ```bash
   python manage.py migrate
   python manage.py setup_groups
   python manage.py createsuperuser
   ```

4. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

## Apps Structure

- **accounts**: User management and client relationships
- **core**: Home page and general functionality
- **jobs**: Job creation, estimation, and PDF export
- **operations**: Printing operations, paper types, and sizes

## Docker Support

```bash
docker-compose up -d
```

## Contributing

This project follows Django best practices with proper separation of concerns across apps.
