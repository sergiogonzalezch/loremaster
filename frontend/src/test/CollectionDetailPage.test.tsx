import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import CollectionDetailPage from "../pages/CollectionDetailPage";
import type { Document } from "../types";
import { ApiError } from "../api/apiClient";

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useParams: () => ({ collectionId: "col-1" }) };
});

vi.mock("../api", () => ({
  getCollection: vi.fn(),
  getDocuments: vi.fn(),
  getDocument: vi.fn(),
  uploadDocument: vi.fn(),
  retryDocument: vi.fn(),
  deleteDocument: vi.fn(),
  getEntities: vi.fn(),
  createEntity: vi.fn(),
  deleteEntity: vi.fn(),
  generateText: vi.fn(),
}));

vi.mock("../hooks/useCollectionDocumentsStatus", () => ({
  useCollectionDocumentsStatus: vi.fn(),
}));

vi.mock("../hooks/useGenerate", () => ({
  useGenerate: vi.fn(),
}));

import {
  getCollection,
  getDocuments,
  retryDocument,
  getEntities,
} from "../api";
import { useCollectionDocumentsStatus } from "../hooks/useCollectionDocumentsStatus";
import { useGenerate } from "../hooks/useGenerate";

const mockGetCollection = vi.mocked(getCollection);
const mockGetDocuments = vi.mocked(getDocuments);
const mockRetryDocument = vi.mocked(retryDocument);
const mockGetEntities = vi.mocked(getEntities);
const mockUseDocsStatus = vi.mocked(useCollectionDocumentsStatus);
const mockUseGenerate = vi.mocked(useGenerate);

const COLLECTION = {
  id: "col-1",
  name: "Arda",
  description: "Middle-earth lore",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: null,
  document_count: 1,
  entity_count: 0,
};

const FAILED_DOC: Document = {
  id: "doc-1",
  collection_id: "col-1",
  filename: "lore.pdf",
  file_type: "application/pdf",
  chunk_count: 0,
  status: "failed",
  processing_error: "Connection to Qdrant timed out after 30 s",
  created_at: "2024-01-01T00:00:00Z",
};

const PROCESSING_DOC: Document = {
  ...FAILED_DOC,
  status: "processing",
  processing_error: null,
};

const COMPLETED_DOC: Document = {
  ...FAILED_DOC,
  status: "completed",
  chunk_count: 12,
  processing_error: null,
};

const EMPTY_DOCS = {
  data: [] as Document[],
  meta: { total: 0, page: 1, page_size: 10, total_pages: 0 },
};

function renderPage() {
  return render(
    <MemoryRouter>
      <CollectionDetailPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGetCollection.mockResolvedValue(COLLECTION);
  mockGetDocuments.mockResolvedValue({
    data: [FAILED_DOC],
    meta: { total: 1, page: 1, page_size: 10, total_pages: 1 },
  });
  mockGetEntities.mockResolvedValue(EMPTY_DOCS);
  // null = estado inicial (sin verificar), evita que GenerateTab renderice su alerta
  mockUseDocsStatus.mockReturnValue({
    hasCompletedDocs: null,
    hasProcessingDocs: false,
    refresh: vi.fn().mockResolvedValue(false),
  });
  mockUseGenerate.mockReturnValue({
    data: null,
    error: null,
    isLoading: false,
    isCancelled: false,
    run: vi.fn(),
    cancel: vi.fn(),
    reset: vi.fn(),
  });
});

describe("CollectionDetailPage — DocumentsTab retry", () => {
  it("muestra el nombre del documento en la tabla", async () => {
    renderPage();
    await waitFor(() =>
      expect(screen.getByText("lore.pdf")).toBeInTheDocument(),
    );
  });

  it("muestra botón Reintentar para documentos en estado failed", async () => {
    renderPage();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Reintentar" }),
      ).toBeInTheDocument(),
    );
  });

  it("no muestra botón Reintentar para documentos completados", async () => {
    mockGetDocuments.mockResolvedValue({
      data: [COMPLETED_DOC],
      meta: { total: 1, page: 1, page_size: 10, total_pages: 1 },
    });
    renderPage();
    await waitFor(() =>
      expect(screen.getByText("lore.pdf")).toBeInTheDocument(),
    );
    expect(
      screen.queryByRole("button", { name: "Reintentar" }),
    ).not.toBeInTheDocument();
  });

  it("muestra processing_error truncado en la fila del documento", async () => {
    renderPage();
    await waitFor(() =>
      expect(
        screen.getByText(/Connection to Qdrant timed out/),
      ).toBeInTheDocument(),
    );
  });

  it("no muestra processing_error si el campo es nulo", async () => {
    mockGetDocuments.mockResolvedValue({
      data: [COMPLETED_DOC],
      meta: { total: 1, page: 1, page_size: 10, total_pages: 1 },
    });
    renderPage();
    await waitFor(() =>
      expect(screen.getByText("lore.pdf")).toBeInTheDocument(),
    );
    expect(
      screen.queryByText(/Connection to Qdrant/),
    ).not.toBeInTheDocument();
  });

  it("reintentar exitoso llama a retryDocument y muestra badge Procesando", async () => {
    mockRetryDocument.mockResolvedValue(PROCESSING_DOC);
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Reintentar" }),
      ).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(mockRetryDocument).toHaveBeenCalledWith("col-1", "doc-1");
    await waitFor(() =>
      expect(screen.getByText("Procesando")).toBeInTheDocument(),
    );
  });

  it("reintentar exitoso elimina el doc de la lista fallida", async () => {
    mockRetryDocument.mockResolvedValue(PROCESSING_DOC);
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Reintentar" }),
      ).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "Reintentar" }),
      ).not.toBeInTheDocument(),
    );
  });

  it("reintentar fallido muestra alerta de error", async () => {
    mockRetryDocument.mockRejectedValue(
      new ApiError(
        409,
        "El documento no está en estado 'failed' o no tiene texto almacenado para reintentar la ingestión.",
      ),
    );
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Reintentar" }),
      ).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument(),
    );
  });

  it("trunca processing_error largo a 90 caracteres con elipsis", async () => {
    const longError =
      "A".repeat(100) + " este texto no debe aparecer completo en la tabla";
    mockGetDocuments.mockResolvedValue({
      data: [{ ...FAILED_DOC, processing_error: longError }],
      meta: { total: 1, page: 1, page_size: 10, total_pages: 1 },
    });
    renderPage();
    await waitFor(() =>
      expect(screen.getByText(/…$/)).toBeInTheDocument(),
    );
    expect(screen.queryByText(longError)).not.toBeInTheDocument();
  });
});