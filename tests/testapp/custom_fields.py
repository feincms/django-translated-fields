from django.db import models


class ChoicesCharField(models.CharField):
    """
    CharField with hardcoded default choices in deconstruct() method.

    Similar to feincms3.utils.ChoicesCharField, this field sets a default set of
    choices in the deconstruct method to avoid migrations when choices change.
    """

    def __init__(self, *args, **kwargs):
        # Non-empty choices for get_*_display
        kwargs.setdefault("choices", [("", "")])
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Always return hardcoded choices in deconstruct - this is what we want to test
        # TranslatedField should preserve the runtime choices, not the ones from deconstruct
        kwargs["choices"] = [("", "")]
        return name, path, args, kwargs


class CustomPathTextField(models.TextField):
    """
    TextField that overrides the path in deconstruct() method.

    This is similar to django-prose-editor's implementation where the field
    returns a different path in deconstruct() to ensure it's reconstructed as
    a standard TextField rather than the custom subclass.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, _path, args, kwargs = super().deconstruct()
        # Override the path to always use the base TextField class
        # This simulates a field with custom behavior that reports a base field type in migrations
        # TranslatedField preserves the original field class, but uses the path for migrations
        return name, "django.db.models.TextField", args, kwargs


class ConfiguredTextField(models.TextField):
    """
    TextField with configuration which isn't returned by deconstruct().

    Similar to django-prose-editor's ProseEditorField, the configuration only
    affects the runtime behavior and shouldn't produce migrations when it changes.
    """

    def __init__(self, *args, **kwargs):
        self.config = kwargs.pop("config", {})
        super().__init__(*args, **kwargs)
