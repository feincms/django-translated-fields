from functools import partial

from django.db import models
from django.utils.translation import gettext_lazy as _

from testapp.custom_fields import (
    ChoicesCharField,
    ConfiguredTextField,
    CustomPathTextField,
)
from translated_fields import TranslatedField


BoldTextField = partial(ConfiguredTextField, config={"extensions": ["Bold"]})


class RelatedModel(models.Model):
    name = models.CharField(_("name"), max_length=100)

    def __str__(self):
        return self.name


class FieldTypesModel(models.Model):
    """Model to test various field types with TranslatedField."""

    # CharField with max_length and choices
    char_field = TranslatedField(
        models.CharField(
            _("char field"),
            max_length=50,
            choices=[("a", "Option A"), ("b", "Option B"), ("c", "Option C")],
        )
    )

    # TextField with max_length and help_text
    text_field = TranslatedField(
        models.TextField(
            _("text field"),
            max_length=500,
            help_text=_("This is a text field"),
        )
    )

    # IntegerField with min/max values
    int_field = TranslatedField(
        models.IntegerField(
            _("integer field"),
            default=0,
            help_text=_("Enter a number"),
        )
    )

    # BooleanField with default
    bool_field = TranslatedField(
        models.BooleanField(
            _("boolean field"),
            default=True,
        )
    )

    # ForeignKey to test relationship fields
    foreign_key = TranslatedField(
        models.ForeignKey(
            RelatedModel,
            on_delete=models.CASCADE,
            verbose_name=_("related model"),
            related_name="+",
            null=True,
            blank=True,
        )
    )

    # URLField with validators
    url_field = TranslatedField(
        models.URLField(
            _("URL field"),
            max_length=200,
        )
    )

    # EmailField
    email_field = TranslatedField(
        models.EmailField(
            _("email field"),
            max_length=100,
        )
    )

    # DecimalField with decimal_places and max_digits
    decimal_field = TranslatedField(
        models.DecimalField(
            _("decimal field"),
            max_digits=10,
            decimal_places=2,
            default=0.0,
        )
    )

    # DateField with auto_now_add
    date_field = TranslatedField(
        models.DateField(
            _("date field"),
            auto_now_add=True,
        )
    )

    def __str__(self):
        return self.char_field


class CustomFieldModel(models.Model):
    """Model with a custom field that has a custom deconstruct() method."""

    # Custom field with hardcoded choices in deconstruct
    custom_choices = TranslatedField(
        ChoicesCharField(
            _("custom choices field"),
            max_length=10,
            choices=[("a", "Option A"), ("b", "Option B"), ("c", "Option C")],
        )
    )

    # Custom field that changes its path in deconstruct
    custom_path_text = TranslatedField(
        CustomPathTextField(
            _("custom path text field"),
            help_text=_("This is a text field with custom path in deconstruct()"),
        )
    )

    # Custom field with configuration which isn't returned by deconstruct()
    configured_text = TranslatedField(
        ConfiguredTextField(
            _("configured text field"),
            config={"extensions": ["Bold", "Italic"]},
        ),
        {"de": {"blank": True}},
    )

    # Custom field with configuration passed via functools.partial()
    partial_text = TranslatedField(
        BoldTextField(_("partial text field")),
        {"de": {"blank": True}},
    )

    def __str__(self):
        return self.custom_choices
