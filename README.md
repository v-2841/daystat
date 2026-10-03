# Daystat

Daystat is a small personal Django app for tracking daily health and expense
data. It keeps daily records for weight, calories, and cycle starts, shows
calendar and chart summaries, and stores expenses sorted into personal
categories.

The app is built around a daily check-in flow: each date has a single record per
user, so the diary page can be used as a compact journal for the current day and
as an archive for previous dates. A record is written only when something is
saved, so browsing an archived date leaves no empty rows behind. The rest of the interface turns those daily
records into calendar markers, predictions, charts, and summary tables.

## Features

- Home screen with tiles for every section.
- Daily page for weight, calories, and cycle start tracking.
- Calendar with recorded values and predicted cycle dates.
- Analytics with three tabs: weight and calories, cycle length, weekly calories.
- Expense tracker with personal categories and weekly and monthly summaries.
- User login, logout, profile editing, and password change pages.
- A gender setting in the profile: men's profiles hide everything about the
  cycle and use a blue palette instead of the pink one.
- Django admin for users, `Daystat`, `Expense`, and expense categories.

## Functional Overview

### Daily Tracking

The diary page at `/day/` opens the record for the current day. A user can enter weight,
calories, and mark whether the day is the start of a new cycle. The page also
shows the current cycle day based on the latest previous cycle start. The cycle
switch is shown to women only; a save made without it keeps the stored cycle
starts as they are.

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
cycle date and whether it is upcoming, today, or overdue. For men the calendar
shows weight and calories only: no cycle markers, predictions, or legend.

### Analytics

Charts and summaries live on one page with tabs. The weight and calories tab
lets the user switch between metrics and time ranges: week, month, six months,
year, and five years. Longer ranges smooth the
data with the same moving-average helper used by the chart API, so long-term
trends are easier to read.

The cycle tab compares completed cycle lengths with smoothed weight
over the full available history. Cycle length points are plotted on the date of
the next cycle start, because that is when the previous cycle length becomes
known. The tab and its chart API are available to women only; for men
`?tab=cycle` falls back to the weight and calories tab.

### Weekly Summary

The weekly tab groups records by ISO year and week, then shows average calories
for each week that has recorded calorie data. ISO numbering keeps a week that
spans the new year as a single row.

### Expenses

The expense tracker stores expense records with a value, an optional category,
and an optional note. The main expense page shows the expenses of the current
week and provides a form for adding new ones; the category is picked with chips.
Existing expenses can be opened from the table, edited, or deleted.

Every user keeps their own list of categories on the «Категории» tab: add,
rename, or delete them there. Names are unique per user regardless of case.
A category is optional, so expenses recorded before categories existed stay
uncategorized, and deleting a category keeps its expenses without one.

There are also weekly and monthly expense summary pages. They group expenses by
calendar period, total the values, break the total down by category, and
concatenate notes so repeated spending patterns are easier to scan. A period
with uncategorized expenses only gets no breakdown.

### User Account

The app uses Django authentication with a custom user model, `users.User`.
Logged-in users can update their profile, change password, and keep their day
statistics and expenses separated from other users' data.

The profile has a gender setting, female by default. It switches two things:
men do not see anything about the menstrual cycle, and the interface uses a
blue palette instead of the pink one. The stored cycle data is kept, so
switching back to female brings it all back.

## Tech Stack

- Python 3.13+
- Django 5.2
- SQLite
- Tailwind CSS 4 via `django-tailwind-cli` (standalone binary, no Node.js)
- Chart.js with the Luxon adapter for charts, self-hosted
- Phosphor duotone icons as a single SVG sprite
- Self-hosted Nunito and Comfortaa fonts
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

Run the development server together with the Tailwind watcher:

```bash
poetry run python manage.py tailwind runserver
```

The first run downloads the standalone Tailwind CLI into `.django_tailwind_cli/`.
To build the stylesheet once (for example before `collectstatic`):

