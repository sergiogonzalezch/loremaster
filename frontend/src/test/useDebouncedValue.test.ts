import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDebouncedValue } from "../hooks/useDebouncedValue";

afterEach(() => {
  vi.useRealTimers();
});

describe("useDebouncedValue", () => {
  it("retorna el valor inicial inmediatamente", () => {
    const { result } = renderHook(() => useDebouncedValue("inicial"));
    expect(result.current).toBe("inicial");
  });

  it("no actualiza antes de que pase el delay", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(
      ({ value }) => useDebouncedValue(value, 350),
      { initialProps: { value: "inicial" } },
    );
    rerender({ value: "nuevo" });
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(result.current).toBe("inicial");
  });

  it("actualiza el valor tras el delay", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(
      ({ value }) => useDebouncedValue(value, 350),
      { initialProps: { value: "inicial" } },
    );
    rerender({ value: "nuevo" });
    act(() => {
      vi.advanceTimersByTime(350);
    });
    expect(result.current).toBe("nuevo");
  });
});
