"""The catalogue: what the library holds.

A Book here is a *title*, not a physical object. The system never tracks WHICH
copy was lent, only HOW MANY are out -- which is why borrowing is a counter
decrement, and why concurrency matters in Phase 8. See the glossary in
BUSINESS-RULES.md.

https://docs.djangoproject.com/en/6.1/topics/db/models/
"""

from django.db import models
from django.db.models import F, Q

from common.models import TimeStampedModel


class Author(TimeStampedModel):
    """A person who wrote one or more Books."""

    # db_index=True asks for a plain single-column index. It is the short form
    # of Meta.indexes for the simplest case; anything involving more than one
    # column, or a condition, has to go in Meta.indexes -- see Book.
    name = models.CharField(max_length=200, db_index=True)

    # This pair of fields is the clearest null-vs-blank example in the schema.
    #
    #     null  -> the DATABASE.   May this column hold NULL?
    #     blank -> VALIDATION.     May a form leave this field empty?
    #
    # They are different layers and are set independently.

    # A birth date that is not recorded is genuinely UNKNOWN, and NULL is the
    # honest representation of unknown -- there is no sensible "empty date".
    # blank=True as well, so a form may leave it out.
    birth_date = models.DateField(null=True, blank=True)

    # blank=True WITHOUT null=True. An absent biography is an EMPTY STRING,
    # not an unknown one. Allowing NULL too would create two ways to say the
    # same thing, and every later query would have to handle both. Avoid
    # null=True on text fields.
    bio = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(TimeStampedModel):
    """A shelf label. A Book may carry several, or none."""

    # The display form: 'Science Fiction'.
    name = models.CharField(max_length=100)

    # The URL form: 'science-fiction'. SlugField accepts only letters, digits,
    # hyphens and underscores. It is kept separate from `name` so the display
    # name can be reworded without breaking a URL that already exists.
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        # Without this, Django calls the model 'Categorys' everywhere it
        # pluralises -- the admin, error messages, the API browser.
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Book(TimeStampedModel):
    """One title the library holds. BR-1 .. BR-5."""

    title = models.CharField(max_length=300, db_index=True)

    # BR-1: two records may not share an ISBN. unique=True gives the UNIQUE
    # index, and on PostgreSQL Django adds a second varchar_pattern_ops index
    # so that __startswith can use it -- the same pair seen on
    # accounts_user.username.
    isbn = models.CharField(max_length=13, unique=True)

    # BR-4: exactly one Author.
    #
    # on_delete=PROTECT (BR-5): deleting an Author who still has Books is
    # refused BY THE DATABASE, not by a check somewhere in the code. The
    # alternatives are worth knowing:
    #     CASCADE   delete the Author -> delete all their Books. Usually a
    #               disaster, and Django's most-misused default.
    #     PROTECT   refuse while anything still references it.  <- here
    #     SET_NULL  keep the Books, blank out author_id.
    #     RESTRICT  like PROTECT but laxer inside a cascading delete.
    #
    # related_name gives the reverse accessor: author.books.all().
    author = models.ForeignKey(
        Author,
        on_delete=models.PROTECT,
        related_name='books',
    )

    # BR-4: zero or more Categories.
    #
    # Django creates the join table catalog_book_categories by itself, with a
    # UNIQUE (book_id, category_id). No `through` model is declared because
    # the relationship carries no extra data -- the day it needs to record
    # WHO attached a category, it needs one.
    #
    # blank=True concerns forms only. A ManyToManyField can never be null:
    # "no categories" is an empty join table, not a NULL.
    categories = models.ManyToManyField(
        Category,
        related_name='books',
        blank=True,
    )

    published_date = models.DateField(null=True, blank=True)

    # BR-2 / BR-3.
    #
    # PositiveIntegerField emits CHECK ("col" >= 0) on PostgreSQL -- see
    # data_type_check_constraints in django/db/backends/postgresql/base.py.
    # So the LOWER bound is free. The upper bound is not; it is the explicit
    # constraint in Meta below.
    total_copies = models.PositiveIntegerField(default=0)

    # Deliberately denormalised: this equals total_copies minus the number of
    # active loans, and could be derived instead of stored. Stored because
    # every catalogue listing would otherwise need a correlated COUNT over
    # loans -- and because the stored counter is what creates the race
    # condition in BR-16, the most valuable lesson in the project.
    #
    # The price is that it can drift from reality if a code path forgets to
    # update it. Hence the check constraint below AND select_for_update in
    # Phase 8: consistency is enforced, not merely intended.
    available_copies = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['title']

        constraints = [
            # BR-3, upper bound. The library cannot have more copies on the
            # shelf than it owns.
            #
            # The keyword is `condition`. It was `check` up to Django 5.0,
            # deprecated in 5.1 and REMOVED in 6.0 -- older examples break.
            #
            # F('total_copies') refers to the value of the other column in the
            # same row, evaluated by the database. A plain self.total_copies
            # would read a Python value at class-definition time, which is not
            # what a constraint can mean.
            models.CheckConstraint(
                condition=Q(available_copies__lte=F('total_copies')),
                name='book_available_lte_total',
            ),
        ]

        indexes = [
            # A PARTIAL index: only rows matching `condition` are indexed.
            # Sold-out books are left out, so the index stays smaller and
            # faster than a full one.
            #
            # It serves the single most common question a borrower asks:
            # "what can I take home right now?" PostgreSQL supports this;
            # MySQL does not.
            models.Index(
                fields=['available_copies'],
                condition=Q(available_copies__gt=0),
                name='book_available_gt0_idx',
            ),
        ]

    def __str__(self):
        return f'{self.title} ({self.isbn})'
