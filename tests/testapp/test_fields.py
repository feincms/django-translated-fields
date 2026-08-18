import re

import django
import pytest
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.forms import modelform_factory
from django.test import Client, SimpleTestCase
from django.utils.translation import override

from testapp.models import (
    CustomLanguagesModel,
    ListDisplayModel,
    ModelWithAnyFallback,
    ModelWithFallback,
    SpecificModel,
    TestModel,
)
from translated_fields import language_code_formfield_callback


if django.VERSION >= (5, 0):
    from pytest_django.asserts import assertInHTML
else:
    # pytest-django 4.14 unconditionally imports django.contrib.messages.test,
    # which only exists since Django 5.0. Use Django's own assertion instead.
    def assertInHTML(needle, haystack):  # noqa: N802
        SimpleTestCase("run").assertInHTML(needle, haystack)


@pytest.fixture
def user(db):
    return User.objects.create_superuser("admin", "admin@test.ch", "blabla")


@pytest.fixture
def login(db, user):
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_meta():
    assert [f.name for f in TestModel._meta.get_fields()] == [
        "id",
        "name_en",
        "name_de",
        "other_en",
        "other_de",
    ]

    creation_counters = [
        TestModel._meta.get_field(field).creation_counter
        for field in ["name_en", "name_de", "other_en", "other_de"]
    ]
    assert creation_counters == sorted(creation_counters)

    other_en = TestModel._meta.get_field("other_en")
    other_de = TestModel._meta.get_field("other_de")

    with override("en"):
        assert str(other_en.verbose_name) == "other field"
        assert str(other_de.verbose_name) == "other field"

    with override("de"):
        assert str(other_en.verbose_name) == "anderes Feld"
        assert str(other_de.verbose_name) == "anderes Feld"


@pytest.mark.django_db
def test_form_field_order():
    form = modelform_factory(TestModel, fields="__all__")()
    assert list(form.fields) == ["name_en", "name_de", "other_en", "other_de"]


@pytest.mark.django_db
def test_translated_fields():
    m = TestModel()
    with override(None):
        assert m.name == m.name_en
    with override("en"):
        assert m.name == m.name_en
    with override("de"):
        assert m.name == m.name_de
    with override("bla"), pytest.raises(AttributeError):
        _ = m.name


@pytest.mark.django_db
def test_translated_attributes():
    m = TestModel()
    with override(None):
        assert m.stuff == m.stuff_en
    with override("en"):
        assert m.stuff == m.stuff_en
    with override("de"):
        assert m.stuff == m.stuff_de
    with override("bla"), pytest.raises(AttributeError):
        _ = m.stuff


@pytest.mark.django_db
def test_translated_attributes_with_fallback_to_default():
    m = ModelWithFallback()
    with override(None):
        assert m.required == m.required_en
    with override("en"):
        assert m.required == m.required_en
    with override("de"):
        assert m.required == m.required_en


@pytest.mark.django_db
def test_translated_attributes_with_fallback_to_any():
    m = ModelWithAnyFallback()
    with override(None):
        assert m.optional == ""
    with override("en"):
        assert m.optional == ""
    with override("de"):
        assert m.optional == ""


@pytest.mark.django_db
def test_admin_changelist_redirect(login):
    client = login
    response = client.get("/admin/testapp/testmodel/?name=bla")
    assert response.status_code == 302


@pytest.mark.django_db
def test_admin(login):
    client = login
    response = client.get("/admin/testapp/testmodel/add/")
    assert "Name [de]" in response.content.decode()
    assert "Other field [en]" in response.content.decode()

    m = TestModel.objects.create(name_en="Test")

    response = client.get("/admin/testapp/testmodel/")
    assert "<span>Name</span>" in response.content.decode()
    assert "<span>Other field</span>" in response.content.decode()

    assert "Name [en]</a>" in response.content.decode()
    assert "Name [de]</a>" in response.content.decode()

    assert (
        f'<th class="field-name_en"><a href="/admin/testapp/testmodel/{m.id}/change/">Test</a></th>'
        in response.content.decode()
    )
    assert 'id="id_form-0-name_de"' in response.content.decode()

    response = client.get(f"/admin/testapp/testmodel/{m.id}/change/")
    expected_content = (
        '<label>Other field [en]:</label><div class="readonly"></div>'
        if django.VERSION < (5, 1)
        else '<label>Other field [en]:</label><div class="readonly">-</div>'
    )
    assertInHTML(expected_content, response.content.decode())

    response = client.post(
        "/admin/testapp/testmodel/add/", {"name_en": "Test", "name_de": "Test"}
    )
    assert response.status_code == 302
    assert response.url == "/admin/testapp/testmodel/"


