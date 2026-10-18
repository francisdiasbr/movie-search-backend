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

Copy `.env.example` to `.env`. Only `MONGODB_CONNECTION_STRING_ATLAS` and `MONGODB_DATABASE` are needed to boot; AWS, Anthropic, RapidAPI and OpenSubtitles keys are validated by the routes that use them. There is no local MongoDB: Atlas is the only database.

## Architecture

Flask 3 + flask-restx (Swagger, request validation) + pymongo. Entrypoint is `app.py`, which registers one blueprint + namespace per feature under `/api`.

### Feature folders

```
favorites/      routes.py, controller.py, scrapper.py (IMDB via Playwright), external_requests.py (RapidAPI, OpenSubtitles)
keywords/       routes.py, controller.py, schemas.py (pydantic schema for the Claude structured output), imdb.py (title lookup in IMDB's public suggestion API)
main_images/    routes.py, controller.py (S3 upload/list/delete + metadata in Mongo)
write_review/   routes.py, controller.py
```

- `routes.py` holds the flask-restx `Namespace`, the Swagger models and thin `Resource` classes that read the body with `utils.json_body()` (always a dict) and call the controller. No business logic there.
- `controller.py` returns `(body, status)` tuples. Success bodies wrap the payload in `data` (or `entries` + `total_documents` for lists). Every error goes through `utils.error(message, status)`, so the body is always `{ "message": ... }`.
- Controllers do not wrap Mongo calls in `try/except`: flask-restx already answers 500 and logs the traceback for unhandled exceptions. Only calls to external services (S3, Claude) catch their own errors to give a specific message.
- Collection names live in `config.py` (`FAVORITES_COLLECTION`, ...); each controller has a one-line accessor such as `reviews()`.

### Shared infrastructure

- `config.py`: loads `.env`, exposes settings, and `get_mongo_collection(name)`. It raises `DatabaseUnavailable` when Atlas cannot be reached; `app.py` turns that into a `503 { message }`. Controllers never check for `None`. A broad `except Exception` in a controller must re-raise `DatabaseUnavailable` first.
- `main_images.controller.s3_client()` is the only way to get an S3 client; it raises `StorageUnavailable` (also 503) when credentials are missing.
- `favorites.scrapper.fetch_soup` raises `IMDBUnavailable` (also 503) when the AWS WAF blocks every attempt, so a blocked session is never answered as a 404. The `_genres` helper in `keywords/controller.py` swallows it on purpose: suggestions still work, only without genres.
- `db.py`: the Mongo helpers every controller uses: `serialize(doc)` (`_id` to str + NaN cleanup), `insert`, `search(collection, filters, projection, sort, page, page_size)` returning `(total, entries)`, `update(collection, query, fields)` (drops `None`, idempotent when no field is sent) and `delete`. New data access should go through them.
- `utils.py`: `error(message, status)`, `json_body()`, `pick(data, keys)`, `sanitize_movie_data`, `sanitize_filters` (client filters before `find`), `optimize_image` (Pillow resize before S3 upload).
- `HTTP_TIMEOUT` in `config.py` applies to every outbound `requests` call.

### IMDB scraper

`favorites/scrapper.py` drives one Chromium through Playwright in a dedicated thread (`_browser_loop`); the sync API is not thread-safe and the persistent profile at `~/.cache/movie-search/imdb-profile` can only be opened once. Pages are rate-limited, cached per `(tconst, path)` for `CACHE_TTL`, and WAF challenges are retried. Each getter is decorated with `@imdb_page(path)` and receives `(soup, tconst)`; it is skipped when the page could not be loaded. Use `_text`/`_texts` to extract strings. `favorites.controller.SCRAPERS` maps each favorite field to its scraper; adding a field means adding one entry there. Run scrapers sequentially (see `collect_movie_data` docstring).

## Conventions

- Code, identifiers, comments and log messages in English; user-facing API messages in Portuguese.
- `logging.getLogger(__name__)` everywhere, never `print`.
- Duplicate resource is `409`; missing resource is `404`; dependency down is `503`.
