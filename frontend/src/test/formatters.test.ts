import { describe, it, expect } from "vitest";
import { formatDate } from "../utils/formatters";

describe("formatDate", () => {
  it("formatea fecha en español sin hora por defecto", () => {
    const result = formatDate("2024-06-15T10:30:00Z");
    expect(result).toMatch(/2024/);
    expect(result).toMatch(/jun/i);
    expect(result).toMatch(/15/);
    expect(result).not.toMatch(/10:30/);
  });

  it("incluye hora cuando includeTime es true", () => {
    const result = formatDate("2024-06-15T10:30:00Z", true);
    expect(result).toMatch(/2024/);
    expect(result).toMatch(/\d{1,2}:\d{2}/);
  });

  it("fecha inválida no lanza excepción", () => {
    expect(() => formatDate("not-a-date")).not.toThrow();
  });
});
