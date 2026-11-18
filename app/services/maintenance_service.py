"""Periodic 7-day maintenance service for database cleanup, backup pruning, and memory."""

import asyncio
import gc
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.logs import MessageLog, WebhookDelivery
from app.schemas.backup import MaintenanceReport
from app.services.backup_service import create_db_snapshot, prune_old_backups

logger = logging.getLogger(__name__)


async def run_maintenance_cycle(
    db: AsyncSession,
    backup_dir: Path,
    retention_days: int = 7,
    redis_client: Any = None,
) -> MaintenanceReport:
    """Create a preventive snapshot, prune old logs/backups, and reclaim memory."""
    snapshot = await create_db_snapshot(db, backup_dir)

    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    msg_result = await db.execute(delete(MessageLog).where(MessageLog.created_at < cutoff))
    webhook_result = await db.execute(
        delete(WebhookDelivery).where(WebhookDelivery.created_at < cutoff)
    )
    await db.flush()

    deleted_message_logs = int(getattr(msg_result, "rowcount", 0) or 0)
    deleted_webhook_deliveries = int(getattr(webhook_result, "rowcount", 0) or 0)

    pruned = prune_old_backups(backup_dir, retention_days)

    if redis_client is not None:
        try:
            await redis_client.execute_command("MEMORY", "PURGE")
        except Exception as exc:
            logger.debug("Redis MEMORY PURGE ignorado: %s", exc)

    collected = gc.collect()

    return MaintenanceReport(
        snapshot_filename=snapshot.filename,
        deleted_message_logs=deleted_message_logs,
        deleted_webhook_deliveries=deleted_webhook_deliveries,
        deleted_backup_files=pruned.deleted_files,
        gc_collected_objects=collected,
        retention_days=retention_days,
        executed_at=datetime.now(UTC),
    )


async def periodic_maintenance_loop(
    interval_seconds: int,
    retention_days: int,
    backup_dir: Path,
    redis_client: Any = None,
) -> None:
    """Run run_maintenance_cycle periodically in the background (default every 7 days)."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            async with async_session_factory() as session:
                report = await run_maintenance_cycle(
                    db=session,
                    backup_dir=backup_dir,
                    retention_days=retention_days,
                    redis_client=redis_client,
                )
                await session.commit()
            logger.info(
                "Manutenção periódica concluída: snapshot=%s, logs=%d, webhooks=%d",
                report.snapshot_filename,
                report.deleted_message_logs,
                report.deleted_webhook_deliveries,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Erro ao executar ciclo periódico de manutenção.")
