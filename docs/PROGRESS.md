# Learning Progress

> **Read this file at the start of every session.** It is the checkpoint: it records
> where we stopped, which concepts are solid, and which ones are still shaky.
> Update it and commit it at the end of every session.

**Last session:** 2026-10-29
**Current phase:** Phase 2 — The ORM (not started; waiting for the owner's go-ahead)
**Resume from:** Phase 1 is done. Phase 2 begins with a `seed_data` management
command, then roughly fifteen queries explored in `manage.py shell`.

Curriculum: [`LEARNING-PLAN.md`](./LEARNING-PLAN.md)

### Legend

- `[ ]` not started · `[~]` explained, not yet solid · `[x]` solid
- A phase is done only when every **Done when** box is ticked by something that
  actually ran — not by having read about it.

---

## Phase 0 — Docker-first environment

**Status:** done — 2026-10-29

### Concepts

- [x] Project vs app — what each one is and why Django separates them
- [x] What `manage.py` actually does when invoked
- [x] `settings.py` — how Django finds it, and why it must not hold secrets
- [x] `DATABASES` — how Django connects to Postgres
- [x] Reading configuration from environment variables
- [~] Docker: image vs container vs volume
- [x] Compose: `depends_on` vs `healthcheck` — why `depends_on` alone is not enough

### Done when

- [x] `docker compose up -d` brings up three healthy containers
- [x] `docker compose exec web python manage.py migrate` succeeds against Postgres
- [x] `psql` shows the `django_migrations` table
- [x] `http://localhost:8000` serves the Django welcome page

### Open questions

- **Phase 1 must begin with `docker compose down -v`.** Phase 0 ran `migrate`,
  which created Django's stock `auth_user` table. Phase 1 replaces it with
  `accounts.User`, and Django refuses to swap `AUTH_USER_MODEL` once any
  migration has been applied. The database holds no data, so wiping the volume
  costs nothing — but skipping this step makes Phase 1 fail in a confusing way.
- `[~] image vs container vs volume` — explained, not yet felt. The named
  volumes `pgdata` / `mongodata` have not survived a `down` / `up` cycle yet.
  The `down -v` above is the first time the distinction will bite.
- `[~] project vs app` — explained, but no app exists yet. Phase 1 settles it.

**Commit:** `feat(phase-0): dockerised Django 6.1 + PostgreSQL 17 + MongoDB 8`

---

## Phase 1 — Models and migrations

**Status:** done — 2026-10-29

### Concepts

- [x] Field types and when to use which
- [x] `null` vs `blank` — the difference and why both exist
- [~] `choices` and the generated `get_FOO_display()`
- [~] `__str__` and where Django uses it
- [~] `class Meta`: `ordering`, `indexes`, `constraints`, `db_table`
- [x] `ForeignKey` and `on_delete` options
- [x] `ManyToManyField` and the implicit through table
- [x] `OneToOneField` — and how it differs from a unique `ForeignKey`
- [x] Abstract base classes — inherited columns without an inherited table
- [x] Custom user model and `AUTH_USER_MODEL` — why it must come first
- [x] Migration lifecycle: `makemigrations` -> `migrate` -> `showmigrations`
- [x] Reading a migration file and its `sqlmigrate` output

### Done when

- [x] `accounts.User` is the active user model, set before the first migrate
- [x] `accounts.Member` exists, one-to-one with `User`
- [x] `Author`, `Category`, `Book` tables exist in Postgres
- [x] Every table that inherits `TimeStampedModel` carries `created_at` /
      `updated_at`. `accounts_user` does not, and must not — `AbstractUser`
      already supplies `date_joined`.
- [x] Owner can read a generated migration and explain each SQL statement

### Open questions

- `[~] get_FOO_display()` — Django generates it at import time, but Pylance
  reads statically and cannot see it. `Member.__str__` therefore calls
  `Status(self.status).label` instead, which is equivalent for valid data and
  raises `ValueError` for invalid data (where `get_status_display()` would
  return it unchanged). The method has never actually been called; try it in
  the Phase 2 shell.
- `[~] __str__` — written for all four models, but not yet seen rendering
  anywhere. Phase 2's shell and Phase 3's admin are where it shows up.
- `[~] class Meta` — `ordering`, `indexes` and `constraints` are all used and
  were read in `sqlmigrate`. `db_table` has never been used: every table took
  Django's default `<app>_<model>` name, as DATA-MODEL.md specifies.
- `showmigrations` has not been run yet, only `makemigrations` and `migrate`.
  Worth running once at the start of Phase 2 to see the applied/unapplied list.
- **Type checking is unresolved, not decided.** Pylance was kept and the code
  was written to suit it. When Phase 2 introduces `Model.objects`, the same
  false positives may return; the alternative (mypy + `django-stubs`, which
  needs Django installed on the host) is still open.
- **CRLF is unguarded.** Git reported `LF will be replaced by CRLF` for
  `Dockerfile` and friends at the Phase 0 commit. Harmless today because the
  files on disk were written with LF, but a fresh clone on Windows would check
  them out with CRLF, and Linux containers choke on ``. A `.gitattributes`
  forcing LF would close this; not added yet.

**Commit:** `feat(phase-1): custom user model, Member, and the catalog schema`

---

## Phase 2 — The ORM

**Status:** not started

### Concepts

- [ ] `filter` / `exclude` / `get` and when `get` raises
- [ ] QuerySet laziness — when the query actually hits the database
- [ ] `Q` objects for OR and complex conditions
- [ ] `F` expressions — updating a column from its own value
- [ ] `annotate` vs `aggregate`
- [ ] `select_related` vs `prefetch_related`
- [ ] The N+1 problem — recognising it in the wild
- [ ] Custom `Manager` and custom `QuerySet`
- [ ] Inspecting `.query` and `.explain()`

### Done when

- [ ] `seed_data` management command populates the database
- [ ] ~15 queries written and run in `manage.py shell`
- [ ] Owner can predict the SQL count of a given QuerySet before running it

### Open questions

- _(none yet)_

**Commit:** —

---

## Phase 3 — The admin site

**Status:** not started

### Concepts

- [ ] Registering models and the `ModelAdmin` class
- [ ] `list_display`, `list_filter`, `search_fields`, `readonly_fields`
- [ ] Inlines (`TabularInline` / `StackedInline`)
- [ ] Custom admin actions

### Done when

- [ ] Superuser created
- [ ] Book and Author fully manageable at `/admin`, with a Category inline

### Open questions

- _(none yet)_

**Commit:** —

---

## Phase 4 — CRUD with plain Django

**Status:** not started

### Concepts

- [ ] URLconf, `path()`, path converters
- [ ] `include()` and URL namespaces
- [ ] `HttpRequest` / `HttpResponse` / `JsonResponse`
- [ ] HTTP status codes and when each applies
- [ ] `ModelForm` for validating incoming data
- [ ] `transaction.atomic`
- [ ] Function-based views vs class-based views

### Done when

- [ ] Five endpoints for Book: list, detail, create, update, delete
- [ ] All verified with `curl`, including 404 and 400-with-field-errors

### Open questions

- _(none yet)_

**Commit:** —

---

## Phase 5 — Testing

**Status:** not started

### Concepts

- [ ] `TestCase` vs `TransactionTestCase`
- [ ] The test `Client`
- [ ] `setUpTestData` vs `setUp`
- [ ] Fixtures and test data creation
- [ ] How Django creates and destroys the test database
- [ ] Coverage measurement

### Done when

- [ ] Every Phase 4 endpoint covered
- [ ] `manage.py test` green
- [ ] `coverage report` at or above 80%

### Open questions

- _(none yet)_

**Commit:** —

---

## Phase 6 — Authentication and permissions

**Status:** not started

### Concepts

- [ ] Authentication vs authorization
- [ ] Sessions and how Django tracks a logged-in user
- [ ] `request.user` and `AnonymousUser`
- [ ] `login_required` and permission decorators
- [ ] Model permissions and groups

### Done when

- [ ] Write endpoints require a logged-in user
- [ ] Only the `librarian` group can delete a book
- [ ] Tests prove both

### Open questions

- _(none yet)_

**Commit:** —

---

## Phase 7 — Refactor to Django REST Framework

**Status:** not started

### Concepts

- [ ] `Serializer` vs Django `Form` — what changed and why
- [ ] `ModelSerializer` and custom validation
- [ ] `APIView` -> generic views -> `ViewSet` + router
- [ ] Pagination, filtering, ordering
- [ ] Permission classes and throttling
- [ ] JWT authentication
- [ ] OpenAPI schema generation

### Done when

- [ ] Phase 4 and Phase 6 behaviour reimplemented in DRF
- [ ] Phase 5 tests pass **unchanged**
- [ ] Swagger UI reachable and JWT login works

### Open questions

- _(none yet)_

**Commit:** —

---

## Phase 8 — Borrow and return

**Status:** not started

### Concepts

- [ ] Where business logic belongs: service vs signal vs model method
- [ ] `CheckConstraint` and `UniqueConstraint`
- [ ] `select_for_update` and row-level locking
- [ ] Race conditions — how to reproduce one in a test
- [ ] Signals and their trade-offs
- [ ] Custom management commands

### Done when

- [ ] `POST /loans/` borrows and decrements stock
- [ ] `POST /loans/{id}/return/` returns and restores stock
- [ ] `mark_overdue_loans` command works
- [ ] A test proves stock cannot go negative under concurrent requests

### Open questions

- _(none yet)_

**Commit:** —

---

## Phase 9 — MongoDB activity log

**Status:** not started

### Concepts

- [ ] Multiple databases in Django
- [ ] Database routers — how Django decides which database a model uses
- [ ] Document modelling: embedded documents and array fields
- [ ] Why no joins across Postgres and Mongo, and what denormalisation costs
- [ ] A raw `pymongo` aggregation pipeline
- [ ] When a second datastore is justified and when it is not

### Done when

- [ ] Borrowing a book writes a document to Mongo
- [ ] `GET /activity/?event=loan.borrowed` returns paginated results
- [ ] One statistics endpoint implemented with an aggregation pipeline

### Open questions

- _(none yet)_

**Commit:** —

---

## Session log

| Date | Phase | What happened |
|---|---|---|
| 2026-10-26 | — | Plan approved. `CLAUDE.md`, `LEARNING-PLAN.md`, `PROGRESS.md` created. |
| 2026-10-27 | — | `ARCHITECTURE.md`, `BUSINESS-RULES.md`, `DATA-MODEL.md` written. |
| 2026-10-29 | 0 | Docker environment built: `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `.env`. `startproject config .` run, `settings.py` moved onto env vars + PostgreSQL. Three healthy containers, `migrate` green, welcome page served. |
| 2026-10-29 | 1 | Database wiped with `down -v` before the first real migrate. `common.TimeStampedModel`, `accounts.User` + `Member`, `catalog.Author` / `Category` / `Book`. `AUTH_USER_MODEL` set before migrating. `sqlmigrate` read line by line for both apps. Found and fixed a contradiction in DATA-MODEL.md: audit columns are not on `accounts_user`. |
