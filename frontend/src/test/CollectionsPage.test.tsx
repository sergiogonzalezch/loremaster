import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import CollectionsPage from "../pages/CollectionsPage";
import { AuthProvider } from "../contexts/AuthContext";
import type { Collection } from "../types";

vi.mock("../api/collections", () => ({
  getCollections: vi.fn(),
  createCollection: vi.fn(),
  updateCollection: vi.fn(),
  deleteCollection: vi.fn(),
}));

import {
  getCollections,
  createCollection,
  deleteCollection,
} from "../api/collections";
const mockGetCollections = vi.mocked(getCollections);
const mockCreateCollection = vi.mocked(createCollection);
const mockDeleteCollection = vi.mocked(deleteCollection);

const SAMPLE: Collection = {
  id: "col-1",
  name: "Middle Earth",
  description: "A fantasy world",
  owner_id: null,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: null,
  document_count: 2,
  entity_count: 5,
};

const EMPTY_PAGE = {
  data: [],
  meta: { total: 0, page: 1, page_size: 12, total_pages: 0 },
};

function renderPage() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <CollectionsPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe("CollectionsPage", () => {
  it("muestra las colecciones recibidas de la API", async () => {
    mockGetCollections.mockResolvedValue({
      data: [SAMPLE],
      meta: { total: 1, page: 1, page_size: 12, total_pages: 1 },
    });
    renderPage();
    await waitFor(() =>
      expect(screen.getByText("Middle Earth")).toBeInTheDocument(),
    );
    // document_count y entity_count se renderizan como <strong>N</strong> texto
    expect(
      screen.getByText((_, el) => el?.textContent === "2 documentos"),
    ).toBeInTheDocument();
    expect(
      screen.getByText((_, el) => el?.textContent === "5 entidades"),
    ).toBeInTheDocument();
  });

  it("muestra estado vacío cuando no hay colecciones", async () => {
    mockGetCollections.mockResolvedValue(EMPTY_PAGE);
    renderPage();
    await waitFor(() =>
      expect(
        screen.getByText(/No hay colecciones todavía/),
      ).toBeInTheDocument(),
    );
  });

  it("muestra alerta de error si getCollections falla", async () => {
    mockGetCollections.mockRejectedValue(new Error("Error de red"));
    renderPage();
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("abre modal de creación al pulsar '+ Nueva colección'", async () => {
    mockGetCollections.mockResolvedValue(EMPTY_PAGE);
    renderPage();
    await waitFor(() => screen.getByText("+ Nueva colección"));

    await userEvent.click(screen.getByText("+ Nueva colección"));

    expect(screen.getByText("Nueva colección")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Nombre de la colección"),
    ).toBeInTheDocument();
  });

  it("llama a createCollection con los datos del formulario al enviar", async () => {
    mockGetCollections.mockResolvedValue(EMPTY_PAGE);
    mockCreateCollection.mockResolvedValue({ ...SAMPLE, id: "col-new" });
    renderPage();
    await waitFor(() => screen.getByText("+ Nueva colección"));

    await userEvent.click(screen.getByText("+ Nueva colección"));
    await userEvent.type(
      screen.getByPlaceholderText("Nombre de la colección"),
      "Westeros",
    );
    await userEvent.click(screen.getByRole("button", { name: "Crear" }));

    await waitFor(() =>
      expect(mockCreateCollection).toHaveBeenCalledWith({
        name: "Westeros",
        description: "",
      }),
    );
  });

  it("botón Crear deshabilitado mientras el nombre está vacío", async () => {
    mockGetCollections.mockResolvedValue(EMPTY_PAGE);
    renderPage();
    await waitFor(() => screen.getByText("+ Nueva colección"));

    await userEvent.click(screen.getByText("+ Nueva colección"));

    expect(screen.getByRole("button", { name: "Crear" })).toBeDisabled();
  });

  it("abre modal de confirmación al pulsar Eliminar y llama deleteCollection al confirmar", async () => {
    mockGetCollections.mockResolvedValue({
      data: [SAMPLE],
      meta: { total: 1, page: 1, page_size: 12, total_pages: 1 },
    });
    mockDeleteCollection.mockResolvedValue(undefined);
    renderPage();

    await waitFor(() => screen.getByText("Middle Earth"));
    await userEvent.click(screen.getByRole("button", { name: "Eliminar" }));

    // La modal muestra el mensaje con el nombre de la colección
    expect(
      screen.getByText(/¿Estás seguro de que quieres eliminar/),
    ).toBeInTheDocument();

    const allConfirm = await screen.findAllByRole("button", {
      name: "Confirmar",
    });
    await userEvent.click(allConfirm[allConfirm.length - 1]);

    await waitFor(() =>
      expect(mockDeleteCollection).toHaveBeenCalledWith("col-1"),
    );
  });

  it("retrocede a la última página válida cuando la página actual queda vacía", async () => {
    // Primera carga: página 2 vacía, pero total_pages=1 indica que hay datos en p.1
    mockGetCollections
      .mockResolvedValueOnce({
        data: [],
        meta: { total: 1, page: 2, page_size: 12, total_pages: 1 },
      })
      .mockResolvedValue({
        data: [SAMPLE],
        meta: { total: 1, page: 1, page_size: 12, total_pages: 1 },
      });

    render(
      <MemoryRouter initialEntries={["/?page=2"]}>
        <AuthProvider>
          <CollectionsPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    // Tras la auto-navegación a page=1, el ítem debe aparecer
    await waitFor(() =>
      expect(screen.getByText("Middle Earth")).toBeInTheDocument(),
    );
    // La segunda llamada fue con page=1
    expect(mockGetCollections).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1 }),
      expect.anything(),
    );
  });

  it("abre modal de edición con datos actuales de la colección", async () => {
    mockGetCollections.mockResolvedValue({
      data: [SAMPLE],
      meta: { total: 1, page: 1, page_size: 12, total_pages: 1 },
    });
    renderPage();

    await waitFor(() => screen.getByText("Middle Earth"));
    await userEvent.click(screen.getByRole("button", { name: "Editar" }));

    expect(screen.getByText("Editar colección")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Middle Earth")).toBeInTheDocument();
    expect(screen.getByDisplayValue("A fantasy world")).toBeInTheDocument();
  });
});
