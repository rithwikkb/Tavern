# Tavern

A social networking web app where authors can post (plain text, Markdown, or images), follow each other, become friends, and comment on and like posts. Built with Django REST Framework and React.

Originally built as a team project for CMPUT 404 at the University of Alberta.

## Features

- Sign up, log in, and edit your profile (display name, GitHub link, profile picture)
- Create, edit, and delete posts with public, unlisted, or friends-only visibility
- Follow requests, followers, and friends (mutual follows)
- Comments and likes on posts and comments
- Pull your public GitHub activity into your stream
- Django admin panel for managing users and content
- Interactive API docs at `/swagger/`

## Tech stack

- **Backend:** Django 5.2, Django REST Framework, Simple JWT, WhiteNoise, Gunicorn
- **Frontend:** React 18, React Router, Material UI
- **Database:** PostgreSQL in production, SQLite locally

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
npm run build
cd ..

cd mistyrose
export DJANGO_DEBUG=True
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then open http://127.0.0.1:8000. The admin panel is at `/admin/`.

Run the backend tests with `python manage.py test` from `mistyrose/`.

## Deploying

The repo includes a `render.yaml` blueprint and a `build.sh` script. See `.env.example` for every environment variable the app reads. At minimum, production needs `DJANGO_SECRET_KEY` and a `DATABASE_URL` pointing at a hosted Postgres database.

## Team

Syjer Asuncion, Rithwik Korukonda Bhattar, Franco Bonilla, Xiangxu Meng, Kelly Shih, Sapandeep Singh

## License

MIT
