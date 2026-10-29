"""Shared abstract models.

`common` is a plain Python package, NOT a Django app, and is deliberately
absent from INSTALLED_APPS. It defines only abstract models: they own no
tables, so there is nothing for Django to migrate. Django exempts abstract
models from the INSTALLED_APPS requirement -- see the `if not abstract` guard
in django/db/models/base.py.

https://docs.djangoproject.com/en/6.1/topics/db/models/#abstract-base-classes
"""

from django.db import models


class TimeStampedModel(models.Model):
    """Audit columns for every table in the project.

    Because this class is abstract, Django creates no `common_timestampedmodel`
    table. The two columns below are copied into each concrete subclass, so
    `catalog_book` and `accounts_member` each carry their own pair. There is no
    shared table and therefore no join -- inheritance here is a code-reuse
    device, not a database relationship.
    """

    # auto_now_add: written once, at INSERT. Assigning to it afterwards in
    # Python is silently ignored, which is the point -- creation time is not
    # something application code should be able to rewrite.
    created_at = models.DateTimeField(auto_now_add=True)

    # auto_now: rewritten on every Model.save().
    #
    # It is NOT touched by QuerySet.update(), which compiles straight to a SQL
    # UPDATE and never calls save(). So this leaves updated_at stale:
    #     Book.objects.filter(pk=1).update(available_copies=3)
    # while this does not:
    #     book.available_copies = 3; book.save()
    # Phase 8 runs into exactly this.
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
