"""Identity for the library: who can log in, and who may borrow.

Two models, deliberately separate:

    User    an account that can authenticate. A librarian has one.
    Member  the borrowing identity. A librarian does NOT have one.

https://docs.djangoproject.com/en/6.1/topics/auth/customizing/
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from common.models import TimeStampedModel


class User(AbstractUser):
    """This project's user model. It adds no fields -- yet.

    It exists so that AUTH_USER_MODEL points at a model this project owns.
    Django cannot swap AUTH_USER_MODEL once any migration has been applied,
    so the subclass has to exist before the first migrate even while empty.
    Adding a column in Phase 6 is then an ordinary migration instead of a
    rewrite.

    `librarian` is NOT a field here. Staff are members of the auth.Group
    named 'librarian', so the role is granted and revoked without a
    migration. See the permissions table in BUSINESS-RULES.md.
    """


class Member(TimeStampedModel):
    """A person entitled to borrow. BR-6."""

    class Status(models.TextChoices):
        # Each entry is (value stored in the column, label shown to humans).
        # A TextChoices class rather than bare strings: a typo in
        # Status.SUSPENDE is an AttributeError, while a typo in 'SUSPENDE '
        # is a silent data bug.
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    # OneToOneField, not ForeignKey(unique=True).
    #
    # The two produce the SAME column and the same UNIQUE index. What differs
    # is the Python side: the reverse accessor here is a single object,
    # `user.member`, rather than a manager, `user.member_set.all()`. The
    # relationship reads as 1:1 in code as well as in the schema.
    #
    # settings.AUTH_USER_MODEL, not User: this is the documented way to refer
    # to the user model. Naming the class directly would bake it into the
    # generated migration.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # BR-8: a Member's history is never deleted
        related_name='member',
    )

    # BR-7.
    #
    # `choices` is enforced by forms and by full_clean() -- NOT by the
    # database. Django emits no CHECK constraint for it, so
    # Member.objects.create(status='banana') succeeds at the SQL level.
    # DATA-MODEL.md lists BR-7 among the rules with no database enforcement;
    # the service layer and the tests are what hold it up.
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        # Meta.ordering applies to EVERY query on this model unless a later
        # .order_by() overrides it -- convenient, but it is a cost paid
        # everywhere, so it has to be cheap. '-created_at' sorts on a column
        # of this table. Ordering by 'user__username' would have forced a JOIN
        # into every single Member query.
        ordering = ['-created_at']

    def __str__(self):
        # __str__ is what the admin, the shell, and repr() display. Without it
        # you get '<Member: Member object (1)>', which is useless when
        # debugging.
        #
        # Django also generates a get_status_display() method on this class at
        # import time, because `status` has choices -- see
        # Field.contribute_to_class in django/db/models/fields/__init__.py.
        # It is NOT written here, so a static type checker such as Pylance
        # cannot see it and reports a false positive. Status(...).label is the
        # equivalent the checker can follow.
        #
        # One real difference: get_status_display() returns the raw value when
        # it is not one of the choices, while Status(...) raises ValueError.
        # `choices` is not enforced by the database (BR-7 has no database row
        # in the enforcement map), so an out-of-choices value is possible in
        # principle -- and here it would fail loudly rather than quietly.
        #
        # Note also that this reads self.user: printing a list of Members
        # without select_related('user') issues one extra query per row. That
        # is the N+1 problem, named in Phase 2.
        return f'{self.user.username} ({self.Status(self.status).label})'
