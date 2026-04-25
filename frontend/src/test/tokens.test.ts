import { describe, it, expect } from "vitest";
import { estimateTokens, QUERY_TOKEN_WARN_AT } from "../utils/tokens";

describe("estimateTokens", () => {
  it("cadena vacía → 0", () => {
    expect(estimateTokens("")).toBe(0);
  });

  it("4 caracteres → 1 token exacto", () => {
    expect(estimateTokens("abcd")).toBe(1);
  });

  it("3 caracteres → 1 token (Math.ceil)", () => {
    expect(estimateTokens("abc")).toBe(1);
  });

  it("5 caracteres → 2 tokens (Math.ceil de 1.25)", () => {
    expect(estimateTokens("abcde")).toBe(2);
  });

  it("texto largo supera QUERY_TOKEN_WARN_AT", () => {
    const textoLargo = "a".repeat(QUERY_TOKEN_WARN_AT * 4 + 4);
    expect(estimateTokens(textoLargo)).toBeGreaterThan(QUERY_TOKEN_WARN_AT);
  });
});

describe("QUERY_TOKEN_WARN_AT", () => {
  it("es 400", () => {
    expect(QUERY_TOKEN_WARN_AT).toBe(400);
  });
});
