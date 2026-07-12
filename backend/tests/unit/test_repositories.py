import abc
from uuid import UUID

from app.domain.entities.client import Client
from app.domain.entities.invoice import Invoice
from app.domain.entities.payment import Payment
from app.ports.repositories import (
    IClientRepository,
    IInvoiceRepository,
    IPaymentRepository,
    IScenarioRepository,
)


def test_iclient_repository_is_abstract_base_class():
    assert issubclass(IClientRepository, abc.ABC)
    # Cannot instantiate abstract class
    try:
        IClientRepository()
        assert False, "Should not be able to instantiate abstract class"
    except TypeError:
        pass


def test_iclient_repository_has_expected_abstract_methods():
    assert set(IClientRepository.__abstractmethods__) == {
        "add",
        "add_many",
        "get_by_scenario_id",
        "get_by_id",
    }


def test_iinvoice_repository_is_abstract_base_class():
    assert issubclass(IInvoiceRepository, abc.ABC)
    try:
        IInvoiceRepository()
        assert False, "Should not be able to instantiate abstract class"
    except TypeError:
        pass


def test_iinvoice_repository_has_expected_abstract_methods():
    assert set(IInvoiceRepository.__abstractmethods__) == {
        "add",
        "add_many",
        "get_by_scenario_id",
        "get_by_id",
    }


def test_ipayment_repository_is_abstract_base_class():
    assert issubclass(IPaymentRepository, abc.ABC)
    try:
        IPaymentRepository()
        assert False, "Should not be able to instantiate abstract class"
    except TypeError:
        pass


def test_ipayment_repository_has_expected_abstract_methods():
    assert set(IPaymentRepository.__abstractmethods__) == {
        "add",
        "add_many",
        "get_by_scenario_id",
        "get_by_id",
    }


# Ensure existing IScenarioRepository still works (no regression)
def test_isce_nario_repository_unchanged():
    assert issubclass(IScenarioRepository, abc.ABC)
    assert set(IScenarioRepository.__abstractmethods__) == {
        "list_all",
        "get_by_id",
        "add",
        "set_active",
        "get_active",
        "get_client_count",
        "create_from_csv",
    }