import hashlib
import json
import logging
import threading
import uuid
from enum import Enum
from typing import Callable

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class Pipeline(str, Enum):
    SEARCH = "search"
    EXTRACT = "extract"
    BUILD_CASE = "build_case"
    STORY = "story"


_locks: dict[tuple[str, Pipeline], threading.Lock] = {}
_locks_guard = threading.Lock()

_last_hashes: dict[tuple[str, Pipeline], str] = {}


def _get_lock(key: tuple[str, Pipeline]) -> threading.Lock:
    with _locks_guard:
        if key not in _locks:
            _locks[key] = threading.Lock()
        return _locks[key]


def _compute_hash(*parts) -> str:
    blob = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def _pipeline_hash(
    pipeline: Pipeline,
    schema_data: list,
    shoebox_ids: list[str],
    evidence_ids: list[str],
) -> str:
    from app.schematization.service import strip_empty_frames, strip_suggestions

    filtered = strip_suggestions(strip_empty_frames(schema_data))
    if pipeline == Pipeline.SEARCH:
        return _compute_hash(filtered, shoebox_ids)
    if pipeline == Pipeline.EXTRACT:
        return _compute_hash(filtered, shoebox_ids, evidence_ids)
    if pipeline == Pipeline.STORY:
        return _compute_hash(filtered)
    return _compute_hash(filtered, evidence_ids)


def try_run(
    ws_id: str,
    pipeline: Pipeline,
    run_fn: Callable[[], None],
    current_hash: str,
    force: bool = False,
) -> bool:
    key = (ws_id, pipeline)
    if not force and _last_hashes.get(key) == current_hash:
        return False
    lock = _get_lock(key)
    if not lock.acquire(blocking=False):
        return False
    thread = threading.Thread(
        target=_thread_wrapper,
        args=(uuid.UUID(ws_id), pipeline, run_fn, lock, current_hash),
        daemon=True,
    )
    thread.start()
    return True


def _thread_wrapper(
    workspace_id: uuid.UUID,
    pipeline: Pipeline,
    run_fn: Callable[[], None],
    lock: threading.Lock,
    pre_run_hash: str,
) -> None:
    try:
        run_fn()
    except Exception:
        logger.exception("pipeline %s failed for %s", pipeline, workspace_id)
    _update_hash_and_chain(workspace_id, pipeline, lock, pre_run_hash)


def _update_hash_and_chain(
    workspace_id: uuid.UUID,
    pipeline: Pipeline,
    lock: threading.Lock,
    pre_run_hash: str,
) -> None:
    from app.database import SessionLocal

    ws_str = str(workspace_id)
    key = (ws_str, pipeline)
    _last_hashes[key] = pre_run_hash
    try:
        db = SessionLocal()
        try:
            schema_data, shoebox_ids, evidence_ids = _load_state(db, workspace_id)
            _last_hashes[key] = _pipeline_hash(pipeline, schema_data, shoebox_ids, evidence_ids)
        finally:
            db.close()
    except Exception:
        pass
    lock.release()
    try:
        db = SessionLocal()
        try:
            check_and_trigger(db, workspace_id)
        finally:
            db.close()
    except Exception:
        logger.exception("pipeline chaining failed for %s", workspace_id)


def _load_state(
    db: Session,
    workspace_id: uuid.UUID,
) -> tuple[list, list[str], list[str]]:
    from app.schematization.service import get_or_create
    from app.shoebox.service import list_items as list_shoebox
    from app.evidence.service import list_items as list_evidence

    schema_data = get_or_create(db, workspace_id).data
    shoebox_ids = sorted(str(i.id) for i in list_shoebox(db, workspace_id))
    evidence_ids = sorted(str(i.id) for i in list_evidence(db, workspace_id))
    return schema_data, shoebox_ids, evidence_ids


def is_any_running(workspace_id: uuid.UUID) -> bool:
    ws_str = str(workspace_id)
    for pipeline in Pipeline:
        lock = _locks.get((ws_str, pipeline))
        if lock is not None and lock.locked():
            return True
    return False


def running_pipelines(workspace_id: uuid.UUID) -> dict[str, bool]:
    ws_str = str(workspace_id)
    result = {}
    for pipeline in Pipeline:
        lock = _locks.get((ws_str, pipeline))
        result[pipeline.value] = lock is not None and lock.locked()
    return result


def check_and_trigger(db: Session, workspace_id: uuid.UUID) -> bool:
    from app import settings
    if not settings.ANTHROPIC_API_KEY:
        return False

    schema_data, shoebox_ids, evidence_ids = _load_state(db, workspace_id)
    ws_str = str(workspace_id)

    from app.ai import search_and_query, read_and_extract, build_case, tell_story

    try_run(
        ws_str,
        Pipeline.SEARCH,
        lambda: search_and_query.run(workspace_id, schema_data),
        _pipeline_hash(Pipeline.SEARCH, schema_data, shoebox_ids, evidence_ids),
    )

    if shoebox_ids:
        try_run(
            ws_str,
            Pipeline.EXTRACT,
            lambda: read_and_extract.run(workspace_id),
            _pipeline_hash(Pipeline.EXTRACT, schema_data, shoebox_ids, evidence_ids),
        )

    if evidence_ids:
        try_run(
            ws_str,
            Pipeline.BUILD_CASE,
            lambda: build_case.run(workspace_id),
            _pipeline_hash(Pipeline.BUILD_CASE, schema_data, shoebox_ids, evidence_ids),
        )

    has_schema_nodes = any(
        n.get("type") == "frame"
        or (n.get("type") == "evidence" and not n.get("suggestion"))
        for n in schema_data
    )
    if has_schema_nodes:
        try_run(
            ws_str,
            Pipeline.STORY,
            lambda: tell_story.run(workspace_id),
            _pipeline_hash(Pipeline.STORY, schema_data, shoebox_ids, evidence_ids),
        )

    return is_any_running(workspace_id)


def force_search(db: Session, workspace_id: uuid.UUID) -> bool:
    from app import settings
    if not settings.ANTHROPIC_API_KEY:
        return False
    from app.schematization.service import get_or_create
    from app.ai import search_and_query
    schema_data = get_or_create(db, workspace_id).data
    return try_run(
        str(workspace_id),
        Pipeline.SEARCH,
        lambda: search_and_query.run(workspace_id, schema_data),
        "",
        force=True,
    )


def force_extract(db: Session, workspace_id: uuid.UUID) -> bool:
    from app import settings
    if not settings.ANTHROPIC_API_KEY:
        return False
    from app.ai import read_and_extract
    return try_run(
        str(workspace_id),
        Pipeline.EXTRACT,
        lambda: read_and_extract.run(workspace_id),
        "",
        force=True,
    )


def force_build_case(db: Session, workspace_id: uuid.UUID) -> bool:
    from app import settings
    if not settings.ANTHROPIC_API_KEY:
        return False
    from app.ai import build_case
    return try_run(
        str(workspace_id),
        Pipeline.BUILD_CASE,
        lambda: build_case.run(workspace_id),
        "",
        force=True,
    )


def force_story(db: Session, workspace_id: uuid.UUID) -> bool:
    from app import settings
    if not settings.ANTHROPIC_API_KEY:
        return False
    from app.ai import tell_story
    return try_run(
        str(workspace_id),
        Pipeline.STORY,
        lambda: tell_story.run(workspace_id),
        "",
        force=True,
    )


def reset_state() -> None:
    _last_hashes.clear()
    with _locks_guard:
        _locks.clear()
