import contextvars
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
    yield
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
    return lambda self, value: setattr(self, to_attribute(name), value)


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
        self._specific = specific or {}
        self._attrgetter = attrgetter or translated_attrgetter
        self._attrsetter = attrsetter or translated_attrsetter
        self.languages = list(languages or (lang[0] for lang in settings.LANGUAGES))

        # Make space for our fields.
        self.creation_counter = Field.creation_counter
        Field.creation_counter += len(self.languages)

    def contribute_to_class(self, cls, name):
        _n, _p, args, kwargs = self._field.deconstruct()
        fields = []
        verbose_name = kwargs.pop("verbose_name", name)
        for index, language_code in enumerate(self.languages):
            field_kw = dict(kwargs, **self._specific.get(language_code, {}))
            field_kw.setdefault(
                "verbose_name",
                _verbose_name_maybe_language_code(verbose_name, language_code),
            )
            f = self._field.__class__(*args, **field_kw)
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
