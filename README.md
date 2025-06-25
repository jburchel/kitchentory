# Kitchentory

A mobile-optimized web application that helps users track their kitchen inventory and discover recipes based on available ingredients.

## Features

- **Inventory Management**: Track what's in your kitchen with barcode scanning and smart categorization
- **Recipe Discovery**: Find recipes based on ingredients you already have
- **Shopping Intelligence**: Generate smart shopping lists based on your needs
- **Expiration Tracking**: Never waste food with expiration alerts
- **Household Sharing**: Share your inventory with family members

## Tech Stack

- **Backend**: Django + Django REST Framework
- **Frontend**: HTMX + Alpine.js + Tailwind CSS
- **Database**: PostgreSQL (Supabase)
- **Deployment**: Railway
- **PWA**: Progressive Web App with offline support

## Development Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/kitchentory.git
cd kitchentory
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scriptsctivate
```

3. Install dependencies
```bash
pip install -r requirements.txt
npm install
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run migrations
```bash
python manage.py migrate
```

6. Create a superuser
```bash
python manage.py createsuperuser
```

7. Run the development server
```bash
python manage.py runserver
```

8. In another terminal, watch for CSS changes
```bash
npm run watch-css
```

## Project Documentation

- [Product Requirements Document](Docs/PRD.md)
- [Design Specification](Docs/DesignSpec.md)
- [Development Task List](Docs/TaskList.md)

## Contributing

Please see [CLAUDE.md](CLAUDE.md) for development guidelines and conventions.

## License

This project is licensed under the MIT License.
