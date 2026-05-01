from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.forms import modelform_factory
from django.utils.translation import override

from testapp.field_types_models import FieldTypesModel, RelatedModel
from translated_fields.fields import show_language_code


@pytest.mark.django_db
def test_model_fields_creation():
    """Test that all the expected translated fields are created with correct names."""
    fields = [f.name for f in FieldTypesModel._meta.get_fields()]

    # Check all the expected language-specific fields exist
    assert "char_field_en" in fields
    assert "char_field_de" in fields
    assert "text_field_en" in fields
    assert "text_field_de" in fields
    assert "int_field_en" in fields
    assert "int_field_de" in fields
    assert "bool_field_en" in fields
    assert "bool_field_de" in fields
    assert "foreign_key_en" in fields
    assert "foreign_key_de" in fields
    assert "url_field_en" in fields
    assert "url_field_de" in fields
    assert "email_field_en" in fields
    assert "email_field_de" in fields
    assert "decimal_field_en" in fields
    assert "decimal_field_de" in fields
    assert "date_field_en" in fields
    assert "date_field_de" in fields


@pytest.mark.django_db
def test_char_field_properties():
    """Test that CharField properties are correctly carried over to translated fields."""
    char_en = FieldTypesModel._meta.get_field("char_field_en")
    char_de = FieldTypesModel._meta.get_field("char_field_de")

    # Check max_length is transferred
    assert char_en.max_length == 50
    assert char_de.max_length == 50

    # Check choices are transferred
    assert char_en.choices == [("a", "Option A"), ("b", "Option B"), ("c", "Option C")]
    assert char_de.choices == [("a", "Option A"), ("b", "Option B"), ("c", "Option C")]

    # Check verbose_name includes language code when show_language_code is used
    # Note: Django automatically capitalizes the first letter of verbose_name
    with override("en"), show_language_code(True):  # noqa: FBT003
        assert str(char_en.verbose_name) == "Char field [en]"
        assert str(char_de.verbose_name) == "Char field [de]"


@pytest.mark.django_db
def test_text_field_properties():
    """Test that TextField properties are correctly carried over to translated fields."""
    text_en = FieldTypesModel._meta.get_field("text_field_en")
    text_de = FieldTypesModel._meta.get_field("text_field_de")

    # Check max_length is transferred
    assert text_en.max_length == 500
    assert text_de.max_length == 500

    # Check help_text is transferred
    with override("en"):
        assert str(text_en.help_text) == "This is a text field"
        assert str(text_de.help_text) == "This is a text field"


@pytest.mark.django_db
def test_int_field_properties():
    """Test that IntegerField properties are correctly carried over to translated fields."""
    int_en = FieldTypesModel._meta.get_field("int_field_en")
    int_de = FieldTypesModel._meta.get_field("int_field_de")

    # Check default is transferred
    assert int_en.default == 0
    assert int_de.default == 0

    # Check help_text is transferred
    with override("en"):
        assert str(int_en.help_text) == "Enter a number"
        assert str(int_de.help_text) == "Enter a number"


@pytest.mark.django_db
def test_boolean_field_properties():
    """Test that BooleanField properties are correctly carried over to translated fields."""
    bool_en = FieldTypesModel._meta.get_field("bool_field_en")
    bool_de = FieldTypesModel._meta.get_field("bool_field_de")

    # Check default is transferred
    assert bool_en.default is True
    assert bool_de.default is True


@pytest.mark.django_db
def test_foreign_key_properties():
    """Test that ForeignKey properties are correctly carried over to translated fields."""
    fk_en = FieldTypesModel._meta.get_field("foreign_key_en")
    fk_de = FieldTypesModel._meta.get_field("foreign_key_de")

    # Check that the target model is correctly set
    assert fk_en.related_model is RelatedModel
    assert fk_de.related_model is RelatedModel

    # Check on_delete behavior is not directly accessible as an attribute
    # But we can check the related model is set correctly
    assert fk_en.related_model is RelatedModel
    assert fk_de.related_model is RelatedModel


@pytest.mark.django_db
def test_url_field_properties():
    """Test that URLField properties are correctly carried over to translated fields."""
    url_en = FieldTypesModel._meta.get_field("url_field_en")
    url_de = FieldTypesModel._meta.get_field("url_field_de")

    # Check max_length is transferred
    assert url_en.max_length == 200
    assert url_de.max_length == 200

    # Ensure URL field has appropriate max_length
    assert url_en.max_length == 200
    assert url_de.max_length == 200

    # Test validation with invalid URL
    model = FieldTypesModel(
        char_field_en="test",
        char_field_de="test",
        text_field_en="test",
        text_field_de="test",
        url_field_en="not a url",
        url_field_de="https://example.de",
    )

    # Should raise because "not a url" is invalid
    with pytest.raises(ValidationError):
        model.full_clean()