```bash
poetry run python manage.py tailwind build
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

- `/` - home screen with tiles for every section.
- `/day/` - today's daily record.
- `/daystats/<YYYY-MM-DD>/` - archived daily record.
- `/calendar/` - calendar and cycle prediction.
- `/analytics/` - charts and weekly summaries (`?tab=trends|cycle|weeks`).
- `/expenses/` - expense tracker.
- `/expenses/weeks/` - weekly expense summary.
- `/expenses/months/` - monthly expense summary.
- `/expenses/categories/` - the user's expense categories.
- `/auth/login/`, `/auth/logout/` - sign in and out.
- `/auth/profile_edit/` - profile, including gender.
- `/auth/password_change/` - password change.
- `/admin/` - Django admin.

The old chart routes (`/chart/`, `/cycle_weight_chart/`, `/calories_summary/`)
redirect to the matching analytics tab.

## Frontend

The interface is a pastel "liquid glass" theme with light and dark modes.
Design tokens (colors, surfaces, radii, motion) live in
`assets/css/source.css` inside the Tailwind `@theme` and `@layer base`
blocks; the compiled result is written to `staticfiles/css/tailwind.css`, which
is generated and therefore not tracked by Git.

- The theme follows the system setting and can be overridden with the header
  toggle; the choice is stored in `localStorage`.
- There are two palettes: pink, the default for women's profiles and the login
  page, and blue for men's profiles. The `palette` context processor
  (`core/context_processors/palette.py`) renders `User.palette` as
  `data-palette` on `<html>` and keeps the browser chrome color of each
  palette; the `[data-palette="blue"]` blocks in
  `source.css` override only the tokens that carry a hue; status colors stay
  the same. Charts and the confetti read their colors from CSS custom
  properties, so they follow the palette too.
- Navigation is a glass header on wide screens and a bottom tab bar on narrow
  ones.
- The calendar is a server-rendered month grid: weight and calories are shown
  inside the cells at every width, cycle days are marked with dots, and a tap
  opens a detail sheet.
- Icons come from `staticfiles/img/sprite.svg` and are rendered by the
  `{% icon "name" %}` template tag.

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
- ISO week number (recalculated on save)
- calories
- weight
- cycle start flag

`User` (`users.User`) is the custom user model. It extends Django's
`AbstractUser` and keeps the original `auth_user` table:

- gender: `Ж` (female, the default) or `М` (male)
- `tracks_cycle` and `palette` properties derived from the gender

`ExpenseCategory` stores a user's category:

- name, unique per user

`Expense` stores a user expense:

- value
- category (optional; cleared when the category is deleted)
- note
- created timestamp

## Upgrading a Database From Before the Custom User Model

Databases created before `users.User` existed already have the users in
`auth_user`, and `migrate` refuses to run on them with
`InconsistentMigrationHistory`. Before the first `migrate` with the new code,
mark the initial users migration as applied and move the user content type to
the new app, once per database. Back the database up first.

With Docker, build the new image while the site still runs, then stop the app
and run in bash (fish has no heredoc). The backup goes outside the project
directory, so it never ends up in the image or in Git:

```bash
docker compose build app
docker compose stop app
mkdir -p ../daystat-backups
cp db.sqlite3 ../daystat-backups/db-before-user-model.sqlite3
docker compose run --rm -T --no-deps --entrypoint python app - <<'EOF'
import sqlite3
db = sqlite3.connect('db.sqlite3')
db.execute("INSERT INTO django_migrations (app, name, applied) VALUES ('users', '0001_initial', datetime('now'))")
db.execute("UPDATE django_content_type SET app_label = 'users' WHERE app_label = 'auth' AND model = 'user'")
db.commit()
EOF
docker compose up -d
```

The remaining migrations, including the `gender` column, are applied by
`entrypoint.sh` on startup. Sessions stay valid, so nobody has to sign in again.
New databases need none of this.

If something goes wrong before `docker compose up -d`, the old version still
works with the prepared database: bring it back with `docker compose start app`.
To undo the whole upgrade, copy the backup over `db.sqlite3` and deploy the
previous commit.

## Notes

- The default database is `db.sqlite3`.
- Runtime static files are collected into `static/`. `collectstatic` gives
  every file a content hash in its name (`core.storage.HashedStaticFilesStorage`),
  so a deploy changes the URLs and browsers never mix new pages with stale
  cached CSS or JS. With `DEBUG=False` pages need that collected manifest;
  `entrypoint.sh` runs `collectstatic` before the app starts.
- Source static assets live in `staticfiles/`. The Tailwind input lives in
  `assets/css/` instead: it is no static file, and its `@import
  "tailwindcss"` would fail the hashing in `collectstatic`.
- `staticfiles/css/tailwind.css` and `.django_tailwind_cli/` are build
  artifacts and are ignored by Git.
- Local secrets, virtual environments, collected static files, and SQLite
  database files are ignored by Git.
