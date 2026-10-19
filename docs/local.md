# Running Noise locally

## Native Python: quickest start

Install Python 3.10 or newer, including pip and venv. On Ubuntu 24.04:

```sh
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

Clone your fork, enter its directory, then run:

```sh
./install.sh
```

The installer generates `.env` and a unique signing secret, installs dependencies,
applies migrations, collects static files, and prompts for an administrator. The
default administrator username is `admin`; choose your own password. It starts
Gunicorn in the foreground. Open <http://localhost:8000/noise/>, log in, and use
the **+** button. Administration lives at <http://localhost:8000/admin/>.

No AWS configuration is needed. SQLite and uploaded files live in `data/`.
Stop with Ctrl-C and restart with `./start.sh`. Rerunning `./install.sh` applies
updates without resetting accounts or content. Use `PYTHON=python3.12 ./install.sh`
to select a specific Python interpreter when creating the environment.

To customize before the first install:

```sh
cp .env.example .env
```

Edit `.env` in your editor. The blank `SECRET_KEY` is filled by the installer;
the other defaults work locally. Real environment variables take precedence.
Do not source this file in a shell: values such as the tagline can contain spaces.

## Local Docker

Install Docker Engine with the Compose plugin on Linux, or Docker Desktop on
macOS. Start Docker, copy `.env.example` to `.env`, and generate a signing secret:

```sh
cp .env.example .env
openssl rand -hex 48
```

Paste the generated value into `SECRET_KEY` without sharing it. Set the initial
administrator email and a strong password in `DJANGO_SUPERUSER_EMAIL` and
`DJANGO_SUPERUSER_PASSWORD`. The username defaults to `admin`.

```sh
docker compose up --build -d
docker compose logs --tail=100 noise
```

Open <http://localhost:8000/noise/>. Remove `DJANGO_SUPERUSER_PASSWORD` from `.env`
after the account is created, then recreate the container to drop it from its
environment:

```sh
docker compose up -d --force-recreate noise
```

Stop with `docker compose down`; restart with `docker compose up -d`.
The named `noise-data` volume persists. `docker compose down -v` deletes it.
The native and Docker workflows use separate databases and upload directories;
switching workflows does not automatically move your content.

## Changing ports or branding

For port 8080, set all three in `.env`:

```dotenv
PORT=8080
PUBLIC_URL=http://localhost:8080
CSRF_TRUSTED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
```

Restart the native server or run `docker compose up -d` to apply changes.
`BIND_ADDRESS=127.0.0.1` keeps access on your own machine; leave it there for
local use. `ALLOWED_HOSTS` contains hostnames only, without schemes or ports.
Set `SITE_TITLE`, `SITE_TAGLINE`, and `TIME_ZONE` to personalize your journal.
Keep `COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, and `TRUST_PROXY_HTTPS` false for
local HTTP. Keep `WEB_CONCURRENCY=1` for SQLite.

## Editing code

For automatic Python reload and Django debugging, stop Gunicorn and run:

```sh
DEBUG=true .venv/bin/python manage.py runserver 127.0.0.1:8000
```

Use this only on your development machine. Run the checks with:

```sh
.venv/bin/python manage.py test
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
```

## Backups

For native Python, stop the server and copy `data/` and `.env` to a private backup
location, then restart it. Stopping writes makes the SQLite copy consistent.
For Docker, use the stopped-container backup procedure in the
[AWS guide](aws.md#backups-and-upgrades), replacing `-f compose.aws.yaml` with
the default `docker compose` command. Keep backups out of version control.
