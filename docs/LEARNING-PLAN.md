# Django 6.1 Learning Plan — Library Management API

A learn-by-building curriculum. Ten phases, each one producing working code and
exercising a distinct part of Django.

**Approved:** 2026-10-26

---

## Ground rules

- **Claude writes the code and explains it.** Every non-trivial block comes with an
  explanation of what it does and which Django concept it demonstrates.
- **The owner runs every command.** Claude prints the command; the owner executes it.
- **Each phase ends with a commit** and a checked-off entry in `PROGRESS.md`.
- **"Done when" is a runtime check, not a reading check.** A phase is complete when
  something observably works, not when the docs have been read.

## Verified environment facts

| Item | Value | Note |
|---|---|---|
| Python | 3.13.0 | Already installed via pyenv-win. Django 6.x needs >= 3.12. |
| Django | 6.1.2 | Latest release; matches the docs being read. |
| PostgreSQL | 17 | `postgres:17` container |
| MongoDB | 8 | `mongo:8` container, used from Phase 9 |
| Docker | CLI 29.4.3, Compose v5.1.4 | Docker Desktop must be running |

---

## Target data model

```
User (custom)  --1:1--  Member
                           |
                           | 1:N
                           v
Author --1:N-- Book --1:N-- Loan
                 |
                 +--N:M-- Category

MongoDB:  activity_log  (one document per domain event)
```

This shape is chosen to force contact with foreign keys, many-to-many, one-to-one,
database constraints, transactions, and genuine business logic (stock, due dates).

---

## Phase 0 — Docker-first environment

**Concepts:** project vs app, what `manage.py` actually does, how `DATABASES`
connects Django to Postgres, reading configuration from the environment.

