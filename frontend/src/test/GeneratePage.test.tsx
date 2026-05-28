import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import GeneratePage from "../pages/GeneratePage";

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...actual,
    useParams: () => ({ collectionId: "col-1" }),
  };
});

vi.mock("../api/collections", () => ({
  getCollection: vi.fn(),
}));

vi.mock("../api/generate", () => ({
  generateText: vi.fn(),
}));

vi.mock("../hooks/useGenerate", () => ({
  useGenerate: vi.fn(),
}));

vi.mock("../hooks/useCollectionDocumentsStatus", () => ({
  useCollectionDocumentsStatus: vi.fn(),
}));

import { getCollection } from "../api/collections";
import { useGenerate } from "../hooks/useGenerate";
import { useCollectionDocumentsStatus } from "../hooks/useCollectionDocumentsStatus";

const mockGetCollection = vi.mocked(getCollection);
const mockUseGenerate = vi.mocked(useGenerate);
const mockUseDocsStatus = vi.mocked(useCollectionDocumentsStatus);

const DEFAULT_GENERATE_HOOK = {
  data: null,
  error: null,
  isLoading: false,
  isCancelled: false,
  run: vi.fn().mockResolvedValue(null),
  cancel: vi.fn(),
  reset: vi.fn(),
};

const DEFAULT_DOCS_HOOK = {
  hasCompletedDocs: true,
  hasProcessingDocs: false,
  refresh: vi.fn().mockResolvedValue(true),
};

async function renderPage() {
  const result = render(
    <MemoryRouter>
      <GeneratePage />
    </MemoryRouter>,
  );
  await act(async () => {});
  return result;
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGetCollection.mockResolvedValue({
    id: "col-1",
    name: "Middle Earth",
    description: "",
    owner_id: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: null,
    document_count: 3,
    entity_count: 2,
  });
  mockUseGenerate.mockReturnValue(DEFAULT_GENERATE_HOOK);
  mockUseDocsStatus.mockReturnValue(DEFAULT_DOCS_HOOK);
});

describe("GeneratePage", () => {
  it("muestra el formulario de consulta", async () => {
    await renderPage();
    expect(
      screen.getByPlaceholderText(/Escribe tu consulta/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generar" })).toBeInTheDocument();
  });

  it("muestra el nombre de la colección en el breadcrumb", async () => {
    await renderPage();
    await waitFor(() =>
      expect(screen.getByText("Middle Earth")).toBeInTheDocument(),
    );
  });

  it("muestra aviso cuando la colección no tiene documentos procesados", async () => {
    mockUseDocsStatus.mockReturnValue({
      ...DEFAULT_DOCS_HOOK,
      hasCompletedDocs: false,
    });
    await renderPage();
    expect(
      screen.getByText(/no tiene documentos procesados/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generar" })).toBeDisabled();
  });

  it("botón Generar deshabilitado con query menor de 5 caracteres", async () => {
    await renderPage();
    expect(screen.getByRole("button", { name: "Generar" })).toBeDisabled();
  });

  it("botón Generar habilitado con query válida", async () => {
    await renderPage();
    await userEvent.type(
      screen.getByRole("textbox"),
      "¿Quién es el portador del Anillo?",
    );
    expect(screen.getByRole("button", { name: "Generar" })).toBeEnabled();
  });

  it("llama a run al enviar el formulario", async () => {
    const mockRun = vi.fn().mockResolvedValue(null);
    mockUseGenerate.mockReturnValue({
      ...DEFAULT_GENERATE_HOOK,
      run: mockRun,
    });

    await renderPage();
    await userEvent.type(
      screen.getByRole("textbox"),
      "¿Quién es el portador del Anillo Único?",
    );
    await userEvent.click(screen.getByRole("button", { name: "Generar" }));

    await waitFor(() => expect(mockRun).toHaveBeenCalled());
  });

  it("muestra barra de carga y botón Cancelar mientras isLoading es true", async () => {
    mockUseGenerate.mockReturnValue({
      ...DEFAULT_GENERATE_HOOK,
      isLoading: true,
    });
    await renderPage();
    expect(screen.getByText(/Analizando documentos/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Cancelar" }),
    ).toBeInTheDocument();
  });

  it("muestra el resultado de la generación cuando data no es null", async () => {
    mockUseGenerate.mockReturnValue({
      ...DEFAULT_GENERATE_HOOK,
      data: {
        answer: "Frodo Bolsón es el portador del Anillo Único.",
        query: "¿Quién porta el Anillo?",
        sources_count: 4,
      },
    });
    await renderPage();
    expect(
      screen.getByText("Frodo Bolsón es el portador del Anillo Único."),
    ).toBeInTheDocument();
    expect(screen.getByText("4 fuentes")).toBeInTheDocument();
  });

  it("muestra alerta de cancelación cuando isCancelled es true", async () => {
    mockUseGenerate.mockReturnValue({
      ...DEFAULT_GENERATE_HOOK,
      isCancelled: true,
    });
    await renderPage();
    expect(screen.getByText(/cancelada/)).toBeInTheDocument();
  });
});
