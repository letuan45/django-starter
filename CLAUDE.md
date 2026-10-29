# `django-starter` — Learn-by-building Django 6.1 backend API

<!-- last verified: 2026-10-26 -->

## Project Identity

- **Purpose**: A teaching repository. The owner is learning Django from scratch by
  building one real project — a **Library Management REST API** — following the
  official Django 6.1 documentation, phase by phase.
- **Type**: Backend-only JSON API. No templates, no frontend, no SSR.
- **Domain**: A library lends copies of books to members. A Book is a *title*; the system
  tracks *how many* copies are out, never *which* one. Borrowing decrements an available
  count, returning restores it, and that count may never go negative. Full rules, with
  stable IDs (`BR-1`, `BR-2`, ...), live in `docs/BUSINESS-RULES.md` — code, tests, and
  commit messages cite those IDs.
- **Status**: Built incrementally. See `docs/PROGRESS.md` for the current phase.

## How to work in this repo

This repo has an explicit teaching contract. It overrides normal "just ship it" instincts.

| Who | Does what |
|---|---|
| **Claude** | Writes all application code, and **explains every non-trivial block** — what it does, why it is written that way, and which Django concept it demonstrates. |
| **The owner** | Runs every command themselves: `docker compose`, `migrate`, `runserver`, `test`. Claude writes the command out; the owner executes it and pastes the result back. |

Rules that follow from this:

1. **Never run `docker compose`, `manage.py`, or any app command.** Print it for the owner to run.
2. **Explain before the code, not after.** The code is the artifact; the explanation is the product.
3. **Follow the plan.** Do not jump ahead to a concept from a later phase just because it is
   "better". Learning order is deliberate — see `docs/LEARNING-PLAN.md`.
4. **Link the official docs** for each new concept: `https://docs.djangoproject.com/en/6.1/...`.
5. **Conversation is in Vietnamese. All files in this repo are in English.**

## Session protocol

At the **start** of every session: read `docs/PROGRESS.md`. It records the current phase,
the exact stopping point, and any concept the owner flagged as not-yet-solid.

At the **end** of every session: update `docs/PROGRESS.md` (tick concepts, record the
stopping point, add anything shaky to "Open questions") and commit it.

## Architecture

- **Language / Framework**: Python 3.13 + Django 6.1.2 (Django 6.x requires Python >= 3.12)
- **Databases**: PostgreSQL 17 (primary) + MongoDB 8 (activity log, from Phase 9)
- **API layer**: hand-written Django views through Phase 6, then refactored to
  Django REST Framework in Phase 7
- **Runtime**: everything runs in Docker containers. Nothing is installed on the host.

## Key Directories

```
django-starter/
├── config/              Django project package (settings, root urls, wsgi/asgi)
├── common/              Abstract base models only (TimeStampedModel). NOT an installed app
├── accounts/            Custom User model + Member — Phase 1, before the first migrate
├── catalog/             Author, Category, Book — the core CRUD domain
├── circulation/         Loan / borrow / return business logic (Phase 8)
├── activity/            MongoDB-backed activity log (Phase 9)
├── docs/ARCHITECTURE.md   Containers, layers, data stores — how the system is put together
├── docs/BUSINESS-RULES.md The domain rules, BR-1..BR-25 — what the system must guarantee
├── docs/DATA-MODEL.md     Tables, columns, constraints, indexes — the schema source of truth
├── docs/LEARNING-PLAN.md  The 10-phase curriculum — what to build and what to read
├── docs/PROGRESS.md       Checkpoint file — where we are, what is still shaky
├── docker-compose.yml   web + db + mongo
└── Dockerfile           the web container image
```

Apps appear as their phase lands. A directory listed here that does not exist yet
simply means that phase has not been reached.

## Development

All commands run through the `web` container.

```bash
docker compose up -d --build        # start web + db + mongo
docker compose logs -f web          # tail application logs
docker compose exec web python manage.py <command>
docker compose down                 # stop (keeps volumes)
docker compose down -v              # stop and WIPE both databases
```

### Migrations

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py showmigrations
docker compose exec web python manage.py sqlmigrate <app> <migration_number>
```

### Testing

```bash
docker compose exec web python manage.py test
docker compose exec web coverage run manage.py test && \
  docker compose exec web coverage report
```

## Common Patterns

- **Business rules go in `services.py`, never in a view.** A view parses input, calls a
  service, and turns the result into a status code. If a view contains an `if` that
  encodes a rule from `BUSINESS-RULES.md`, it is in the wrong layer. See
  `docs/ARCHITECTURE.md` section 2.
- **Cite the rule ID.** When code or a test enforces a business rule, name it:
  `# BR-14: a member with an overdue loan may not borrow`.
- **No column exists until `DATA-MODEL.md` says so.** That file is the schema source of
  truth. Adding a field to a model means updating it in the same change — never after.
- **Explicit over clever.** This is a learning repo: a readable loop beats a dense
  comprehension. Optimise for the reader, not for line count.
- **One concept per commit.** Commit messages name the Django concept learned, e.g.
  `feat(catalog): add Book model with M2M to Category`.
- **Docs link in the docstring.** When a module demonstrates a specific Django feature,
  put the `docs.djangoproject.com/en/6.1/...` link in the module docstring.
- **No premature abstraction.** Do not add a service layer, a base class, or a mixin
  until the phase that teaches it.

## Gotchas

- **`AUTH_USER_MODEL` is set in Phase 1, before the first `migrate`.** Swapping the user
  model after any migration has run is extremely painful in Django. This is why Phase 1
  touches authentication even though auth is not taught until Phase 6.
- **`docker compose down -v` wipes both databases.** Use plain `down` unless a reset is wanted.
- **The host has Python 3.10.0 as the active pyenv version**, which cannot run Django 6.x.
  This does not matter because nothing runs on the host — but a `python manage.py ...`
  typed outside the container will fail confusingly.
- **Mongo and Postgres cannot be JOINed.** From Phase 9 onward, anything the activity log
  needs from Postgres must be denormalised into the document at write time.
- **`django-mongodb-backend` is a young package** (first released 2025). If multi-database
  routing fights back, the fallback is to drop the ORM for Mongo and use `pymongo` directly.

## Related

- How the system is put together: `docs/ARCHITECTURE.md`
- What the system must guarantee: `docs/BUSINESS-RULES.md`
- Every table, column and constraint: `docs/DATA-MODEL.md`
- Curriculum and per-phase reading list: `docs/LEARNING-PLAN.md`
- Current progress and open questions: `docs/PROGRESS.md`
- Django 6.1 documentation: https://docs.djangoproject.com/en/6.1/
