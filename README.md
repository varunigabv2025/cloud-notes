# Cloud Notes

A small, polished full-stack notes application built for a simple AWS EC2 deployment. Code goes to GitHub, is copied to Ubuntu EC2 over SSH, and is then available on the internet.
Live Demo:http://65.1.100.90:8000

## Features

- Create, view, edit, and delete private, user-owned notes
- Secure signup, login, persistent signed-cookie sessions, and logout
- Persistent SQLite storage in `data/notes.db`
- Responsive warm editorial interface with loading, empty, validation, success, and error states
- REST API with FastAPI, SQLAlchemy, and Pydantic validation
- One server serves both the frontend and API


## Technology stack and architecture

- Backend: Python, FastAPI, SQLAlchemy, SQLite, Uvicorn
- Frontend: HTML, CSS, vanilla JavaScript

`Browser → FastAPI (/ and /static) → signed HttpOnly session cookie → user-scoped notes → SQLite`

## Project structure

```text
app/                 FastAPI application, database model, schemas, and routes
frontend/            Browser interface (HTML, CSS, JavaScript)
data/.gitkeep        Keeps the database directory in Git; notes.db is ignored
tests/               Small CRUD API test suite
requirements.txt     Python packages
start.sh             Ubuntu/EC2 startup command
```

## Local setup

Python 3.10+ is recommended.

```bash
git clone <YOUR-REPOSITORY-URL>
cd cloud-notes-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1`, then use `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`. Open `http://localhost:8000` locally.

Before starting the app, set a session-signing secret. Copy `.env.example` for reference, but do not commit a real `.env`. The app reads environment variables directly.

```bash
export SECRET_KEY="replace-with-a-long-random-secret"
export COOKIE_SECURE=false  # use true when the app is behind HTTPS
uvicorn app.main:app --host 0.0.0.0 --port 8000
pytest -q
```

On Windows PowerShell: `$env:SECRET_KEY = "replace-with-a-long-random-secret"`. The frontend deliberately uses relative API paths, so it works unchanged on EC2.

## Authentication and private notes

Create an account from **Sign up**, then log in. Passwords are hashed with Argon2 via `pwdlib`; plaintext passwords and hashes are never returned to the browser. Login issues a seven-day, signed `HttpOnly`, `SameSite=Lax` cookie. Logout removes it.

Authentication endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/auth/signup` | Create an account |
| POST | `/api/auth/login` | Start an authenticated session |
| POST | `/api/auth/logout` | End the session |
| GET | `/api/auth/me` | Read the current user’s safe profile |

All note endpoints below require login. The API filters every operation by the authenticated user, so another user’s note is returned as `404` rather than exposed.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/notes` | List notes, newest updated first |
| GET | `/api/notes/{id}` | Read one note |
| POST | `/api/notes` | Create a note |
| PUT | `/api/notes/{id}` | Replace a note |
| DELETE | `/api/notes/{id}` | Delete a note |

Create or update body: `{"title": "A thought", "content": "Optional note body"}`. `title` is required, trimmed, and limited to 200 characters. `content` is optional and limited to 10,000 characters.

## Database

SQLite is stored at `data/notes.db`. The directory and tables are created automatically at application startup. Authentication adds a `users` table and a nullable `notes.user_id` relationship. On an existing database, the app safely adds the column without deleting data. Earlier notes remain unowned and are not shown to any account; assign them manually only if you decide their owner. The database is ignored by Git, but remains on disk across server restarts.

## AWS EC2 deployment

EC2 is Amazon’s virtual-server service. Ubuntu is the operating system on that server. SSH is the secure remote terminal connection used to administer it.

1. Launch an Ubuntu EC2 instance and download its `.pem` key. Keep that private key out of Git.
2. In the instance Security Group (EC2’s virtual firewall), add inbound rules:
   - **SSH / TCP 22** from *your public IP only* (administration)
   - **Custom TCP / TCP 8000** from `0.0.0.0/0` (and `::/0` if using IPv6) for public app access
3. Connect and install the app:

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
git clone <YOUR-REPOSITORY-URL>
cd cloud-notes-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="replace-with-a-long-random-secret"
chmod +x start.sh
./start.sh
```

4. Visit `http://<EC2-PUBLIC-IP>:8000`.

```text
Developer → GitHub → SSH → EC2 → Ubuntu → FastAPI → SQLite → Internet
```

Port 22 permits SSH management; port 8000 lets browsers reach Uvicorn for this assignment. Uvicorn uses `--host 0.0.0.0` so it accepts traffic arriving at the EC2 network interface. Binding only to `127.0.0.1` would make it reachable only inside the server, not from your browser.

## Troubleshooting

- **Site will not open:** confirm the server is running, use the current public IP, and check the port-8000 Security Group rule.
- **SSH fails:** confirm username `ubuntu`, key permissions `400`, and a port-22 rule for your current IP.
- **Module not found:** activate `.venv` and run `pip install -r requirements.txt`.
- **SECRET_KEY must be set:** export a long random `SECRET_KEY` before starting. Keep it stable across restarts or existing sessions will be invalidated.
- **Address already in use:** stop the prior Uvicorn process or choose another port and update the Security Group.
- **Notes missing:** start from the project directory and inspect `data/notes.db` on that server.

For a long-running production service, use a process manager and reverse proxy. For this EC2 assignment, `start.sh` is deliberately simple.
