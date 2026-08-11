from django.utils.functional import keep_lazy_text
from django.utils.text import capfirst

from translated_fields.fields import TranslatedField, to_attribute


__all__ = [
    "TranslatedFieldWithFallback",
    "fallback_to_any",
    "fallback_to_default",
    "language_code_formfield_callback",
]


def fallback_to_default(name, field):
    def getter(self):
        return getattr(self, to_attribute(name), None) or getattr(
            self, to_attribute(name, field.languages[0])
        )

    return getter


def fallback_to_any(name, field):
    def getter(self):
        current = getattr(self, to_attribute(name), None)
        if current:
            return current
        for language in field.languages:
            value = getattr(self, to_attribute(name, language))
            if value:
                return value
        return ""

    return getter


class TranslatedFieldWithFallback(TranslatedField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrgetter", fallback_to_default)
        super().__init__(*args, **kwargs)
        for language in self.languages[1:]:
            # Only the primary language is required
            self._specific.setdefault(language, {})["blank"] = True


def language_code_formfield_callback(db_field, **kwargs):
    language_code = getattr(db_field, "_translated_field_language_code", "")
    if language_code:
        kwargs["label"] = keep_lazy_text(lambda s: f"{s} [{language_code}]")(
            capfirst(db_field.verbose_name)
        )
    return db_field.formfield(**kwargs)
