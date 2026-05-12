"""Cliente HTTP para la API de ComfyUI.

Endpoints utilizados:
- POST /prompt → Envía workflow en formato API para ejecución
- GET /history/{prompt_id} → Consulta estado y resultados
- GET /view → Descarga imágenes generadas

El template debe estar en formato API (Export API desde ComfyUI con Developer Mode).
"""

import json
import re
import time
from pathlib import Path

import httpx


def _sanitize_filename(name: str) -> str:
    """Elimina caracteres que podrían permitir path traversal."""
    return re.sub(r"[^\w\-.]", "", name)


class ComfyUIClient:
    """Cliente para interactuar con la API REST de ComfyUI."""

    def __init__(self, base_url: str):
        """Inicializa el cliente con la URL base del servidor ComfyUI."""
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Ejecuta una petición HTTP contra la API de ComfyUI."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client(timeout=30.0) as client:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

    def queue_prompt(self, workflow: dict) -> str:
        """Envía un workflow en formato API para ejecución.

        Args:
            workflow: Workflow en formato API (dict con IDs de nodo como claves string)

        Returns:
            prompt_id: ID de la ejecución para tracking

        Raises:
            httpx.HTTPStatusError: Si el workflow es inválido o ComfyUI rechaza la petición
        """

        response = self._request(
            "POST",
            "prompt",
            json={"prompt": workflow},
        )
        data = response.json()

        if "prompt_id" in data:
            return data["prompt_id"]

        if "node_errors" in data:
            raise RuntimeError(f"Errores en nodos:{data['node_errors']}")

        raise RuntimeError(f"Respuesta inesperada de ComfyUI: {data}")

    def get_history(self, prompt_id: str) -> dict:
        """Obtiene el estado y resultados de una ejecución.

        Devuelve dict con:
        - status: "queued" | "running" | "completed" | "failed"
        - outputs: {node_id: {"images": [...]}} si completado
        - error: mensaje de error si falló
        """

        response = self._request("GET", f"history/{prompt_id}")
        data = response.json()

        if prompt_id not in data:
            return {"status": "queued", "outputs": {}}

        entry = data[prompt_id]
        status_str = entry.get("status", {}).get("status_str", "")

        if status_str == "success":
            return {"status": "completed", "outputs": entry.get("outputs", {})}

        if status_str == "error":
            messages = entry.get("status", {}).get("messages", [])
            return {"status": "failed", "error": str(messages)}

        return {"status": "running", "outputs": {}}

    def get_history_until_complete(
        self, prompt_id, timeout: int = 300, poll_interval: float = 2.0
    ) -> dict:
        """Espera hasta que la ejecución complete (polling).

        Args:
            prompt_id: ID del prompt
            timeout: Timeout máximo en segundos (default 300 = 5 min)
            poll_interval: Intervalo de polling en segundos (default 2)

        Returns:
            Resultado de get_history() cuando status="completed"

        Raises:
            TimeoutError: Si excede el timeout
            RuntimeError: Si la ejecución falla
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Timeout después de {timeout}s esperando generación ComfyUI"
                )
            result = self.get_history(prompt_id)
            status = result.get("status", "queued")

            if status == "completed":
                return result

            if status == "failed":
                raise RuntimeError(
                    f"Generación falló: {result.get('error','Unknown error')}"
                )
            time.sleep(poll_interval)

    def download_image(
        self, filename: str, subfolder: str = "", folder_type: str = "output"
    ) -> bytes:
        """Descarga una imagen generada.

        Args:
            filename: Nombre del archivo (del history)
            subfolder: Subcarpeta donde se guardó (del history)
            folder_type: "output", "input" o "temp" (default: "output")

        Returns:
            Bytes de la imagen
        """
        safe_filename = _sanitize_filename(filename)
        safe_subfolder = _sanitize_filename(subfolder)
        params = {"filename": safe_filename, "type": folder_type}
        if safe_subfolder:
            params["subfolder"] = safe_subfolder

        response = self._request("GET", "view", params=params)
        return response.content

    def get_output_images(self, history_result: dict) -> list[dict]:
        """Extrae las imágenes generadas del resultado del history.

        Args:
            history_result: Resultado de get_history() con status="completed"

        Returns:
            Lista de dicts con: {"filename", "subfolder", "type", "node_id"}
        """
        outputs = history_result.get("outputs", {})
        images = []

        for node_id, node_output in outputs.items():
            if "images" in node_output:
                images.extend(
                    {
                        "filename": img.get("filename"),
                        "subfolder": img.get("subfolder", ""),
                        "type": img.get("type", "output"),
                        "node_id": node_id,
                    }
                    for img in node_output["images"]
                )

        return images

    # ── Funciones auxiliares para el template ───────────────────────────────────────────────


def load_template(template_name: str) -> dict:
    """Carga un template de workflow de ComfyUI en formato API desde JSON.

    Args:
        template_name: Nombre del archivo template (sin path). Debe ser formato API.

    Returns:
        Workflow JSON como dict

    Raises:
        FileNotFoundError: Si el template no existe
    """
    template_dir = Path(__file__).parent.parent / "domain" / "templates"
    template_path = template_dir / template_name

    if not template_path.exists():
        raise FileNotFoundError(f"Template no encontrado: {template_path}")

    with template_path.open(encoding="utf-8") as f:
        return json.load(f)


def inject_seed(workflow: dict, seed: int) -> dict:
    """Inyecta un seed fijo en el nodo 104 (RandomNoise).

    Sin esto, múltiples llamadas a queue_prompt con el mismo workflow
    producen la misma imagen (el seed de la plantilla no varía vía API).
    """
    workflow = json.loads(json.dumps(workflow))
    node = workflow.get("104")
    if node is not None:
        node["inputs"]["noise_seed"] = seed
        node["inputs"]["control_after_generate"] = "fixed"
    return workflow


def inject_prompt(workflow: dict, prompt: str) -> dict:
    """Inyecta el prompt en el nodo 12 (PrimitiveStringMultiline) del workflow.

    El template debe estar en formato API de ComfyUI. En este formato, los nodos
    son claves string y el prompt se inyecta en inputs["value"], no en widgets_values.

    Args:
        workflow: Workflow en formato API (dict con claves string de IDs de nodo)
        prompt: Prompt del usuario a inyectar

    Returns:
        Copia del workflow con el prompt inyectado

    Raises:
        ValueError: Si el nodo 12 no existe en el template
    """
    workflow = json.loads(json.dumps(workflow))  # deep copy

    node = workflow.get("12")
    if node is None:
        raise ValueError(
            "Nodo 12 (PrimitiveStringMultiline) no encontrado en el template. "
            "Verificar que el template esté en formato API (ver Sección 0)."
        )

    node["inputs"]["value"] = prompt
    return workflow
