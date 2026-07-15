from __future__ import annotations

import asyncio
import gzip
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BackupError, ConflictError
from app.repositories import platform_setting_repository
from app.schemas.admin import AdminBackupActionResponse, AdminBackupResponse
from app.services import audit_service

BACKUP_NAME_RE = re.compile(r"^dtransfert_(?P<stamp>\d{8}_\d{6})\.dump\.gz$")


@dataclass(slots=True)
class _DatabaseTarget:
    host: str
    port: int
    username: str
    password: str
    database: str


def _backup_dir() -> Path:
    path = Path(get_settings().backup_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _database_target() -> _DatabaseTarget:
    url = make_url(get_settings().database_url)
    return _DatabaseTarget(
        host=url.host or "localhost",
        port=int(url.port or 5432),
        username=url.username or "",
        password=url.password or "",
        database=url.database or "",
    )


def _backup_filename(now: datetime | None = None) -> str:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return current.strftime("dtransfert_%Y%m%d_%H%M%S.dump.gz")


def _parse_backup_datetime(filename: str) -> datetime | None:
    match = BACKUP_NAME_RE.match(filename)
    if match is None:
        return None
    return datetime.strptime(match.group("stamp"), "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)


def _to_response(path: Path) -> AdminBackupResponse:
    created_at = _parse_backup_datetime(path.name)
    if created_at is None:
        created_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return AdminBackupResponse(filename=path.name, created_at=created_at, size_bytes=path.stat().st_size)


async def _run_command(*args: str, password: str) -> None:
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    process = await asyncio.create_subprocess_exec(
        *args,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        message = stderr.decode().strip() or stdout.decode().strip() or "Commande PostgreSQL échouée."
        raise BackupError(message)


async def list_backups() -> list[AdminBackupResponse]:
    backups = [path for path in _backup_dir().glob("dtransfert_*.dump.gz") if path.is_file()]
    backups.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return [_to_response(path) for path in backups]


async def create_backup(session: AsyncSession, acted_by_user_id: uuid.UUID) -> AdminBackupActionResponse:
    target = _database_target()
    if not target.database:
        raise BackupError("Base de données introuvable dans DATABASE_URL.")
    backup_dir = _backup_dir()

    current = datetime.now(timezone.utc)
    backup_path = backup_dir / _backup_filename(current)
    while backup_path.exists():
        current = current + timedelta(seconds=1)
        backup_path = backup_dir / _backup_filename(current)

    dump_fd, dump_path_str = tempfile.mkstemp(suffix=".dump", dir=str(backup_dir))
    dump_path = Path(dump_path_str)
    os.close(dump_fd)
    try:
        await _run_command(
            "pg_dump",
            "-h",
            target.host,
            "-p",
            str(target.port),
            "-U",
            target.username,
            "-d",
            target.database,
            "-Fc",
            "-f",
            str(dump_path),
            password=target.password,
        )

        with dump_path.open("rb") as source, gzip.open(backup_path, "wb") as destination:
            shutil.copyfileobj(source, destination)
    except Exception as exc:
        if dump_path.exists():
            dump_path.unlink(missing_ok=True)
        if backup_path.exists():
            backup_path.unlink(missing_ok=True)
        if isinstance(exc, BackupError):
            raise
        raise BackupError("Impossible de créer la sauvegarde.") from exc
    else:
        dump_path.unlink(missing_ok=True)

    backup = _to_response(backup_path)
    await audit_service.log_action(
        session,
        None,
        acted_by_user_id,
        "admin.backup_create",
        "system_backup",
        None,
        note=backup.filename,
    )
    await session.commit()
    return AdminBackupActionResponse(detail="Sauvegarde créée avec succès.", backup=backup)


async def restore_backup(
    session: AsyncSession, acted_by_user_id: uuid.UUID, filename: str
) -> AdminBackupActionResponse:
    settings = await platform_setting_repository.get(session)
    if settings is None or not settings.maintenance_mode:
        raise ConflictError("Active le mode maintenance avant de restaurer une sauvegarde.")

    backup_path = _backup_dir() / filename
    if not backup_path.exists():
        raise BackupError("Sauvegarde introuvable.")

    target = _database_target()
    if not target.database:
        raise BackupError("Base de données introuvable dans DATABASE_URL.")
    temp_fd, temp_dump_path_str = tempfile.mkstemp(suffix=".dump", dir=str(_backup_dir()))
    temp_dump_path = Path(temp_dump_path_str)
    os.close(temp_fd)
    try:
        with gzip.open(backup_path, "rb") as source, temp_dump_path.open("wb") as destination:
            shutil.copyfileobj(source, destination)

        await _run_command(
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--exit-on-error",
            "-h",
            target.host,
            "-p",
            str(target.port),
            "-U",
            target.username,
            "-d",
            target.database,
            str(temp_dump_path),
            password=target.password,
        )
    except Exception as exc:
        if temp_dump_path.exists():
            temp_dump_path.unlink(missing_ok=True)
        if isinstance(exc, BackupError):
            raise
        raise BackupError("Impossible de restaurer la sauvegarde.") from exc
    else:
        temp_dump_path.unlink(missing_ok=True)

    await audit_service.log_action(
        session,
        None,
        acted_by_user_id,
        "admin.backup_restore",
        "system_backup",
        None,
        note=filename,
    )
    await session.commit()
    return AdminBackupActionResponse(detail="Sauvegarde restaurée avec succès.", backup=_to_response(backup_path))
