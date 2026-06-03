"""Cliente para RunPod Serverless API.

Backend alternativo de generación de imágenes. Envía workflows ComfyUI
al endpoint serverless de RunPod y recupera las imágenes resultantes.

RunPod Serverless API (v2):
  POST /v2/{endpoint_id}/run          → encola un job async
  GET  /v2/{endpoint_id}/status/{id}  → consulta estado y resultado

Estados de job: IN_QUEUE → IN_PROGRESS → COMPLETED | FAILED | CANCELLED

Arranque en frío: ~15-30 s si el worker estaba idle.

Integrado en services/image/_backends._generate_runpod_images cuando
IMAGE_BACKEND=runpod. Diseñado para el worker-comfyui oficial de RunPod.
"""

import base64
import time

import httpx

_RUNPOD_BASE_URL = "https://api.runpod.ai/v2"

# Estados terminales del job (polling para cuando dejar de esperar)
_TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED"}

# Tope de tamaño por imagen descargada/decodificada (defensa ante respuestas
# inesperadamente grandes que podrían agotar la memoria del proceso).
_MAX_IMAGE_BYTES = 25 * 1024 * 1024  # 25 MB


class RunPodClient:
    """Cliente HTTP para la API Serverless de RunPod."""

    def __init__(
        self,
        api_key: str,
        endpoint_id: str,
        request_timeout: float = 30.0,
    ) -> None:
        """Inicializa el cliente con la API key, el endpoint y el timeout por request."""
        self._endpoint_id = endpoint_id
        self._request_timeout = request_timeout
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{_RUNPOD_BASE_URL}/{self._endpoint_id}/{path.lstrip('/')}"
        with httpx.Client(timeout=self._request_timeout) as client:
            response = client.request(method, url, headers=self._headers, **kwargs)
            response.raise_for_status()
            return response

    def submit_workflow(self, workflow: dict) -> str:
        """Encola un workflow ComfyUI para ejecución serverless.

        Args:
            workflow: Workflow en formato API de ComfyUI (mismo formato que
                      ComfyUIClient.queue_prompt — generado por inject_prompt/inject_seed)

        Returns:
            job_id: ID del job para tracking posterior con get_status()

        Raises:
            httpx.HTTPStatusError: Si RunPod rechaza el request
            RuntimeError: Si la respuesta no contiene un job id

        Payload del worker-comfyui oficial: { "input": { "workflow": <dict> } }
        Respuesta de POST /run: { "id": "<job_id>", "status": "IN_QUEUE" }
        """
        response = self._request("POST", "run", json={"input": {"workflow": workflow}})
        data = response.json()

        job_id = data.get("id")
        if not job_id:
            msg = f"RunPod no devolvió un job id: {data}"
            raise RuntimeError(msg)
        return job_id

    def get_status(self, job_id: str) -> dict:
        """Consulta el estado actual de un job.

        Returns:
            Dict con al menos:
            - "status": "IN_QUEUE" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "CANCELLED"
            - "output": resultado del worker (solo si status="COMPLETED")
            - "error": mensaje de error (solo si status="FAILED")

        Endpoint: GET /v2/{endpoint_id}/status/{job_id}
        """
        response = self._request("GET", f"status/{job_id}")
        return response.json()

    def wait_for_completion(
        self,
        job_id: str,
        timeout: int = 300,
        poll_interval: float = 3.0,
    ) -> dict:
        """Espera hasta que el job complete (polling).

        Args:
            job_id: ID devuelto por submit_workflow()
            timeout: Segundos máximos de espera total (default 300 = 5 min)
            poll_interval: Segundos entre consultas (default 3.0)
                           Usar ≥3 s para no sobrecargar la API de RunPod.

        Returns:
            Resultado de get_status() cuando status="COMPLETED"

        Raises:
            TimeoutError: Si se supera el timeout
            RuntimeError: Si el job falla o es cancelado

        Nota: el arranque en frío de RunPod tarda 15-30 s en el primer job.
        El timeout por defecto (300 s) cubre ese caso.
        """
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                msg = f"Timeout después de {timeout}s esperando el job RunPod {job_id}"
                raise TimeoutError(msg)

            result = self.get_status(job_id)
            status = result.get("status")

            if status == "COMPLETED":
                return result

            if status in _TERMINAL_STATUSES:  # FAILED | CANCELLED
                error = result.get("error", "error desconocido")
                msg = f"Job RunPod {job_id} terminó en {status}: {error}"
                raise RuntimeError(msg)

            time.sleep(poll_interval)

    def extract_image_bytes(self, job_result: dict) -> list[bytes]:
        """Extrae los bytes de imagen del resultado de un job completado.

        Args:
            job_result: Resultado de wait_for_completion() con status="COMPLETED"

        Returns:
            Lista de bytes de imagen (una por imagen generada en el batch)

        Raises:
            RuntimeError: Si el job no contiene imágenes decodificables.

        Formato del worker-comfyui oficial:
            output.images = [ { "filename": ..., "type": "base64", "data": "<b64>" } ]
        Si el worker está configurado para subir a S3, "type" es "s3_url"/"url" y
        "data" es la URL pública; en ese caso se descarga el contenido.
        """
        output = job_result.get("output") or {}
        images = output.get("images", [])

        result: list[bytes] = []
        for img in images:
            data = img.get("data")
            if not data:
                continue

            if img.get("type") in ("s3_url", "url"):
                result.append(self._download_image_url(data))
            else:  # base64 (default)
                raw = base64.b64decode(data)
                if len(raw) > _MAX_IMAGE_BYTES:
                    msg = f"Imagen RunPod excede el tamaño máximo ({_MAX_IMAGE_BYTES} bytes)"
                    raise RuntimeError(msg)
                result.append(raw)

        if not result:
            msg = f"Job RunPod completado pero sin imágenes: {job_result}"
            raise RuntimeError(msg)
        return result

    def _download_image_url(self, url: str) -> bytes:
        """Descarga una imagen desde una URL devuelta por el worker (modo S3).

        Defensa en profundidad: exige https (bloquea http a hosts internos/metadata)
        y corta la descarga si supera _MAX_IMAGE_BYTES. La URL proviene de la
        respuesta de RunPod, pero se valida igualmente.

        Raises:
            RuntimeError: Si la URL no es https o la imagen excede el tamaño máximo.
            httpx.HTTPError: Si la descarga falla.
        """
        if not url.lower().startswith("https://"):
            msg = f"URL de imagen RunPod no es https: {url[:60]}"
            raise RuntimeError(msg)

        with httpx.Client(timeout=self._request_timeout) as client, client.stream("GET", url) as resp:
            resp.raise_for_status()
            chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_bytes():
                total += len(chunk)
                if total > _MAX_IMAGE_BYTES:
                    msg = f"Imagen RunPod excede el tamaño máximo ({_MAX_IMAGE_BYTES} bytes)"
                    raise RuntimeError(msg)
                chunks.append(chunk)
            return b"".join(chunks)


def build_runpod_client() -> "RunPodClient":
    """Instancia RunPodClient con la config actual de Settings.

    Raises:
        ValueError: Si RUNPOD_API_KEY o RUNPOD_ENDPOINT_ID no están configurados.
    """
    from app.core.config import settings  # import local para evitar ciclo en tests

    if not settings.runpod_api_key:
        msg = "RUNPOD_API_KEY es requerido cuando IMAGE_BACKEND=runpod"
        raise ValueError(msg)
    if not settings.runpod_endpoint_id:
        msg = "RUNPOD_ENDPOINT_ID es requerido cuando IMAGE_BACKEND=runpod"
        raise ValueError(msg)

    return RunPodClient(
        api_key=settings.runpod_api_key,
        endpoint_id=settings.runpod_endpoint_id,
        request_timeout=settings.comfyui_request_timeout,
    )
