# Data Model — Library Management API

The authoritative specification of every table, column, constraint, and index.

When this document and the code disagree, **this document is wrong** and must be
updated — but no column may be added to the code without being added here first.

Rule IDs in the right-hand columns refer to [`BUSINESS-RULES.md`](./BUSINESS-RULES.md).

---

## Conventions

These apply to every table unless stated otherwise.

| Decision | Choice | Why |
|---|---|---|
| Primary key | `BigAutoField` (`id`) | Django's default. Short URLs (`/books/42/`), small indexes, readable while debugging. |
| Audit columns | `created_at`, `updated_at` on every table, via an abstract base | One definition, no repetition. Invaluable when debugging "when did this change?". |
| Deletion | Hard delete, blocked by `on_delete=PROTECT` | The database refuses to delete a row that is still referenced. No soft-delete flag to forget in a filter. |
| Timestamps | `DateTimeField`, stored in UTC (`USE_TZ = True`) | `due_date` is the one exception — see `circulation_loan`. |
| Table names | Django default: `<app>_<model>` | No reason to fight the convention. |

### Abstract base

```
TimeStampedModel            (abstract — creates no table)
├── created_at   DateTimeField(auto_now_add=True)   set once, on insert
└── updated_at   DateTimeField(auto_now=True)       rewritten on every save
```

