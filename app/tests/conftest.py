import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.database import get_db
from app.core.permission_codes import PERMISSION_DESCRIPTIONS, RoleCode
from app.main import app
from app.models.base import Base
from app.models.role import Permission, Role

TEST_DATABASE_URL = "postgresql+asyncpg://dtransfert:dtransfert@localhost:5432/dtransfert_test"

test_engine = create_async_engine(TEST_DATABASE_URL)


async def _seed_reference_data(conn) -> None:
    session = AsyncSession(bind=conn, expire_on_commit=False)
    for code, description in PERMISSION_DESCRIPTIONS.items():
        session.add(Permission(code=code.value, description=description))
    for code, name in [
        (RoleCode.OWNER, "Owner"),
        (RoleCode.EMPLOYEE, "Employé"),
        (RoleCode.SUPER_ADMIN, "Super Admin"),
    ]:
        session.add(Role(code=code.value, name=name, is_system=True))
    await session.flush()
    await session.close()


@pytest.fixture(scope="session", autouse=True)
async def _setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await _seed_reference_data(conn)
    yield
    await test_engine.dispose()


@pytest.fixture
async def db_session():
    connection = await test_engine.connect()
    trans = await connection.begin()
    session = AsyncSession(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield session
    app.dependency_overrides.pop(get_db, None)
    await session.close()
    await trans.rollback()
    await connection.close()


@pytest.fixture
async def client(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
