"""Cliente para RunPod Serverless API.

Backend alternativo de generación de imágenes. Envía workflows ComfyUI
al endpoint serverless de RunPod y recupera las imágenes resultantes.

RunPod Serverless API (v2):
  POST /v2/{endpoint_id}/run          → encola un job async
  GET  /v2/{endpoint_id}/status/{id}  → consulta estado y resultado

Estados de job: IN_QUEUE → IN_PROGRESS → COMPLETED | FAILED | CANCELLED

Arranque en frío: ~15-30 s si el worker estaba idle.

TODO: integrar en _backends.py cuando se active IMAGE_BACKEND=runpod.
"""

import time

import httpx

_RUNPOD_BASE_URL = "https://api.runpod.io/v2"

# Estados terminales del job (polling para cuando dejar de esperar)
_TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED"}


class RunPodClient:
    """Cliente HTTP para la API Serverless de RunPod."""

    def __init__(
        self,
        api_key: str,
        endpoint_id: str,
        request_timeout: float = 30.0,
    ) -> None:
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
            NotImplementedError: Pendiente de implementación

        TODO: confirmar el campo "input" exacto que espera el worker RunPod elegido.
              Con el template oficial de ComfyUI, el payload suele ser:
              { "input": { "workflow": <workflow_dict> } }
              Verificar en el dashboard de RunPod → Endpoint → Request Schema.
        """
        raise NotImplementedError(
            "RunPodClient.submit_workflow — pendiente de implementación. "
            "Ver TODO en el docstring."
        )

    def get_status(self, job_id: str) -> dict:
        """Consulta el estado actual de un job.

        Returns:
            Dict con al menos:
            - "status": "IN_QUEUE" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "CANCELLED"
            - "output": resultado del worker (solo si status="COMPLETED")
            - "error": mensaje de error (solo si status="FAILED")

        TODO: implementar junto con submit_workflow.
              Endpoint: GET /v2/{endpoint_id}/status/{job_id}
        """
        raise NotImplementedError(
            "RunPodClient.get_status — pendiente de implementación."
        )

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

        TODO: implementar junto con get_status().
              Nota: el arranque en frío de RunPod tarda 15-30 s en el primer job.
              El timeout por defecto (300 s) cubre ese caso.
        """
        raise NotImplementedError(
            "RunPodClient.wait_for_completion — pendiente de implementación."
        )

    def extract_image_bytes(self, job_result: dict) -> list[bytes]:
        """Extrae los bytes de imagen del resultado de un job completado.

        Args:
            job_result: Resultado de wait_for_completion() con status="COMPLETED"

        Returns:
            Lista de bytes de imagen (una por imagen generada en el batch)

        TODO: el formato de salida depende del worker RunPod elegido:
          - Worker ComfyUI oficial: suele devolver imágenes como base64 en "output.images"
          - Worker personalizado: verificar el schema de salida en el dashboard
          Decodificar con: bytes_data = base64.b64decode(img["image"])
        """
        raise NotImplementedError(
            "RunPodClient.extract_image_bytes — pendiente de implementación. "
            "El formato de salida depende del worker elegido en RunPod."
        )


def build_runpod_client() -> "RunPodClient":
    """Instancia RunPodClient con la config actual de Settings.

    Raises:
        ValueError: Si RUNPOD_API_KEY o RUNPOD_ENDPOINT_ID no están configurados.

    TODO: llamar desde _backends._generate_runpod_images() cuando IMAGE_BACKEND=runpod.
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
