import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useCollectionDocumentsStatus } from "../hooks/useCollectionDocumentsStatus";
import { ApiAbortError } from "../api/apiClient";

vi.mock("../api", () => ({
  getDocuments: vi.fn(),
}));

import { getDocuments } from "../api";
const mockGetDocuments = vi.mocked(getDocuments);

vi.mock("../utils/token", () => ({
  getToken: vi.fn().mockReturnValue(null),
}));

const EMPTY_PAGE = {
  data: [] as import("../types/document").Document[],
  meta: { total: 0, page: 1, page_size: 100, total_pages: 0 },
};

const PROCESSING_PAGE = {
  data: [
    {
      id: "doc-1",
      collection_id: "col-1",
      filename: "test.txt",
      file_type: "text/plain",
      chunk_count: 5,
      status: "processing" as const,
      created_at: new Date().toISOString(),
    },
  ],
  meta: { total: 1, page: 1, page_size: 100, total_pages: 1 },
};

const COMPLETED_PAGE = {
  data: [
    {
      id: "doc-1",
      collection_id: "col-1",
      filename: "test.txt",
      file_type: "text/plain",
      chunk_count: 5,
      status: "completed" as const,
      created_at: new Date().toISOString(),
    },
  ],
  meta: { total: 1, page: 1, page_size: 100, total_pages: 1 },
};

describe("useCollectionDocumentsStatus", () => {
  let mockEventSource: {
    onmessage: ((event: { data: string }) => void) | null;
    onerror: (() => void) | null;
    close: () => void;
  };

  beforeEach(() => {
    vi.clearAllMocks();

    mockEventSource = {
      onmessage: null,
      onerror: null,
      close: vi.fn(),
    };

    vi.spyOn(global, "EventSource").mockImplementation(() => {
      return mockEventSource as unknown as EventSource;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

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

  it("crea EventSource cuando hay documentos en processing", async () => {
    mockGetDocuments.mockResolvedValue(PROCESSING_PAGE);
    const eventSourceSpy = vi.spyOn(global, "EventSource");

    const { result } = renderHook(() => useCollectionDocumentsStatus("col-1"));
    await act(async () => {});

    expect(eventSourceSpy).toHaveBeenCalled();
    expect(result.current.hasProcessingDocs).toBe(true);
  });

  it("hace refresh al recibir evento 'processing' del SSE", async () => {
    mockGetDocuments.mockResolvedValue(PROCESSING_PAGE);
    const { result } = renderHook(() => useCollectionDocumentsStatus("col-1"));

    await act(async () => {});
    expect(result.current.hasProcessingDocs).toBe(true);

    const callsBefore = mockGetDocuments.mock.calls.length;

    mockGetDocuments.mockResolvedValue(PROCESSING_PAGE);
    act(() => {
      mockEventSource.onmessage?.({ data: "processing" });
    });

    expect(mockGetDocuments.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  it("hace refresh y cierra EventSource al recibir evento 'completed'", async () => {
    mockGetDocuments
      .mockResolvedValueOnce(PROCESSING_PAGE)
      .mockResolvedValueOnce(COMPLETED_PAGE);

    const { result } = renderHook(() => useCollectionDocumentsStatus("col-1"));

    await act(async () => {});
    expect(result.current.hasProcessingDocs).toBe(true);

    const closeSpy = vi.spyOn(mockEventSource, "close");

    act(() => {
      mockEventSource.onmessage?.({ data: "completed" });
    });

    await act(async () => {});

    expect(result.current.hasProcessingDocs).toBe(false);
    expect(closeSpy).toHaveBeenCalled();
  });

  it("cierra EventSource cuando hasProcessingDocs es false", async () => {
    mockGetDocuments
      .mockResolvedValueOnce(PROCESSING_PAGE)
      .mockResolvedValueOnce(COMPLETED_PAGE);

    const { unmount } = renderHook(() => useCollectionDocumentsStatus("col-1"));

    await act(async () => {});

    const closeSpy = vi.spyOn(mockEventSource, "close");

    act(() => {
      mockEventSource.onmessage?.({ data: "completed" });
    });

    await act(async () => {});

    expect(closeSpy).toHaveBeenCalled();

    unmount();
    expect(closeSpy).toHaveBeenCalledTimes(2);
  });

  it("ApiAbortError no actualiza estado (queda en valores iniciales)", async () => {
    mockGetDocuments.mockRejectedValue(new ApiAbortError());
    const { result } = renderHook(() => useCollectionDocumentsStatus("col-1"));
    await act(async () => {});
    expect(result.current.hasCompletedDocs).toBeNull();
    expect(result.current.hasProcessingDocs).toBe(false);
  });

  it("maneja error de EventSource cerrando la conexión", async () => {
    mockGetDocuments.mockResolvedValue(PROCESSING_PAGE);

    renderHook(() => useCollectionDocumentsStatus("col-1"));
    await act(async () => {});

    const closeSpy = vi.spyOn(mockEventSource, "close");

    act(() => {
      mockEventSource.onerror?.();
    });

    expect(closeSpy).toHaveBeenCalled();
  });
});