`abstract = True` in `Meta` means Django creates no table for it; the columns are copied
into each concrete subclass. See
[Abstract base classes](https://docs.djangoproject.com/en/6.1/topics/db/models/#abstract-base-classes).

> `auto_now` only fires on `Model.save()`. A `QuerySet.update()` bypasses it. That
> surprise will come up in Phase 8.

---

## Entity relationship overview

```
  accounts_user
       │ 1:1  (PROTECT)
       ▼
  accounts_member ────┐
                      │ 1:N (PROTECT)
                      ▼
                circulation_loan
                      ▲
                      │ 1:N (PROTECT)
  catalog_author      │
       │ 1:N          │
       │ (PROTECT)    │
       ▼              │
  catalog_book ───────┘
       │ N:M
       ▼
  catalog_category
```

Every relationship is `PROTECT`. Nothing in this system cascades — a delete that would
destroy history is refused, not silently propagated.

---

## `accounts_user`

Django's `AbstractUser`, subclassed with **no extra fields yet**.

| Column | Type | Null | Notes |
|---|---|---|---|
| *(inherited)* | — | — | `username`, `password`, `email`, `first_name`, `last_name`, `is_active`, `is_staff`, `is_superuser`, `date_joined`, `last_login` |

**Why subclass at all if nothing is added:** because `AUTH_USER_MODEL` cannot be changed
after the first migration without serious pain. Creating the subclass now costs one file
and buys the ability to add a column in Phase 6 without a rewrite.

**Librarian is a group, not a column.** Staff membership is expressed by Django's
`auth.Group` named `librarian`, not by a boolean on this table — so permissions can be
granted and revoked without a migration.

---

## `accounts_member`

The borrowing identity of a person. Separate from `User` because not every account is a
borrower — a librarian has a `User` and no `Member`.

| Column | Type | Null | Default | Rule |
|---|---|---|---|---|
| `id` | `BigAutoField` PK | no | auto | |
| `user_id` | `OneToOneField(User, PROTECT)` | no | — | **BR-6** |
| `status` | `CharField(16, choices)` | no | `ACTIVE` | **BR-7** |
| `created_at` | `DateTimeField` | no | auto | |
| `updated_at` | `DateTimeField` | no | auto | |

`status` ∈ `{ACTIVE, SUSPENDED}` — a `TextChoices` class, not bare strings.

| Constraint / index | Enforces |
|---|---|
| `UNIQUE (user_id)` — implicit in `OneToOneField` | BR-6: one Member per account |
| `PROTECT` on `user_id` | A `User` with a `Member` cannot be deleted |

> **Why `CharField` with choices and not an integer?** The stored value is readable in
> `psql` without a lookup table. At this scale the few extra bytes buy real clarity.

---

## `catalog_author`

| Column | Type | Null | Default | Rule |
|---|---|---|---|---|
| `id` | `BigAutoField` PK | no | auto | |
| `name` | `CharField(200)` | no | — | |
| `birth_date` | `DateField` | **yes** | `NULL` | |
| `bio` | `TextField(blank=True)` | no | `''` | |
| `created_at` / `updated_at` | `DateTimeField` | no | auto | |

**`null` vs `blank` — the clearest example in the schema:**

- `birth_date` uses `null=True`: the date is genuinely *unknown*, and `NULL` is the honest
  representation of unknown.
- `bio` uses `blank=True` with `null=False`: an empty biography is an *empty string*, not
  an unknown one. Two ways to say "no bio" would be one too many.

The rule: **`null` is about the database, `blank` is about validation.** Avoid
`null=True` on text fields.

| Index | Why |
|---|---|
| `name` | Author search in Phase 2 and Phase 4 |

---

## `catalog_category`

| Column | Type | Null | Default | Rule |
|---|---|---|---|---|
| `id` | `BigAutoField` PK | no | auto | |
| `name` | `CharField(100)` | no | — | |
| `slug` | `SlugField(100, unique=True)` | no | — | |
| `created_at` / `updated_at` | `DateTimeField` | no | auto | |

`slug` is the URL-safe form (`science-fiction`) and is unique; `name` is the display form
(`Science Fiction`).

---

## `catalog_book`

The central table. A row is a **title**, not a physical object.

| Column | Type | Null | Default | Rule |
|---|---|---|---|---|
| `id` | `BigAutoField` PK | no | auto | |
| `title` | `CharField(300)` | no | — | |
| `isbn` | `CharField(13, unique=True)` | no | — | **BR-1** |
| `author_id` | `ForeignKey(Author, PROTECT)` | no | — | **BR-4** |
| `published_date` | `DateField` | **yes** | `NULL` | |
| `total_copies` | `PositiveIntegerField` | no | `0` | **BR-2** |
| `available_copies` | `PositiveIntegerField` | no | `0` | **BR-3** |
| `created_at` / `updated_at` | `DateTimeField` | no | auto | |

### Why `available_copies` is a stored column

It could be derived: `total_copies` minus the count of active loans. Storing it is
**denormalisation**, chosen deliberately:

- Every catalogue listing would otherwise need a correlated `COUNT` over loans.
- The stored counter is what creates the concurrency problem in BR-16 — which is the
  single most valuable lesson in this project.

The price of denormalisation is that the number **can drift from reality** if a code path
forgets to update it. That is why it is protected by a check constraint *and* by
row-level locking, rather than by careful coding alone.

### Constraints

| Name | Definition | Rule |
|---|---|---|
| `UNIQUE (isbn)` | implicit in `unique=True` | BR-1 |
| `book_total_copies_non_negative` | implicit in `PositiveIntegerField` | BR-2 |
| `book_available_copies_non_negative` | implicit in `PositiveIntegerField` | BR-3 |
| `book_available_lte_total` | `CheckConstraint(available_copies <= total_copies)` | BR-3 |

`PositiveIntegerField` emits a `CHECK (col >= 0)` in PostgreSQL, so the lower bound is
free. The upper bound is not — it must be written explicitly.

### Indexes

| Index | Why |
|---|---|
| `title` | Title search |
| `author_id` | Automatic (foreign key) |
| `(available_copies)` partial, `WHERE available_copies > 0` | "What can I borrow right now?" — the most common catalogue query |

---

## `catalog_book_categories`

The join table Django creates for `Book.categories = ManyToManyField(Category)`.
Not declared by hand.

| Column | Type |
|---|---|
| `id` | `BigAutoField` PK |
| `book_id` | FK → `catalog_book` |
| `category_id` | FK → `catalog_category` |

`UNIQUE (book_id, category_id)` — automatic. The same category cannot be attached twice.

> A plain `ManyToManyField` is used because the relationship carries **no extra data**.
> The moment it needs one (say, "who assigned this category"), it needs an explicit
> `through` model. It does not need one here.

---

## `circulation_loan`

One Member borrowing one Copy of one Book. Introduced in Phase 8.

| Column | Type | Null | Default | Rule |
|---|---|---|---|---|
| `id` | `BigAutoField` PK | no | auto | |
| `member_id` | `ForeignKey(Member, PROTECT)` | no | — | **BR-8** |
| `book_id` | `ForeignKey(Book, PROTECT)` | no | — | **BR-5** |
| `borrowed_at` | `DateTimeField` | no | now | **BR-9** |
| `due_date` | `DateField` | no | — | **BR-10** |
| `returned_at` | `DateTimeField` | **yes** | `NULL` | **BR-9** |
| `status` | `CharField(16, choices)` | no | `ACTIVE` | **BR-11** |
| `created_at` / `updated_at` | `DateTimeField` | no | auto | |

`status` ∈ `{ACTIVE, OVERDUE, RETURNED}`.

### Why `due_date` is a `DateField` while the others are `DateTimeField`

A library due date is **a day**, not an instant: a book is due *on the 9th*, not at
09:14:22 on the 9th. Storing a timestamp would invent a precision the business does not
have, and would make "is this overdue?" depend on the time of day.

### The redundancy between `status` and `returned_at`, and how it is contained

`RETURNED` is derivable from `returned_at IS NOT NULL`. Two sources of truth for one fact
is exactly how data goes bad — so they are **tied together by a constraint** rather than
by convention:

| Name | Definition | Rule |
|---|---|---|
| `loan_returned_consistency` | `(status = 'RETURNED') = (returned_at IS NOT NULL)` | BR-11, BR-18 |

A row where `status = 'RETURNED'` but `returned_at` is `NULL` cannot be written. The
database will not allow the two to disagree.

`status` is kept despite this because `ACTIVE` and `OVERDUE` are **not** derivable at
read time under BR-20 — the overdue transition is performed by a job, so the stored value
is the truth.

### Remaining constraints

| Name | Definition | Rule |
|---|---|---|
| `loan_one_active_per_member_book` | `UniqueConstraint(member, book, condition=Q(returned_at__isnull=True))` | **BR-12** |
| `loan_due_after_borrow` | `CheckConstraint(due_date >= borrowed_at::date)` | BR-10 |

The first is a **partial unique index**: uniqueness applies only to rows where
`returned_at IS NULL`. A member may borrow the same book many times across their life —
just not twice at once. PostgreSQL supports this; most databases do not. See
[`UniqueConstraint.condition`](https://docs.djangoproject.com/en/6.1/ref/models/constraints/#django.db.models.UniqueConstraint.condition).

### Indexes

| Index | Serves |
|---|---|
| `(member_id, status)` | BR-13.3 (count active loans) and BR-14 (any overdue?) — checked on **every** borrow |
| `(status, due_date)` | BR-20, the `mark_overdue_loans` job |
| `book_id` | Automatic. Also serves BR-5's "any active loan?" check |

---

## MongoDB: `activity_log`

A single collection. **No schema is enforced** — these are the fields the application
writes, by agreement rather than by constraint.

```javascript
{
  _id:        ObjectId("..."),
  event:      "loan.borrowed",          // required, from the fixed list in BR-23
  actor:      { id: 7, username: "nghia" },
  target:     { type: "book", id: 42, title: "Dune" },
  payload:    { due_date: "2026-11-09", copies_left: 3 },
  created_at: ISODate("2026-10-27T09:00:00Z")
}
```

| Field | Always present | Notes |
|---|---|---|
| `event` | yes | One of the six names in BR-23 |
| `actor` | yes | `null` for system-generated events such as `loan.overdue` |
| `target` | yes | `type` + `id` + a human-readable label |
| `payload` | yes | **Shape differs per event type.** This is the reason for MongoDB |
| `created_at` | yes | UTC |

`actor.username` and `target.title` are **copies taken at write time**, not references
(**BR-24**). If the book is renamed later, this document keeps the old title — correctly,
because it records what was true then.

| Index | Serves |
|---|---|
| `(event, created_at desc)` | `GET /activity/?event=loan.borrowed` |
| `(actor.id, created_at desc)` | "What has this member done?" |
| `created_at desc` | The unfiltered feed |

---

## Rule → enforcement map

Every business rule and where it is actually prevented. A rule with no database row in
this table is enforced **only** by application code, and is therefore only as reliable as
the code path that remembers to call it.

| Rule | Service layer | Database |
|---|---|---|
| BR-1 unique ISBN | validation message | `UNIQUE (isbn)` |
| BR-2 `total_copies >= 0` | — | `PositiveIntegerField` |
| BR-3 `0 <= available <= total` | pre-check before decrement | `PositiveIntegerField` + `book_available_lte_total` |
| BR-5 no delete with active loan | friendly error | `on_delete=PROTECT` |
| BR-6 one Member per User | — | `UNIQUE (user_id)` |
| BR-7 only ACTIVE may borrow | yes | — |
| BR-8 no delete of Member with loans | friendly error | `on_delete=PROTECT` |
| BR-10 due date = +14 days | computed at borrow | `loan_due_after_borrow` |
| BR-11 active = no return date | yes | `loan_returned_consistency` |
| BR-12 one active loan per book | yes | `loan_one_active_per_member_book` |
| BR-13 borrow preconditions | **yes — all five** | partially, via the above |
| BR-14 overdue blocks borrowing | yes | — |
| BR-15 borrow is atomic | `transaction.atomic` | — |
| BR-16 concurrency | `select_for_update` | `available_copies >= 0` |
| BR-17 no double return | yes | `loan_returned_consistency` |
| BR-20 overdue transition | management command | — |
| BR-22 members act on own loans only | permission check | — |

**Read this table as a risk register.** The rows with an empty *Database* column are the
ones a bug can violate — BR-7, BR-14, BR-22. They need the most test coverage.

---

## Build order

| Phase | Tables created |
|---|---|
| 1 | `accounts_user`, `accounts_member`, `catalog_author`, `catalog_category`, `catalog_book`, `catalog_book_categories` |
| 8 | `circulation_loan` |
| 9 | `activity_log` (MongoDB) |

`accounts_user` must exist, and `AUTH_USER_MODEL` must point at it, **before the first
`migrate` runs**.

---

## Related

- Why these rules exist: [`BUSINESS-RULES.md`](./BUSINESS-RULES.md)
- Where enforcement lives in the code: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- When each table gets built: [`LEARNING-PLAN.md`](./LEARNING-PLAN.md)
