const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

const HTTP_STATUS_MESSAGES: Partial<Record<number, string>> = {
  400: "La solicitud contiene datos inválidos.",
  401: "No tienes permiso para realizar esta acción.",
  403: "Acceso denegado.",
  404: "El recurso solicitado no existe.",
  409: "Ya existe un elemento con esos datos.",
  413: "El archivo es demasiado grande.",
  422: "Los datos enviados no son válidos.",
  429: "Demasiadas solicitudes. Inténtalo de nuevo en un momento.",
  500: "Error interno del servidor. Inténtalo de nuevo más tarde.",
  502: "El servidor no está disponible temporalmente.",
  503: "El servicio no está disponible. Inténtalo de nuevo más tarde.",
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ApiAbortError extends Error {
  constructor() {
    super("Solicitud cancelada");
    this.name = "ApiAbortError";
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${endpoint}`, { ...options, headers });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiAbortError();
    }
    throw err;
  }

  if (!response.ok) {
    // Fallback descriptivo por código — se sobreescribe si el backend envía detail
    let message =
      HTTP_STATUS_MESSAGES[response.status] ??
      "Error inesperado. Inténtalo de nuevo más tarde.";
    try {
      const body = await response.json();
      // Solo usar detail cuando es un string; los arrays de validación de FastAPI
      // (422 con [{type, loc, msg}]) no son legibles para el usuario
      if (typeof body?.detail === "string" && body.detail.trim()) {
        message = body.detail;
      }
    } catch {
      // cuerpo no parseable — mantener el mensaje por código
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
