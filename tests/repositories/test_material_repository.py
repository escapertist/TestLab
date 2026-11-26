"""Репозиторий материалов: пагинация, изоляция по преподавателю, удаление."""

from datetime import UTC, datetime, timedelta

from testlab.models.material import Material
from testlab.models.user import User
from testlab.repositories.uow import UnitOfWork


async def seed(session) -> tuple[UnitOfWork, User, User]:
    uow = UnitOfWork(session)
    alice = await uow.users.create(User(username="alice", password_hash="x", full_name="Алиса"))
    bob = await uow.users.create(User(username="bob", password_hash="x", full_name="Боб"))
    await uow.commit()
    return uow, alice, bob


async def add_materials(uow: UnitOfWork, teacher_id: str, count: int, start: datetime) -> None:
    for index in range(count):
        await uow.materials.create(
            Material(
                teacher_id=teacher_id,
                title=f"материал-{index}",
                file_path=f"/tmp/{index}.pdf",
                filename=f"lecture-{index}.pdf",
                created_at=start + timedelta(minutes=index),
            )
        )
    await uow.commit()


async def test_list_returns_newest_first(session):
    uow, alice, _ = await seed(session)
    await add_materials(uow, alice.id, 5, datetime.now(UTC))

    items, total = await uow.materials.list_by_teacher(alice.id, limit=10, offset=0)

    assert total == 5
    assert [item.title for item in items] == [f"материал-{index}" for index in reversed(range(5))]


async def test_list_paginates(session):
    uow, alice, _ = await seed(session)
    await add_materials(uow, alice.id, 5, datetime.now(UTC))

    items, total = await uow.materials.list_by_teacher(alice.id, limit=2, offset=1)

    assert total == 5
    assert [item.title for item in items] == ["материал-3", "материал-2"]


async def test_list_is_isolated_by_teacher(session):
    uow, alice, bob = await seed(session)
    await add_materials(uow, alice.id, 2, datetime.now(UTC))
    await add_materials(uow, bob.id, 3, datetime.now(UTC))

    alice_items, alice_total = await uow.materials.list_by_teacher(alice.id, limit=10, offset=0)
    bob_items, bob_total = await uow.materials.list_by_teacher(bob.id, limit=10, offset=0)

    assert alice_total == 2
    assert bob_total == 3
    assert all(item.teacher_id == alice.id for item in alice_items)
    assert all(item.teacher_id == bob.id for item in bob_items)


async def test_get_by_id_and_teacher(session):
    uow, alice, bob = await seed(session)
    await add_materials(uow, alice.id, 1, datetime.now(UTC))
    material = (await uow.materials.list_by_teacher(alice.id, limit=1, offset=0))[0][0]

    assert await uow.materials.get_by_id_and_teacher(material.id, alice.id) is not None
    assert await uow.materials.get_by_id_and_teacher(material.id, bob.id) is None


async def test_delete_removes_row(session):
    uow, alice, _ = await seed(session)
    await add_materials(uow, alice.id, 1, datetime.now(UTC))
    material = (await uow.materials.list_by_teacher(alice.id, limit=1, offset=0))[0][0]

    await uow.materials.delete(material)
    await uow.commit()

    items, total = await uow.materials.list_by_teacher(alice.id, limit=10, offset=0)
    assert total == 0
    assert items == []
