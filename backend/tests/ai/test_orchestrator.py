import threading
import time
import uuid

from app.ai.orchestrator import (
    Pipeline,
    _compute_hash,
    _pipeline_hash,
    is_any_running,
    reset_state,
    running_pipelines,
    try_run,
)


def setup_function():
    reset_state()


def test_compute_hash_deterministic():
    h1 = _compute_hash([1, 2], ["a"])
    h2 = _compute_hash([1, 2], ["a"])
    assert h1 == h2


def test_compute_hash_differs_on_change():
    h1 = _compute_hash([1], ["a"])
    h2 = _compute_hash([1], ["b"])
    assert h1 != h2


def test_pipeline_hash_search_ignores_evidence():
    h1 = _pipeline_hash(Pipeline.SEARCH, [], ["s1"], ["e1"])
    h2 = _pipeline_hash(Pipeline.SEARCH, [], ["s1"], ["e2"])
    assert h1 == h2


def test_pipeline_hash_build_case_ignores_shoebox():
    h1 = _pipeline_hash(Pipeline.BUILD_CASE, [], ["s1"], ["e1"])
    h2 = _pipeline_hash(Pipeline.BUILD_CASE, [], ["s2"], ["e1"])
    assert h1 == h2


def test_pipeline_hash_extract_uses_all():
    h1 = _pipeline_hash(Pipeline.EXTRACT, [], ["s1"], ["e1"])
    h2 = _pipeline_hash(Pipeline.EXTRACT, [], ["s1"], ["e2"])
    assert h1 != h2


def test_try_run_starts_thread():
    ran = threading.Event()

    def job():
        ran.set()

    ws = str(uuid.uuid4())
    started = try_run(ws, Pipeline.SEARCH, job, "hash1")
    assert started
    ran.wait(timeout=2)
    assert ran.is_set()


def test_try_run_noop_on_same_hash():
    done = threading.Event()

    def job():
        done.set()

    ws = str(uuid.uuid4())
    try_run(ws, Pipeline.SEARCH, job, "hash1")
    done.wait(timeout=2)
    time.sleep(0.05)

    started = try_run(ws, Pipeline.SEARCH, lambda: None, "hash1")
    assert not started


def test_try_run_runs_on_new_hash():
    first_done = threading.Event()
    second_ran = threading.Event()

    def first():
        first_done.set()

    def second():
        second_ran.set()

    ws = str(uuid.uuid4())
    try_run(ws, Pipeline.SEARCH, first, "hash1")
    first_done.wait(timeout=2)
    time.sleep(0.05)

    started = try_run(ws, Pipeline.SEARCH, second, "hash2")
    assert started
    second_ran.wait(timeout=2)
    assert second_ran.is_set()


def test_try_run_rejects_while_locked():
    hold = threading.Event()
    started_first = threading.Event()

    def slow_job():
        started_first.set()
        hold.wait(timeout=5)

    ws = str(uuid.uuid4())
    try_run(ws, Pipeline.SEARCH, slow_job, "hash1")
    started_first.wait(timeout=2)

    started = try_run(ws, Pipeline.SEARCH, lambda: None, "hash2")
    assert not started

    hold.set()


def test_force_skips_hash_check():
    done = threading.Event()

    def job():
        done.set()

    ws = str(uuid.uuid4())
    try_run(ws, Pipeline.SEARCH, job, "hash1")
    done.wait(timeout=2)
    time.sleep(0.05)

    second_ran = threading.Event()
    started = try_run(ws, Pipeline.SEARCH, lambda: second_ran.set(), "hash1", force=True)
    assert started
    second_ran.wait(timeout=2)
    assert second_ran.is_set()


def test_force_still_respects_lock():
    hold = threading.Event()
    started_first = threading.Event()

    def slow_job():
        started_first.set()
        hold.wait(timeout=5)

    ws = str(uuid.uuid4())
    try_run(ws, Pipeline.SEARCH, slow_job, "hash1")
    started_first.wait(timeout=2)

    started = try_run(ws, Pipeline.SEARCH, lambda: None, "x", force=True)
    assert not started

    hold.set()


def test_is_any_running():
    ws = uuid.uuid4()
    assert not is_any_running(ws)

    hold = threading.Event()
    started = threading.Event()

    def job():
        started.set()
        hold.wait(timeout=5)

    try_run(str(ws), Pipeline.EXTRACT, job, "h")
    started.wait(timeout=2)
    assert is_any_running(ws)

    hold.set()
    time.sleep(0.1)
    assert not is_any_running(ws)


def test_different_pipelines_independent():
    hold_search = threading.Event()
    search_started = threading.Event()

    def search_job():
        search_started.set()
        hold_search.wait(timeout=5)

    extract_ran = threading.Event()

    ws = str(uuid.uuid4())
    try_run(ws, Pipeline.SEARCH, search_job, "h1")
    search_started.wait(timeout=2)

    started = try_run(ws, Pipeline.EXTRACT, lambda: extract_ran.set(), "h2")
    assert started
    extract_ran.wait(timeout=2)
    assert extract_ran.is_set()

    hold_search.set()


def test_running_pipelines_reports_per_pipeline():
    ws = uuid.uuid4()
    status = running_pipelines(ws)
    assert status == {"search": False, "extract": False, "build_case": False}

    hold = threading.Event()
    started = threading.Event()

    def job():
        started.set()
        hold.wait(timeout=5)

    try_run(str(ws), Pipeline.SEARCH, job, "h")
    started.wait(timeout=2)

    status = running_pipelines(ws)
    assert status["search"] is True
    assert status["extract"] is False
    assert status["build_case"] is False

    hold.set()
    time.sleep(0.1)

    status = running_pipelines(ws)
    assert status == {"search": False, "extract": False, "build_case": False}


def test_different_workspaces_independent():
    hold = threading.Event()
    started = threading.Event()

    def slow():
        started.set()
        hold.wait(timeout=5)

    ws1 = str(uuid.uuid4())
    ws2 = str(uuid.uuid4())

    try_run(ws1, Pipeline.SEARCH, slow, "h")
    started.wait(timeout=2)

    other_ran = threading.Event()
    result = try_run(ws2, Pipeline.SEARCH, lambda: other_ran.set(), "h")
    assert result
    other_ran.wait(timeout=2)

    hold.set()
