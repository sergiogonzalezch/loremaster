import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ImagePreviewCard from "../components/ImagePreviewCard";
import type { GenerateImageResponse } from "../types";
import { ApiError } from "../api/apiClient";

vi.mock("../api/images", () => ({
  generateImage: vi.fn(),
}));

import * as imagesApi from "../api/images";

const mockGenerateImage = vi.mocked(imagesApi.generateImage);

function makeImageResponse(
  overrides: Partial<GenerateImageResponse> = {},
): GenerateImageResponse {
  return {
    image_url: "https://placehold.co/1024x1024?text=Aragorn",
    visual_prompt:
      "fantasy character portrait, Aragorn, ranger of the north, high quality",
    token_count: 60,
    truncated: false,
    prompt_source: "content",
    seed: 42,
    backend: "mock",
    generation_ms: 0,
    entity_id: "ent-1",
    collection_id: "col-1",
    content_id: "cnt-1",
    ...overrides,
  };
}

function renderCard(confirmedContentId?: string) {
  return render(
    <ImagePreviewCard
      collectionId="col-1"
      entityId="ent-1"
      entityName="Aragorn"
      confirmedContentId={confirmedContentId}
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

// ── Estado inicial ─────────────────────────────────────────────────────────────

describe("ImagePreviewCard — estado inicial", () => {
  it("IP-01: muestra placeholder y botón Generar preview", () => {
    renderCard();
    expect(screen.getByText(/sin preview generado/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /generar preview/i }),
    ).toBeInTheDocument();
  });

  it("IP-02: el botón Generar está habilitado al inicio", () => {
    renderCard();
    expect(
      screen.getByRole("button", { name: /generar preview/i }),
    ).not.toBeDisabled();
  });
});

// ── Llamada a la API ───────────────────────────────────────────────────────────

describe("ImagePreviewCard — llamada a API", () => {
  it("IP-03: Generar llama a generateImage con los ids correctos", async () => {
    mockGenerateImage.mockResolvedValue(makeImageResponse());
    renderCard("cnt-1");
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await waitFor(() =>
      expect(mockGenerateImage).toHaveBeenCalledWith("col-1", "ent-1", {
        content_id: "cnt-1",
      }),
    );
  });

  it("IP-04: sin confirmedContentId llama a generateImage con content_id undefined", async () => {
    mockGenerateImage.mockResolvedValue(makeImageResponse());
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await waitFor(() =>
      expect(mockGenerateImage).toHaveBeenCalledWith("col-1", "ent-1", {
        content_id: undefined,
      }),
    );
  });
});

// ── Estado de carga ────────────────────────────────────────────────────────────

describe("ImagePreviewCard — carga", () => {
  it("IP-05: muestra spinner y deshabilita botón durante la carga", async () => {
    let resolve!: (v: GenerateImageResponse) => void;
    mockGenerateImage.mockReturnValue(
      new Promise<GenerateImageResponse>((r) => {
        resolve = r;
      }),
    );
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    expect(screen.getByRole("button", { name: /generando/i })).toBeDisabled();
    resolve(makeImageResponse());
  });
});

// ── Estado exitoso ─────────────────────────────────────────────────────────────

describe("ImagePreviewCard — éxito", () => {
  it("IP-06: muestra imagen con alt que incluye el nombre de la entidad", async () => {
    mockGenerateImage.mockResolvedValue(makeImageResponse());
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    const img = await screen.findByRole("img");
    expect(img).toHaveAttribute(
      "src",
      "https://placehold.co/1024x1024?text=Aragorn",
    );
    expect(img).toHaveAttribute("alt", expect.stringMatching(/Aragorn/i));
  });

  it("IP-07: muestra badge con el backend (MOCK)", async () => {
    mockGenerateImage.mockResolvedValue(makeImageResponse({ backend: "mock" }));
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await screen.findByRole("img");
    expect(screen.getByText("MOCK")).toBeInTheDocument();
  });

  it("IP-08: muestra conteo de tokens", async () => {
    mockGenerateImage.mockResolvedValue(makeImageResponse({ token_count: 60 }));
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await screen.findByRole("img");
    expect(screen.getByText(/~60 tokens/i)).toBeInTheDocument();
  });

  it("IP-09: botón cambia a Regenerar preview tras éxito", async () => {
    mockGenerateImage.mockResolvedValue(makeImageResponse());
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await screen.findByRole("img");
    expect(
      screen.getByRole("button", { name: /regenerar preview/i }),
    ).toBeInTheDocument();
  });

  it("IP-10: muestra advertencia de tokens cuando token_count > 100", async () => {
    mockGenerateImage.mockResolvedValue(
      makeImageResponse({ token_count: 120 }),
    );
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await screen.findByRole("img");
    expect(
      screen.getByText(/considera usar contenido más conciso/i),
    ).toBeInTheDocument();
  });

  it("IP-11: NO muestra advertencia de tokens cuando token_count <= 100", async () => {
    mockGenerateImage.mockResolvedValue(makeImageResponse({ token_count: 80 }));
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await screen.findByRole("img");
    expect(
      screen.queryByText(/considera usar contenido más conciso/i),
    ).not.toBeInTheDocument();
  });

  it("IP-12: muestra badge 'prompt truncado' cuando truncated=true", async () => {
    mockGenerateImage.mockResolvedValue(makeImageResponse({ truncated: true }));
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await screen.findByRole("img");
    expect(screen.getByText(/prompt truncado/i)).toBeInTheDocument();
  });

  it("IP-13: NO muestra badge 'prompt truncado' cuando truncated=false", async () => {
    mockGenerateImage.mockResolvedValue(
      makeImageResponse({ truncated: false }),
    );
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await screen.findByRole("img");
    expect(screen.queryByText(/prompt truncado/i)).not.toBeInTheDocument();
  });

  it("IP-14: el resumen del prompt colapsable está disponible tras éxito", async () => {
    mockGenerateImage.mockResolvedValue(makeImageResponse());
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await screen.findByRole("img");
    expect(screen.getByText(/ver prompt visual generado/i)).toBeInTheDocument();
  });

  it("IP-15: la fuente del prompt se muestra correctamente (contenido RAG)", async () => {
    mockGenerateImage.mockResolvedValue(
      makeImageResponse({ prompt_source: "content" }),
    );
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await screen.findByRole("img");
    expect(screen.getByText(/contenido rag/i)).toBeInTheDocument();
  });

  it("IP-16: fuente 'description' muestra 'descripción de entidad'", async () => {
    mockGenerateImage.mockResolvedValue(
      makeImageResponse({ prompt_source: "description" }),
    );
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await screen.findByRole("img");
    expect(screen.getByText(/descripción de entidad/i)).toBeInTheDocument();
  });
});

// ── Estado de error ────────────────────────────────────────────────────────────

describe("ImagePreviewCard — error", () => {
  it("IP-17: error 422 muestra alerta de advertencia", async () => {
    mockGenerateImage.mockRejectedValue(
      new ApiError(422, "La entidad no tiene contenido confirmado."),
    );
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    const alert = await screen.findByRole("alert");
    expect(alert).toBeInTheDocument();
  });

  it("IP-18: el alert de error se puede cerrar", async () => {
    mockGenerateImage.mockRejectedValue(new ApiError(500, "Error interno"));
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    const alert = await screen.findByRole("alert");
    const closeBtn = alert.querySelector("button[aria-label='Close']");
    if (closeBtn) {
      await userEvent.click(closeBtn);
      await waitFor(() =>
        expect(screen.queryByRole("alert")).not.toBeInTheDocument(),
      );
    }
  });

  it("IP-19: tras error el placeholder sigue visible (no imagen)", async () => {
    mockGenerateImage.mockRejectedValue(new ApiError(422, "Sin contenido"));
    renderCard();
    await userEvent.click(
      screen.getByRole("button", { name: /generar preview/i }),
    );
    await screen.findByRole("alert");
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText(/sin preview generado/i)).toBeInTheDocument();
  });
});
