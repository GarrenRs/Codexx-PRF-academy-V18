# Codexx Academy - Portfolio Management Platform

### Overview
Codexx Academy is a professional multi-tenant portfolio management platform. It allows admins to manage users and inquiries, while providing professionals with tools to build and host their portfolios.

### Authentication & Access
- **Login:** Access via `/dashboard/login`.
- **Registration:** Disabled. New accounts are managed by the administrator.
- **Admin Access:** Standard admin credentials are set via environment variables.

### Deployment & Configuration
The system is optimized for **Render** with the following setup:
- **Build Command:** `./build.sh` (handles dependency installation and directory setup)
- **Start Command:** `gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 120 --reuse-port app:app`
- **Database:** PostgreSQL (using `DATABASE_URL`). The system automatically handles `postgres://` to `postgresql://` conversion.

### Core Features
- **Multi-tenant isolation:** User data stored in individual JSON files.
- **CRM & Inquiries:** Integrated tracking of leads and messages.
- **Security:** Rate limiting and IP activity logging.
- **Themes:** Support for multiple professional themes.
