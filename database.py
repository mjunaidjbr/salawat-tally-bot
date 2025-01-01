from sqlalchemy import String, Integer, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.sql import select
from sqlalchemy.sql import func
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Base(DeclarativeBase):
    pass

class DhikarType(Base):
    __tablename__ = "dhikar_type"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    dhikar_topic_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    dhikar_title: Mapped[str] = mapped_column(String(225), nullable=False)
    
    # Add the reverse relationship
    entries: Mapped[list["DhikarEntry"]] = relationship("DhikarEntry", back_populates="dhikar_type")
    
    # Add composite unique constraint
    __table_args__ = (
        UniqueConstraint('group_id', 'dhikar_topic_id', name='uq_group_topic'),
    )

class DhikarEntry(Base):
    __tablename__ = "dhikar_entry"
    
    entry_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    dhikar_count: Mapped[int] = mapped_column(Integer, nullable=False)
    dhikar_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("dhikar_type.id"), nullable=False)
    
    # Relationship to DhikarType
    dhikar_type: Mapped["DhikarType"] = relationship("DhikarType", back_populates="entries")

# Global engine instance
_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None

def init_db():
    """Initialize database engine and session maker."""
    global _engine, _async_session_maker
    if _engine is None:
        # _engine = create_async_engine(
        #     "sqlite+aiosqlite:///./dhikr.db",
        #     echo=False
        # )
        DB_USER = os.getenv("DB_USER")
        DB_PASSWORD = os.getenv("DB_PASSWORD")
        DB_HOST = os.getenv("DB_HOST")
        DB_NAME = os.getenv("DB_NAME")
        
        DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
        
        _engine = create_async_engine(
            DATABASE_URL,
            echo=False
        )

        _async_session_maker = async_sessionmaker(_engine, expire_on_commit=False)

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session as an async context manager."""
    if _async_session_maker is None:
        init_db()
    
    async with _async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def create_tables(engine):
    """Create database tables if they don't exist."""
    async with engine.begin() as conn:
        # Check if tables exist by inspecting the database
        tables_exist = await conn.run_sync(
            lambda sync_conn: sync_conn.dialect.has_table(sync_conn, "dhikar_type")
        )
        
        if not tables_exist:
            # Only create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)

async def get_dhikar_type_id(session: AsyncSession, group_id: int, topic_id: int) -> int | None:
    """
    Get the DhikarType id based on group_id and topic_id.
    Returns None if no matching record is found.
    """
    result = await session.execute(
        select(DhikarType.id)
        .where(
            DhikarType.group_id == group_id,
            DhikarType.dhikar_topic_id == topic_id
        )
    )
    row = result.scalar_one_or_none()
    return row

# async def test_get_dhikar_type():
#     # Create engine and tables
#     if _engine is None:
#         init_db()
#     await create_tables(_engine)
    
#     # Use the session context manager
#     async with get_session() as session:
#         # Create dummy DhikarType
#         dummy_dhikar = DhikarType(
#             group_id=12345,
#             dhikar_topic_id=3,
#             dhikar_title="Test Dhikar"
#         )
#         session.add(dummy_dhikar)
#         await session.commit()
        
#         # Test getting the id
#         result = await get_dhikar_type_id(session, group_id=12345, topic_id=1)
#         print(f"Found DhikarType ID: {result}")
        
#         # Test with non-existent data
#         no_result = await get_dhikar_type_id(session, group_id=99999, topic_id=99)
#         print(f"Non-existent search result: {no_result}")

async def create_dhikar_entry(session: AsyncSession, user_id: int, dhikar_count: int, dhikar_type_id: int) -> DhikarEntry:
    """
    Create a new dhikar entry in the database.
    
    Args:
        session: AsyncSession - The database session
        user_id: int - The ID of the user
        dhikar_count: int - The count of dhikars
        dhikar_type_id: int - The ID of the dhikar type
        
    Returns:
        DhikarEntry: The created entry
    """
    new_entry = DhikarEntry(
        user_id=user_id,
        dhikar_count=dhikar_count,
        dhikar_type_id=dhikar_type_id
    )
    
    session.add(new_entry)
    await session.commit()
    
    return new_entry

# async def test_create_dhikar_entry():
#     if _engine is None:
#         init_db()
#     await create_tables(_engine)
    
#     # Use the session context manager
#     async with get_session() as session:
#         # Create a test entry
#         entry = await create_dhikar_entry(
#             session=session,
#             user_id=123456,
#             dhikar_count=10,
#             dhikar_type_id=1
#         )
#         print(f"Created entry with ID: {entry.entry_id}")

async def get_total_dhikar_count(session: AsyncSession, dhikar_type_id: int) -> tuple[int, str | None]:
    """
    Get the total dhikar count and title for a specific dhikar type.
    
    Args:
        session: AsyncSession - The database session
        dhikar_type_id: int - The ID of the dhikar type
        
    Returns:
        tuple[int, str | None]: A tuple containing:
            - The total count of dhikars for the specified type
            - The dhikar title (None if dhikar type not found)
    """
    # Get the title from DhikarType
    type_result = await session.execute(
        select(DhikarType.dhikar_title)
        .where(DhikarType.id == dhikar_type_id)
    )
    title = type_result.scalar_one_or_none()
    
    # Get the sum separately
    count_result = await session.execute(
        select(func.sum(DhikarEntry.dhikar_count))
        .where(DhikarEntry.dhikar_type_id == dhikar_type_id)
    )
    total = count_result.scalar_one_or_none()
    
    return total or 0, title

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(test_create_dhikar_entry())
