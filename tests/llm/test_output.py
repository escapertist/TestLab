"""Схемы ответа модели совместимы с function calling GigaChat."""

import pytest
from langchain_gigachat.utils.function_calling import convert_to_gigachat_tool

from testlab.llm.output import Test, Verdict


@pytest.mark.parametrize(("schema", "name"), [(Test, "generate_test"), (Verdict, "check_answer")])
def test_schema_is_supported_by_gigachat(schema, name):
    function = convert_to_gigachat_tool(schema)["function"]

    assert function["name"] == name
    assert "anyOf" not in str(function)
    assert "oneOf" not in str(function)
