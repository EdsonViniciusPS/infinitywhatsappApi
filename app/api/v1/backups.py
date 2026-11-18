"""Administrative endpoints for database snapshots, backup downloads, and retention."""

from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.schemas.backup import (
    BackupFileInfo,
    BackupPruneResponse,
    MaintenanceReport,
    SnapshotCreatedResponse,
    SnapshotRestoreResponse,
)
from app.services.backup_service import (
    create_db_snapshot,
    list_backup_files,
    prune_old_backups,
    resolve_backup_path,
    restore_db_snapshot,
)
from app.services.maintenance_service import run_maintenance_cycle

router = APIRouter(
    prefix="/backups",
    tags=["Backups"],
    dependencies=[Depends(require_admin)],
)


def _get_backup_dir() -> Path:
    return Path(get_settings().BACKUP_DIR)


@router.get("", response_model=list[BackupFileInfo])
async def list_backups() -> list[BackupFileInfo]:
    """List all backup archives and snapshots available on disk."""
    return list_backup_files(_get_backup_dir())


@router.post("/snapshot", response_model=SnapshotCreatedResponse)
async def create_snapshot(db: AsyncSession = Depends(get_db)) -> SnapshotCreatedResponse:
    """Create a compressed JSON snapshot of the application database."""
    return await create_db_snapshot(db, _get_backup_dir())


@router.get("/{filename}/download")
async def download_backup(filename: str) -> FileResponse:
    """Download a backup archive or database snapshot."""
    target = resolve_backup_path(_get_backup_dir(), filename)
    if not target.is_file():
        raise NotFoundError(f"Arquivo de backup '{filename}' não encontrado.")
    return FileResponse(path=target, filename=target.name, media_type="application/gzip")


@router.post("/{filename}/restore", response_model=SnapshotRestoreResponse)
async def restore_snapshot(
    filename: str,
    db: AsyncSession = Depends(get_db),
) -> SnapshotRestoreResponse:
    """Restore Tenants, ApiKeys, and Instances from a .json.gz snapshot."""
    return await restore_db_snapshot(db, _get_backup_dir(), filename)


@router.delete("/prune", response_model=BackupPruneResponse)
async def prune_backups(
    retention_days: int | None = Query(default=None, ge=0),
) -> BackupPruneResponse:
    """Delete backup files older than retention_days."""
    settings = get_settings()
    days = retention_days if retention_days is not None else settings.BACKUP_RETENTION_DAYS
    return prune_old_backups(_get_backup_dir(), days)


@router.post("/maintenance", response_model=MaintenanceReport)
async def trigger_maintenance(
    request: Request,
    retention_days: int | None = Query(default=None, ge=0),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceReport:
    """Run preventive snapshot, clean old logs/backups, and reclaim memory."""
    settings = get_settings()
    days = retention_days if retention_days is not None else settings.LOG_RETENTION_DAYS
    return await run_maintenance_cycle(
        db=db,
        backup_dir=_get_backup_dir(),
        retention_days=days,
        redis_client=getattr(request.app.state, "redis", None),
    )
