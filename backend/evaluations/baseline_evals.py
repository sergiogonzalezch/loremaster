#!/usr/bin/env python3
"""Baseline Evaluation -- Loremaster
Ejecuta el golden dataset contra la API en ejecucion y reporta PASS/FAIL por caso.

Modos de ejecucion:
  - Standalone (default): arranca un backend aislado en :8001 con evaluations/evals.db.
    La base de datos principal (loremaster.db) no se modifica.
  - Conectado: usa un backend ya corriendo con --no-standalone --base-url <url>.

Prerequisitos:
  - Qdrant disponible : docker-compose up -d qdrant
  - Ollama disponible (para casos LLM)
  - venv activo con dependencias instaladas

Uso (desde backend/ con el venv activo):
    python evaluations/baseline_evals.py
    python evaluations/baseline_evals.py --eval-port 8002
    python evaluations/baseline_evals.py --categories rag_query guardrail
    python evaluations/baseline_evals.py --ids RAG-001 CHAR-005 FLOW-001
    python evaluations/baseline_evals.py --keep-collection
    python evaluations/baseline_evals.py --no-seed
    python evaluations/baseline_evals.py --no-standalone --base-url http://localhost:8000

Notas de seguridad:
  - Este script es para desarrollo/testing local. No ejecutar en produccion.
  - No commitear tokens ni credenciales en el golden dataset.
"""

import argparse
import atexit
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

DATASET_PATH = Path(__file__).parent / "dataset" / "golden_dataset.json"
SEED_DOC_PATH = Path(__file__).parent / "dataset" / "golden_seed.txt"
EVAL_DB_FILENAME = "evals.db"
EVAL_BACKEND_PORT = 8001
API_PREFIX = "/api/v1"
LLM_TIMEOUT = 180.0  # Ollama puede ser lento
CRUD_TIMEOUT = 30.0
DOC_POLL_INTERVAL = 2  # segundos entre polls de estado del documento
DOC_POLL_MAX = 30  # max intentos (~60s)
WIDTH = 90


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #


def _sep(char: str = "=") -> None:
    print(char * WIDTH)


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _warn(msg: str) -> None:
    print(f"  [!!] {msg}")


def _err(msg: str) -> None:
    print(f"  [XX] {msg}")


def _result_line(case_id: str, status: str, duration_ms: int, desc: str) -> None:
    icon = {"PASS": "OK ", "FAIL": "XX ", "SKIP": "-- ", "ERROR": "EE "}.get(
        status,
        "?? ",
    )
    print(f"  [{icon}] {case_id:<12} {status:<5}  {duration_ms:>6}ms  {desc[:52]}")


# --------------------------------------------------------------------------- #
# Backend aislado (standalone mode)
# --------------------------------------------------------------------------- #

_eval_proc: "subprocess.Popen[bytes] | None" = None
_eval_log_path: "Path | None" = None


def _stop_eval_backend() -> None:
    global _eval_proc
    if _eval_proc and _eval_proc.poll() is None:
        _eval_proc.terminate()
        try:
            _eval_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _eval_proc.kill()
    _eval_proc = None


def _kill_port(port: int) -> None:
    """Mata cualquier proceso escuchando en el puerto dado."""
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(
                ["netstat", "-ano"], text=True, errors="replace",
            )
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", pid], capture_output=True,
                    )
        else:
            out = subprocess.check_output(
                ["lsof", f"-ti:{port}"], text=True, errors="replace",
            )
            for pid in out.split():
                subprocess.run(["kill", "-9", pid], capture_output=True)
    except Exception:
        pass


def _init_eval_db(eval_db: Path, backend_dir: Path) -> None:
    """Aplica migraciones Alembic a la DB de evaluación via subproceso.

    Se usa un proceso separado (no el padre) para que DATABASE_URL se resuelva
    correctamente. Si se llamara a alembic.command directamente, env.py leería
    settings.database_url del padre (loremaster.db) e ignoraría la URL de eval.
    Con un subproceso el entorno es limpio y apunta a evals.db.

    Al terminar, la DB está en 'head'; cuando el servidor arranca, la migración
    en lifespan es un no-op instantáneo.
    """
    rel_db = eval_db.relative_to(backend_dir)
    db_url = f"sqlite:///{rel_db.as_posix()}"
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(backend_dir),
        env={**os.environ, "DATABASE_URL": db_url},
        check=True,
    )


def _start_eval_backend(eval_db: Path, port: int) -> str:
    """Arranca un uvicorn aislado apuntando a eval_db. Retorna la base_url."""
    global _eval_proc, _eval_log_path

    # Limpiar estado de ejecuciones anteriores
    _kill_port(port)
    for suffix in ("", "-shm", "-wal"):
        Path(str(eval_db) + suffix).unlink(missing_ok=True)
    time.sleep(0.5)

    backend_dir = Path(__file__).parent.parent  # backend/

    # Pre-inicializar la DB desde el proceso padre (sin asyncio) para que el subprocess
    # encuentre el esquema listo y la migración en lifespan sea un no-op instantáneo.
    _init_eval_db(eval_db, backend_dir)

    # Ruta relativa al cwd (backend/) para que SQLAlchemy la parsee correctamente en Windows
    rel_db = eval_db.relative_to(backend_dir)
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{rel_db.as_posix()}",
        "RATE_LIMIT_ENABLED": "false",
        "PYTHONUNBUFFERED": "1",
        "SKIP_MIGRATIONS": "true",  # migración ya aplicada por _init_eval_db
    }

    # Log a archivo para evitar que el buffer del pipe oculte errores de startup
    _eval_log_path = eval_db.parent / "eval_backend.log"
    log_file = open(_eval_log_path, "wb")  # noqa: SIM115

    _eval_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--port", str(port),
        ],
        cwd=str(backend_dir),
        env=env,
        stdout=log_file,
        stderr=log_file,
    )
    atexit.register(_stop_eval_backend)
    return f"http://127.0.0.1:{port}"


def _show_eval_log(tail: int = 40) -> None:
    """Imprime las últimas líneas relevantes del log del backend eval."""
    if not _eval_log_path or not _eval_log_path.exists():
        return
    try:
        lines = _eval_log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        relevant = [ln for ln in lines if ln.strip() and "Loading weights" not in ln]
        snippet = relevant[-tail:] if len(relevant) > tail else relevant
        if snippet:
            print(f"\n  --- {_eval_log_path.name} (últimas líneas) ---")
            for line in snippet:
                print(f"  {line}")
            print("  ---\n")
    except OSError:
        pass


