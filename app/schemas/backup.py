"""Pydantic schemas for backup management and database snapshots."""

from datetime import datetime

from pydantic import BaseModel


class BackupFileInfo(BaseModel):
    filename: str
    size_bytes: int
    sha256: str
    created_at: datetime


class SnapshotCreatedResponse(BaseModel):
    filename: str
    size_bytes: int
    sha256: str
    counts: dict[str, int]
    created_at: datetime


class SnapshotRestoreResponse(BaseModel):
    filename: str
    restored_counts: dict[str, int]


class BackupPruneResponse(BaseModel):
    deleted_files: list[str]
    retention_days: int


class MaintenanceReport(BaseModel):
    snapshot_filename: str
    deleted_message_logs: int
    deleted_webhook_deliveries: int
    deleted_backup_files: list[str]
    gc_collected_objects: int
    retention_days: int
    executed_at: datetime
