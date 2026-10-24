import pytest
from django.db import models
from django.forms import CharField, modelform_factory
from django.utils.translation import override

from testapp.custom_fields import CustomPathTextField
from testapp.field_types_models import CustomFieldModel, RelatedModel
from translated_fields.fields import _copy_field


CUSTOM_CHOICES = [("a", "Option A"), ("b", "Option B"), ("c", "Option C")]


@pytest.mark.django_db
def test_custom_field_deconstruct_hardcodes_choices():
    """
    Test that migrations keep seeing the placeholder choices.

    That's the whole point of a field such as ChoicesCharField: changing the choices
    shouldn't produce a migration. Preserving the runtime choices (see below) must
    not start writing them into migrations.
    """
    for name in ("custom_choices_en", "custom_choices_de"):
        *_rest, kwargs = CustomFieldModel._meta.get_field(name).deconstruct()
        assert kwargs["choices"] == [("", "")]


@pytest.mark.django_db
def test_custom_field_choices_preserved():
    """
    Test that choices from custom fields with custom deconstruct methods are preserved.

    Fields such as feincms3's ``ChoicesCharField`` deliberately report different
    kwargs from ``deconstruct()`` than they were constructed with, so that changing
    the choices doesn't produce migrations. ``TranslatedField`` used to rebuild the
    per-language fields from ``deconstruct()``, baking those placeholder kwargs into
    the actual runtime fields. It copies the original field now.
    """
    custom_en = CustomFieldModel._meta.get_field("custom_choices_en")
    custom_de = CustomFieldModel._meta.get_field("custom_choices_de")

    # The runtime choices should be the ones we specified at field creation time,
    # not the placeholders from deconstruct()
    assert custom_en.choices == CUSTOM_CHOICES
    assert custom_de.choices == CUSTOM_CHOICES


@pytest.mark.django_db
def test_custom_field_form_generation():
    """
    Test that forms generated from custom fields have the correct choices.
    """
    form_class = modelform_factory(CustomFieldModel, fields="__all__")
    form = form_class()

    for name in ("custom_choices_en", "custom_choices_de"):
        # Skip the blank choice; whether Django adds one and how it labels it
        # differs between versions and isn't what we're testing here.
        choices = [choice for choice in form.fields[name].choices if choice[0]]
        assert choices == CUSTOM_CHOICES


@pytest.mark.django_db
def test_custom_field_display():
    """
    Test that get_FOO_<language>_display() uses the choices we defined.
    """
    model = CustomFieldModel.objects.create(
        custom_choices_en="a",
        custom_choices_de="b",
    )

    assert model.get_custom_choices_en_display() == "Option A"
    assert model.get_custom_choices_de_display() == "Option B"


@pytest.mark.xfail(reason="TranslatedField doesn't proxy get_FOO_display() yet")
@pytest.mark.django_db
def test_translated_field_display():
    """
    Test that get_FOO_display() follows the active language.

    Unrelated to the deconstruct() issue above: Django only adds the helper for the
    per-language fields it knows about, so only get_custom_choices_en_display() and
    get_custom_choices_de_display() exist. TranslatedField doesn't add a descriptor
    proxying the helper for the active language.
    """
    model = CustomFieldModel.objects.create(
        custom_choices_en="a",
        custom_choices_de="b",
    )

    with override("en"):
        assert model.get_custom_choices_display() == "Option A"

    with override("de"):
        assert model.get_custom_choices_display() == "Option B"


@pytest.mark.django_db
def test_custom_field_model_usage():
    """Test that the translated descriptor follows the active language."""
    model = CustomFieldModel.objects.create(
        custom_choices_en="a",
        custom_choices_de="b",
    )

    with override("en"):
        assert model.custom_choices == "a"

    with override("de"):
        assert model.custom_choices == "b"


@pytest.mark.parametrize("option", ["a", "b", "c"])
@pytest.mark.django_db
def test_custom_field_valid_options(option):
    """Test that valid choice options can be saved."""
    # This test should pass even if the choices aren't preserved correctly
    # as long as the field validation isn't overly strict
    model = CustomFieldModel()
    model.custom_choices_en = option
    model.custom_choices_de = option
    model.save()
    assert model.custom_choices_en == option
    assert model.custom_choices_de == option


