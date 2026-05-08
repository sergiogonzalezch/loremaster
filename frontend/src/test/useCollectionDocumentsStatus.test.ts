import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useCollectionDocumentsStatus } from "../hooks/useCollectionDocumentsStatus";
import { ApiAbortError } from "../api/apiClient";

vi.mock("../api", () => ({
  getDocuments: vi.fn(),
}));

import { getDocuments } from "../api";
const mockGetDocuments = vi.mocked(getDocuments);

const EMPTY_PAGE = {
  data: [] as { id: string; status: string }[],
  meta: { total: 0, page: 1, page_size: 100, total_pages: 0 },
};

const PROCESSING_PAGE = {
  data: [{ id: "doc-1", status: "processing" }],
  meta: { total: 1, page: 1, page_size: 100, total_pages: 1 },
};

const COMPLETED_PAGE = {
  data: [{ id: "doc-1", status: "completed" }],
  meta: { total: 1, page: 1, page_size: 100, total_pages: 1 },
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useCollectionDocumentsStatus", () => {
  it("sin collectionId no llama a la API", async () => {
    renderHook(() => useCollectionDocumentsStatus(undefined));
    await act(async () => {});
    expect(mockGetDocuments).not.toHaveBeenCalled();
  });

  it("carga inicial sin documentos: hasCompletedDocs=false, hasProcessingDocs=false", async () => {
    mockGetDocuments.mockResolvedValue(EMPTY_PAGE);
    const { result } = renderHook(() => useCollectionDocumentsStatus("col-1"));
    await act(async () => {});
    expect(result.current.hasCompletedDocs).toBe(false);
    expect(result.current.hasProcessingDocs).toBe(false);
  });

  it("carga inicial con documentos completados: hasCompletedDocs=true", async () => {
    mockGetDocuments.mockResolvedValue(COMPLETED_PAGE);
    const { result } = renderHook(() => useCollectionDocumentsStatus("col-1"));
    await act(async () => {});
    expect(result.current.hasCompletedDocs).toBe(true);
    expect(result.current.hasProcessingDocs).toBe(false);
  });

  it("el polling se activa cuando hay documentos en 'processing'", async () => {
    mockGetDocuments.mockResolvedValue(PROCESSING_PAGE);
    const { result } = renderHook(() => useCollectionDocumentsStatus("col-1"));

    // Flush initial load
    await act(async () => {});
    expect(result.current.hasProcessingDocs).toBe(true);

    const callsBefore = mockGetDocuments.mock.calls.length;

    // Advance 3s — interval fires once
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(mockGetDocuments.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  it("el polling se detiene cuando todos los documentos salen de 'processing'", async () => {
    mockGetDocuments
      .mockResolvedValueOnce(PROCESSING_PAGE) // initial load
      .mockResolvedValue(COMPLETED_PAGE); // interval calls

    const { result } = renderHook(() => useCollectionDocumentsStatus("col-1"));

    // Initial load → hasProcessingDocs=true
    await act(async () => {});
    expect(result.current.hasProcessingDocs).toBe(true);

    // Interval fires → COMPLETED → hasProcessingDocs=false → interval cleared
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(result.current.hasProcessingDocs).toBe(false);

    const callsAfterStop = mockGetDocuments.mock.calls.length;

    // 9 more seconds — no new calls because interval was cleared
    await act(async () => {
      await vi.advanceTimersByTimeAsync(9000);
    });

    expect(mockGetDocuments.mock.calls.length).toBe(callsAfterStop);
  });

  it("ApiAbortError no actualiza estado (queda en valores iniciales)", async () => {
    mockGetDocuments.mockRejectedValue(new ApiAbortError());
    const { result } = renderHook(() => useCollectionDocumentsStatus("col-1"));
    await act(async () => {});
    expect(result.current.hasCompletedDocs).toBeNull();
    expect(result.current.hasProcessingDocs).toBe(false);
  });
});
