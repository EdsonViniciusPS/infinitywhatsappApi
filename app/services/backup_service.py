"""Backup service for database snapshots, archive listing, restore, and retention."""

import gzip
import hashlib
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.models.instance import Instance
from app.models.logs import MessageLog, WebhookDelivery
from app.models.tenant import ApiKey, Tenant
from app.schemas.backup import (
    BackupFileInfo,
    BackupPruneResponse,
    SnapshotCreatedResponse,
    SnapshotRestoreResponse,
)

_SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")
_BACKUP_EXTENSIONS = (".tar.gz", ".json.gz")
_PRUNABLE_SUFFIXES = (".tar.gz", ".tar.gz.sha256", ".json.gz")


def validate_backup_filename(filename: str) -> str:
    """Validate backup filename and block path traversal attempts."""
    if not filename or ".." in filename or not _SAFE_FILENAME_RE.match(filename):
        raise AppError("Nome de arquivo de backup inválido.", status_code=400)
    return filename


def resolve_backup_path(backup_dir: Path, filename: str) -> Path:
    """Resolve a validated backup filename safely inside backup_dir."""
    safe_name = validate_backup_filename(filename)
    base_dir = backup_dir.resolve()
    target = (base_dir / safe_name).resolve()
    if target.parent != base_dir:
        raise AppError("Caminho de arquivo de backup inválido.", status_code=400)
    return target


def _compute_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _serialize_model(obj: Any) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, uuid.UUID):
            data[col.name] = str(val)
        elif isinstance(val, datetime):
            data[col.name] = val.isoformat()
        else:
            data[col.name] = val
    return data


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _parse_uuid(value: Any) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def list_backup_files(backup_dir: Path) -> list[BackupFileInfo]:
    """List .tar.gz and .json.gz backups in backup_dir sorted newest first."""
    if not backup_dir.exists():
        return []

    items: list[tuple[float, BackupFileInfo]] = []
    for entry in backup_dir.iterdir():
        if not entry.is_file() or not entry.name.endswith(_BACKUP_EXTENSIONS):
            continue
        stat = entry.stat()
        info = BackupFileInfo(
            filename=entry.name,
            size_bytes=stat.st_size,
            sha256=_compute_sha256(entry),
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        )
        items.append((stat.st_mtime, info))

    items.sort(key=lambda item: item[0], reverse=True)
    return [info for _, info in items]


async def create_db_snapshot(
    db: AsyncSession, backup_dir: Path
) -> SnapshotCreatedResponse:
    """Serialize all database records into a gzipped JSON snapshot file."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    filename = f"snapshot_{now.strftime('%Y%m%d_%H%M%S_%f')}.json.gz"
    target = resolve_backup_path(backup_dir, filename)

    models_map: list[tuple[str, Any]] = [
        ("tenants", Tenant),
        ("api_keys", ApiKey),
        ("instances", Instance),
        ("message_logs", MessageLog),
        ("webhook_deliveries", WebhookDelivery),
    ]
    tables_data: dict[str, list[dict[str, Any]]] = {}
    counts: dict[str, int] = {}

    for key, model_cls in models_map:
        rows = list((await db.execute(select(model_cls))).scalars().all())
        tables_data[key] = [_serialize_model(row) for row in rows]
        counts[key] = len(rows)

    payload = {
        "version": 1,
        "created_at": now.isoformat(),
        "tables": tables_data,
    }
    with gzip.open(target, "wt", encoding="utf-8") as gz_file:
        json.dump(payload, gz_file, ensure_ascii=False)

    stat = target.stat()
    return SnapshotCreatedResponse(
        filename=filename,
        size_bytes=stat.st_size,
        sha256=_compute_sha256(target),
        counts=counts,
        created_at=now,
    )


async def restore_db_snapshot(
    db: AsyncSession, backup_dir: Path, filename: str
) -> SnapshotRestoreResponse:
    """Idempotently restore Tenants, ApiKeys, and Instances from a .json.gz snapshot."""
    target = resolve_backup_path(backup_dir, filename)
    if not target.name.endswith(".json.gz"):
        raise AppError(
            "A restauração via API aceita apenas arquivos de snapshot (.json.gz).",
            status_code=400,
        )
    if not target.is_file():
        raise NotFoundError(f"Snapshot '{filename}' não encontrado.")

    with gzip.open(target, "rt", encoding="utf-8") as gz_file:
        payload = json.load(gz_file)

    tables = payload.get("tables", {})
    restored = {"tenants": 0, "api_keys": 0, "instances": 0}

    for row in tables.get("tenants", []):
        await db.merge(
            Tenant(
                id=_parse_uuid(row["id"]),
                name=row["name"],
                email=row["email"],
                is_active=row["is_active"],
                is_admin=row["is_admin"],
                created_at=_parse_datetime(row.get("created_at")) or datetime.now(UTC),
            )
        )
        restored["tenants"] += 1

    for row in tables.get("api_keys", []):
        await db.merge(
            ApiKey(
                id=_parse_uuid(row["id"]),
                tenant_id=_parse_uuid(row["tenant_id"]),
                name=row["name"],
                key_prefix=row["key_prefix"],
                key_hash=row["key_hash"],
                is_active=row["is_active"],
                expires_at=_parse_datetime(row.get("expires_at")),
                created_at=_parse_datetime(row.get("created_at")) or datetime.now(UTC),
            )
        )
        restored["api_keys"] += 1

    for row in tables.get("instances", []):
        await db.merge(
            Instance(
                id=_parse_uuid(row["id"]),
                tenant_id=_parse_uuid(row["tenant_id"]),
                instance_name=row["instance_name"],
                evo_instance_id=row.get("evo_instance_id"),
                status=row.get("status", "created"),
                webhook_url=row.get("webhook_url"),
                webhook_secret=row.get("webhook_secret"),
                webhook_events=row.get("webhook_events") or [],
                ai_enabled=row.get("ai_enabled", False),
                ai_model=row.get("ai_model"),
                ai_system_prompt=row.get("ai_system_prompt"),
                created_at=_parse_datetime(row.get("created_at")) or datetime.now(UTC),
                updated_at=_parse_datetime(row.get("updated_at")) or datetime.now(UTC),
            )
        )
        restored["instances"] += 1

    await db.flush()
    return SnapshotRestoreResponse(filename=target.name, restored_counts=restored)


def prune_old_backups(backup_dir: Path, retention_days: int) -> BackupPruneResponse:
    """Remove backup archives older than retention_days."""
    if not backup_dir.exists():
        return BackupPruneResponse(deleted_files=[], retention_days=retention_days)

    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    deleted_files: list[str] = []

    for entry in backup_dir.iterdir():
        if not entry.is_file() or not entry.name.endswith(_PRUNABLE_SUFFIXES):
            continue
        mtime = datetime.fromtimestamp(entry.stat().st_mtime, tz=UTC)
        if mtime < cutoff:
            entry.unlink()
            deleted_files.append(entry.name)

    deleted_files.sort()
    return BackupPruneResponse(deleted_files=deleted_files, retention_days=retention_days)
