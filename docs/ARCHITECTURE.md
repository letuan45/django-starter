# Architecture — Library Management API

What this system is made of and how a request moves through it.

This is a learning project, so the architecture is deliberately **small but honest**:
every boundary here exists for a reason that also holds in a real system.

---

## 1. Runtime topology

Everything runs in Docker. Nothing is installed on the host.

```
                   host :8000
                        |
          +-------------v-------------+
          |          web              |   Python 3.13 + Django 6.1.2
          |   Django application      |
          +------+--------------+-----+
                 |              |
       psycopg   |              |  pymongo
                 v              v
          +------------+  +------------+
          |     db     |  |   mongo    |
          | postgres:17|  |  mongo:8   |
          +-----+------+  +-----+------+
                |               |
             pgdata         mongodata        (named volumes, survive `down`)
```

| Container | Image | Role |
|---|---|---|
| `web` | built from `Dockerfile` | the Django application |
| `db` | `postgres:17` | **system of record** — all transactional data |
| `mongo` | `mongo:8` | **activity log only** — append-only event documents (Phase 9) |

`web` waits on a `healthcheck`, not merely `depends_on`, because `depends_on` only
waits for the container to *start*, not for Postgres to be *ready to accept connections*.

---

## 2. Application layers

A request flows downward. Nothing ever calls upward.

```
  HTTP request
       |
       v
  +--------------------------------------------+
  |  URL layer          config/urls.py          |   routing only
  |                     <app>/urls.py           |
  +--------------------------------------------+
       |
       v
  +--------------------------------------------+
  |  View layer         <app>/views.py          |   HTTP in, HTTP out
  |                                             |   parse, validate, serialise,
  |                                             |   choose a status code
  +--------------------------------------------+
       |
       v
  +--------------------------------------------+
  |  Service layer      <app>/services.py       |   business rules live HERE
  |                                             |   transactions, locking,
  |                                             |   cross-model invariants
  +--------------------------------------------+
       |
       v
  +--------------------------------------------+
  |  Model layer        <app>/models.py         |   shape of the data,
  |                                             |   field-level validation,
  |                                             |   database constraints
  +--------------------------------------------+
       |
       v
   PostgreSQL                     MongoDB (activity log, written from services)
```

### The rule that matters

**Business rules live in the service layer.** A view must not decide whether a member
is allowed to borrow a book; it calls `services.borrow_book(...)` and translates the
result into an HTTP response.

Why this boundary, and not "fat models":

- The borrow operation touches `Book`, `Loan`, and `Member` at once. Putting it on any
  one of those models makes that model know about the other two.
- A service function is callable from a view, a management command, a test, or the
  admin — without an HTTP request existing.
- When Phase 7 replaces hand-written views with DRF views, **the service layer does not
  change**. That is the proof the boundary was in the right place.

### What each layer must not do

| Layer | Must not |
|---|---|
| View | contain an `if` that encodes a business rule |
| Service | import anything from `django.http`, or know about status codes |
| Model | reach across to another aggregate to enforce a multi-model rule |

---

## 3. Django apps

Each app owns one concept. Apps appear as their phase lands.

| App | Owns | Introduced |
|---|---|---|
| `config` | settings, root URLconf, WSGI/ASGI entrypoints | Phase 0 |
| `accounts` | the custom `User` model, `Member` profile | Phase 1 |
| `catalog` | `Author`, `Category`, `Book` — the things a library holds | Phase 1 |
| `circulation` | `Loan` — the act of borrowing and returning | Phase 8 |
| `activity` | the MongoDB-backed event log | Phase 9 |

**Dependency direction:** `activity` <- `circulation` -> `catalog` -> `accounts`.
No cycles. `catalog` never imports from `circulation`.

---

## 4. Data stores — and why there are two

| | PostgreSQL | MongoDB |
|---|---|---|
| Holds | books, authors, members, loans | activity events |
| Shape | fixed schema, enforced by migrations | one shape per event type |
| Writes | read-modify-write, transactional | append-only, never updated |
| Constraints | foreign keys, unique, check | none |
| Queried by | the API, with joins | filters and aggregation pipelines |

The activity log is a genuinely poor fit for a relational table: each event type carries
a different payload, so a single table would be mostly nullable columns, and the log is
written far more often than it is read. That is the argument for the second store — not
novelty.

### The cost, stated plainly

**There are no joins between Postgres and Mongo.** An activity document that needs a book
title must carry the title *copied into the document at write time*. If the book is later
renamed, the log keeps the old title — and that is correct: a log records what was true
when the event happened.

### Routing

A Django **database router** sends models in `activity` to the `mongo` connection and
everything else to `default` (Postgres). See
[Multiple databases](https://docs.djangoproject.com/en/6.1/topics/db/multi-db/).

---

## 5. Configuration

`config/settings.py` reads every environment-specific value from the environment:

```
DJANGO_SECRET_KEY   DJANGO_DEBUG   DJANGO_ALLOWED_HOSTS
POSTGRES_HOST  POSTGRES_PORT  POSTGRES_DB  POSTGRES_USER  POSTGRES_PASSWORD
MONGO_URI  MONGO_DB
```

- `.env` holds real local values and is **git-ignored**.
- `.env.example` is committed, with placeholder values, as the list of what must be set.
- Inside Compose, `POSTGRES_HOST` is `db` and `MONGO_URI` points at `mongo` — the
  service names, not `localhost`. Containers resolve each other by service name.

---

## 6. How the API layer evolves

The HTTP surface is written twice, on purpose.

| Phases | Implementation | Purpose |
|---|---|---|
| 4 – 6 | hand-written views returning `JsonResponse`, `ModelForm` for validation | see the machinery: routing, parsing, validation, status codes |
| 7 onward | Django REST Framework: serializers, viewsets, routers | see what a framework removes — after knowing what it removed |

**The Phase 5 tests are not rewritten during the Phase 7 refactor.** They are the
contract. If they still pass, the refactor preserved behaviour; if they fail, it did not.

---

## 7. Error handling

| Condition | Where detected | HTTP result |
|---|---|---|
| Malformed or missing field | view, via form/serializer | `400` with per-field errors |
| Record does not exist | view, via `get_object_or_404` | `404` |
| Not logged in | view, via permission check | `401` |
| Logged in but not allowed | view, via permission check | `403` |
| Business rule violated | **service**, raises a domain exception | `409` |
| Database constraint violated | PostgreSQL | `500` — means a service check was missing |

The last row is the safety net, and it is deliberate: every business rule is enforced
**twice** — once in the service layer for a readable error, and once as a database
constraint so that a bug in the service cannot corrupt the data.

---

## 8. Transactions and concurrency

Borrowing is the one place where two simultaneous requests can corrupt state.

- The whole borrow operation runs inside `transaction.atomic`.
- The book row is locked with `select_for_update` before its available count is read,
  so two concurrent borrows of the last copy serialise instead of both succeeding.
- A `CheckConstraint` guarantees `available_copies >= 0` even if the lock is forgotten.

This is exercised by a real concurrent test in Phase 8, not asserted by comment.

---

## Related

- Rules this architecture enforces: [`BUSINESS-RULES.md`](./BUSINESS-RULES.md)
- The schema those rules live in: [`DATA-MODEL.md`](./DATA-MODEL.md)
- Build order and reading list: [`LEARNING-PLAN.md`](./LEARNING-PLAN.md)
- Current state: [`PROGRESS.md`](./PROGRESS.md)
