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

## Auth and user APIs

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Create an account and send a verification email |
| POST | `/auth/login` | JSON login; returns access and refresh JWTs and sets HttpOnly cookies |
| POST | `/auth/token` | OAuth2 password form login (OpenAPI / Swagger) |
| POST | `/auth/refresh` | Rotate tokens from a refresh JWT or cookie |
| POST | `/auth/logout` | Clear auth cookies |
| GET | `/auth/verify-email/{token}` | Confirm email from the activation link |
| POST | `/auth/verify-email/resend` | Resend the activation email |
| POST | `/auth/password/forgot` | Start a password reset |
| POST | `/auth/password/reset` | Finish a password reset with `{ token, password }` |
| GET | `/auth/users/me` | Current user profile |
| PATCH | `/auth/users/me` | Update the current profile |
| GET/PUT | `/auth/users/me/address` | Read or upsert address |
| GET/PUT | `/auth/users/me/image` | Read or upsert profile image extension |
| GET | `/auth/users/{userId}` | Public profile |
| POST | `/auth/users/{userId}/suspensions` | Admin-only suspension |
| GET | `/auth/health` | Liveness |

Access tokens last `JWT_EXPIRE_MINUTES` (default 15). Refresh tokens last `JWT_REFRESH_EXPIRE_DAYS` (default 14). Send `Authorization: Bearer <accessToken>` or rely on the `access_token` cookie.

## Tests

```bash
pytest --cov --cov-report=term-missing
```

## Bruno

Import `resources/Maplux Bruno Collection` in Bruno. Use the `local` environment, register a user, then log in. The login request stores `accessToken` in the `token` environment variable.

Activation links use `CLIENT_ORIGIN` plus the API prefix. Password reset emails point at `{CLIENT_ORIGIN}/password/reset/{token}`.

If you already have a local `Maplux.sqlite` file from an older schema, delete it so tables can be recreated on startup.
