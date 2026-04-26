import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ContentCard from "../components/ContentCard";
import type { EntityContent } from "../types";
import { ApiError } from "../api/apiClient";

vi.mock("../api/contents", () => ({
  confirmContent: vi.fn(),
  discardContent: vi.fn(),
  deleteContent: vi.fn(),
  updateContent: vi.fn(),
}));

import * as contentsApi from "../api/contents";

const mockConfirm = vi.mocked(contentsApi.confirmContent);
const mockDiscard = vi.mocked(contentsApi.discardContent);
const mockDelete = vi.mocked(contentsApi.deleteContent);
const mockUpdate = vi.mocked(contentsApi.updateContent);

function makeContent(overrides: Partial<EntityContent> = {}): EntityContent {
  return {
    id: "cnt-1",
    entity_id: "ent-1",
    collection_id: "col-1",
    query: "Historia del personaje",
    sources_count: 3,
    category: "backstory",
    content: "Texto del contenido generado.",
    status: "pending",
    created_at: "2024-06-01T10:00:00Z",
    confirmed_at: null,
    updated_at: null,
    ...overrides,
  };
}

function renderCard(content: EntityContent, onAction = vi.fn()) {
  return render(
    <ContentCard
      content={content}
      collectionId="col-1"
      entityId="ent-1"
      onAction={onAction}
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

// ── Pending ────────────────────────────────────────────────────────────────────

describe("ContentCard — pending", () => {
  it("muestra badge Borrador", () => {
    renderCard(makeContent({ status: "pending" }));
    expect(screen.getByText("Borrador")).toBeInTheDocument();
  });

  it("muestra los 4 botones de acción", () => {
    renderCard(makeContent({ status: "pending" }));
    expect(screen.getByRole("button", { name: /confirmar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /editar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /descartar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /eliminar/i })).toBeInTheDocument();
  });

  it("Confirmar llama a confirmContent y onAction", async () => {
    const onAction = vi.fn();
    mockConfirm.mockResolvedValue({} as never);
    renderCard(makeContent({ status: "pending" }), onAction);
    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }));
    await waitFor(() => expect(mockConfirm).toHaveBeenCalledWith("col-1", "ent-1", "cnt-1"));
    expect(onAction).toHaveBeenCalledOnce();
  });

  it("Eliminar abre modal de confirmación y llama deleteContent al confirmar", async () => {
    mockDelete.mockResolvedValue(undefined);
    renderCard(makeContent({ status: "pending" }));
    await userEvent.click(screen.getByRole("button", { name: /eliminar/i }));
    const modalConfirmBtn = await screen.findAllByRole("button", { name: /confirmar/i });
    await userEvent.click(modalConfirmBtn[modalConfirmBtn.length - 1]);
    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith("col-1", "ent-1", "cnt-1"));
  });

  it("Descartar abre modal de confirmación y llama discardContent al confirmar", async () => {
    mockDiscard.mockResolvedValue({} as never);
    renderCard(makeContent({ status: "pending" }));
    await userEvent.click(screen.getByRole("button", { name: /descartar/i }));
    const modalConfirmBtn = await screen.findAllByRole("button", { name: /confirmar/i });
    await userEvent.click(modalConfirmBtn[modalConfirmBtn.length - 1]);
    await waitFor(() => expect(mockDiscard).toHaveBeenCalledWith("col-1", "ent-1", "cnt-1"));
  });

  it("error 409 de confirmContent muestra alerta warning", async () => {
    mockConfirm.mockRejectedValue(new ApiError(409, "Conflicto de contenido"));
    renderCard(makeContent({ status: "pending" }));
    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/Conflicto de contenido/);
    expect(alert.className).toMatch(/alert-warning/);
  });
});

// ── Confirmed ─────────────────────────────────────────────────────────────────

describe("ContentCard — confirmed", () => {
  it("muestra badge Confirmado", () => {
    renderCard(makeContent({ status: "confirmed" }));
    expect(screen.getByText("Confirmado")).toBeInTheDocument();
  });

  it("muestra Editar y Eliminar, no Confirmar ni Descartar", () => {
    renderCard(makeContent({ status: "confirmed" }));
    expect(screen.getByRole("button", { name: /editar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /eliminar/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /confirmar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /descartar/i })).not.toBeInTheDocument();
  });

  it("Editar abre modal y guardar llama updateContent", async () => {
    mockUpdate.mockResolvedValue({} as never);
    renderCard(makeContent({ status: "confirmed" }));
    await userEvent.click(screen.getByRole("button", { name: /editar/i }));
    const textarea = await screen.findByRole("textbox");
    await userEvent.clear(textarea);
    await userEvent.type(textarea, "Texto editado");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await waitFor(() =>
      expect(mockUpdate).toHaveBeenCalledWith("col-1", "ent-1", "cnt-1", {
        content: "Texto editado",
      }),
    );
  });
});

// ── Discarded ─────────────────────────────────────────────────────────────────

describe("ContentCard — discarded", () => {
  it("muestra badge Descartado", () => {
    renderCard(makeContent({ status: "discarded" }));
    expect(screen.getByText("Descartado")).toBeInTheDocument();
  });

  it("solo muestra botón Eliminar", () => {
    renderCard(makeContent({ status: "discarded" }));
    expect(screen.getByRole("button", { name: /eliminar/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /confirmar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /editar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /descartar/i })).not.toBeInTheDocument();
  });
});
