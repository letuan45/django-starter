# Business Rules — Library Management API

What the system is *about*, in the language of a librarian rather than of Django.

Every rule has an ID. Code, tests, and commit messages refer to these IDs, so that a
rule and its enforcement can always be traced to each other.

---

## Glossary

| Term | Meaning |
|---|---|
| **Book** | A *title* the library holds, not a physical object. "Dune" is one Book. |
| **Copy** | One physical object of a Book. A Book has `total_copies` of them. |
| **Available copies** | Copies currently on the shelf: `total_copies` minus active loans. |
| **Member** | A person entitled to borrow. One Member per user account. |
| **Loan** | One Member borrowing one Copy of one Book, from a date until a date. |
| **Librarian** | Staff. Manages the catalogue. Does not borrow in that capacity. |
| **Overdue** | An active Loan whose due date has passed. |

The Book / Copy distinction is the single most important idea here. The system never
tracks *which* physical copy was lent — only *how many* are out. That is why borrowing
is a counter decrement, and why concurrency matters.

---

## Policy constants

These are library policy, not technical limits. They live in one place in the code so
that changing policy is a one-line change.

| Constant | Value | Meaning |
|---|---|---|
| `LOAN_PERIOD_DAYS` | `14` | How long a Member may keep a Copy |
| `MAX_ACTIVE_LOANS_PER_MEMBER` | `5` | How many Copies a Member may hold at once |

**No monetary fines.** The only consequence of being overdue is losing the right to
borrow (BR-14). This is a deliberate scope decision: it keeps money, decimals, and
rounding out of the project.

---

## Entities and their invariants

### Book

| Rule | Statement |
|---|---|
| **BR-1** | A Book has a unique ISBN. Two records may not share one. |
| **BR-2** | `total_copies` is at least `0`. |
| **BR-3** | `available_copies` is always between `0` and `total_copies`, inclusive. Never negative, never more than the library owns. |
| **BR-4** | A Book has exactly one Author and zero or more Categories. |
| **BR-5** | A Book with at least one active Loan may not be deleted. The catalogue may not forget a Copy that is out in the world. |

### Member

| Rule | Statement |
|---|---|
| **BR-6** | Every Member corresponds to exactly one user account, and every user account has at most one Member record. |
| **BR-7** | A Member is either `ACTIVE` or `SUSPENDED`. Only an `ACTIVE` Member may borrow. |
| **BR-8** | A Member with any Loan — active or historical — may not be deleted. History is preserved. |

### Loan

A Loan is in exactly one state at a time:

```
            borrow                 return
   (none) ----------> ACTIVE ----------------> RETURNED
                        |                          ^
                        | due date passes          |
                        v                          | return
                     OVERDUE ----------------------+
```

| Rule | Statement |
|---|---|
| **BR-9** | A Loan records the Member, the Book, the borrow date, the due date, and the return date (empty until returned). |
| **BR-10** | `due_date` is `borrowed_at` plus `LOAN_PERIOD_DAYS`. It is computed at borrow time and then fixed. |
| **BR-11** | A Loan is *active* when it has no return date. `ACTIVE` and `OVERDUE` are both active states. |
| **BR-12** | A Member may hold at most one active Loan of the same Book. Wanting two copies of one title is not a supported need. |

---

## Borrowing

**BR-13 — Borrow preconditions.** A borrow is accepted only when *all* of these hold:

1. The Member is `ACTIVE` (BR-7).
2. The Book has `available_copies > 0`.
3. The Member has fewer than `MAX_ACTIVE_LOANS_PER_MEMBER` active Loans.
4. The Member has no `OVERDUE` Loan (BR-14).
5. The Member does not already hold this Book (BR-12).

If any fails, the borrow is rejected with a message naming **which** rule failed. A
rejection is a normal outcome, not an error — the caller gets `409`, not `500`.

**BR-14 — Overdue block.** A Member holding any `OVERDUE` Loan may not start a new one,
whatever the title. Returning the overdue Copy immediately restores the right to borrow.

**BR-15 — Borrow effects.** A successful borrow, as one indivisible unit:

1. decrements `available_copies` by one,
2. creates a Loan in state `ACTIVE` with `due_date` per BR-10,
3. records a `loan.borrowed` event in the activity log.

Either all three happen or none do. A borrow that fails halfway must leave no trace.

**BR-16 — Concurrency.** Two Members borrowing the last Copy at the same instant: exactly
one succeeds, the other is rejected under BR-13.2. `available_copies` may never go
negative, regardless of how the requests interleave.

---

## Returning

**BR-17 — Return preconditions.** The Loan must exist and must be active (BR-11).
Returning an already-returned Loan is rejected — it is not silently accepted, because a
silent accept would double-count the Copy back onto the shelf.

**BR-18 — Return effects.** A successful return, as one indivisible unit:

1. sets the return date to now,
2. moves the Loan to `RETURNED`, from either `ACTIVE` or `OVERDUE`,
3. increments `available_copies` by one,
4. records a `loan.returned` event in the activity log.

**BR-19 — Late returns are accepted.** An overdue Copy is always accepted back. Being
late never blocks a return; it only blocked borrowing, and that block now lifts.

---

## Overdue detection

**BR-20.** A Loan becomes `OVERDUE` when it is still active and its `due_date` is earlier
than today. The transition is performed by a scheduled job (`mark_overdue_loans`), not
at read time, so that the stored state is the truth and queries stay simple.

**BR-21.** Overdue detection is **idempotent**. Running the job twice in one day changes
nothing the second time, and emits no duplicate events.

---

## Permissions

| Action | Anonymous | Member | Librarian |
|---|---|---|---|
| Browse and search books | yes | yes | yes |
| View book detail | yes | yes | yes |
| Create / edit a book | no | no | yes |
| Delete a book | no | no | yes (subject to BR-5) |
| Borrow a book | no | own account only | no |
| Return a book | no | own loans only | any loan |
| View loan history | no | own loans only | all loans |
| Read the activity log | no | no | yes |

**BR-22.** A Member may act only on their own Loans. Borrowing or returning on behalf of
another Member is a librarian action.

---

## Activity log

**BR-23.** Every state change is recorded as an event. Events are **append-only**: never
updated, never deleted.

| Event | Emitted when |
|---|---|
| `book.created` | a Book is added to the catalogue |
| `book.updated` | a Book's details change |
| `book.deleted` | a Book is removed |
| `loan.borrowed` | BR-15 succeeds |
| `loan.returned` | BR-18 succeeds |
| `loan.overdue` | BR-20 moves a Loan to `OVERDUE` |

**BR-24.** An event carries everything needed to read it later **without querying
Postgres** — including the book title and the member name as they were at that moment.
See the denormalisation note in [`ARCHITECTURE.md`](./ARCHITECTURE.md).

**BR-25.** A failure to write the activity log must not fail the business operation. The
log is a record of what happened, not a participant in making it happen.

---

## Deliberately out of scope

Named here so they are understood as *decisions*, not oversights:

- Reservations and waiting lists
- Monetary fines, payments, membership fees
- Renewals and extensions
- Tracking individual physical copies by barcode
- Multiple branches or inter-branch transfers
- Notifications of any kind (email, SMS, push)

---

## Related

- How these rules are enforced in code: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- The tables and constraints behind them: [`DATA-MODEL.md`](./DATA-MODEL.md)
- When each rule gets built: [`LEARNING-PLAN.md`](./LEARNING-PLAN.md) — Phase 8 and Phase 9
