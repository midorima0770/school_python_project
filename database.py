from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import declarative_base
from sqlalchemy import select
from config import load_config
from typing import AsyncGenerator

from models import Base,SchoolORM

conf = load_config()

engine = create_async_engine(
    conf.database_url,
    echo=False,  # можно убрать в проде
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

from contextlib import asynccontextmanager

@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

async def create_all_tables(async_engine: AsyncEngine):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_all_tables(async_engine: AsyncEngine):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def create_all_schools():
    async with get_async_db() as session:  
        try:
            created_count = 0
            for school_number in range(1, 35):
                # Проверяем, существует ли уже школа с таким номером
                result = await session.execute(
                    select(SchoolORM).where(SchoolORM.name == str(school_number))
                )
                existing_school = result.scalar_one_or_none()
                
                if not existing_school:
                    school = SchoolORM(name=str(school_number))
                    session.add(school)
                    created_count += 1

            await session.commit()

        except Exception as e:
            ...