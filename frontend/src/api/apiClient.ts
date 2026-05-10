/**
 * Cliente HTTP base para la API del backend.
 *
 * Envuelve `fetch` con manejo de token JWT, mensajes de error por código HTTP
 * y redirección automática al login en caso de 401.
 */

import { getToken, removeToken } from "../utils/token";

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
 * Agrega automáticamente el header Authorization con el token JWT
 * y el Content-Type cuando el body no es FormData.
 *
 * En respuesta 401 elimina el token y redirige al login.
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
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
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

  if (response.status === 401) {
    removeToken();
    const isAlreadyOnLogin = window.location.pathname === "/login";
    if (!isAlreadyOnLogin) {
      window.location.href = "/login";
    }
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
