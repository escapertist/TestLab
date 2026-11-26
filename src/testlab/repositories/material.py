"""Репозиторий учебных материалов."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from testlab.models.material import Material
from testlab.models.test import Test


class MaterialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, material: Material) -> Material:
        self.session.add(material)
        await self.session.flush()
        return material

    async def list_by_teacher(self, teacher_id: str, limit: int, offset: int) -> tuple[list[Material], int]:
        total = await self.session.scalar(
            select(func.count()).select_from(Material).where(Material.teacher_id == teacher_id)
        )
        result = await self.session.execute(
            select(Material)
            .where(Material.teacher_id == teacher_id)
            .order_by(Material.created_at.desc(), Material.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    async def get_by_id_and_teacher(self, material_id: str, teacher_id: str) -> Material | None:
        result = await self.session.execute(
            select(Material).where(Material.id == material_id, Material.teacher_id == teacher_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, material: Material) -> None:
        await self.session.delete(material)
        await self.session.flush()

    async def count_tests(self, material_id: str) -> int:
        total = await self.session.scalar(
            select(func.count()).select_from(Test).where(Test.material_id == material_id)
        )
        return int(total or 0)
