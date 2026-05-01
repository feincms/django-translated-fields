========================
django-translated-fields
========================

.. image:: https://github.com/matthiask/django-translated-fields/workflows/Tests/badge.svg
    :target: https://github.com/matthiask/django-translated-fields/
    :alt: CI Status

Django model translation without magic-inflicted pain.

Installation
============

Install the package into your virtualenv::

    pip install django-translated-fields

Add the package to your ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS = [
        *INSTALLED_APPS,
        "translated_fields",
    ]

django-translated-fields supports all versions of Django from 3.2 to 6.0. If in
doubt, check the test runs in the GitHub actions environment.


Usage
=====

You should define the `the list of languages your project supports in your
settings first
<https://docs.djangoproject.com/en/5.0/ref/settings/#languages>`__ by defining
``LANGUAGES``. Otherwise, you'll get fields for all the dozens of languages
Django supports out of the box.

Next, add translated fields to your models:

.. code-block:: python

    from django.db import models
    from django.utils.translation import gettext_lazy as _

    from translated_fields import TranslatedField

    class Question(models.Model):
        question = TranslatedField(
            models.CharField(_("question"), max_length=200),
        )
        answer = TranslatedField(
            models.CharField(_("answer"), max_length=200),
        )

        def __str__(self):
            return self.question


Basic usage
===========

Model fields are automatically created from the field passed to
``TranslatedField``, one field per language.  For example, with
``LANGUAGES = [("en", "English"), ("de", "German"), ("fr", "French")]``,
the following list of fields would be created: ``question_en``,
``question_de``, ``question_fr``, ``answer_en``, ``answer_de``,
and ``answer_fr``.

This implies that when changing ``LANGUAGES`` you'll have to run
``makemigrations`` and ``migrate`` too.

No ``question`` or ``answer`` model field is actually created. The
``TranslatedField`` instance is a `descriptor
<https://docs.python.org/3/howto/descriptor.html>`_ which by default
acts as a property for the current language's field:

.. code-block:: python

    from django.utils.translation import override

    question = Question(
        question_en="How are you?",
        question_de="Wie geht es Dir?",
        question_fr="Ça va?",
    )

    # The default getter automatically returns the value
    # in the current language:
    with override("en"):
        assert question.question == "How are you?"

    with override("de"):
        assert question.question == "Wie geht es Dir?"

    # The default setter can also be used to set the value
    # in the current language:
    with override("fr"):
        question.question = "Comment vas-tu?"

    assert question.question_fr == "Comment vas-tu?"

``TranslatedField`` has a ``fields`` attribute that returns a list of all
the language fields created.

.. code-block:: python

    assert Question.answer.fields == ["answer_en", "answer_de", "answer_fr"]

For more attributes look at the *``TranslatedField`` instance API*
section below.

``question`` and ``answer`` can only be used with model instances, they
do not exist in the database. If you want to use queryset methods which
reference individual translated fields you have to use language-specific
field names yourself. If you wanted to fetch only the english question
and answer fields you could do this as follows:

.. code-block:: python

    questions = Question.objects.values_list("question_en", "answer_en")

Or better yet, using the ``to_attribute`` helper which automatically
uses the active language (if you don't pass a specific language code as
its second argument):

.. code-block:: python

    from django.utils.translation import override
    from translated_fields import to_attribute

    with override("en"):
        questions = Question.objects.values_list(
            to_attribute("question"), to_attribute("answer")
        )


The ``to_attribute`` helper can also be used when filtering, for example:

.. code-block:: python

    from django.utils.translation import override
    from translated_fields import to_attribute

    # Find the value in a specific field:
    with override("en"):
        questions = Question.objects.filter(
            **{to_attribute("question"): "How are you?"}
        )

    # Find the value in all fields:
    from django.db.models import Q

    s = "How are you?"
    q = Q(**{Question.question.fields[0]: s})
    for field in Question.question.fields[1:]:
        q |= Q(**{field: s})
    questions = Question.objects.filter(q)

