import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ConfirmModal from "../components/ConfirmModal";

function renderModal(props: Partial<Parameters<typeof ConfirmModal>[0]> = {}) {
  const defaults = {
    show: true,
    title: "Título del modal",
    message: "¿Confirmas esta acción?",
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  };
  return render(<ConfirmModal {...defaults} {...props} />);
}

describe("ConfirmModal", () => {
  it("renderiza el título y el mensaje cuando show=true", () => {
    renderModal();
    expect(screen.getByText("Título del modal")).toBeInTheDocument();
    expect(screen.getByText("¿Confirmas esta acción?")).toBeInTheDocument();
  });

  it("no es visible cuando show=false", () => {
    renderModal({ show: false });
    expect(screen.queryByText("Título del modal")).not.toBeInTheDocument();
  });

  it("botón Confirmar llama a onConfirm", async () => {
    const onConfirm = vi.fn();
    renderModal({ onConfirm });
    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("botón Cancelar llama a onCancel", async () => {
    const onCancel = vi.fn();
    renderModal({ onCancel });
    await userEvent.click(screen.getByRole("button", { name: /cancelar/i }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("usa variant danger por defecto en el botón de confirmación", () => {
    renderModal();
    const btn = screen.getByRole("button", { name: /confirmar/i });
    expect(btn.className).toMatch(/btn-danger/);
  });

  it("usa variant personalizado en el botón de confirmación", () => {
    renderModal({ variant: "warning" });
    const btn = screen.getByRole("button", { name: /confirmar/i });
    expect(btn.className).toMatch(/btn-warning/);
  });
});
