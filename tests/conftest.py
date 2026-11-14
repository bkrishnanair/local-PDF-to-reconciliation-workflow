from pathlib import Path

import pytest

from reconciliation.models import Invoice
from reconciliation.reconcile import load_purchase_orders
from scripts.generate_demo import generate, records


@pytest.fixture(scope="session")
def demo_data(tmp_path_factory):
    path = tmp_path_factory.mktemp("synthetic")
    generate(path)
    return path


@pytest.fixture
def invoice():
    return Invoice.model_validate(records()["invoice_a_digital.pdf"])


@pytest.fixture
def orders(demo_data):
    return load_purchase_orders(demo_data / "purchase_orders.csv")