@pytest.mark.django_db
def test_custom_path_field_type_preserved():
    """
    Test that custom field classes are preserved even when the path is overridden.

    This test passes unexpectedly. It seems TranslatedField actually does preserve
    the field class, which is good! The path from deconstruct() is used only for
    migrations, but the actual field instance in the model is of the correct type.

    This shows that TranslatedField doesn't use the path from deconstruct() when
    creating the field instances, but rather the original class.
    """
    # Get the field instances
    custom_en = CustomFieldModel._meta.get_field("custom_path_text_en")
    custom_de = CustomFieldModel._meta.get_field("custom_path_text_de")

    # Check that the field instances are of the custom field type
    assert isinstance(custom_en, CustomPathTextField)
    assert isinstance(custom_de, CustomPathTextField)

    # Get the deconstruct values
    _name_en, path_en, _args_en, _kwargs_en = custom_en.deconstruct()
    _name_de, path_de, _args_de, _kwargs_de = custom_de.deconstruct()

    # Confirm that deconstruct returns the base TextField path
    assert path_en == "django.db.models.TextField"
    assert path_de == "django.db.models.TextField"

    # Confirm we're using the right class despite the wrong path
    assert type(custom_en) is CustomPathTextField
    assert type(custom_de) is CustomPathTextField


@pytest.mark.django_db
def test_custom_path_field_form_generation():
    """
    Test form field generation for custom fields.

    This test shows that while the model field instance is correctly preserved as CustomPathTextField,
    when forms are generated, Django uses the field's formfield() method which returns a standard
    form field type. This is expected behavior and not a bug in TranslatedField.
    """
    form_class = modelform_factory(
        CustomFieldModel, fields=["custom_path_text_en", "custom_path_text_de"]
    )
    form = form_class()

    # Get the form fields
    field_en = form.fields["custom_path_text_en"]
    field_de = form.fields["custom_path_text_de"]

    # Get the model fields for comparison
    model_field_en = CustomFieldModel._meta.get_field("custom_path_text_en")
    model_field_de = CustomFieldModel._meta.get_field("custom_path_text_de")

    # Check that the model field is our custom type
    assert isinstance(model_field_en, CustomPathTextField)
    assert isinstance(model_field_de, CustomPathTextField)

    # Model field class is correctly preserved
    assert type(model_field_en).__name__ == "CustomPathTextField"
    assert type(model_field_de).__name__ == "CustomPathTextField"

    # Form field is based on standard Django form fields - these assertions should pass
    # Django maps TextField to Textarea widget by default

    assert isinstance(field_en, CharField)
    assert field_en.widget.__class__.__name__ == "Textarea"

    # This is Django's standard behavior - model field's formfield() method determines
    # what form field type is used, not TranslatedField's behavior
    assert field_en.__class__.__name__ == "CharField"
    assert field_de.__class__.__name__ == "CharField"


@pytest.mark.django_db
def test_custom_path_field_model_usage():
    """
    Test using the custom path text field with a model instance.

    This test verifies that the basic functionality of the model works properly
    with the CustomPathTextField when its path is overridden in deconstruct().
    """
    # Create a model instance with values for the custom path text field
    text_en = "English text content"
    text_de = "Deutscher Textinhalt"

    model = CustomFieldModel.objects.create(
        custom_choices_en="a",
        custom_choices_de="a",
        custom_path_text_en=text_en,
        custom_path_text_de=text_de,
    )

    # Check that the values are correctly stored
    assert model.custom_path_text_en == text_en
    assert model.custom_path_text_de == text_de

    # Check that the translated descriptor works
    with override("en"):
        assert model.custom_path_text == text_en

    with override("de"):
        assert model.custom_path_text == text_de


def test_configured_field_preserves_config():
    """
    Test that state which deconstruct() doesn't return survives.

    That's what django-prose-editor's ProseEditorField does with its configuration,
    see https://github.com/feincms/django-prose-editor/issues/41
    """
    for name in ("configured_text_en", "configured_text_de"):
        field = CustomFieldModel._meta.get_field(name)
        assert field.config == {"extensions": ["Bold", "Italic"]}
        assert "config" not in field.deconstruct()[3]


def test_configured_field_specific():
    """Test that specific overrides are applied to the copied field."""
    field_en = CustomFieldModel._meta.get_field("configured_text_en")
    field_de = CustomFieldModel._meta.get_field("configured_text_de")

    assert not field_en.blank
    assert field_de.blank
    assert str(field_en.verbose_name) == "configured text field"
    assert str(field_de.verbose_name) == "configured text field"


def test_copy_field_specific_relation():
    """Test that specific overrides of relationship fields point at the copy."""
    field = models.ForeignKey(RelatedModel, on_delete=models.CASCADE)
    copy = _copy_field(field, {"related_name": "+", "null": True})

    assert copy.null
    assert copy.remote_field.related_name == "+"
    assert copy.remote_field.field is copy
    assert not field.null
    assert field.remote_field.related_name is None
    assert field.remote_field.field is field
