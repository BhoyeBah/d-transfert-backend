import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ConflictError
from app.services import backup_service


@pytest.mark.asyncio
async def test_list_backups_sorts_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_service, "_backup_dir", lambda: tmp_path)
    (tmp_path / "dtransfert_20260715_120000.dump.gz").write_bytes(b"a")
    (tmp_path / "dtransfert_20260715_130000.dump.gz").write_bytes(b"ab")

    backups = await backup_service.list_backups()

    assert [backup.filename for backup in backups] == [
        "dtransfert_20260715_130000.dump.gz",
        "dtransfert_20260715_120000.dump.gz",
    ]


@pytest.mark.asyncio
async def test_create_backup_writes_backup_file(tmp_path, monkeypatch):
    session = SimpleNamespace(commit=AsyncMock())
    monkeypatch.setattr(backup_service, "_backup_dir", lambda: tmp_path)
    monkeypatch.setattr(
        backup_service,
        "_database_target",
        lambda: SimpleNamespace(host="localhost", port=5432, username="dtransfert", password="secret", database="db"),
    )
    monkeypatch.setattr(backup_service, "_run_command", AsyncMock())
    monkeypatch.setattr(backup_service.audit_service, "log_action", AsyncMock())

    result = await backup_service.create_backup(session, acted_by_user_id=uuid.uuid4())

    assert result.backup.filename.endswith(".dump.gz")
    assert (tmp_path / result.backup.filename).exists()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_restore_backup_requires_maintenance_mode(tmp_path, monkeypatch):
    session = SimpleNamespace(commit=AsyncMock())
    monkeypatch.setattr(backup_service, "_backup_dir", lambda: tmp_path)
    monkeypatch.setattr(
        backup_service.platform_setting_repository,
        "get",
        AsyncMock(return_value=SimpleNamespace(maintenance_mode=False)),
    )

    with pytest.raises(ConflictError):
        await backup_service.restore_backup(
            session,
            acted_by_user_id=uuid.uuid4(),
            filename="dtransfert_20260715_130000.dump.gz",
        )
