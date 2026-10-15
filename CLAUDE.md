# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
./venv/bin/python app.py        # start the API on :5000 (Swagger at /docs)
./verify_imdb.sh                # same, but renews the IMDB session first if the WAF is blocking
./venv/bin/python imdb_verify.py # only the manual IMDB verification window (backend must be stopped)
./venv/bin/python -c "import app"  # quickest sanity check: every blueprint and model loads
```

No test suite exists. Black is configured in `.pre-commit-config.yaml`.

## Environment

Copy `.env.example` to `.env`. Only `MONGODB_CONNECTION_STRING_ATLAS` and `MONGODB_DATABASE` are needed to boot; AWS, OpenAI, RapidAPI and OpenSubtitles keys are validated by the routes that use them. There is no local MongoDB: Atlas is the only database.

## Architecture

Flask 3 + flask-restx (Swagger, request validation) + pymongo. Entrypoint is `app.py`, which registers one blueprint + namespace per feature under `/api`.

### Feature folders

```
favorites/      routes.py, controller.py, scrapper.py (IMDB via Playwright), external_requests.py (RapidAPI, OpenSubtitles)
keywords/       routes.py, controller.py, schemas.py (pydantic schema for the OpenAI structured output)
main_images/    routes.py, controller.py (S3 upload/list/delete + metadata in Mongo)
write_review/   routes.py, controller.py
```

- `routes.py` holds the flask-restx `Namespace`, the Swagger models and thin `Resource` classes that parse the request (`request.get_json(silent=True)`) and call the controller. No business logic there.
- `controller.py` returns `(body, status)` tuples. Success bodies wrap the payload in `data` (or `entries` + `total_documents` for lists). Every error goes through `utils.error(message, status)`, so the body is always `{ "message": ... }`.
- Controllers do not wrap Mongo calls in `try/except`: flask-restx already answers 500 and logs the traceback for unhandled exceptions. Only calls to external services (S3, OpenAI) catch their own errors to give a specific message.
- Collection names live in `config.py` (`FAVORITES_COLLECTION`, ...); each controller has a one-line accessor such as `reviews()`.

### Shared infrastructure

- `config.py`: loads `.env`, exposes settings, and `get_mongo_collection(name)`. It raises `DatabaseUnavailable` when Atlas cannot be reached; `app.py` turns that into a `503 { message }`. Controllers never check for `None`. A broad `except Exception` in a controller must re-raise `DatabaseUnavailable` first.
- `main_images.controller.s3_client()` is the only way to get an S3 client; it raises `StorageUnavailable` (also 503) when credentials are missing.
- `db.py`: the Mongo helpers every controller uses: `serialize(doc)` (`_id` to str + NaN cleanup), `insert`, `search(collection, filters, projection, sort, page, page_size)` returning `(total, entries)`, `update(collection, query, fields)` (drops `None`, idempotent when no field is sent) and `delete`. New data access should go through them.
- `utils.py`: `error(message, status)`, `pick(data, keys)`, `sanitize_movie_data`, `sanitize_filters` (client filters before `find`), `optimize_image` (Pillow resize before S3 upload).
- `HTTP_TIMEOUT` in `config.py` applies to every outbound `requests` call.

### IMDB scraper

`favorites/scrapper.py` drives one Chromium through Playwright in a dedicated thread (`_browser_loop`); the sync API is not thread-safe and the persistent profile at `~/.cache/movie-search/imdb-profile` can only be opened once. Pages are rate-limited, cached per `(tconst, path)` for `CACHE_TTL`, and WAF challenges are retried. `favorites.controller.SCRAPERS` maps each favorite field to its scraper; adding a field means adding one entry there. Run scrapers sequentially (see `collect_movie_data` docstring).

## Conventions

- Code, identifiers, comments and log messages in English; user-facing API messages in Portuguese.
- `logging.getLogger(__name__)` everywhere, never `print`.
- Duplicate resource is `409`; missing resource is `404`; dependency down is `503`.
