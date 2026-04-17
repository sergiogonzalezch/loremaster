export function getErrorMessage(error: unknown, fallback = "Error inesperado"): string {
  return error instanceof Error ? error.message : fallback;
}

export function parseApiError(error: unknown): { variant: "warning" | "danger"; text: string } {
  const msg = getErrorMessage(error, "Error desconocido");
  if (msg.includes("422") || msg.toLowerCase().includes("unprocessable")) {
    return { variant: "warning", text: "No hay documentos en esta colección. Sube documentos primero." };
  }
  if (msg.includes("503") || msg.toLowerCase().includes("unavailable")) {
    return { variant: "danger", text: "El servicio de generación no está disponible." };
  }
  return { variant: "danger", text: msg };
}