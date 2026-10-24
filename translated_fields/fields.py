import contextvars
import copy
import re
from contextlib import contextmanager

from django.conf import settings
from django.db.models import Field
from django.utils.functional import lazy
from django.utils.text import capfirst
from django.utils.translation import get_language


__all__ = [
    "TranslatedField",
    "show_language_code",
    "to_attribute",
    "translated_attrgetter",
    "translated_attributes",
    "translated_attrsetter",
]


_show_language_code = contextvars.ContextVar("show_language_code")


@contextmanager
def show_language_code(show):
    token = _show_language_code.set(show)
    try:
        yield
    finally:
        _show_language_code.reset(token)


def _verbose_name_maybe_language_code(verbose_name, language_code):
    def verbose_name_fn():
        if _show_language_code.get(False):
            return f"{capfirst(verbose_name)} [{language_code}]"
        return str(verbose_name)

    return lazy(verbose_name_fn, str)()


def to_attribute(name, language_code=None):
    language = language_code or get_language()
    return re.sub(r"[^a-z0-9_]+", "_", (f"{name}_{language}").lower())


def translated_attrgetter(name, field):
    return lambda self: getattr(
        self, to_attribute(name, get_language() or field.languages[0])
    )


def translated_attrsetter(name, field):
    return lambda self, value: setattr(
        self, to_attribute(name, get_language() or field.languages[0]), value
    )


def _copy_field(field, specific):
    """
    Return a copy of ``field`` with the ``specific`` keyword arguments applied

    Copying instead of reconstructing the field from ``deconstruct()`` keeps
    state which isn't (or deliberately isn't) part of the deconstructed
    keyword arguments, e.g. configuration which shouldn't end up in migrations.

    There's no general way to apply keyword arguments to an existing field.
    Instead, the field is reconstructed twice, with and without ``specific``,
    and the attributes which differ are transferred to the copy.
    """
    new = copy.deepcopy(field)
    if not specific:
        return new

    _n, _p, args, kwargs = field.deconstruct()
    base = vars(field.__class__(*args, **kwargs))
    changed = field.__class__(*args, **(kwargs | specific))
    missing = object()
    for attr, value in vars(changed).items():
        if attr != "creation_counter" and base.get(attr, missing) != value:
            setattr(new, attr, value)
    if getattr(new.remote_field, "field", None) is changed:
        new.remote_field.field = new
    return new


def translated_attributes(*names, attrgetter=translated_attrgetter):
    field = TranslatedField(None)  # Allow accessing field.languages etc. in the getter

    def decorator(cls):
        for name in names:
            setattr(cls, name, property(attrgetter(name, field)))
        return cls

    return decorator


class TranslatedField:
    def __init__(
        self, field, specific=None, *, languages=None, attrgetter=None, attrsetter=None
    ):
        self._field = field
        self._specific = {
            language: dict(kwargs) for language, kwargs in (specific or {}).items()
        }
        self._attrgetter = attrgetter or translated_attrgetter
        self._attrsetter = attrsetter or translated_attrsetter
        self.languages = list(languages or (lang[0] for lang in settings.LANGUAGES))

        # Make space for our fields.
        self.creation_counter = Field.creation_counter
        Field.creation_counter += len(self.languages)

    def contribute_to_class(self, cls, name):
        fields = []
        verbose_name = self._field.verbose_name
        if verbose_name is None:
            verbose_name = name
        for index, language_code in enumerate(self.languages):
            specific = self._specific.get(language_code, {})
            f = _copy_field(self._field, specific)
            if "verbose_name" not in specific:
                f.verbose_name = _verbose_name_maybe_language_code(
                    verbose_name, language_code
                )
            f._translated_field_language_code = language_code
            f.creation_counter = self.creation_counter + index
            attr = to_attribute(name, language_code)
            f.contribute_to_class(cls, attr)
            fields.append(attr)

        setattr(cls, name, self)
        self.fields = fields
        self.short_description = verbose_name

        self._getter = self._attrgetter(name, field=self)
        self._setter = self._attrsetter(name, field=self)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self._getter(obj)

    def __set__(self, obj, value):
        self._setter(obj, value)