def _wait_for_backend(base_url: str, timeout: int = 60) -> bool:
    """Espera hasta que /health devuelva 200, el proceso muera, o se agote el timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _eval_proc and _eval_proc.poll() is not None:
            _show_eval_log()
            return False
        try:
            r = httpx.get(f"{base_url}/health", timeout=10)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    _show_eval_log()
    return False


# --------------------------------------------------------------------------- #
# HTTP client
# --------------------------------------------------------------------------- #


class APIClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=LLM_TIMEOUT)
        self._prefix = API_PREFIX

    def _csrf_headers(self) -> dict:
        token = self._client.cookies.get("csrf_token")
        return {"X-CSRF-Token": token} if token else {}

    def _url(self, path: str) -> str:
        return f"{self._prefix}{path}"

    def get(self, path: str, **kw) -> httpx.Response:
        return self._client.get(self._url(path), **kw)

    def post(self, path: str, json=None, **kw) -> httpx.Response:
        kw.setdefault("headers", {}).update(self._csrf_headers())
        return self._client.post(self._url(path), json=json, **kw)

    def patch(self, path: str, json=None, **kw) -> httpx.Response:
        kw.setdefault("headers", {}).update(self._csrf_headers())
        return self._client.patch(self._url(path), json=json, **kw)

    def delete(self, path: str, **kw) -> httpx.Response:
        kw.setdefault("headers", {}).update(self._csrf_headers())
        return self._client.delete(self._url(path), **kw)

    def post_file(self, path: str, file_path: Path) -> httpx.Response:
        with open(file_path, "rb") as f:
            return self._client.post(
                self._url(path),
                files={"file": (file_path.name, f, "text/plain")},
                headers=self._csrf_headers(),
                timeout=CRUD_TIMEOUT,
            )

    def close(self) -> None:
        self._client.close()


# --------------------------------------------------------------------------- #
# Assertion helpers
# --------------------------------------------------------------------------- #

Result = tuple[bool, str]


def ok() -> Result:
    return True, ""


def fail(msg: str) -> Result:
    return False, msg


def check_all(checks: list[Result]) -> Result:
    for passed, msg in checks:
        if not passed:
            return False, msg
    return True, ""


def check_status(actual: int, expected: int) -> Result:
    if actual != expected:
        return False, f"HTTP {actual} != esperado {expected}"
    return True, ""


def check_fields(body: dict, fields: dict) -> list[Result]:
    return [(body.get(k) == v, f"campo '{k}': {body.get(k)!r} != {v!r}") for k, v in fields.items()]


# --------------------------------------------------------------------------- #
# API helpers
# --------------------------------------------------------------------------- #


def create_collection(api: APIClient, name: str) -> tuple[str | None, str]:
    """Crea una colección para la evaluación. Retorna (collection_id, error_msg)."""
    resp = api.post("/collections/", json={"name": name, "description": "Eval run"})
    if resp.status_code == 201:
        return resp.json()["id"], ""
    return None, f"create collection failed: HTTP {resp.status_code}"


def delete_collection(api: APIClient, cid: str) -> None:
    """Elimina una colección de evaluación."""
    api.delete(f"/collections/{cid}")


def ingest_seed(api: APIClient, cid: str, seed_path: Path) -> tuple[bool, str]:
    """Ingesta el documento semilla en la colección indicada."""
    if not seed_path.exists():
        return False, f"seed not found: {seed_path}"
    resp = api.post_file(f"/collections/{cid}/documents", seed_path)
    if resp.status_code not in (200, 201, 202):
        return False, f"ingest HTTP {resp.status_code}: {resp.text[:80]}"
    return True, ""


def wait_for_docs(api: APIClient, cid: str) -> tuple[bool, str]:
    """Espera a que los documentos de una colección terminen de procesarse."""
    for _ in range(DOC_POLL_MAX):
        resp = api.get(f"/collections/{cid}/documents")
        if resp.status_code != 200:
            return False, f"list docs HTTP {resp.status_code}"
        # The list endpoint excludes 'processing' docs, so if we get items it's done
        items = resp.json().get("data", [])
        if items:
            return True, ""
        time.sleep(DOC_POLL_INTERVAL)
    return False, "timeout waiting for document processing"


def create_entity(
    api: APIClient,
    cid: str,
    etype: str,
    name: str,
    description: str = "",
) -> tuple[str | None, str]:
    resp = api.post(
        f"/collections/{cid}/entities",
        json={"type": etype, "name": name, "description": description},
    )
    if resp.status_code == 201:
        return resp.json()["id"], ""
    return None, f"create entity HTTP {resp.status_code}: {resp.text[:80]}"


def generate_content(
    api: APIClient,
    cid: str,
    eid: str,
    category: str,
    query: str,
) -> tuple[str | None, str]:
    resp = api.post(
        f"/collections/{cid}/entities/{eid}/generate/{category}",
        json={"query": query},
    )
    if resp.status_code == 201:
        return resp.json()["id"], ""
    return None, f"generate HTTP {resp.status_code}: {resp.text[:80]}"


def confirm_content(
    api: APIClient,
    cid: str,
    eid: str,
    content_id: str,
) -> tuple[bool, str]:
    resp = api.post(f"/collections/{cid}/entities/{eid}/contents/{content_id}/confirm")
    if resp.status_code == 200:
        return True, ""
    return False, f"confirm HTTP {resp.status_code}"


def discard_content(
    api: APIClient,
    cid: str,
    eid: str,
    content_id: str,
) -> tuple[bool, str]:
    resp = api.patch(f"/collections/{cid}/entities/{eid}/contents/{content_id}/discard")
    if resp.status_code == 200:
        return True, ""
    return False, f"discard HTTP {resp.status_code}"


def list_contents(api: APIClient, cid: str, eid: str, **params) -> httpx.Response:
    return api.get(f"/collections/{cid}/entities/{eid}/contents", params=params)


def get_contents_by_status(
    api: APIClient,
    cid: str,
    eid: str,
    status: str = "all",
    category: str = None,
) -> list[dict]:
    params: dict = {"page_size": 50, "status": status}
    if category:
        params["category"] = category
    resp = list_contents(api, cid, eid, **params)
    if resp.status_code != 200:
        return []
    return resp.json().get("data", [])


def get_latest_pending(
    api: APIClient,
    cid: str,
    eid: str,
    category: str = None,
) -> dict | None:
    items = get_contents_by_status(api, cid, eid, "pending", category)
    return items[0] if items else None


# --------------------------------------------------------------------------- #
# Setup handler — procesa el campo 'setup' de cada caso
# --------------------------------------------------------------------------- #


def apply_setup(
    api: APIClient,
    cid: str,
    setup: dict,
    entity_cache: dict,
) -> tuple[str | None, str | None, str]:
    """Crea entidad + genera/confirma/descarta contenido segun el setup.
    Retorna (entity_id, last_content_id, error_msg).
    """
    if not setup:
        return None, None, ""

    etype = setup.get("entity_type")
    ename = setup.get("entity_name") or setup.get("entity")
    edesc = setup.get("entity_description", "")

    entity_id: str | None = None
    if ename:
        if ename in entity_cache:
            entity_id = entity_cache[ename]
        else:
            entity_id, err = create_entity(api, cid, etype, ename, edesc)
            if err:
                return None, None, f"setup.create_entity: {err}"
            entity_cache[ename] = entity_id

    content_id: str | None = None
    gen_cat = setup.get("generate_category")
    gen_query = setup.get("generate_query", "Query de setup para evaluacion baseline")
    gen_n = setup.get("generate_n", 1)
    gen_n_pending = setup.get("generate_n_pending", 0)
    then = setup.get("then")

    if entity_id and gen_n_pending > 0:
        for _ in range(gen_n_pending):
            content_id, err = generate_content(api, cid, entity_id, gen_cat, gen_query)
            if err:
                return entity_id, None, f"setup.generate_n_pending: {err}"
    elif entity_id and gen_cat:
        for _ in range(gen_n):
            content_id, err = generate_content(api, cid, entity_id, gen_cat, gen_query)
            if err:
                return entity_id, None, f"setup.generate: {err}"
        if then == "confirm" and content_id:
            ok_c, err = confirm_content(api, cid, entity_id, content_id)
            if not ok_c:
                return entity_id, content_id, f"setup.confirm: {err}"
        elif then == "discard" and content_id:
            ok_d, err = discard_content(api, cid, entity_id, content_id)
            if not ok_d:
                return entity_id, content_id, f"setup.discard: {err}"

    return entity_id, content_id, ""


# --------------------------------------------------------------------------- #
# Case runners
# --------------------------------------------------------------------------- #


def _run_rag_query(api: APIClient, cid: str, case: dict) -> Result:
    inp = case.get("input", {})
    exp = case.get("expected", {})

    payload: dict = {"query": inp.get("query", "")}

    resp = api.post(f"/collections/{cid}/query", json=payload)
    checks: list[Result] = [check_status(resp.status_code, exp["http_status"])]

    if resp.status_code == 200:
        body = resp.json()
        if exp.get("has_answer"):
            checks.append((bool(body.get("answer")), "falta campo 'answer'"))
        if "sources_count_gte" in exp:
            sc = body.get("sources_count", 0)
            checks.append(
                (
                    sc >= exp["sources_count_gte"],
                    f"sources_count {sc} < {exp['sources_count_gte']}",
                ),
            )
        if "sources_count_lte" in exp:
            sc = body.get("sources_count", 0)
            checks.append(
                (
                    sc <= exp["sources_count_lte"],
                    f"sources_count {sc} > {exp['sources_count_lte']}",
                ),
            )
        if "answer_min_length" in exp:
            alen = len(body.get("answer", ""))
            checks.append(
                (
                    alen >= exp["answer_min_length"],
                    f"answer len {alen} < {exp['answer_min_length']}",
                ),
            )
        if "answer_contains_any" in exp:
            answer = body.get("answer", "").lower()
            found = any(kw.lower() in answer for kw in exp["answer_contains_any"])
            checks.append(
                (found, f"answer sin ninguno de {exp['answer_contains_any']}"),
            )

    return check_all(checks)


def _run_entity_crud(
    api: APIClient,
    cid: str,
    case: dict,
    entity_cache: dict,
) -> Result:
    action = case.get("action", "create")
    inp = case.get("input", {})
    setup = case.get("setup", {})
    exp = case.get("expected", {})

    entity_id: str | None = None

    if setup:
        entity_id, _, err = apply_setup(api, cid, setup, entity_cache)
        if err:
            return fail(f"setup: {err}")

    if action == "create":
        resp = api.post(
            f"/collections/{cid}/entities",
            json={
                "type": inp["type"],
                "name": inp["name"],
                "description": inp.get("description", ""),
            },
        )
        checks: list[Result] = [check_status(resp.status_code, exp["http_status"])]
        if resp.status_code == 201:
            body = resp.json()
            entity_cache[inp["name"]] = body["id"]
            if "fields" in exp:
                checks += check_fields(body, exp["fields"])
        return check_all(checks)

    if action == "read":
        eid = entity_id or inp.get("entity_id", "00000000-0000-0000-0000-000000000000")
        resp = api.get(f"/collections/{cid}/entities/{eid}")
        checks = [check_status(resp.status_code, exp["http_status"])]
        if resp.status_code == 200:
            body = resp.json()
            if "fields" in exp:
                checks += check_fields(body, exp["fields"])
            for field in exp.get("field_present", []):
                checks.append((field in body, f"falta campo '{field}'"))
        return check_all(checks)

    if action == "update":
        if not entity_id:
            return fail("no entity_id para update")
        resp = api.patch(f"/collections/{cid}/entities/{entity_id}", json=inp)
        return check_status(resp.status_code, exp["http_status"])

    if action == "delete":
        if not entity_id:
            return fail("no entity_id para delete")
        resp = api.delete(f"/collections/{cid}/entities/{entity_id}")
        checks = [check_status(resp.status_code, exp["http_status"])]
        if resp.status_code == 204 and "after_delete" in exp:
            after = exp["after_delete"]
            gr = api.get(f"/collections/{cid}/entities/{entity_id}")
            checks.append(check_status(gr.status_code, after.get("http_status", 404)))
        return check_all(checks)

    if action == "list":
        params: dict = {}
        if "type_filter" in inp:
            params["type"] = inp["type_filter"]
        resp = api.get(f"/collections/{cid}/entities", params=params)
        checks = [check_status(resp.status_code, exp["http_status"])]
        if resp.status_code == 200:
            items = resp.json().get("data", [])
            if "count_gte" in exp:
                checks.append(
                    (
                        len(items) >= exp["count_gte"],
                        f"count {len(items)} < {exp['count_gte']}",
                    ),
                )
            if "all_items_type" in exp:
                wrong = [i for i in items if i.get("type") != exp["all_items_type"]]
                checks.append((not wrong, f"{len(wrong)} items con tipo incorrecto"))
        return check_all(checks)

    return fail(f"action desconocida: {action}")


def _run_entity_content(
    api: APIClient,
    cid: str,
    case: dict,
    entity_cache: dict,
) -> Result:
    inp = case.get("input", {})
    setup = case.get("setup", {})
    action = case.get("action")
    exp = case.get("expected", {})

    etype = inp.get("entity_type") or setup.get("entity_type")
    ename = inp.get("entity_name") or setup.get("entity_name")
    edesc = inp.get("entity_description") or setup.get("entity_description", "")

    if not ename:
        return fail("no entity_name en input ni setup")

    entity_id: str | None
    if ename in entity_cache:
        entity_id = entity_cache[ename]
    else:
        entity_id, err = create_entity(api, cid, etype, ename, edesc)
        if err:
            return fail(f"create entity: {err}")
        entity_cache[ename] = entity_id

    # Procesar setup (generate, confirm, discard, generate_n)
    setup_content_id: str | None = None
    if setup:
        gen_cat = setup.get("generate_category")
        gen_query = setup.get("generate_query", "Query de setup baseline")
        gen_n = setup.get("generate_n", 1)
        gen_n_pending = setup.get("generate_n_pending", 0)
        then = setup.get("then")

        if gen_n_pending > 0:
            for _ in range(gen_n_pending):
                cid_g, err = generate_content(api, cid, entity_id, gen_cat, gen_query)
                if err:
                    return fail(f"setup generate_n_pending: {err}")
            setup_content_id = cid_g
        elif gen_cat:
            for _ in range(gen_n):
                cid_g, err = generate_content(api, cid, entity_id, gen_cat, gen_query)
                if err:
                    return fail(f"setup generate: {err}")
            setup_content_id = cid_g
            if then == "confirm" and setup_content_id:
                ok_c, err = confirm_content(api, cid, entity_id, setup_content_id)
                if not ok_c:
                    return fail(f"setup confirm: {err}")
            elif then == "discard" and setup_content_id:
                ok_d, err = discard_content(api, cid, entity_id, setup_content_id)
                if not ok_d:
                    return fail(f"setup discard: {err}")

    # ── Detectar lista ──────────────────────────────────────────────────────
    is_list = action is None and "query" not in inp and "category" not in inp and ("page" in inp or "page_size" in inp or "category_filter" in inp)
    if is_list:
        params: dict = {
            "page": inp.get("page", 1),
            "page_size": inp.get("page_size", 10),
        }
        if "category_filter" in inp:
            params["category"] = inp["category_filter"]
        resp = list_contents(api, cid, entity_id, **params)
        checks: list[Result] = [check_status(resp.status_code, exp["http_status"])]
        if resp.status_code == 200:
            body = resp.json()
            items = body.get("data", [])
            if exp.get("has_pagination_meta"):
                checks.append(("meta" in body, "falta 'meta' en response"))
            for mf in exp.get("meta_fields", []):
                checks.append((mf in body.get("meta", {}), f"falta meta.{mf}"))
            if "items_count_lte" in exp:
                checks.append(
                    (
                        len(items) <= exp["items_count_lte"],
                        f"items {len(items)} > {exp['items_count_lte']}",
                    ),
                )
            if "all_items_category" in exp:
                wrong = [i for i in items if i.get("category") != exp["all_items_category"]]
                checks.append(
                    (not wrong, f"{len(wrong)} items con categoria incorrecta"),
                )
        return check_all(checks)

    # ── Generar contenido (accion por defecto) ──────────────────────────────
    if action is None:
        category = inp.get("category")
        query = inp.get("query", "")
        resp = api.post(
            f"/collections/{cid}/entities/{entity_id}/generate/{category}",
            json={"query": query},
        )
        checks = [check_status(resp.status_code, exp["http_status"])]
        if resp.status_code == 201:
            body = resp.json()
            if "status" in exp:
                checks.append(
                    (
                        body.get("status") == exp["status"],
                        f"status {body.get('status')!r} != {exp['status']!r}",
                    ),
                )
            if "content_min_length" in exp:
                clen = len(body.get("content", ""))
                checks.append(
                    (
                        clen >= exp["content_min_length"],
                        f"content len {clen} < {exp['content_min_length']}",
                    ),
                )
            if exp.get("has_generated_text_id"):
                checks.append(
                    (bool(body.get("generated_text_id")), "falta generated_text_id"),
                )
            if "was_edited" in exp:
                checks.append(
                    (
                        body.get("was_edited") == exp["was_edited"],
                        f"was_edited {body.get('was_edited')} != {exp['was_edited']}",
                    ),
                )
        return check_all(checks)

    # ── Confirmar ──────────────────────────────────────────────────────────
    if action == "confirm":
        target = setup_content_id or (get_latest_pending(api, cid, entity_id) or {}).get("id")
        if not target:
            return fail("sin contenido pending para confirmar")
        resp = api.post(
            f"/collections/{cid}/entities/{entity_id}/contents/{target}/confirm",
        )
        checks = [check_status(resp.status_code, exp["http_status"])]
        # confirm devuelve EntityResponse; verificamos el status via list
        if resp.status_code == 200 and "fields" in exp:
            confirmed = get_contents_by_status(api, cid, entity_id, "confirmed")
            if confirmed:
                checks += check_fields(confirmed[0], exp["fields"])
        return check_all(checks)

    # ── Descartar ─────────────────────────────────────────────────────────
    if action == "discard":
        target = setup_content_id or (get_latest_pending(api, cid, entity_id) or {}).get("id")
        if not target:
            return fail("sin contenido para descartar")
        resp = api.patch(
            f"/collections/{cid}/entities/{entity_id}/contents/{target}/discard",
        )
        checks = [check_status(resp.status_code, exp["http_status"])]
        if resp.status_code == 200 and "fields" in exp:
            checks += check_fields(resp.json(), exp["fields"])
        return check_all(checks)

    # ── Editar ────────────────────────────────────────────────────────────
    if action == "edit":
        target = setup_content_id or (get_latest_pending(api, cid, entity_id) or {}).get("id")
        if not target:
            confirmed = get_contents_by_status(api, cid, entity_id, "confirmed")
            target = confirmed[0]["id"] if confirmed else None
        if not target:
            return fail("sin contenido para editar")
        resp = api.patch(
            f"/collections/{cid}/entities/{entity_id}/contents/{target}",
            json={"content": inp.get("text", inp.get("content", "Texto editado."))},
        )
        checks = [check_status(resp.status_code, exp["http_status"])]
        if resp.status_code == 200 and "fields" in exp:
            checks += check_fields(resp.json(), exp["fields"])
        return check_all(checks)

    # ── Borrar contenido ──────────────────────────────────────────────────
    if action == "delete_content":
        target = setup_content_id or (get_latest_pending(api, cid, entity_id) or {}).get("id")
        if not target:
            return fail("sin contenido para borrar")
        resp = api.delete(f"/collections/{cid}/entities/{entity_id}/contents/{target}")
        checks = [check_status(resp.status_code, exp["http_status"])]
        if resp.status_code == 204 and exp.get("content_not_in_list"):
            all_items = get_contents_by_status(api, cid, entity_id, "all")
            ids = [i["id"] for i in all_items]
            checks.append((target not in ids, "contenido borrado sigue en el listado"))
        return check_all(checks)

    return fail(f"action desconocida: {action}")


def _run_guardrail(api: APIClient, cid: str, case: dict, entity_cache: dict) -> Result:
    endpoint = case.get("endpoint", "rag_query")
    inp = case.get("input", {})
    exp = case.get("expected", {})

    if endpoint == "rag_query":
        resp = api.post(
            f"/collections/{cid}/query",
            json={"query": inp.get("query", "")},
        )
        return check_status(resp.status_code, exp["http_status"])

    if endpoint == "entity_content":
        etype = inp.get("entity_type")
        ename = inp.get("entity_name")
        edesc = inp.get("entity_description", "")
        category = inp.get("category")
        query = inp.get("query", "")
        if ename not in entity_cache:
            entity_id, err = create_entity(api, cid, etype, ename, edesc)
            if err:
                return fail(f"create entity: {err}")
            entity_cache[ename] = entity_id
        eid = entity_cache[ename]
        resp = api.post(
            f"/collections/{cid}/entities/{eid}/generate/{category}",
            json={"query": query},
        )
        return check_status(resp.status_code, exp["http_status"])

    return fail(f"endpoint desconocido: {endpoint}")


def _run_image_generation(
    api: APIClient,
    cid: str,
    case: dict,
    entity_cache: dict,
) -> Result:
    inp = case.get("input", {})
    setup = case.get("setup", {})
    exp = case.get("expected", {})

    etype = inp.get("entity_type") or setup.get("entity_type")
    ename = inp.get("entity_name") or setup.get("entity_name")
    edesc = inp.get("entity_description") or setup.get("entity_description", "")

    if not ename:
        return fail("no entity_name")

    if ename not in entity_cache:
        entity_id, err = create_entity(api, cid, etype, ename, edesc)
        if err:
            return fail(f"create entity: {err}")
        entity_cache[ename] = entity_id
    entity_id = entity_cache[ename]

    confirmed_content_id: str | None = None
    pending_content_id: str | None = None

    if setup:
        gen_cat = setup.get("generate_category")
        gen_query = setup.get("generate_query", "Setup image generation")
        then = setup.get("then")
        if gen_cat:
            cid_g, err = generate_content(api, cid, entity_id, gen_cat, gen_query)
            if err:
                return fail(f"setup generate: {err}")
            pending_content_id = cid_g
            if then == "confirm":
                ok_c, err = confirm_content(api, cid, entity_id, cid_g)
                if ok_c:
                    confirmed_content_id = cid_g

    content_id: str | None = None
    if inp.get("use_confirmed_content_id") and confirmed_content_id:
        content_id = confirmed_content_id
    elif inp.get("use_pending_content_id") and pending_content_id:
        content_id = pending_content_id
    elif inp.get("content_id") is not None:
        content_id = inp["content_id"]

    # Paso 1: build-prompt (valida content_id y genera auto_prompt via LLM)
    build_payload: dict = {}
    if content_id is not None:
        build_payload["content_id"] = content_id

    build_resp = api.post(
        f"/collections/{cid}/entities/{entity_id}/image-generation/build-prompt",
        json=build_payload,
    )

    # Si build-prompt falló, comparar su status con el esperado directamente
    if build_resp.status_code != 200:
        return check_status(build_resp.status_code, exp["http_status"])

    auto_prompt = build_resp.json().get("auto_prompt", "")

    # Paso 2: generate — envía content_id + prompts obtenidos del build
    gen_resp = api.post(
        f"/collections/{cid}/entities/{entity_id}/image-generation/generate",
        json={
            "content_id": content_id,
            "auto_prompt": auto_prompt,
            "final_prompt": auto_prompt,
            "batch_size": 1,
        },
    )

    checks: list[Result] = [check_status(gen_resp.status_code, exp["http_status"])]

    if gen_resp.status_code == 201:
        body = gen_resp.json()
        images = body.get("images", [])

        if exp.get("has_image_url"):
            has_url = bool(images and images[0].get("image_url"))
            checks.append((has_url, "falta 'image_url' en images[0]"))

        if exp.get("has_visual_prompt"):
            checks.append((bool(auto_prompt), "auto_prompt vacio"))

        if "backend" in exp:
            allowed = exp["backend"] if isinstance(exp["backend"], list) else [exp["backend"]]
            checks.append(
                (
                    body.get("backend") in allowed,
                    f"backend {body.get('backend')!r} no está en {allowed!r}",
                ),
            )

        for kw in exp.get("visual_prompt_contains", []):
            checks.append(
                (kw.lower() in auto_prompt.lower(), f"auto_prompt sin '{kw}'"),
            )

    return check_all(checks)


def _run_share_content(
    api: APIClient,
    cid: str,
    case: dict,
    entity_cache: dict,
) -> Result:
    setup = case.get("setup", {})
    inp = case.get("input", {})
    exp = case.get("expected", {})

    etype = setup.get("entity_type") or inp.get("entity_type")
    ename = setup.get("entity_name") or inp.get("entity_name")
    edesc = setup.get("entity_description", "")

    if not ename:
        return fail("no entity_name en input ni setup")

    entity_id: str | None = entity_cache.get(ename)
    if not entity_id:
        entity_id, err = create_entity(api, cid, etype, ename, edesc)
        if err:
            return fail(f"create entity: {err}")
        entity_cache[ename] = entity_id

    setup_content_id: str | None = None
    gen_cat = setup.get("generate_category")
    gen_query = setup.get("generate_query", "Setup query baseline")
    then = setup.get("then")

    if gen_cat:
        setup_content_id, err = generate_content(
            api,
            cid,
            entity_id,
            gen_cat,
            gen_query,
        )
        if err:
            return fail(f"setup generate: {err}")
        if then == "confirm":
            ok_c, err = confirm_content(api, cid, entity_id, setup_content_id)
            if not ok_c:
                return fail(f"setup confirm: {err}")

    if not setup_content_id:
        return fail("no content_id disponible para compartir")

    shared = inp.get("shared", True)
    resp = api.patch(
        f"/collections/{cid}/entities/{entity_id}/contents/{setup_content_id}/share",
        json={"shared": shared},
    )

    checks: list[Result] = [check_status(resp.status_code, exp["http_status"])]
    if resp.status_code == 200 and "fields" in exp:
        checks += check_fields(resp.json(), exp["fields"])
    return check_all(checks)


def _run_share_image(
    api: APIClient,
    cid: str,
    case: dict,
    entity_cache: dict,
) -> Result:
    inp = case.get("input", {})
    setup = case.get("setup", {})
    exp = case.get("expected", {})

    etype = inp.get("entity_type") or setup.get("entity_type")
    ename = inp.get("entity_name") or setup.get("entity_name")
    edesc = inp.get("entity_description") or setup.get("entity_description", "")

    if not ename:
        return fail("no entity_name")

    entity_id: str | None = entity_cache.get(ename)
    if not entity_id:
        entity_id, err = create_entity(api, cid, etype, ename, edesc)
        if err:
            return fail(f"create entity: {err}")
        entity_cache[ename] = entity_id

    confirmed_content_id: str | None = None
    if setup:
        gen_cat = setup.get("generate_category")
        gen_query = setup.get("generate_query", "Setup image share")
        then = setup.get("then")
        if gen_cat:
            cid_g, err = generate_content(api, cid, entity_id, gen_cat, gen_query)
            if err:
                return fail(f"setup generate: {err}")
            if then == "confirm":
                ok_c, err = confirm_content(api, cid, entity_id, cid_g)
                if ok_c:
                    confirmed_content_id = cid_g

    build_payload: dict = {}
    if inp.get("use_confirmed_content_id") and confirmed_content_id:
        build_payload["content_id"] = confirmed_content_id

    build_resp = api.post(
        f"/collections/{cid}/entities/{entity_id}/image-generation/build-prompt",
        json=build_payload,
    )
    if build_resp.status_code != 200:
        return fail(f"build-prompt HTTP {build_resp.status_code}")

    auto_prompt = build_resp.json().get("auto_prompt", "")

    gen_resp = api.post(
        f"/collections/{cid}/entities/{entity_id}/image-generation/generate",
        json={
            "content_id": confirmed_content_id,
            "auto_prompt": auto_prompt,
            "final_prompt": auto_prompt,
            "batch_size": 1,
        },
    )
    if gen_resp.status_code != 201:
        return fail(f"generate image HTTP {gen_resp.status_code}")

    body = gen_resp.json()
    generation_id = body.get("generation_id")
    images = body.get("images", [])
    if not images:
        return fail("no images en la respuesta de generacion")
    image_id = images[0].get("id")

    shared = inp.get("shared", True)
    resp = api.patch(
        f"/collections/{cid}/entities/{entity_id}/image-generation/{generation_id}/images/{image_id}/share",
        json={"shared": shared},
    )

    checks: list[Result] = [check_status(resp.status_code, exp["http_status"])]
    if resp.status_code == 200 and "fields" in exp:
        checks += check_fields(resp.json(), exp["fields"])
    return check_all(checks)


def _run_full_flow(api: APIClient, cid: str, case: dict, entity_cache: dict) -> Result:
    setup = case.get("setup", {})
    steps = case.get("steps", [])
    exp = case.get("expected", {})

    # Crear entidad del setup si existe
    last_entity_id: str | None = None
    entity_created = False
    if setup:
        etype = setup.get("entity_type")
        ename = setup.get("entity_name")
        edesc = setup.get("entity_description", "")
        if ename:
            if ename not in entity_cache:
                eid, err = create_entity(api, cid, etype, ename, edesc)
                if err:
                    return fail(f"setup create: {err}")
                entity_cache[ename] = eid
            last_entity_id = entity_cache[ename]
            entity_created = True

    # Tracking de contenidos por categoria: category -> [content_id, ...]
    contents_by_cat: dict[str, list[str]] = {}
    last_content_id: str | None = None
    last_entity_name: str | None = None
    image_resp: httpx.Response | None = None
    public_feed_visible: bool | None = None

    for i, step in enumerate(steps):
        action = step.get("action")

        if action == "create_entity":
            eid, err = create_entity(
                api,
                cid,
                step["type"],
                step["name"],
                step.get("description", ""),
            )
            if err:
                return fail(f"step {i} create_entity: {err}")
            entity_cache[step["name"]] = eid
            last_entity_id = eid
            last_entity_name = step["name"]
            entity_created = True

        elif action == "generate":
            cat = step["category"]
            query = step.get("query", "Query de flujo")
            cid_g, err = generate_content(api, cid, last_entity_id, cat, query)
            if err:
                return fail(f"step {i} generate: {err}")
            contents_by_cat.setdefault(cat, []).append(cid_g)
            last_content_id = cid_g

        elif action == "confirm":
            target_spec = step.get("target", "first")
            target: str | None = None
            if target_spec == "first":
                for ids in contents_by_cat.values():
                    if ids:
                        target = ids[0]
                        break
            elif target_spec == "last":
                target = last_content_id
            elif target_spec.endswith("_first"):
                cat_key = target_spec[: -len("_first")]
                ids = contents_by_cat.get(cat_key, [])
                target = ids[0] if ids else None
            if not target:
                return fail(f"step {i} confirm: sin contenido para '{target_spec}'")
            ok_c, err = confirm_content(api, cid, last_entity_id, target)
            if not ok_c:
                return fail(f"step {i} confirm: {err}")

        elif action == "edit":
            target_spec = step.get("target", "last")
            new_text = step.get("new_text", "Texto editado por flujo.")
            target = last_content_id
            if target_spec == "confirmed":
                confirmed = get_contents_by_status(
                    api,
                    cid,
                    last_entity_id,
                    "confirmed",
                )
                target = confirmed[0]["id"] if confirmed else last_content_id
            if not target:
                return fail(f"step {i} edit: sin contenido")
            resp = api.patch(
                f"/collections/{cid}/entities/{last_entity_id}/contents/{target}",
                json={"content": new_text},
            )
            if resp.status_code != 200:
                return fail(f"step {i} edit HTTP {resp.status_code}")
            last_content_id = target

        elif action == "generate_image":
            content_id_for_image: str | None = None
            if step.get("use_confirmed_content"):
                confirmed = get_contents_by_status(
                    api,
                    cid,
                    last_entity_id,
                    "confirmed",
                )
                if confirmed:
                    content_id_for_image = confirmed[0]["id"]

            # Paso 1: build-prompt
            build_payload: dict = {}
            if content_id_for_image:
                build_payload["content_id"] = content_id_for_image

            build_resp = api.post(
                f"/collections/{cid}/entities/{last_entity_id}/image-generation/build-prompt",
                json=build_payload,
            )

            if build_resp.status_code == 200:
                auto_prompt_flow = build_resp.json().get("auto_prompt", "")
                image_resp = api.post(
                    f"/collections/{cid}/entities/{last_entity_id}/image-generation/generate",
                    json={
                        "content_id": content_id_for_image,
                        "auto_prompt": auto_prompt_flow,
                        "final_prompt": auto_prompt_flow,
                        "batch_size": 1,
                    },
                )
            else:
                image_resp = build_resp

        elif action == "share_content":
            confirmed = get_contents_by_status(api, cid, last_entity_id, "confirmed")
            target = confirmed[0]["id"] if confirmed else last_content_id
            if not target:
                return fail(f"step {i} share_content: sin contenido para compartir")
            shared_val = step.get("shared", True)
            resp = api.patch(
                f"/collections/{cid}/entities/{last_entity_id}/contents/{target}/share",
                json={"shared": shared_val},
            )
            if resp.status_code != 200:
                return fail(f"step {i} share_content HTTP {resp.status_code}")

        elif action == "check_public_feed":
            pub_resp = api.get("/public/feed", params={"page_size": 50})
            if pub_resp.status_code != 200:
                return fail(f"step {i} check_public_feed HTTP {pub_resp.status_code}")
            feed_names = [item.get("entity_name") for item in pub_resp.json().get("data", [])]
            public_feed_visible = last_entity_name in feed_names if last_entity_name else False

    # ── Evaluar estado final ──────────────────────────────────────────────
    checks: list[Result] = []

    if "entity_created" in exp:
        checks.append(
            (
                entity_created == exp["entity_created"],
                f"entity_created {entity_created} != {exp['entity_created']}",
            ),
        )

    needs_all = any(
        k in exp
        for k in (
            "confirmed_count",
            "discarded_count",
            "pending_count",
            "active_confirmed_query_contains",
        )
    )
    needs_cat = any(
        k in exp
        for k in (
            "backstory_confirmed_count",
            "backstory_pending_count",
            "extended_description_pending_count",
            "extended_description_discarded_count",
        )
    )

    if (needs_all or needs_cat) and last_entity_id:
        all_items = get_contents_by_status(api, cid, last_entity_id, "all")
        confirmed_all = [i for i in all_items if i.get("status") == "confirmed"]
        discarded_all = [i for i in all_items if i.get("status") == "discarded"]
        pending_all = [i for i in all_items if i.get("status") == "pending"]

        if "confirmed_count" in exp:
            checks.append(
                (
                    len(confirmed_all) == exp["confirmed_count"],
                    f"confirmed {len(confirmed_all)} != {exp['confirmed_count']}",
                ),
            )
        if "discarded_count" in exp:
            checks.append(
                (
                    len(discarded_all) == exp["discarded_count"],
                    f"discarded {len(discarded_all)} != {exp['discarded_count']}",
                ),
            )
        if "pending_count" in exp:
            checks.append(
                (
                    len(pending_all) == exp["pending_count"],
                    f"pending {len(pending_all)} != {exp['pending_count']}",
                ),
            )
        if "active_confirmed_query_contains" in exp:
            kw = exp["active_confirmed_query_contains"]
            found = any(kw in (i.get("query") or "") for i in confirmed_all)
            checks.append((found, f"ningun confirmed con query que contenga '{kw}'"))

        if needs_cat:
            bs_confirmed = [i for i in all_items if i.get("category") == "backstory" and i.get("status") == "confirmed"]
            bs_pending = [i for i in all_items if i.get("category") == "backstory" and i.get("status") == "pending"]
            ed_pending = [i for i in all_items if i.get("category") == "extended_description" and i.get("status") == "pending"]
            ed_discarded = [i for i in all_items if i.get("category") == "extended_description" and i.get("status") == "discarded"]

            if "backstory_confirmed_count" in exp:
                checks.append(
                    (
                        len(bs_confirmed) == exp["backstory_confirmed_count"],
                        f"backstory confirmed {len(bs_confirmed)} != {exp['backstory_confirmed_count']}",
                    ),
                )
            if "backstory_pending_count" in exp:
                checks.append(
                    (
                        len(bs_pending) == exp["backstory_pending_count"],
                        f"backstory pending {len(bs_pending)} != {exp['backstory_pending_count']}",
                    ),
                )
            if "extended_description_pending_count" in exp:
                checks.append(
                    (
                        len(ed_pending) == exp["extended_description_pending_count"],
                        f"ext_desc pending {len(ed_pending)} != {exp['extended_description_pending_count']}",
                    ),
                )
            if "extended_description_discarded_count" in exp:
                checks.append(
                    (
                        len(ed_discarded) == exp["extended_description_discarded_count"],
                        f"ext_desc discarded {len(ed_discarded)} != {exp['extended_description_discarded_count']}",
                    ),
                )

    needs_final = any(k in exp for k in ("final_status", "final_was_edited", "final_text_contains"))
    if needs_final and last_entity_id:
        confirmed = get_contents_by_status(api, cid, last_entity_id, "confirmed")
        item = confirmed[0] if confirmed else None
        if not item:
            all_items = get_contents_by_status(api, cid, last_entity_id, "all")
            item = all_items[0] if all_items else None
        if not item:
            return fail("sin contenido para assertions finales")
        if "final_status" in exp:
            checks.append(
                (
                    item.get("status") == exp["final_status"],
                    f"status {item.get('status')!r} != {exp['final_status']!r}",
                ),
            )
        if "final_was_edited" in exp:
            checks.append(
                (
                    item.get("was_edited") == exp["final_was_edited"],
                    f"was_edited {item.get('was_edited')} != {exp['final_was_edited']}",
                ),
            )
        if "final_text_contains" in exp:
            text = item.get("content", "")
            kw = exp["final_text_contains"]
            checks.append((kw in text, f"texto sin '{kw}'"))

    if image_resp is not None:
        img_status = exp.get("image_http_status", 201)
        checks.append(check_status(image_resp.status_code, img_status))
        if image_resp.status_code == 201:
            ibody = image_resp.json()
            if exp.get("image_has_url"):
                flow_images = ibody.get("images", [])
                has_url = bool(flow_images and flow_images[0].get("image_url"))
                checks.append((has_url, "falta image_url en images[0]"))
            if "image_backend" in exp:
                allowed = exp["image_backend"] if isinstance(exp["image_backend"], list) else [exp["image_backend"]]
                checks.append(
                    (
                        ibody.get("backend") in allowed,
                        f"backend {ibody.get('backend')!r} no está en {allowed!r}",
                    ),
                )
        if "content_status" in exp and last_entity_id:
            confirmed = get_contents_by_status(api, cid, last_entity_id, "confirmed")
            cs = confirmed[0].get("status") if confirmed else None
            checks.append(
                (
                    cs == exp["content_status"],
                    f"content status {cs!r} != {exp['content_status']!r}",
                ),
            )

    if "content_in_public_feed" in exp and public_feed_visible is not None:
        checks.append(
            (
                public_feed_visible == exp["content_in_public_feed"],
                f"content_in_public_feed: visible={public_feed_visible}, expected={exp['content_in_public_feed']}",
            ),
        )

    return check_all(checks) if checks else ok()


# --------------------------------------------------------------------------- #
# Runner principal
# --------------------------------------------------------------------------- #


def run_case(api: APIClient, cid: str, case: dict, entity_cache: dict) -> Result:
    """Ejecuta un caso de prueba del golden dataset contra la API.

    Delega al runner específico según la categoría del caso.
    """
    category = case.get("category")
    try:
        if category == "rag_query":
            return _run_rag_query(api, cid, case)
        if category == "entity_crud":
            return _run_entity_crud(api, cid, case, entity_cache)
        if category == "entity_content":
            return _run_entity_content(api, cid, case, entity_cache)
        if category == "guardrail":
            return _run_guardrail(api, cid, case, entity_cache)
        if category == "image_generation":
            return _run_image_generation(api, cid, case, entity_cache)
        if category == "share_content":
            return _run_share_content(api, cid, case, entity_cache)
        if category == "share_image":
            return _run_share_image(api, cid, case, entity_cache)
        if category == "full_flow":
            return _run_full_flow(api, cid, case, entity_cache)
        return False, f"categoria desconocida: {category}"
    except httpx.TimeoutException:
        return False, "timeout — LLM o servicio no disponible"
    except httpx.ConnectError:
        return False, "connection refused — backend no esta corriendo"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #


def _print_summary(results: list[dict]) -> None:
    _sep()
    print("  RESUMEN POR CATEGORIA")
    _sep("-")
    print(
        f"  {'Categoria':<22} | {'Total':>5} | {'PASS':>5} | {'FAIL':>5} " f"| {'ERROR':>5} | {'SKIP':>5} | {'Pass%':>6}",
    )
    print(f"  {'-'*22}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}-+-{'-'*6}")

    categories = list(dict.fromkeys(r["category"] for r in results))
    for cat in categories:
        cat_rows = [r for r in results if r["category"] == cat]
        total = len(cat_rows)
        n_pass = sum(1 for r in cat_rows if r["status"] == "PASS")
        n_fail = sum(1 for r in cat_rows if r["status"] == "FAIL")
        n_error = sum(1 for r in cat_rows if r["status"] == "ERROR")
        n_skip = sum(1 for r in cat_rows if r["status"] == "SKIP")
        pct = f"{n_pass / total * 100:.0f}%" if total else "N/A"
        print(
            f"  {cat:<22} | {total:>5} | {n_pass:>5} | {n_fail:>5} " f"| {n_error:>5} | {n_skip:>5} | {pct:>6}",
        )

    _sep("-")
    total = len(results)
    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_fail = sum(1 for r in results if r["status"] == "FAIL")
    n_error = sum(1 for r in results if r["status"] == "ERROR")
    n_skip = sum(1 for r in results if r["status"] == "SKIP")
    pct = f"{n_pass / total * 100:.1f}%" if total else "N/A"
    print(
        f"  {'TOTAL':<22} | {total:>5} | {n_pass:>5} | {n_fail:>5} " f"| {n_error:>5} | {n_skip:>5} | {pct:>6}",
    )
    _sep()

    failures = [r for r in results if r["status"] in ("FAIL", "ERROR")]
    if failures:
        print()
        print("  FALLOS DETALLADOS")
        _sep("-")
        for r in failures:
            print(f"  [{r['status']}] {r['id']:<12}  {r['description'][:55]}")
            if r.get("detail"):
                print(f"         => {r['detail']}")
        _sep()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Loremaster Baseline Evaluation — ejecuta el golden dataset contra la API",
    )
    parser.add_argument(
        "--standalone",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Arrancar backend aislado con evals.db (default: True); --no-standalone para usar --base-url",
    )
    parser.add_argument(
        "--eval-port",
        type=int,
        default=EVAL_BACKEND_PORT,
        help=f"Puerto del backend eval aislado (default: {EVAL_BACKEND_PORT})",
    )
    parser.add_argument(
        "--eval-db",
        default=EVAL_DB_FILENAME,
        help=f"Nombre del archivo SQLite de evaluaciones en evaluations/ (default: {EVAL_DB_FILENAME})",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="URL base del backend; solo relevante con --no-standalone (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--username",
        default="eval_runner",
        help="Usuario para login/registro (default: eval_runner)",
    )
    parser.add_argument(
        "--email",
        default="eval_runner@example.com",
        help="Email para registro (default: eval_runner@example.com)",
    )
    parser.add_argument(
        "--password",
        default="eval_password_123",
        help="Contraseña para login/registro (default: eval_password_123)",
    )
    parser.add_argument(
        "--categories",
        nargs="*",
        help="Ejecutar solo estas categorias (ej: rag_query guardrail)",
    )
    parser.add_argument(
        "--ids",
        nargs="*",
        help="Ejecutar solo estos IDs de caso (ej: RAG-001 CHAR-005)",
    )
    parser.add_argument(
        "--keep-collection",
        action="store_true",
        help="No borrar la coleccion al finalizar",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Omitir la ingestion del documento semilla",
    )
    args = parser.parse_args()

    # Resolver base_url según el modo
    if args.standalone:
        args.base_url = f"http://127.0.0.1:{args.eval_port}"
    elif args.base_url is None:
        args.base_url = "http://localhost:8000"

    # ── Cargar dataset ──────────────────────────────────────────────────────
    if not DATASET_PATH.exists():
        _err(f"Dataset no encontrado: {DATASET_PATH}")
        sys.exit(1)
    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    all_cases: list[dict] = dataset.get("cases", [])
    if args.categories:
        all_cases = [c for c in all_cases if c.get("category") in args.categories]
    if args.ids:
        all_cases = [c for c in all_cases if c.get("id") in args.ids]

    _sep()
    print("  LOREMASTER -- BASELINE EVALUATION")
    print(
        f"  Dataset  : {DATASET_PATH.name}  ({len(dataset.get('cases', []))} casos totales)",
    )
    print(f"  Ejecutar : {len(all_cases)} casos")
    print(f"  Base URL : {args.base_url}")
    if args.standalone:
        eval_db = (Path(__file__).parent / args.eval_db).resolve()
        print(f"  DB eval  : {eval_db}")
    _sep()

    # ── Arrancar backend aislado si corresponde ─────────────────────────────
    if args.standalone:
        _ok(f"Arrancando backend eval en :{args.eval_port} con {eval_db.name}...")
        _start_eval_backend(eval_db, args.eval_port)
        if not _wait_for_backend(args.base_url, timeout=60):
            _err("El backend eval no respondio en 60s. Revisa logs o el SECRET_KEY en .env.")
            sys.exit(1)
        _ok("Backend eval listo.")

    # ── Verificar backend (sin auth) ────────────────────────────────────────
    probe = httpx.Client(base_url=args.base_url, timeout=5)
    try:
        health = probe.get("/health")
        if health.status_code != 200:
            _err(f"Backend no disponible: HTTP {health.status_code}")
            sys.exit(1)
        _ok("Backend disponible")
    except Exception as exc:
        _err(f"No se puede conectar al backend: {exc}")
        sys.exit(1)
    finally:
        probe.close()

    # ── Autenticar via cookies HttpOnly (H-13/H-14) ─────────────────────────
    api = APIClient(args.base_url)
    login_creds = {"username_or_email": args.username, "password": args.password}
    register_creds = {
        "username": args.username,
        "email": args.email,
        "password": args.password,
    }
    try:
        resp = api.post("/auth/login", json=login_creds)
        if resp.status_code == 200:
            _ok(f"Login OK como '{args.username}'")
        elif resp.status_code in (401, 422):
            resp = api.post("/auth/register", json=register_creds)
            if resp.status_code == 200:
                _ok(f"Usuario '{args.username}' registrado y autenticado")
            else:
                _err(f"No se pudo registrar el usuario: HTTP {resp.status_code}")
                api.close()
                sys.exit(1)
        else:
            _err(f"Error de autenticacion: HTTP {resp.status_code}")
            api.close()
            sys.exit(1)
    except Exception as exc:
        _err(f"Error obteniendo token: {exc}")
        api.close()
        sys.exit(1)

    # ── Crear coleccion ─────────────────────────────────────────────────────
    collection_name = f"Eval Baseline {int(time.time())}"
    cid, err = create_collection(api, collection_name)
    if err:
        _err(f"No se pudo crear la coleccion: {err}")
        sys.exit(1)
    _ok(f"Coleccion creada: '{collection_name}' (id={cid[:8]}...)")

    # ── Ingestar documento semilla ──────────────────────────────────────────
    if not args.no_seed:
        ingested, err = ingest_seed(api, cid, SEED_DOC_PATH)
        if not ingested:
            _warn(f"Seed no ingestado: {err}")
            _warn("Los casos RAG y de generacion pueden fallar por falta de contexto")
        else:
            _ok(f"Documento semilla enviado ({SEED_DOC_PATH.name})")
            print("  Esperando procesamiento del documento...", end=" ", flush=True)
            ready, err = wait_for_docs(api, cid)
            if ready:
                print("listo.")
            else:
                print(f"\n  [!!] {err}")
    else:
        _warn("Ingestion del seed omitida (--no-seed)")

    print()
    _sep("-")
    print(f"  {'ID':<13} {'STATUS':<5}  {'ms':>6}  Descripcion")
    _sep("-")

    # ── Ejecutar casos ──────────────────────────────────────────────────────
    results: list[dict] = []
    entity_cache: dict[str, str] = {}

    for case in all_cases:
        case_id = case.get("id", "?")
        desc = case.get("description", "")
        category = case.get("category", "")

        t0 = time.monotonic()
        passed, detail = run_case(api, cid, case, entity_cache)
        duration_ms = int((time.monotonic() - t0) * 1000)

        status = "PASS" if passed else "FAIL"
        _result_line(case_id, status, duration_ms, desc)
        if not passed and detail:
            print(f"         => {detail}")

        results.append(
            {
                "id": case_id,
                "category": category,
                "description": desc,
                "status": status,
                "detail": detail if not passed else "",
                "duration_ms": duration_ms,
            },
        )

    # ── Cleanup ─────────────────────────────────────────────────────────────
    print()
    if args.keep_collection:
        _warn(f"Coleccion conservada: {cid} (--keep-collection)")
    else:
        delete_collection(api, cid)
        _ok("Coleccion de evaluacion eliminada")

    api.close()

    if args.standalone:
        _stop_eval_backend()
        _ok("Backend eval detenido.")

    # ── Resumen ─────────────────────────────────────────────────────────────
    print()
    _print_summary(results)

    n_fail = sum(1 for r in results if r["status"] in ("FAIL", "ERROR"))
    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
