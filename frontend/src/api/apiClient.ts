/**
 * Cliente HTTP base para la API del backend.
 *
 * Envuelve `fetch` con manejo de token JWT, mensajes de error por código HTTP
 * y redirección automática al login en caso de 401.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

/** Lee el token CSRF de las cookies del navegador. */
function getCsrfToken(): string | null {
  const match = document.cookie.match(
    new RegExp("(^| )" + "csrf_token" + "=([^;]+)"),
  );
  return match ? decodeURIComponent(match[2]) : null;
}

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

/** Error lanzado cuando la API retorna una respuesta no exitosa. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Error lanzado cuando una solicitud es cancelada mediante AbortController. */
export class ApiAbortError extends Error {
  constructor() {
    super("Solicitud cancelada");
    this.name = "ApiAbortError";
  }
}

/**
 * Ejecuta una petición fetch contra la API del backend.
 *
 * El token JWT se transporta automaticamente via cookie HttpOnly.
 * Para mutaciones (POST/PUT/PATCH/DELETE) agrega el header X-CSRF-Token.
 * Usa credentials="include" para enviar cookies cross-origin.
 *
 * En respuesta 401 redirige al login.
 * En respuestas de error extrae el mensaje del body o usa uno por código HTTP.
 *
 * @param endpoint - Ruta relativa de la API (ej: `/collections/`)
 * @param options - Opciones de fetch adicionales
 * @returns Promise con el body JSON parseado al tipo T
 * @throws ApiError si la respuesta no es exitosa
 * @throws ApiAbortError si la solicitud fue cancelada
 */
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

  // CSRF token para mutaciones (POST/PUT/PATCH/DELETE)
  const method = options.method?.toUpperCase() ?? "GET";
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) {
      headers["X-CSRF-Token"] = csrf;
    }
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers,
      credentials: "include",
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiAbortError();
    }
    throw err;
  }

  if (response.status === 401) {
    const isAlreadyOnLogin = window.location.pathname === "/login";
    if (!isAlreadyOnLogin) {
      // 401 fuera de /login = sesión expirada; navegar sin full-reload via evento
      window.dispatchEvent(new CustomEvent("auth:unauthorized"));
      throw new ApiError(401, "Sesión expirada. Inicia sesión de nuevo.");
    }
    // 401 en /login = credenciales incorrectas (login fallido)
    let message = "Usuario o contraseña incorrectos.";
    try {
      const body = await response.json();
      if (typeof body?.detail === "string" && body.detail.trim()) {
        message = body.detail;
      }
    } catch {
      // cuerpo no parseable — mantener mensaje por defecto
    }
    throw new ApiError(401, message);
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
