import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TokenCounter from "../components/TokenCounter";
import { QUERY_TOKEN_WARN_AT } from "../utils/tokens";

describe("TokenCounter", () => {
  it("texto vacío muestra 0 tokens", () => {
    render(<TokenCounter text="" />);
    expect(screen.getByText(/≈ 0 tokens/)).toBeInTheDocument();
  });

  it("texto corto muestra clase text-muted (sin advertencia)", () => {
    render(<TokenCounter text="hola" />);
    const el = screen.getByText(/tokens/);
    expect(el.className).toContain("text-muted");
    expect(el.textContent).not.toMatch(/acortar/i);
  });

  it("texto que supera el umbral muestra clase text-warning y advertencia", () => {
    const textoLargo = "a".repeat(QUERY_TOKEN_WARN_AT * 4);
    render(<TokenCounter text={textoLargo} />);
    const el = screen.getByText(/tokens/);
    expect(el.className).toContain("text-warning");
    expect(el.textContent).toMatch(/acortar/i);
  });

  it("respeta warnAt personalizado", () => {
    render(<TokenCounter text="abcd" warnAt={1} />);
    const el = screen.getByText(/tokens/);
    expect(el.className).toContain("text-warning");
  });
});