**Read:** [Installation](https://docs.djangoproject.com/en/6.1/topics/install/) ·
[Tutorial 01](https://docs.djangoproject.com/en/6.1/intro/tutorial01/) ·
[Databases](https://docs.djangoproject.com/en/6.1/ref/databases/) ·
[Settings](https://docs.djangoproject.com/en/6.1/topics/settings/)

**Build:** `Dockerfile` (Python 3.13 + Django 6.1.2), `docker-compose.yml`
(`web` + `db` + `mongo`), `requirements.txt`, `.env` / `.env.example`, `.gitignore`,
`django-admin startproject config .`, `DATABASES` reading from environment variables.

**Done when:**
- `docker compose up -d` brings up three healthy containers
- `docker compose exec web python manage.py migrate` succeeds against Postgres
- `psql` shows the `django_migrations` table
- `http://localhost:8000` serves the Django welcome page

---

## Phase 1 — Models and migrations

**Concepts:** field types, `null` vs `blank`, `choices`, `__str__`, `class Meta`
(`ordering`, `indexes`, `constraints`), the migration lifecycle, reading generated SQL.

**Read:** [Models](https://docs.djangoproject.com/en/6.1/topics/db/models/) ·
[Field reference](https://docs.djangoproject.com/en/6.1/ref/models/fields/) ·
[Migrations](https://docs.djangoproject.com/en/6.1/topics/migrations/)

**Build:** `accounts.User(AbstractUser)` plus `AUTH_USER_MODEL`, then the `catalog` app
with `Author`, `Category`, `Book`.

> **Critical ordering:** the custom user model must exist and `AUTH_USER_MODEL` must be
> set **before the first `migrate` of this phase**. Swapping it later is extremely painful.

**Done when:** tables exist in Postgres, and the owner can read a generated migration
file and the output of `sqlmigrate` and explain what each statement does.

---

## Phase 2 — The ORM

The heaviest phase. Everything later rests on this.

**Concepts:** `filter` / `exclude` / `get`, `Q` objects, `F` expressions,
`annotate` / `aggregate`, `select_related` vs `prefetch_related`, the N+1 problem,
lazy evaluation, custom `Manager` and `QuerySet`.

**Read:** [Making queries](https://docs.djangoproject.com/en/6.1/topics/db/queries/) ·
[QuerySet API](https://docs.djangoproject.com/en/6.1/ref/models/querysets/) ·
[Aggregation](https://docs.djangoproject.com/en/6.1/topics/db/aggregation/)

**Build:** a `seed_data` management command, then roughly fifteen queries of increasing
difficulty explored in `manage.py shell`, inspecting `.query` and `.explain()`.

**Done when:** given a QuerySet, the owner can predict how many SQL statements it issues.

---

## Phase 3 — The admin site

**Concepts:** `ModelAdmin`, `list_display`, `list_filter`, `search_fields`, inlines,
custom admin actions.

**Read:** [The Django admin site](https://docs.djangoproject.com/en/6.1/ref/contrib/admin/)

**Done when:** books and authors are fully manageable at `/admin`, with a Category inline.

---

## Phase 4 — CRUD with plain Django (no DRF)

Written by hand on purpose, so that DRF in Phase 7 is understood rather than trusted.

**Concepts:** URLconf, path converters, `include`, namespaces, `HttpRequest` and
`HttpResponse`, `JsonResponse`, HTTP status codes, `ModelForm` for validation,
`transaction.atomic`.

**Read:** [URL dispatcher](https://docs.djangoproject.com/en/6.1/topics/http/urls/) ·
[Writing views](https://docs.djangoproject.com/en/6.1/topics/http/views/) ·
[Forms](https://docs.djangoproject.com/en/6.1/topics/forms/) ·
[Transactions](https://docs.djangoproject.com/en/6.1/topics/db/transactions/)

**Build:** list / detail / create / update / delete for `Book`, returning JSON.

**Done when:** all five endpoints respond correctly to `curl`, including the failure
cases — 404 for a missing book, 400 with field errors for invalid input.

---

## Phase 5 — Testing

**Concepts:** `TestCase` vs `TransactionTestCase`, the test `Client`, fixtures,
`setUpTestData`, how Django creates and destroys the test database.

**Read:** [Testing in Django](https://docs.djangoproject.com/en/6.1/topics/testing/)

**Done when:** every Phase 4 endpoint is covered, `manage.py test` is green, and
`coverage report` shows at least 80%.

---

## Phase 6 — Authentication and permissions

**Concepts:** authentication vs authorization, sessions, `login_required`, the
permission framework, groups, `request.user`.

**Read:** [Using the auth system](https://docs.djangoproject.com/en/6.1/topics/auth/default/) ·
[Customizing authentication](https://docs.djangoproject.com/en/6.1/topics/auth/customizing/)

**Done when:** write endpoints require a logged-in user, and only a user in the
`librarian` group can delete a book. Tests prove both.

---

## Phase 7 — Refactor to Django REST Framework

**Concepts:** `Serializer` vs `Form`, `ModelSerializer`, `APIView` then generic views
then `ViewSet` plus router, pagination, filtering, throttling, permission classes, JWT,
OpenAPI schema generation.

**Read:** [Django REST Framework](https://www.django-rest-framework.org/) ·
`drf-spectacular` documentation

**Build:** reimplement Phase 4 and Phase 6 behaviour in DRF, **keeping the Phase 5 tests
unchanged** — they are the proof that the refactor preserved behaviour.

**Done when:** Swagger UI is reachable, JWT login works, and the original tests still pass.

---

## Phase 8 — Real business logic: borrow and return

**Concepts:** where business logic belongs (service function vs signal vs model method),
`CheckConstraint` and `UniqueConstraint`, `select_for_update` against race conditions,
signals, custom management commands.

**Read:** [Constraints](https://docs.djangoproject.com/en/6.1/ref/models/constraints/) ·
[Signals](https://docs.djangoproject.com/en/6.1/topics/signals/) ·
[Custom management commands](https://docs.djangoproject.com/en/6.1/howto/custom-management-commands/)

**Build:** the `circulation` app — `Loan` model, `POST /loans/` (borrow, decrement
stock), `POST /loans/{id}/return/`, and a `mark_overdue_loans` command.

**Done when:** a test proves a book cannot be borrowed beyond its available copies,
**including when two requests arrive concurrently**.

---

## Phase 9 — MongoDB: the activity log

Why MongoDB here: high write volume, a different payload shape per event type, no joins,
no cross-document transactions. Modelling this in Postgres would mean a table full of
nullable columns. The point is to feel why a second datastore exists.

**Concepts:**

- [Multiple databases and database routers](https://docs.djangoproject.com/en/6.1/topics/db/multi-db/)
  — an official Django topic not touched by any earlier phase
- Document modelling: embedded documents, array fields
- The real constraint: **no joins across Postgres and Mongo**, so data must be
  denormalised into the document at write time
- One raw `pymongo` aggregation pipeline, to see what the ORM hides

**Build:** an `activity` app routed to MongoDB via a database router. Every Phase 8
domain event writes a document:

```javascript
{ event: "loan.borrowed",
  actor:  { id: 7, username: "nghia" },
  target: { type: "book", id: 42, title: "Dune" },
  payload: { due_date: "2026-11-09", copies_left: 3 },
  created_at: ISODate("2026-10-26T09:00:00Z") }
```

**Done when:** borrowing a book produces a document in Mongo;
`GET /activity/?event=loan.borrowed` returns paginated results; one statistics endpoint
is implemented with an aggregation pipeline.

**Fallback:** `django-mongodb-backend` was first released in 2025. If multi-database
routing proves unstable, drop the ORM for this app and use `pymongo` directly. The
MongoDB lessons survive; only the database-router lesson is lost.

---

## Coverage

**Covered:** models, ORM, migrations, admin, URL routing, views, forms and validation,
authentication and permissions, testing, transactions and constraints, signals,
management commands, multiple databases, Django REST Framework, Docker-based development.

**Deliberately out of scope** (backend-only, breadth over depth): templates and the
template language, static-file pipelines, Channels and WebSockets, async views,
GeoDjango, deep i18n, Celery, caching, custom middleware, production deployment.
