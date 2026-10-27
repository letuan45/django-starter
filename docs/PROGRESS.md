# Learning Progress

> **Read this file at the start of every session.** It is the checkpoint: it records
> where we stopped, which concepts are solid, and which ones are still shaky.
> Update it and commit it at the end of every session.

**Last session:** — (not started yet)
**Current phase:** Phase 0 — Docker-first environment
**Resume from:** nothing built yet; start with `Dockerfile` and `docker-compose.yml`

Curriculum: [`LEARNING-PLAN.md`](./LEARNING-PLAN.md)

### Legend

- `[ ]` not started · `[~]` explained, not yet solid · `[x]` solid
- A phase is done only when every **Done when** box is ticked by something that
  actually ran — not by having read about it.

---

## Phase 0 — Docker-first environment

**Status:** not started

### Concepts

- [ ] Project vs app — what each one is and why Django separates them
- [ ] What `manage.py` actually does when invoked
- [ ] `settings.py` — how Django finds it, and why it must not hold secrets
- [ ] `DATABASES` — how Django connects to Postgres
- [ ] Reading configuration from environment variables
- [ ] Docker: image vs container vs volume
- [ ] Compose: `depends_on` vs `healthcheck` — why `depends_on` alone is not enough

### Done when

- [ ] `docker compose up -d` brings up three healthy containers
- [ ] `docker compose exec web python manage.py migrate` succeeds against Postgres
- [ ] `psql` shows the `django_migrations` table
- [ ] `http://localhost:8000` serves the Django welcome page

### Open questions

- _(none yet)_

**Commit:** —

---

## Phase 1 — Models and migrations

**Status:** not started

### Concepts

- [ ] Field types and when to use which
- [ ] `null` vs `blank` — the difference and why both exist
- [ ] `choices` and the generated `get_FOO_display()`
- [ ] `__str__` and where Django uses it
- [ ] `class Meta`: `ordering`, `indexes`, `constraints`, `db_table`
- [ ] `ForeignKey` and `on_delete` options
- [ ] `ManyToManyField` and the implicit through table
- [ ] Custom user model and `AUTH_USER_MODEL` — why it must come first
- [ ] Migration lifecycle: `makemigrations` -> `migrate` -> `showmigrations`
- [ ] Reading a migration file and its `sqlmigrate` output

### Done when

- [ ] `accounts.User` is the active user model, set before the first migrate
- [ ] `Author`, `Category`, `Book` tables exist in Postgres
- [ ] Owner can read a generated migration and explain each SQL statement

### Open questions

- _(none yet)_

**Commit:** —

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
