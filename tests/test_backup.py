"""Unit tests for backup service (filename validation, listing, and retention pruning)."""

import gzip
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.core.exceptions import AppError
from app.models.instance import Instance
from app.models.tenant import ApiKey, Tenant
from app.services.backup_service import (
    create_db_snapshot,
    list_backup_files,
    prune_old_backups,
    resolve_backup_path,
    restore_db_snapshot,
    validate_backup_filename,
)
from app.services.maintenance_service import run_maintenance_cycle


def test_validate_backup_filename_accepts_safe_names() -> None:
    assert validate_backup_filename("full_backup_20261118_120000.tar.gz") == (
        "full_backup_20261118_120000.tar.gz"
    )
    assert validate_backup_filename("snapshot-01.json.gz") == "snapshot-01.json.gz"


@pytest.mark.parametrize(
    "bad_name",
    [
        "",
        "../secret.tar.gz",
        "..\\secret.tar.gz",
        "subdir/backup.tar.gz",
        "backup with spaces.tar.gz",
        "backup;rm.tar.gz",
    ],
)
def test_validate_backup_filename_rejects_traversal_and_invalid_chars(bad_name: str) -> None:
    with pytest.raises(AppError) as exc_info:
        validate_backup_filename(bad_name)
    assert exc_info.value.status_code == 400


def test_resolve_backup_path_stays_inside_backup_dir(tmp_path: Path) -> None:
    resolved = resolve_backup_path(tmp_path, "snapshot_1.json.gz")
    assert resolved.parent == tmp_path.resolve()


def test_list_and_prune_old_backups(tmp_path: Path) -> None:
    old_file = tmp_path / "full_backup_old.tar.gz"
    old_sha = tmp_path / "full_backup_old.tar.gz.sha256"
    recent_file = tmp_path / "snapshot_recent.json.gz"
    ignored_file = tmp_path / ".gitkeep"

    old_file.write_bytes(b"old-archive")
    old_sha.write_text("abc123", encoding="utf-8")
    with gzip.open(recent_file, "wt", encoding="utf-8") as fh:
        fh.write('{"version": 1}')
    ignored_file.write_text("", encoding="utf-8")

    now = time.time()
    ten_days_ago = now - (10 * 86400)
    os.utime(old_file, (ten_days_ago, ten_days_ago))
    os.utime(old_sha, (ten_days_ago, ten_days_ago))

    listed = list_backup_files(tmp_path)
    assert [item.filename for item in listed] == [
        "snapshot_recent.json.gz",
        "full_backup_old.tar.gz",
    ]
    assert len(listed[0].sha256) == 64

    pruned = prune_old_backups(tmp_path, retention_days=7)
    assert pruned.retention_days == 7
    assert pruned.deleted_files == [
        "full_backup_old.tar.gz",
        "full_backup_old.tar.gz.sha256",
    ]
    assert not old_file.exists()
    assert not old_sha.exists()
    assert recent_file.exists()
    assert ignored_file.exists()


class _FakeScalarResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class _FakeExecuteResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._rows)


class _FakeDeleteResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _FakeAsyncSession:
    def __init__(self, data_by_model: dict[Any, list[Any]], delete_rowcount: int = 0) -> None:
        self._data_by_model = data_by_model
        self._delete_rowcount = delete_rowcount
        self.merged: list[Any] = []
        self.deleted_stmts: list[Any] = []
        self.flushed = False

    async def execute(self, stmt: Any) -> Any:
        if hasattr(stmt, "column_descriptions"):
            model_cls = stmt.column_descriptions[0]["entity"]
            return _FakeExecuteResult(self._data_by_model.get(model_cls, []))
        self.deleted_stmts.append(stmt)
        return _FakeDeleteResult(self._delete_rowcount)

    async def merge(self, obj: Any) -> Any:
        self.merged.append(obj)
        return obj

    async def flush(self) -> None:
        self.flushed = True


async def test_create_and_restore_db_snapshot_roundtrip(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Empresa Teste",
        email="teste@empresa.com",
        is_active=True,
        is_admin=False,
        created_at=now,
    )
    api_key = ApiKey(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Chave Principal",
        key_prefix="inf_12345678",
        key_hash="a" * 64,
        is_active=True,
        expires_at=None,
        created_at=now,
    )
    instance = Instance(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        instance_name="atendimento",
        evo_instance_id="evo-1",
        status="open",
        webhook_url="https://example.com/hook",
        webhook_secret="sec",
        webhook_events=["messages.upsert"],
        ai_enabled=True,
        ai_model="gemini-4-hydrogen",
        ai_system_prompt="Ajude o cliente.",
        created_at=now,
        updated_at=now,
    )

    session = _FakeAsyncSession({Tenant: [tenant], ApiKey: [api_key], Instance: [instance]})
    created = await create_db_snapshot(session, tmp_path)  # type: ignore[arg-type]

    assert created.filename.startswith("snapshot_")
    assert created.filename.endswith(".json.gz")
    assert created.counts["tenants"] == 1
    assert created.counts["api_keys"] == 1
    assert created.counts["instances"] == 1

    restore_session = _FakeAsyncSession({})
    restored = await restore_db_snapshot(
        restore_session,  # type: ignore[arg-type]
        tmp_path,
        created.filename,
    )
    assert restored.restored_counts == {"tenants": 1, "api_keys": 1, "instances": 1}
    assert restore_session.flushed is True
    assert len(restore_session.merged) == 3
    assert isinstance(restore_session.merged[0].id, uuid.UUID)
    assert isinstance(restore_session.merged[2].created_at, datetime)


class _FakeRedisMaintenance:
    def __init__(self) -> None:
        self.commands: list[tuple[Any, ...]] = []

    async def execute_command(self, *args: Any) -> str:
        self.commands.append(args)
        return "OK"


async def test_run_maintenance_cycle_creates_snapshot_and_prunes(tmp_path: Path) -> None:
    expired_backup = tmp_path / "full_backup_old.tar.gz"
    expired_backup.write_bytes(b"old")
    old_ts = time.time() - (10 * 86400)
    os.utime(expired_backup, (old_ts, old_ts))

    session = _FakeAsyncSession({}, delete_rowcount=5)
    redis_mock = _FakeRedisMaintenance()

    report = await run_maintenance_cycle(
        db=session,  # type: ignore[arg-type]
        backup_dir=tmp_path,
        retention_days=7,
        redis_client=redis_mock,
    )

    assert report.snapshot_filename.startswith("snapshot_")
    assert (tmp_path / report.snapshot_filename).is_file()
    assert report.deleted_message_logs == 5
    assert report.deleted_webhook_deliveries == 5
    assert report.deleted_backup_files == ["full_backup_old.tar.gz"]
    assert not expired_backup.exists()
    assert len(session.deleted_stmts) == 2
    assert session.flushed is True
    assert redis_mock.commands == [("MEMORY", "PURGE")]
    assert report.retention_days == 7


