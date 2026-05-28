/**
 * Cliente HTTP base para la API del backend.
 *
 * Envuelve `fetch` con manejo de token JWT, mensajes de error por código HTTP
 * y redirección automática al login en caso de 401.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

// Endpoints que no deben intentar refresh al recibir 401 (evita bucles)
const NO_REFRESH_ENDPOINTS = new Set(["/auth/login", "/auth/refresh"]);

/**
 * Promesa singleton del refresh en vuelo. Si varias peticiones reciben 401
 * concurrentemente (caso común con N llamadas paralelas tras expirar el
 * access token), todas comparten la misma promesa de refresh en vez de
 * disparar N POST /auth/refresh independientes.
 */
let _refreshPromise: Promise<boolean> | null = null;

/** Intenta rotar el access token llamando a POST /auth/refresh.
 * Coalesce llamadas concurrentes en una única request al backend.
 */
async function _tryRefresh(): Promise<boolean> {
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = (async () => {
    try {
      const res = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        // No enviamos X-CSRF-Token: /auth/* está exento en el backend y
        // así evitamos coupling con el CSRF que podría estar caducado.
      });
      return res.ok;
    } catch {
      return false;
    } finally {
      // Liberar el singleton para permitir refreshes futuros cuando el
      // access vuelva a expirar.
      _refreshPromise = null;
    }
  })();

  return _refreshPromise;
}

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
  _isRetry = false,
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
    const isOnLogin = window.location.pathname === "/login";

    // En /login el 401 es por credenciales incorrectas, no por token expirado
    if (isOnLogin) {
      let message = "Usuario o contraseña incorrectos.";
      try {
        const body = await response.json();
        if (typeof body?.detail === "string" && body.detail.trim())
          message = body.detail;
      } catch {
        /* body no parseable */
      }
      throw new ApiError(401, message);
    }

    // Fuera de /login: intentar refresh una vez antes de redirigir al login
    if (!_isRetry && !NO_REFRESH_ENDPOINTS.has(endpoint)) {
      const refreshed = await _tryRefresh();
      if (refreshed) {
        // Refresh exitoso — reintentar la petición original con los nuevos tokens
        return apiFetch<T>(endpoint, options, true);
      }
    }

    // Refresh fallido o segundo intento: sesión expirada definitivamente
    window.dispatchEvent(new CustomEvent("auth:unauthorized"));
    throw new ApiError(401, "Sesión expirada. Inicia sesión de nuevo.");
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