@pytest.mark.django_db
def test_custom_languages():
    m = CustomLanguagesModel()

    assert m.name == "NO VALUE"
    m.name_it = "it"
    assert m.name == "it"
    m.name_fr = "fr"
    assert m.name == "fr"
    m.name_it = ""
    assert m.name == "fr"

    with pytest.raises(AttributeError):
        _ = m.name_en
    with pytest.raises(AttributeError):
        _ = m.name_de


@pytest.mark.django_db
def test_translated_field_instance():
    assert CustomLanguagesModel.name.languages == ["fr", "it"]
    m = CustomLanguagesModel()
    with pytest.raises(AttributeError):
        _ = m.name.languages

    assert m.__class__.name.languages == ["fr", "it"]
    assert CustomLanguagesModel.name.fields == ["name_fr", "name_it"]

    # Not str, lazy!
    assert CustomLanguagesModel.name.short_description is not str


@pytest.mark.django_db
def test_specific():
    m = SpecificModel()

    with pytest.raises(ValidationError) as exc:
        m.full_clean()

    assert list(exc.value.error_dict) == ["name_en"]

    m.name_en = "bla"
    m.full_clean()

    assert str(m._meta.get_field("name_en").verbose_name) == "name"
    assert str(m._meta.get_field("name_de").verbose_name) == "Der Name"


@pytest.mark.django_db
def test_setter():
    m = TestModel()
    with override("en"):
        m.name = "english"
    with override("de"):
        m.name = "german"
    assert m.name_en == "english"
    assert m.name_de == "german"

    with override("bla"):
        m.name = "blub"
    assert m.name_bla == "blub"


@pytest.mark.django_db
def test_list_display_columns(login):
    obj = ListDisplayModel.objects.create(
        name_en="english",
        name_de="german",
        choice_en="a",
        choice_de="b",
        is_active_de=False,
    )
    obj.file_en.save("test.txt", ContentFile(b"Hello"), save=True)

    client = login
    response = client.get("/admin/testapp/listdisplaymodel/")

    assert "<span>Stuff</span>" in response.content.decode()
    assert "Name [en]" in response.content.decode()
    assert "Name [de]" in response.content.decode()

    assert response.content.decode().count("Andrew") == 1
    assert response.content.decode().count("Betty") == 1

    assert (
        response.content.decode().count('img src="/static/admin/img/icon-yes.svg"') == 1
    )
    assert (
        response.content.decode().count('img src="/static/admin/img/icon-no.svg"') == 1
    )

    assert re.search(
        rb'<a href="/media/test(_\w+)?.txt">test(_\w+)?.txt</a>', response.content
    )


@pytest.mark.django_db
def test_fallback():
    assert not ModelWithFallback._meta.get_field("required_en").blank
    assert ModelWithFallback._meta.get_field("required_de").blank
    assert ModelWithFallback._meta.get_field("optional_en").blank
    assert ModelWithFallback._meta.get_field("optional_de").blank

    obj = ModelWithFallback(required_en="bla")
    with override("en"):
        assert obj.required == "bla"
    with override("de"):
        assert obj.required == "bla"
    with override(None):
        assert obj.required == "bla"


@pytest.mark.django_db
def test_fallback_to_any():
    obj = ModelWithAnyFallback(optional_de="chic")
    with override("en"):
        assert obj.optional == "chic"
    with override("de"):
        assert obj.optional == "chic"

    obj.optional_en = "chic-en"
    with override("en"):
        assert obj.optional == "chic-en"
    with override("de"):
        assert obj.optional == "chic"

    obj = ModelWithAnyFallback()
    with override("en"):
        assert obj.optional == ""
    with override("de"):
        assert obj.optional == ""


@pytest.mark.skipif(
    django.VERSION < (4, 2),
    reason="Specifying the callback wasn't officially supported before",
)
@pytest.mark.django_db
def test_formfield_callback():
    class Form(forms.ModelForm):
        class Meta:
            model = TestModel
            fields = "__all__"  # noqa: DJ007
            formfield_callback = language_code_formfield_callback

    with override("en"):
        result = str(Form())
        assert "Other field [en]:" in result
        assert "Other field [de]:" in result

    with override("de"):
        result = str(Form())
        assert "Anderes Feld [en]:" in result
        assert "Anderes Feld [de]:" in result
