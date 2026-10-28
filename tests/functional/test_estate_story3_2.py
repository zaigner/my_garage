"""Functional tests for Story 3.2: estate scope and executor replacement."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import Client, override_settings

from my_garage.api.services import activate_estate_plan, revoke_executor_access
from my_garage.models import (
    Beneficiary,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateAccessLog,
    EstateAccessToken,
    EstateChangeLog,
    EstateExecutor,
)

User = get_user_model()
pytestmark = pytest.mark.django_db

PORTAL = "/estate/portal/"
DASH = "/estate/portal/dashboard/"
EXECUTOR_URL = "/estate/executor/"
ASSIGN_URL = "/estate/assign/"
PROFILE_URL = "/accounts/profile/"
REVOKED_MSG = (
    "Executor updated. Their previous access code has been revoked — issue a new "
    "code from Activate Estate Access."
)
HINT = 'id="executor-name-hint"'
SAVED_MSG = "Executor designated successfully."


def detail(pk):
    return f"/estate/portal/items/{pk}/"


@pytest.fixture
def owner():
    return User.objects.create_user(username="estate_3_2", password="pass")


@pytest.fixture
def owner_client(owner):
    client = Client()
    client.force_login(owner)
    return client


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


@pytest.fixture
def wines(owner):
    return CollectionType.objects.create(owner=owner, name="Wines")


def _item(owner, ct, name, value=None):
    return DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=name, current_market_value=value
    )


def _soft_delete(ct):
    ct.is_active = False
    ct.save()


def _executor_client(owner):
    client = Client()
    assert client.post(PORTAL, {"code": activate_estate_plan(owner)}).status_code == 302
    return client


def _summary(body):
    start = body.index('id="summary-heading"')
    return body[start : body.index("</section>", start)]


class TestPortalScope:
    def test_soft_deleted_before_activation_hidden(self, owner, cars, wines):
        _item(owner, cars, "Kept Porsche", Decimal("100000"))
        hidden = _item(owner, wines, "Hidden Petrus", Decimal("9000"))
        _soft_delete(wines)
        client = _executor_client(owner)

        body = client.get(DASH).content.decode()
        assert "Kept Porsche" in body
        assert "Hidden Petrus" not in body
        assert detail(hidden.pk) not in body
        summary = _summary(body)
        assert "$100,000" in summary
        assert "$109,000" not in summary
        assert "removed after activation" not in summary

    def test_soft_deleted_after_activation_is_removed_row(self, owner, cars, wines):
        _item(owner, cars, "Kept Porsche", Decimal("100000"))
        hidden = _item(owner, wines, "Hidden Petrus", Decimal("9000"))
        client = _executor_client(owner)
        _soft_delete(wines)

        body = client.get(DASH).content.decode()
        start = body.index('data-testid="removed-row"')
        row = body[start : body.index("</tr>", start)]
        assert "Hidden Petrus" in row and "Removed after activation" in row
        assert "<a " not in row
        assert detail(hidden.pk) not in body
        assert "$109,000" in _summary(body)  # value at activation unchanged

    def test_detail_and_photo_404(self, owner, cars, wines, tmp_path):
        with override_settings(MEDIA_ROOT=str(tmp_path)):
            hidden = _item(owner, wines, "Hidden Petrus", Decimal("9000"))
            hidden.photo.save("w.png", ContentFile(b"PNGBYTES"), save=True)
            client = _executor_client(owner)
            assert client.get(detail(hidden.pk) + "photo/").status_code == 200
            _soft_delete(wines)
            assert client.get(detail(hidden.pk)).status_code == 404
            assert client.get(detail(hidden.pk) + "photo/").status_code == 404
            assert not EstateAccessLog.objects.filter(event="ITEM_VIEW").exists()


class TestOwnerScope:
    def test_assign_overview_lists_only_active(self, owner_client, owner, cars, wines):
        _item(owner, cars, "Kept Porsche")
        _item(owner, wines, "Hidden Petrus")
        _soft_delete(wines)
        body = owner_client.get(ASSIGN_URL).content.decode()
        assert "Kept Porsche" in body
        assert "Hidden Petrus" not in body

    def test_profile_card_totals(self, owner_client, owner, cars, wines):
        _item(owner, cars, "Kept Porsche")
        _item(owner, wines, "Hidden Petrus")
        _soft_delete(wines)
        ctx = owner_client.get(PROFILE_URL).context
        assert ctx["estate_items_total"] == 1
        assert ctx["estate_items_assigned"] == 0
        assert ctx["estate_completeness_pct"] == 0

    def test_estate_dashboard_lists_only_active(self, owner_client, owner, cars, wines):
        _item(owner, cars, "Kept Porsche")
        _item(owner, wines, "Hidden Petrus")
        _soft_delete(wines)
        r = owner_client.get("/estate/")
        assert r.context["items_total"] == 1
        assert "Hidden Petrus" not in r.content.decode()


class TestAssignInactiveCollection:
    def test_assign_and_remove_404(self, owner_client, owner, wines):
        item = _item(owner, wines, "Hidden Petrus")
        ben = Beneficiary.objects.create(owner=owner, name="Ann")
        _soft_delete(wines)
        base = f"/estate/assign/{wines.slug}/items/{item.pk}/"
        payload = {
            "beneficiary": ben.pk,
            "conditional_note": "",
            "is_charitable": False,
            "charitable_org": "",
        }
        assert owner_client.post(base, payload).status_code == 404
        assert not BeneficiaryAssignment.objects.exists()

        BeneficiaryAssignment.objects.create(item=item, beneficiary=ben)
        assert owner_client.post(base + "remove/").status_code == 404
        assert BeneficiaryAssignment.objects.filter(item=item).exists()
        assert not EstateChangeLog.objects.exists()


class TestExecutorReplacement:
    @pytest.fixture
    def executor(self, owner):
        return EstateExecutor.objects.create(
            owner=owner, name="Jo Smith", contact_info="jo@x.com"
        )

    def _post(self, owner_client, name, contact="jo@x.com"):
        return owner_client.post(
            EXECUTOR_URL, {"name": name, "contact_info": contact}, follow=True
        )

    def test_name_change_revokes_code(self, owner_client, owner, executor, cars):
        _item(owner, cars, "Kept Porsche")
        portal = _executor_client(owner)
        assert portal.get(DASH).status_code == 200

        body = self._post(owner_client, "Sam Lee").content.decode()
        assert REVOKED_MSG in body
        assert EstateExecutor.objects.get(owner=owner).name == "Sam Lee"
        assert not EstateAccessToken.objects.get(owner=owner).is_active
        assert EstateAccessLog.objects.filter(event="TOKEN_REVOKED").count() == 1
        # The old code no longer opens the portal on its next request
        r = portal.get(DASH)
        assert r.status_code == 302 and r.url == PORTAL

    def test_case_and_spacing_keep_code(self, owner_client, owner, executor):
        portal = _executor_client(owner)
        body = self._post(owner_client, "jo  smith").content.decode()
        assert SAVED_MSG in body and REVOKED_MSG not in body
        assert EstateAccessToken.objects.get(owner=owner).is_active
        assert portal.get(DASH).status_code == 200

    def test_contact_only_edit_keeps_code(self, owner_client, owner, executor):
        _executor_client(owner)
        body = self._post(owner_client, "Jo Smith", "new@x.com").content.decode()
        assert SAVED_MSG in body
        assert EstateAccessToken.objects.get(owner=owner).is_active
        assert not EstateAccessLog.objects.filter(event="TOKEN_REVOKED").exists()

    def test_name_change_with_revoked_code(self, owner_client, owner, executor):
        activate_estate_plan(owner)
        revoke_executor_access(owner)
        body = self._post(owner_client, "Sam Lee").content.decode()
        assert SAVED_MSG in body and REVOKED_MSG not in body
        assert EstateAccessLog.objects.filter(event="TOKEN_REVOKED").count() == 1

    def test_name_change_with_no_token(self, owner_client, owner, executor):
        body = self._post(owner_client, "Sam Lee").content.decode()
        assert SAVED_MSG in body
        assert EstateExecutor.objects.get(owner=owner).name == "Sam Lee"

    def test_first_designation(self, owner_client, owner):
        body = self._post(owner_client, "Sam Lee").content.decode()
        assert SAVED_MSG in body
        assert not EstateAccessLog.objects.filter(event="TOKEN_REVOKED").exists()


class TestConfirmPrompt:
    def _update_form(self, body):
        start = body.index(f'action="{EXECUTOR_URL}"')
        return body[start : body.index(">", start)]

    def test_rendered_with_active_code(self, owner_client, owner):
        EstateExecutor.objects.create(owner=owner, name="Jo Smith")
        activate_estate_plan(owner)
        tag = self._update_form(owner_client.get(EXECUTOR_URL).content.decode())
        assert 'data-current-name="Jo Smith"' in tag
        assert "onsubmit=" in tag
        assert "revokes the current access code" in tag

    def test_hint_with_active_code(self, owner_client, owner):
        EstateExecutor.objects.create(owner=owner, name="Jo Smith")
        activate_estate_plan(owner)
        body = owner_client.get(EXECUTOR_URL).content.decode()
        start = body.index(HINT)
        hint = body[start : body.index("</p>", start)]
        assert "Saving a different name revokes the current access code." in hint
        start = body.index('name="name"')
        name_input = body[body.rindex("<input", 0, start) : body.index(">", start)]
        assert 'aria-describedby="executor-name-hint"' in name_input

    def test_absent_without_active_code(self, owner_client, owner):
        EstateExecutor.objects.create(owner=owner, name="Jo Smith")
        body = owner_client.get(EXECUTOR_URL).content.decode()
        tag = self._update_form(body)
        assert "data-current-name" not in tag and "onsubmit" not in tag
        assert HINT not in body
        start = body.index('name="name"')
        name_input = body[body.rindex("<input", 0, start) : body.index(">", start)]
        assert "aria-describedby" not in name_input

    def test_absent_with_revoked_code(self, owner_client, owner):
        EstateExecutor.objects.create(owner=owner, name="Jo Smith")
        activate_estate_plan(owner)
        revoke_executor_access(owner)
        tag = self._update_form(owner_client.get(EXECUTOR_URL).content.decode())
        assert "data-current-name" not in tag

    def test_absent_on_first_designation(self, owner_client):
        body = owner_client.get(EXECUTOR_URL).content.decode()
        assert "data-current-name" not in body

    def test_current_name_escaped(self, owner_client, owner):
        EstateExecutor.objects.create(owner=owner, name='Jo "JJ" <Smith>')
        activate_estate_plan(owner)
        tag = self._update_form(owner_client.get(EXECUTOR_URL).content.decode())
        assert 'data-current-name="Jo &quot;JJ&quot; &lt;Smith&gt;"' in tag


class TestPortalLabels:
    def test_snapshot_labels(self, owner, cars):
        item = DynamicCollectionItem.objects.create(
            owner=owner,
            collection_type=cars,
            name="Porsche",
            current_market_value=Decimal("100"),
            purchase_price=Decimal("80"),
        )
        body = _executor_client(owner).get(detail(item.pk)).content.decode()
        start = body.index("<dl", body.index('id="snapshot-heading"'))
        snapshot = body[start : body.index("</dl>", start)]
        assert ">Purchase price</dt>" in snapshot
        assert ">Value minus purchase price</dt>" in snapshot
        assert "Cost basis" not in snapshot
        assert "Equity" not in snapshot
