from abc import ABC

import pytest

from app.ports.llm_port import ILLMPort


def test_illmport_is_abstract_base_class():
    assert issubclass(ILLMPort, ABC)


def test_illmport_cannot_be_instantiated():
    with pytest.raises(TypeError):
        ILLMPort()


def test_illmport_has_abstract_methods():
    assert hasattr(ILLMPort, 'generate')
    assert hasattr(ILLMPort, 'query')
    assert ILLMPort.generate.__isabstractmethod__ is True
    assert ILLMPort.query.__isabstractmethod__ is True