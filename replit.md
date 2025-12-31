# Codexx Academy - Portfolio Management Platform

### Overview
Codexx Academy is a professional multi-tenant portfolio management platform providing client CRM, analytics, and content management. Built with Flask and using JSON file storage, it offers professional portfolio hosting, client relationship management, portfolio analytics, and customizable themes. The platform aims to provide a robust solution for professionals to manage their online presence and client interactions.

### User Preferences
- **Request:** Complete removal of payment/subscription system

### System Architecture
The platform is built on Flask and uses a multi-tenant JSON file-based data architecture (`data.json`) for per-user portfolio isolation, chosen for its simplicity and ease of setup. Authentication is session-based, securing user access. Six professional themes are available for portfolio customization, with full dark mode support.

Key features include:
-   **Client Management CRM:** Tracks client stages (Lead to Completed), project details, and revenue.
-   **Notification Systems:** Integrates with Telegram for real-time alerts and supports SMTP for HTML-formatted email notifications. Both are configurable per user.
-   **Visitor Analytics:** Tracks anonymized visitor data (IP, user agent, referrer, geolocation) to provide insights into portfolio engagement.
-   **Backup & Recovery:** Features an automated hourly backup system using APScheduler, with manual backup creation and restoration capabilities, including automatic cleanup of old backups.
-   **Security System:** Implements IP-based rate limiting, security headers (CSP, HSTS), and secure session management.
-   **Contact Form System:** Captures inquiries, tracks read status, and triggers notifications.
-   **Admin Dashboard:** Provides comprehensive tools for user management, portfolio settings, content management (projects, skills, clients, messages), and backup management.

The project structure is organized with `app.py` as the main application file, `config.py` for configuration, and separate directories for static assets (`static/`), templates (`templates/`), backups (`backups/`), and security logs (`security/`).

### External Dependencies
-   **Backend:** Flask 2.x
-   **Database:** JSON files (`data.json`)
-   **Authentication:** `werkzeug.security`
-   **Scheduling:** `APScheduler`
-   **Email:** SMTP (`smtplib`)
-   **PDF Generation:** `WeasyPrint`
-   **Frontend Framework:** Bootstrap 5
-   **Styling:** Custom CSS + SCSS
-   **Icons:** Font Awesome 6
-   **Python Libraries:** `email-validator`, `flask-dance`, `flask-login`, `flask-sqlalchemy`, `gunicorn`, `oauthlib`, `psycopg2-binary`, `pyjwt`