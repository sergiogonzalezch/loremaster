import { describe, it, expect, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useGenerate } from "../hooks/useGenerate";
import { ApiAbortError } from "../api/apiClient";

function makeAsyncFn<T>(result: T, delay = 10) {
  return vi.fn(async (..._args: unknown[]) => {
    await new Promise((r) => setTimeout(r, delay));
    return result;
  });
}

describe("useGenerate", () => {
  it("estado inicial correcto", () => {
    const fn = makeAsyncFn("dato");
    const { result } = renderHook(() => useGenerate(fn));
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isCancelled).toBe(false);
  });

  it("run() activa isLoading y resuelve con data", async () => {
    const fn = makeAsyncFn("resultado");
    const { result } = renderHook(() => useGenerate(fn));
    act(() => {
      result.current.run();
    });
    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toBe("resultado");
    expect(result.current.error).toBeNull();
  });

  it("run() con error de API popula error y limpia isLoading", async () => {
    const fn = vi.fn().mockRejectedValue(new Error("fallo de red"));
    const { result } = renderHook(() => useGenerate(fn));
    await act(() => result.current.run());
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.isLoading).toBe(false);
  });

  it("cancel() dispara ApiAbortError → isCancelled=true, error=null", async () => {
    const fn = vi.fn(async (...args: unknown[]) => {
      const signal = args[args.length - 1] as AbortSignal;
      await new Promise((_, reject) => {
        signal.addEventListener("abort", () => reject(new ApiAbortError()));
      });
      return "nunca";
    });
    const { result } = renderHook(() => useGenerate(fn));
    act(() => {
      result.current.run();
    });
    act(() => {
      result.current.cancel();
    });
    await waitFor(() => expect(result.current.isCancelled).toBe(true));
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it("reset() vuelve al estado inicial", async () => {
    const fn = vi.fn().mockRejectedValue(new Error("algo"));
    const { result } = renderHook(() => useGenerate(fn));
    await act(() => result.current.run());
    expect(result.current.error).not.toBeNull();
    act(() => {
      result.current.reset();
    });
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isCancelled).toBe(false);
  });

  it("la función recibe AbortSignal como último argumento", async () => {
    const fn = makeAsyncFn("x");
    const { result } = renderHook(() => useGenerate(fn));
    await act(() => result.current.run("arg1", "arg2"));
    expect(fn).toHaveBeenCalledWith("arg1", "arg2", expect.any(AbortSignal));
  });

  it("segunda llamada a run() aborta la primera", async () => {
    let firstAborted = false;
    const fn = vi.fn(async (...args: unknown[]) => {
      const signal = args[args.length - 1] as AbortSignal;
      await new Promise<void>((resolve, reject) => {
        signal.addEventListener("abort", () => {
          firstAborted = true;
          reject(new ApiAbortError());
        });
        setTimeout(resolve, 50);
      });
      return "primera";
    });
    const { result } = renderHook(() => useGenerate(fn));
    act(() => {
      result.current.run();
    });
    act(() => {
      result.current.run();
    });
    await waitFor(() => expect(fn).toHaveBeenCalledTimes(2));
    expect(firstAborted).toBe(true);
  });
});
