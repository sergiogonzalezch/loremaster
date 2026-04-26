import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import EntityDetailPage from "../pages/EntityDetailPage";
import type { Collection, Entity, EntityContent } from "../types";

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...actual,
    useParams: () => ({ collectionId: "col-1", entityId: "ent-1" }),
  };
});

vi.mock("../api", () => ({
  getEntity: vi.fn(),
  getCollection: vi.fn(),
  generateContent: vi.fn(),
  updateEntity: vi.fn(),
  getEntityCategories: vi.fn().mockRejectedValue(new Error("mocked")),
}));

vi.mock("../hooks/useEntityContents", () => ({
  useEntityContents: vi.fn(),
}));

vi.mock("../hooks/useGenerate", () => ({
  useGenerate: vi.fn(),
}));

import { getEntity, getCollection } from "../api";
import { useEntityContents } from "../hooks/useEntityContents";
import { useGenerate } from "../hooks/useGenerate";

const mockGetEntity = vi.mocked(getEntity);
const mockGetCollection = vi.mocked(getCollection);
const mockUseEntityContents = vi.mocked(useEntityContents);
const mockUseGenerate = vi.mocked(useGenerate);

const SAMPLE_ENTITY: Entity = {
  id: "ent-1",
  collection_id: "col-1",
  type: "character",
  name: "Gandalf",
  description: "Un mago muy poderoso",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: null,
};

const SAMPLE_COLLECTION: Collection = {
  id: "col-1",
  name: "Middle Earth",
  description: "A fantasy world",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: null,
  document_count: 5,
  entity_count: 3,
};

const DEFAULT_CONTENTS_HOOK = {
  contents: [] as EntityContent[],
  setContents: vi.fn(),
  meta: { total: 0, page: 1, page_size: 10, total_pages: 0 },
  loading: false,
  error: null,
  refresh: vi.fn().mockResolvedValue(undefined),
  setError: vi.fn(),
};

const DEFAULT_GENERATE_HOOK = {
  data: null,
  error: null,
  isLoading: false,
  isCancelled: false,
  run: vi.fn().mockResolvedValue(null),
  cancel: vi.fn(),
  reset: vi.fn(),
};

function renderPage() {
  return render(
    <MemoryRouter>
      <EntityDetailPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGetEntity.mockResolvedValue(SAMPLE_ENTITY);
  mockGetCollection.mockResolvedValue(SAMPLE_COLLECTION);
  mockUseEntityContents.mockReturnValue(DEFAULT_CONTENTS_HOOK);
  mockUseGenerate.mockReturnValue(DEFAULT_GENERATE_HOOK);
});

describe("EntityDetailPage", () => {
  it("renderiza nombre, tipo y descripción de la entidad", async () => {
    renderPage();
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Gandalf" }),
      ).toBeInTheDocument(),
    );
    // badge de tipo (solo aparece una vez en el header de la entidad)
    expect(screen.getAllByText("Personaje")[0]).toBeInTheDocument();
    expect(screen.getByText("Un mago muy poderoso")).toBeInTheDocument();
  });

  it("muestra el formulario de generación con selector de categoría", async () => {
    renderPage();
    await waitFor(() => screen.getByRole("heading", { name: "Gandalf" }));
    expect(screen.getAllByText("Trasfondo").length).toBeGreaterThan(0); // primer category del character
    expect(screen.getByRole("button", { name: "Generar" })).toBeInTheDocument();
  });

  it("botón Generar deshabilitado con query menor de 5 caracteres", async () => {
    renderPage();
    await waitFor(() => screen.getByRole("heading", { name: "Gandalf" }));

    const generateBtn = screen.getByRole("button", { name: "Generar" });
    expect(generateBtn).toBeDisabled();

    await userEvent.type(screen.getByRole("textbox"), "ok");
    expect(generateBtn).toBeDisabled();
  });

  it("botón Generar habilitado con query de al menos 5 caracteres", async () => {
    renderPage();
    await waitFor(() => screen.getByRole("heading", { name: "Gandalf" }));

    await userEvent.type(screen.getByRole("textbox"), "Historia del mago gris");
    expect(screen.getByRole("button", { name: "Generar" })).toBeEnabled();
  });

  it("muestra aviso de límite cuando hay 5 borradores pendientes en la categoría", async () => {
    const pendingContents: EntityContent[] = Array.from(
      { length: 5 },
      (_, i) => ({
        id: `cnt-${i}`,
        entity_id: "ent-1",
        collection_id: "col-1",
        query: "query de prueba",
        sources_count: 1,
        token_count: 0,
        category: "backstory" as const,
        content: "contenido de prueba",
        status: "pending" as const,
        created_at: "2024-01-01T00:00:00Z",
        confirmed_at: null,
        updated_at: null,
      }),
    );
    mockUseEntityContents.mockReturnValue({
      ...DEFAULT_CONTENTS_HOOK,
      contents: pendingContents,
    });

    renderPage();
    await waitFor(() => screen.getByRole("heading", { name: "Gandalf" }));

    expect(
      screen.getByText(/contenidos pendientes en esta categoría/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generar" })).toBeDisabled();
  });

  it("llama a run al enviar el formulario de generación", async () => {
    const mockRun = vi.fn().mockResolvedValue({ id: "cnt-new" });
    mockUseGenerate.mockReturnValue({
      ...DEFAULT_GENERATE_HOOK,
      run: mockRun,
    });

    renderPage();
    await waitFor(() => screen.getByRole("heading", { name: "Gandalf" }));

    await userEvent.type(
      screen.getByRole("textbox"),
      "Historia del mago gris en la Tierra Media",
    );
    await userEvent.click(screen.getByRole("button", { name: "Generar" }));

    await waitFor(() => expect(mockRun).toHaveBeenCalled());
  });

  it("muestra barra de carga mientras isLoading es true", async () => {
    mockUseGenerate.mockReturnValue({
      ...DEFAULT_GENERATE_HOOK,
      isLoading: true,
    });

    renderPage();
    await waitFor(() => screen.getByRole("heading", { name: "Gandalf" }));

    expect(screen.getByText(/Procesando prompt/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Generando/ }),
    ).toBeInTheDocument();
  });

  it("muestra estado vacío cuando no hay contenidos", async () => {
    renderPage();
    await waitFor(() => screen.getByRole("heading", { name: "Gandalf" }));

    expect(screen.getByText(/No hay contenidos todavía/)).toBeInTheDocument();
  });

  it("abre modal de edición de entidad con datos actuales", async () => {
    renderPage();
    await waitFor(() => screen.getByRole("heading", { name: "Gandalf" }));

    await userEvent.click(screen.getByRole("button", { name: "Editar" }));

    expect(screen.getByText("Editar entidad")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Gandalf")).toBeInTheDocument();
  });
});
