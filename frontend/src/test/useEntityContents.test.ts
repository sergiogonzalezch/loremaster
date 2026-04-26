import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useEntityContents } from "../hooks/useEntityContents";
import { ApiAbortError } from "../api/apiClient";
import type { PaginatedResponse, EntityContent } from "../types";

vi.mock("../api/contents", () => ({
  getContents: vi.fn(),
}));

import { getContents } from "../api/contents";
const mockGetContents = vi.mocked(getContents);

const EMPTY_PAGE: PaginatedResponse<EntityContent> = {
  data: [],
  meta: { total: 0, page: 1, page_size: 10, total_pages: 0 },
};

const SAMPLE_CONTENT: EntityContent = {
  id: "cnt-1",
  entity_id: "ent-1",
  collection_id: "col-1",
  query: "Historia del personaje",
  sources_count: 2,
  token_count: 10,
  category: "backstory",
  content: "Texto de prueba",
  status: "pending",
  created_at: "2024-01-01T00:00:00Z",
  confirmed_at: null,
  updated_at: null,
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useEntityContents", () => {
  it("sin collectionId/entityId no llama a la API", async () => {
    const { result } = renderHook(() =>
      useEntityContents(undefined, undefined),
    );
    await act(() => result.current.refresh());
    expect(mockGetContents).not.toHaveBeenCalled();
  });

  it("refresh() con ids llama a getContents y popula contents y meta", async () => {
    const page: PaginatedResponse<EntityContent> = {
      data: [SAMPLE_CONTENT],
      meta: { total: 1, page: 1, page_size: 10, total_pages: 1 },
    };
    mockGetContents.mockResolvedValue(page);
    const { result } = renderHook(() => useEntityContents("col-1", "ent-1"));
    await act(() => result.current.refresh());
    expect(result.current.contents).toEqual([SAMPLE_CONTENT]);
    expect(result.current.meta.total).toBe(1);
  });

  it("durante el fetch loading=true", async () => {
    let resolveCall!: (v: PaginatedResponse<EntityContent>) => void;
    mockGetContents.mockReturnValue(
      new Promise((r) => {
        resolveCall = r;
      }),
    );
    const { result } = renderHook(() => useEntityContents("col-1", "ent-1"));
    act(() => {
      result.current.refresh();
    });
    expect(result.current.loading).toBe(true);
    act(() => resolveCall(EMPTY_PAGE));
    await waitFor(() => expect(result.current.loading).toBe(false));
  });

  it("error de API popula error con mensaje", async () => {
    mockGetContents.mockRejectedValue(new Error("Error de red"));
    const { result } = renderHook(() => useEntityContents("col-1", "ent-1"));
    await act(() => result.current.refresh());
    expect(result.current.error).toMatch(/Error de red/);
  });

  it("ApiAbortError no popula error (se ignora silenciosamente)", async () => {
    mockGetContents.mockRejectedValue(new ApiAbortError());
    const { result } = renderHook(() => useEntityContents("col-1", "ent-1"));
    await act(() => result.current.refresh());
    expect(result.current.error).toBeNull();
  });

  it("refresh() con opciones de filtro pasa parámetros a getContents", async () => {
    mockGetContents.mockResolvedValue(EMPTY_PAGE);
    const { result } = renderHook(() => useEntityContents("col-1", "ent-1"));
    await act(() =>
      result.current.refresh({
        category: "backstory",
        status: "pending",
        page: 2,
      }),
    );
    expect(mockGetContents).toHaveBeenCalledWith(
      "col-1",
      "ent-1",
      expect.objectContaining({
        category: "backstory",
        status: "pending",
        page: 2,
      }),
      undefined,
    );
  });

  it("setError(null) limpia el error existente", async () => {
    mockGetContents.mockRejectedValue(new Error("fallo"));
    const { result } = renderHook(() => useEntityContents("col-1", "ent-1"));
    await act(() => result.current.refresh());
    expect(result.current.error).not.toBeNull();
    act(() => result.current.setError(null));
    expect(result.current.error).toBeNull();
  });
});