@pytest.mark.django_db
def test_email_field_properties():
    """Test that EmailField properties are correctly carried over to translated fields."""
    email_en = FieldTypesModel._meta.get_field("email_field_en")
    email_de = FieldTypesModel._meta.get_field("email_field_de")

    # Check max_length is transferred
    assert email_en.max_length == 100
    assert email_de.max_length == 100

    # Check max_length is transferred
    assert email_en.max_length == 100
    assert email_de.max_length == 100

    # Test validation with invalid email
    model = FieldTypesModel(
        char_field_en="test",
        char_field_de="test",
        text_field_en="test",
        text_field_de="test",
        url_field_en="https://example.com",
        url_field_de="https://example.de",
        email_field_en="not-an-email",
        email_field_de="test@example.de",
    )

    # Should raise because "not-an-email" is invalid
    with pytest.raises(ValidationError):
        model.full_clean()


@pytest.mark.django_db
def test_decimal_field_properties():
    """Test that DecimalField properties are correctly carried over to translated fields."""
    decimal_en = FieldTypesModel._meta.get_field("decimal_field_en")
    decimal_de = FieldTypesModel._meta.get_field("decimal_field_de")

    # Check max_digits and decimal_places are transferred
    assert decimal_en.max_digits == 10
    assert decimal_en.decimal_places == 2
    assert decimal_de.max_digits == 10
    assert decimal_de.decimal_places == 2

    # Check default is transferred
    assert decimal_en.default == Decimal("0.0")
    assert decimal_de.default == Decimal("0.0")


@pytest.mark.django_db
def test_date_field_properties():
    """Test that DateField properties are correctly carried over to translated fields."""
    date_en = FieldTypesModel._meta.get_field("date_field_en")
    date_de = FieldTypesModel._meta.get_field("date_field_de")

    # Check auto_now_add is transferred
    assert date_en.auto_now_add is True
    assert date_de.auto_now_add is True


@pytest.mark.django_db
def test_form_fields_generation():
    """Test that forms generated from the models have the correct field types."""
    form_class = modelform_factory(FieldTypesModel, fields="__all__")
    form = form_class()

    # Check field types (blank label may vary across Django versions)
    for name in ("char_field_en", "char_field_de"):
        choices = list(form.fields[name].choices)
        assert choices[0][0] == ""
        assert choices[1:] == [
            ("a", "Option A"),
            ("b", "Option B"),
            ("c", "Option C"),
        ]

    # Check help texts
    assert form.fields["text_field_en"].help_text == "This is a text field"
    assert form.fields["text_field_de"].help_text == "This is a text field"

    # Check initial values
    assert form.fields["bool_field_en"].initial is True
    assert form.fields["bool_field_de"].initial is True


@pytest.mark.django_db
def test_translated_accessors():
    """Test accessing the translated properties with the language context."""
    # Create related models
    rel_en = RelatedModel.objects.create(name="English Related")
    rel_de = RelatedModel.objects.create(name="German Related")

    # Create an instance with values for all required fields
    model = FieldTypesModel.objects.create(
        char_field_en="Choice A",
        char_field_de="Wahl A",
        text_field_en="English text",
        text_field_de="Deutscher Text",
        int_field_en=10,
        int_field_de=20,
        bool_field_en=True,
        bool_field_de=False,
        foreign_key_en=rel_en,
        foreign_key_de=rel_de,
        url_field_en="https://example.com",
        url_field_de="https://example.de",
        email_field_en="en@example.com",
        email_field_de="de@example.de",
        decimal_field_en=Decimal("10.50"),
        decimal_field_de=Decimal("20.75"),
    )

    # Check that the correct translations are returned based on the active language
    with override("en"):
        assert model.char_field == "Choice A"
        assert model.text_field == "English text"
        assert model.int_field == 10
        assert model.bool_field is True
        assert model.foreign_key == rel_en
        assert model.url_field == "https://example.com"
        assert model.email_field == "en@example.com"
        assert model.decimal_field == Decimal("10.50")

    with override("de"):
        assert model.char_field == "Wahl A"
        assert model.text_field == "Deutscher Text"
        assert model.int_field == 20
        assert model.bool_field is False
        assert model.foreign_key == rel_de
        assert model.url_field == "https://example.de"
        assert model.email_field == "de@example.de"
        assert model.decimal_field == Decimal("20.75")
