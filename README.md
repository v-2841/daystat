# DayStat

DayStat is a small personal Django app for tracking daily health and expense
data. It keeps daily records for weight, calories, and cycle starts, shows
calendar and chart summaries, and stores simple expense notes.

The app is built around a daily check-in flow: each date has a single record per
user, so the main page can be used as a compact journal for the current day and
as an archive for previous dates. The rest of the interface turns those daily
records into calendar markers, predictions, charts, and summary tables.

## Features

- Daily page for weight, calories, and cycle start tracking.
- Calendar with recorded values and predicted cycle dates.
- Weight and calories chart with selectable ranges.
- Cycle length and smoothed weight chart over the full available history.
- Weekly calories summary.
- Expense tracker with weekly and monthly summaries.
- User login, logout, profile editing, and password change pages.
- Django admin for `Daystat` and `Expense` records.

## Functional Overview

### Daily Tracking

The home page opens the record for the current day. A user can enter weight,
calories, and mark whether the day is the start of a new cycle. The page also
shows the current cycle day based on the latest previous cycle start.

Past days are available through dated URLs, so existing records can be edited
after the fact. Future dates are intentionally blocked with a separate page,
because the app is designed around recording known daily data rather than
planning future entries.

### Calendar

The calendar shows daily records in a month view. Each recorded day can display
weight and calories, and cycle start days are highlighted separately.

The app also predicts upcoming cycle start dates from recent cycle history. It
uses the last year of recorded cycle starts, gives more weight to newer cycles,
and projects dates for the next year. The calendar page shows the next predicted
cycle date and whether it is upcoming, today, or overdue.

### Charts

The weight and calories chart lets the user switch between metrics and time
ranges: week, month, six months, year, and five years. Longer ranges smooth the
data with the same moving-average helper used by the chart API, so long-term
trends are easier to read.

The cycle and weight chart compares completed cycle lengths with smoothed weight
over the full available history. Cycle length points are plotted on the date of
the next cycle start, because that is when the previous cycle length becomes
known.

### Calories Summary

The calories summary groups records by year and week, then shows average
calories for each week that has recorded calorie data. This gives a compact view
of weekly intake trends without opening the full chart.

### Expenses

The expense tracker stores simple expense records with a value and optional
note. The main expense page shows recent expenses and provides a form for adding
new ones. Existing expenses can be opened from the table, edited, or deleted.

There are also weekly and monthly expense summary pages. They group expenses by
calendar period, total the values, and concatenate notes so repeated spending
patterns are easier to scan.

### User Account

The app uses Django authentication. Logged-in users can update their profile,
change password, and keep their day statistics and expenses separated from other
users' data.

## Tech Stack

- Python 3.13+
- Django 5.2
- SQLite
- Chart.js and FullCalendar on the frontend
- Bootstrap 5 and Bootstrap Icons
- Poetry for dependency management
- Docker Compose with Gunicorn and Caddy for containerized deployment

## Environment

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Available settings:

```env
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=127.0.0.1, localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000, http://localhost:8000
```

For production, use a long random `SECRET_KEY`, set `DEBUG=False`, and replace
`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` with the real domain names.

## Local Development

Install dependencies:

```bash
poetry install
```

Apply migrations:

```bash
poetry run python manage.py migrate
```

Create an admin user:

```bash
poetry run python manage.py createsuperuser
```

Run the development server:

```bash
poetry run python manage.py runserver
```

Open the app at:

```text
http://127.0.0.1:8000/
```

## Docker

The Docker setup runs the Django app behind Caddy. Static files are collected on
container startup and served by Caddy.

If the SQLite file does not exist yet, create it before starting Compose:

```bash
touch db.sqlite3
```

Start the stack:

```bash
docker compose up --build
```

Open the app at:

```text
http://127.0.0.1:8005/
```

Useful commands:

```bash
docker compose exec app python manage.py createsuperuser
docker compose exec app python manage.py migrate
docker compose logs -f app
```

## Main Routes

- `/` - today's daily record.
- `/daystats/<YYYY-MM-DD>/` - archived daily record.
- `/calendar/` - calendar and cycle prediction.
- `/chart/` - weight and calories chart.
- `/cycle_weight_chart/` - cycle length and weight chart.
- `/calories_summary/` - weekly calories averages.
- `/expenses/` - expense tracker.
- `/expenses/weeks/` - weekly expense summary.
- `/expenses/months/` - monthly expense summary.
- `/admin/` - Django admin.

## Development Commands

Run Django checks:

```bash
poetry run python manage.py check
```

Run deployment-oriented Django checks:

```bash
poetry run python manage.py check --deploy
```

Check template formatting:

```bash
poetry run djlint templates --check
```

Format templates:

```bash
poetry run djlint templates --reformat
```

Sort Python imports:

```bash
poetry run isort .
```

Check project metadata:

```bash
poetry check
```

## Data Model

`Daystat` stores one daily record per user and date:

- date
- week number
- calories
- weight
- cycle start flag

`Expense` stores a simple user expense:

- value
- note
- created timestamp

## Notes

- The default database is `db.sqlite3`.
- Runtime static files are collected into `static/`.
- Source static assets live in `staticfiles/`.
- Local secrets, virtual environments, collected static files, and SQLite
  database files are ignored by Git.
