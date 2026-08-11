import pytest
from django.forms import CharField, modelform_factory
from django.utils.translation import override

from testapp.custom_fields import CustomPathTextField
from testapp.field_types_models import CustomFieldModel


@pytest.mark.django_db
def test_custom_field_choices_actual_behavior():
    """
    Test to demonstrate the current behavior with custom field deconstruct.

    This test confirms what actually happens (not what we want to happen).
    """
    # Get the runtime field instances
    custom_en = CustomFieldModel._meta.get_field("custom_choices_en")
    custom_de = CustomFieldModel._meta.get_field("custom_choices_de")

    # The actual current behavior - choices are taken from deconstruct() [("", "")]
    # rather than the original [("a", "Option A"), ("b", "Option B"), ("c", "Option C")]
    actual_choices = [("", "")]

    # These assertions show what actually happens (would pass)
    assert custom_en.choices == actual_choices
    assert custom_de.choices == actual_choices

    # Get the deconstruct() values to confirm this behavior
    _name_en, _path_en, _args_en, kwargs_en = custom_en.deconstruct()
    _name_de, _path_de, _args_de, kwargs_de = custom_de.deconstruct()

    # Confirm that deconstruct() returns the same hardcoded choices
    assert kwargs_en["choices"] == actual_choices
    assert kwargs_de["choices"] == actual_choices


@pytest.mark.xfail(
    reason="TranslatedField doesn't handle custom deconstruct correctly yet"
)
@pytest.mark.django_db
def test_custom_field_choices_preserved():
    """
    Test that choices from custom fields with custom deconstruct methods are preserved.

    This is currently an expected failure because TranslatedField doesn't properly
    handle fields with custom deconstruct methods that modify field parameters.

    The issue is in translated_fields/fields.py line 82:
        _n, _p, args, kwargs = self._field.deconstruct()

    When using a field with a custom deconstruct() method that modifies parameters like 'choices',
    those modifications affect the translated fields that are created.

    A possible fix would be to store the original parameters before deconstruct() is called,
    or to copy the field's __dict__ attributes directly instead of using deconstruct().
    """
    # Get the runtime field instances
    custom_en = CustomFieldModel._meta.get_field("custom_choices_en")
    custom_de = CustomFieldModel._meta.get_field("custom_choices_de")

    # The runtime choices should be the ones we specified at field creation time,
    # not the hardcoded ones from deconstruct()
    expected_choices = [("a", "Option A"), ("b", "Option B"), ("c", "Option C")]

    # Check the field choices match what we defined, not what deconstruct() returns
    assert custom_en.choices == expected_choices
    assert custom_de.choices == expected_choices


@pytest.mark.xfail(
    reason="TranslatedField doesn't handle custom deconstruct correctly yet"
)
@pytest.mark.django_db
def test_custom_field_form_generation():
    """
    Test that forms generated from custom fields have the correct choices.

    This fails for the same reason as test_custom_field_choices_preserved:
    the choices from the original field definition are not preserved when
    deconstruct() replaces them with hardcoded values.
    """
    form_class = modelform_factory(CustomFieldModel, fields="__all__")
    form = form_class()

    # Form field choices should include the default empty choice plus our defined choices
    expected_form_choices = [
        ("", "---------"),
        ("a", "Option A"),
        ("b", "Option B"),
        ("c", "Option C"),
    ]

    # Check that form fields have the expected choices
    assert form.fields["custom_choices_en"].choices == expected_form_choices
    assert form.fields["custom_choices_de"].choices == expected_form_choices


@pytest.mark.xfail(
    reason="TranslatedField doesn't handle custom deconstruct correctly yet"
)
@pytest.mark.django_db
def test_custom_field_model_usage():
    """
    Test using the custom field with a model instance.

    This fails because the get_FOO_display() method relies on the correct choices
    being set on the field. Since the choices are replaced with [("", "")] during
    field creation, the display values don't match what we expect.
    """
    # Create a model instance with values for the custom field
    model = CustomFieldModel.objects.create(
        custom_choices_en="a",
        custom_choices_de="b",
    )

    # Check that the values are correctly stored and the choices behavior works
    with override("en"):
        assert model.custom_choices == "a"
        assert model.get_custom_choices_display() == "Option A"

    with override("de"):
        assert model.custom_choices == "b"
        assert model.get_custom_choices_display() == "Option B"


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