.. important::

   **Fields with custom deconstruct() methods**

   If you use fields with custom ``deconstruct()`` methods that modify field
   parameters (such as ``ChoicesCharField`` from feincms3), be aware that
   ``TranslatedField`` currently uses the output of ``deconstruct()`` to create
   the translated fields. This means any parameter modifications in the field's
   ``deconstruct()`` method will affect the translated fields.

   For example, if your custom field's ``deconstruct()`` method changes the
   ``choices`` parameter, the translated fields will use those modified choices
   rather than the original ones.


Changing field attributes per language
======================================

It is sometimes useful to have slightly differing model fields per
language, e.g. for making the primary language mandatory. This can be
achieved by passing a dictionary with keyword arguments per language as
the second positional argument to ``TranslatedField``.

For example, if you add a language to ``LANGUAGES`` when a site is
already running, it might be useful to make the new language
non-mandatory to simplify editing already existing data through Django's
administration interface.

The following example adds ``blank=True`` to the spanish field:

.. code-block:: python

    from translated_fields import TranslatedField

    class Question(models.Model):
        question = TranslatedField(
            models.CharField(_("question"), max_length=200),
            {"es": {"blank": True}},
        )


Overriding attribute access (defaults, fallbacks)
=================================================

There are no default values or fallbacks, only a wrapped attribute
access. The default attribute getter and setter functions simply return
or set the field for the current language (as returned by
``django.utils.translation.get_language``). The default getter falls
back to the first language of the field in case ``get_language()``
returns ``None``. Apart from that the default getter has no
safetyfeatures and may raise an ``AttributeError`` and the setter might
set an attribute on the model instance not related to a model field.

Both getters and setters can be overridden by specifying your own
``attrgetter`` and ``attrsetter`` functions. If you want to always fallback to
the default language and allow other languages' fields to be empty you can use
the ``TranslatedFieldWithFallback``:

.. code-block:: python

    from translated_fields import TranslatedFieldWithFallback

    class Question(models.Model):
        question = TranslatedFieldWithFallback(
            models.CharField(_("question"), max_length=200),
        )

What it does is: It adds a question field for all languages and automatically
falls back to the first defined language if the current language's field is
left empty or if no language is activated at all. It also sets ``blank=True``
on all field instances except for the first. Since this is such a common use
case the ``TranslatedFieldWithFallback`` can be used directly, or you can use
the ``translated_fields.utils.fallback_to_default`` attrgetter.

A different use case might require falling back to any language, this is
handled by the bundled ``translated_fields.utils.fallback_to_any`` attrgetter.

A different use case might be when you're using locales with region codes such
as ``fr-fr`` where you want to fall back to the language without a region code.
An example ``attrgetter`` implementation follows:

.. code-block:: python

    from translated_fields import to_attribute

    def fallback_to_all_regions(name, field):
        def getter(self):
            value = getattr(self, to_attribute(name), None)
            if value:
                return value
            return getattr(self, to_attribute(name, get_language().split("-")[0]))

        return getter

A custom ``attrsetter`` which always sets all fields follows (probably
not very useful, but hopefully instructive):

.. code-block:: python

    def set_all_fields(name, field):
        def setter(self, value):
            for field in field.fields:
                setattr(self, field, value)
        return setter


``TranslatedField`` instance API
================================

The ``TranslatedField`` descriptor has a few useful attributes (sticking
with the model and field from the examples above):

* ``Question.question.fields`` contains the names of all automatically
  generated fields, e.g. ``["question_en", "question_...", ...]``.
* ``Question.question.languages`` is the list of language codes.
* ``Question.question.short_description`` is set to the ``verbose_name``
  of the base field, so that the translatable attribute can be nicely
  used e.g. in ``ModelAdmin.list_display``.


Using a different set of languages
==================================

