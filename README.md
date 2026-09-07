Use Python 3.14.2.

## Setup

Create a virtual environment, install dependencies, and copy the example environment file:

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env
```

On macOS/Linux, activate with `source .venv/bin/activate` and copy with `cp .env.example .env`.

Replace the placeholder secrets in `.env` before sending mail or exposing the API. `ACTIVATE_SECRET_KEY` and `JWT_SECRET_KEY` must be long, random values.

### `uvicorn main:app --reload`

Runs the backend in development mode. Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the OpenAPI UI. API routes are prefixed with `API_PREFIX` (default `/auth`).

## Tests

```bash
pytest --cov --cov-report=term-missing
```

## Bruno

Import `resources/Maplux Bruno Collection` in Bruno. Use the `local` environment, create a user, then log in. The login request stores `accessToken` in the `token` environment variable for authenticated requests.

Activation links in email use `CLIENT_ORIGIN` plus the API prefix so they are not taken from the incoming `Host` header. Password reset emails point at `{CLIENT_ORIGIN}/password/reset/{token}`.

If you already have a local `Maplux.sqlite` file from an older schema, delete it so tables can be recreated on startup.
