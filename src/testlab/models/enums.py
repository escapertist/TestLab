"""Перечисления, которые хранятся в колонках БД."""

from enum import StrEnum


class UserRole(StrEnum):
    teacher = "teacher"
    student = "student"


class TestStatus(StrEnum):
    draft = "draft"
    published = "published"
    archived = "archived"


class QuestionType(StrEnum):
    open = "open"
    closed = "closed"