It is also possible to override the list of language codes used, for
example if you want to translate a sub- or superset of
``settings.LANGUAGES``. Combined with ``attrgetter`` and ``attrsetter``
there is nothing stopping you from using this field for a different kind
of translations, not necessarily bound to ``django.utils.translation``
or even languages at all.


Translated attributes without model field creation
==================================================

If model field creation is not desired, you may also use the
``translated_attributes`` class decorator. This only creates the
attribute getter property:

.. code-block:: python

    from translated_fields import translated_attributes

    @translated_attributes("attribute", "anything", ...)
    class Test(object):
        attribute_en = "some value"
        attribute_de = "some other value"


Model admin support
===================

The ``TranslatedFieldAdmin`` class adds the respective language to the
label of individual fields. Instead of three fields named "Question"
you'll get the fields "Question [en]", "Question [de]" and "Question
[fr]". It intentionally offers no functionality except for modifying the
label of fields:

.. code-block:: python

    from django.contrib import admin
    from translated_fields import TranslatedFieldAdmin
    from .models import Question

    @admin.register(Question)
    class QuestionAdmin(TranslatedFieldAdmin, admin.ModelAdmin):
        pass

    # For inlines:
    # class SomeInline(TranslatedFieldAdmin, admin.StackedInline):
    #     ...

As mentioned above, the ``fields`` attribute on the ``TranslatedField``
instance contains the list of generated fields. This may be useful if
you want to customize various aspects of the ``ModelAdmin`` subclass. An
example showing various techniques follows:

.. code-block:: python

    from django.contrib import admin
    from django.utils.translation import gettext_lazy as _
    from translated_fields import TranslatedFieldAdmin, to_attribute
    from .models import Question

    @admin.register(Question)
    class QuestionAdmin(TranslatedFieldAdmin, admin.ModelAdmin):
        # Pack question and answer fields into their own fieldsets:
        fieldsets = [
            (_("question"), {"fields": Question.question.fields}),
            (_("answer"), {"fields": Question.answer.fields}),
        ]

        # Show all fields in the changelist:
        list_display = [
            *Question.question.fields,
            *Question.answer.fields
        ]

        # Order by current language's question field:
        def get_ordering(self, request):
            return [to_attribute("question")]

.. note::
   It's strongly recommended to set the ``verbose_name`` of fields when
   using ``TranslatedFieldAdmin``, the first argument of most model
   fields. Otherwise, you'll get duplicated languages, e.g. "Question en
   [en]".


Forms
=====

django-translated-fields provides a helper when you want form fields'
labels to contain the language code. If this sounds useful to you do
this:

.. code-block:: python

    from django import forms
    from translated_fields.utils import language_code_formfield_callback
    from .models import Question

    class QuestionForm(forms.ModelForm):

        class Meta:
            model = Question
            fields = [
                *Question.question.fields,
                *Question.answer.fields
            ]
            # Supported starting with Django 4.2: (Previously it was supported
            # directly on the modelform class, but only as an implementation
            # detail https://code.djangoproject.com/ticket/26456)
            formfield_callback = language_code_formfield_callback


You may also globally configure language code labels to be shown within
a block:

.. code-block:: python

    from translated_fields import show_language_code

    def view(request):
        form = ...
        with show_language_code(True):
            return render(request, "...", {"form": form})

Please note that the response has to be rendered within the
``show_language_code`` block. This doesn't happen automatically when
using Django's ``TemplateResponse`` objects.


Other features
==============

There is no support for automatically referencing the current language's
field in queries or automatically adding fields to admin fieldsets and
whatnot. The code required for these features isn't too hard to write,
but it is hard to maintain down the road which contradicts my goal of
writing `low maintenance software
<https://406.ch/writing/low-maintenance-software/>`_. Still, feedback
and pull requests are very welcome! Please run the style checks and test
suite locally before submitting a pull request though -- all that this
requires is running `tox <https://tox.readthedocs.io/>`_.
