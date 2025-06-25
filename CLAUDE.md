# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Claude AI Interaction Guidelines

- Begin each response with the words 'Let's get to work!'

## Development Commands

### Python/Django Commands
```bash
# Activate virtual environment first
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Database operations
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Django management
python manage.py check
python manage.py collectstatic
python manage.py shell
```

### Frontend/CSS Commands
```bash
# Build CSS for production
npm run build-css

# Watch CSS changes during development
npm run watch-css

# Manual Tailwind build
npx tailwindcss -i ./static/css/input.css -o ./static/css/output.css --watch
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8

# Run tests
pytest

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## Architecture Overview

### Project Structure
Kitchentory is a Django web application with a mobile-first design using HTMX, Alpine.js, and Tailwind CSS. The project follows Django's app-based architecture with these core apps:

- **accounts**: Custom user authentication with household sharing capabilities
- **inventory**: Kitchen inventory management (barcode scanning, expiration tracking)
- **recipes**: Recipe discovery based on available ingredients
- **shopping**: Smart shopping list generation

### Settings Architecture
The project uses environment-specific settings:
- `kitchentory/settings/base.py`: Common settings
- `kitchentory/settings/development.py`: Local development
- `kitchentory/settings/production.py`: Production (Railway)
- `kitchentory/settings/__init__.py`: Auto-loads based on DJANGO_ENV

### Authentication System
Uses a custom User model (`accounts.User`) extending Django's AbstractUser:
- Email-based authentication (not username)
- Household sharing with invite codes
- Profile fields: dietary restrictions, phone, date of birth
- Integration with Django-Allauth for social auth

### Database Design
- **User Model**: Custom with household relationships
- **Household Model**: Enables family/group sharing with invite codes
- Uses PostgreSQL via Supabase in production, SQLite in development
- Automatic household invite code generation

### Frontend Architecture
- **Templates**: Django templates with mobile-first responsive design
- **CSS**: Tailwind CSS with custom component classes
- **JavaScript**: Alpine.js for reactivity, HTMX for dynamic updates
- **PWA Ready**: Service worker and manifest support planned

### Supabase Integration
Utility functions in `kitchentory/utils/supabase_client.py`:
- `get_supabase_client()`: Regular client for user operations
- `get_supabase_admin_client()`: Admin client for privileged operations
- `sync_user_to_supabase()`: Syncs Django users to Supabase auth
- `SupabaseStorage`: File upload/management helper

### Key Environment Variables
- `DATABASE_URL`: PostgreSQL connection (Supabase)
- `SUPABASE_URL` & `SUPABASE_ANON_KEY`: Client operations
- `SUPABASE_SERVICE_KEY`: Admin operations
- `DJANGO_ENV`: Controls which settings module loads (development/production)

## Development Workflow

### Adding New Features
1. Create models in appropriate app
2. Run `python manage.py makemigrations app_name`
3. Apply with `python manage.py migrate`
4. Add forms, views, and templates
5. Update URL configurations
6. Build CSS if styling changes: `npm run build-css`

### CSS Development
Always edit `static/css/input.css` (Tailwind source), never `static/css/output.css` (generated). Use custom component classes defined in the input file for consistency.

### Testing User Authentication
The custom signup form includes household invite code functionality. Test with:
1. Create household as first user
2. Use generated invite code to join as second user
3. Verify household member permissions

### Database Migrations
When changing the User model, you may need to reset the database:
```bash
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### Deployment Notes
- Railway auto-deploys from main branch
- Uses Dockerfile for containerization
- Environment variables set in Railway dashboard
- Static files served via WhiteNoise
- Database migrations run automatically on deploy

## Code Guidelines

### File Management
- Make every effort to keep individual files to 500 lines of code or less

## Project Documentation 

### Specification Files
- Use the @Docs/PRD.md as our spec file
- Use the @Docs/DesignSpec.md file for design decisions

## Development Best Practices

- When you complete items from the @Docs/TaskList.md make sure to check them off the list