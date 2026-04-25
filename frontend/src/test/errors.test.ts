import { describe, it, expect } from "vitest";
import { ApiError } from "../api/apiClient";
import { getErrorMessage, parseApiError } from "../utils/errors";

describe("getErrorMessage", () => {
  it("retorna el message de un Error", () => {
    expect(getErrorMessage(new Error("algo salió mal"))).toBe("algo salió mal");
  });

  it("retorna el fallback cuando el valor no es un Error", () => {
    expect(getErrorMessage(null)).toBe("Error inesperado");
    expect(getErrorMessage(undefined)).toBe("Error inesperado");
    expect(getErrorMessage("cadena")).toBe("Error inesperado");
  });

  it("respeta el fallback personalizado", () => {
    expect(getErrorMessage(42, "Mi fallback")).toBe("Mi fallback");
  });
});

describe("parseApiError", () => {
  it("400 → variant warning con el mensaje del error", () => {
    const result = parseApiError(new ApiError(400, "Petición inválida"));
    expect(result).toEqual({ variant: "warning", text: "Petición inválida" });
  });

  it("409 → variant warning", () => {
    const result = parseApiError(new ApiError(409, "Conflicto"));
    expect(result).toEqual({ variant: "warning", text: "Conflicto" });
  });

  it("422 → variant warning", () => {
    const result = parseApiError(new ApiError(422, "No procesable"));
    expect(result).toEqual({ variant: "warning", text: "No procesable" });
  });

  it("503 → variant danger con texto hardcoded en español", () => {
    const result = parseApiError(new ApiError(503, "cualquier cosa"));
    expect(result.variant).toBe("danger");
    expect(result.text).toMatch(/no está disponible/i);
  });

  it("500 → variant danger con mensaje del error", () => {
    const result = parseApiError(new ApiError(500, "Internal Server Error"));
    expect(result).toEqual({ variant: "danger", text: "Internal Server Error" });
  });

  it("error que no es ApiError → variant danger con fallback", () => {
    const result = parseApiError(new Error("error genérico"));
    expect(result.variant).toBe("danger");
    expect(result.text).toBe("Error de conexión con el servidor.");
  });

  it("valor no-Error → variant danger con fallback personalizado", () => {
    const result = parseApiError(null, "Sin conexión");
    expect(result).toEqual({ variant: "danger", text: "Sin conexión" });
  });
});
