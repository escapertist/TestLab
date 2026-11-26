"""Правила разбора ответа модели."""

import json

import pytest

from testlab.errors import LLMResponseError
from testlab.llm.generation import parse_generated_test, strip_code_fence
from testlab.models.enums import QuestionType
from tests.helpers import build_llm_response


def make_payload(**overrides) -> str:
    data = json.loads(build_llm_response())
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


def test_parse_valid_response():
    test = parse_generated_test(build_llm_response(title="Тест"))

    assert test.title == "Тест"
    assert test.closed_count == 5
    assert test.open_count == 2
    assert test.questions[0].type is QuestionType.closed
    assert len(test.questions[0].options) == 2
    assert test.questions[0].options[0].is_correct is True
    assert test.questions[-1].rubric is not None
    assert test.questions[-1].rubric.criteria_text == "Критерии"


def test_strip_code_fence():
    raw = "```json\n" + build_llm_response() + "\n```"
    assert parse_generated_test(raw).closed_count == 5
    assert strip_code_fence("просто текст") == "просто текст"


def test_rejects_non_json():
    with pytest.raises(LLMResponseError, match="не JSON"):
        parse_generated_test("это не json")


def test_rejects_json_array():
    with pytest.raises(LLMResponseError, match="не в виде объекта"):
        parse_generated_test("[]")


def test_rejects_empty_questions():
    with pytest.raises(LLMResponseError, match="нет вопросов"):
        parse_generated_test(json.dumps({"questions": []}, ensure_ascii=False))


def test_rejects_wrong_composition():
    with pytest.raises(LLMResponseError, match="неверный состав"):
        parse_generated_test(build_llm_response(closed=4))
    with pytest.raises(LLMResponseError, match="неверный состав"):
        parse_generated_test(build_llm_response(open_=1))


def test_rejects_question_without_text():
    data = json.loads(build_llm_response())
    data["questions"][0]["text"] = "  "
    with pytest.raises(LLMResponseError, match="без текста"):
        parse_generated_test(json.dumps(data, ensure_ascii=False))


def test_rejects_unknown_type():
    data = json.loads(build_llm_response())
    data["questions"][0]["type"] = "essay"
    with pytest.raises(LLMResponseError, match="тип вопроса"):
        parse_generated_test(json.dumps(data, ensure_ascii=False))


def test_rejects_single_option():
    data = json.loads(build_llm_response())
    data["questions"][0]["options"] = [{"text": "Один", "is_correct": True}]
    with pytest.raises(LLMResponseError, match="меньше двух вариантов"):
        parse_generated_test(json.dumps(data, ensure_ascii=False))


def test_rejects_two_correct_options():
    data = json.loads(build_llm_response())
    data["questions"][0]["options"][1]["is_correct"] = True
    with pytest.raises(LLMResponseError, match="ровно один правильный"):
        parse_generated_test(json.dumps(data, ensure_ascii=False))


def test_rejects_non_boolean_is_correct():
    data = json.loads(build_llm_response())
    data["questions"][0]["options"][0]["is_correct"] = "false"
    with pytest.raises(LLMResponseError, match="is_correct"):
        parse_generated_test(json.dumps(data, ensure_ascii=False))


def test_rejects_options_as_object():
    data = json.loads(build_llm_response())
    data["questions"][0]["options"] = {"text": "Один"}
    with pytest.raises(LLMResponseError, match="нет списка вариантов"):
        parse_generated_test(json.dumps(data, ensure_ascii=False))


def test_rejects_missing_rubric():
    data = json.loads(build_llm_response())
    data["questions"][-1]["rubric"] = None
    with pytest.raises(LLMResponseError, match="нет рубрики"):
        parse_generated_test(json.dumps(data, ensure_ascii=False))


def test_rejects_incomplete_rubric():
    data = json.loads(build_llm_response())
    data["questions"][-1]["rubric"]["reference_answer"] = ""
    with pytest.raises(LLMResponseError, match="эталонного ответа"):
        parse_generated_test(json.dumps(data, ensure_ascii=False))


@pytest.mark.parametrize("points", ["пять", 0, 10, -1])
def test_rejects_invalid_points(points):
    data = json.loads(build_llm_response())
    data["questions"][0]["points"] = points
    with pytest.raises(LLMResponseError, match="Баллы"):
        parse_generated_test(json.dumps(data, ensure_ascii=False))


def test_default_points():
    data = json.loads(build_llm_response())
    del data["questions"][0]["points"]
    test = parse_generated_test(json.dumps(data, ensure_ascii=False))
    assert test.questions[0].points == 1.0
