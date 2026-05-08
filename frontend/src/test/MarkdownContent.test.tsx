import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import MarkdownContent from "../components/MarkdownContent";

function renderMd(content: string) {
  return render(<MarkdownContent>{content}</MarkdownContent>);
}

describe("MarkdownContent — sanitización XSS", () => {
  it("elimina etiquetas <script> del DOM", () => {
    const { container } = renderMd(
      "contenido seguro\n\n<script>alert('xss')</script>",
    );
    expect(container.querySelector("script")).toBeNull();
  });

  it("elimina elementos <img> con atributos de evento inline (onerror)", () => {
    const { container } = renderMd(
      '<img src="x" onerror="alert(1)" alt="imagen">',
    );
    const img = container.querySelector("img");
    // rehypeSanitize elimina el elemento entero o el atributo peligroso
    expect(img === null || img.getAttribute("onerror") === null).toBe(true);
  });

  it("elimina hrefs con protocolo javascript:", () => {
    const { container } = renderMd("[clic aquí](javascript:alert(1))");
    const anchor = container.querySelector("a");
    const href = anchor?.getAttribute("href") ?? "";
    expect(href).not.toMatch(/^javascript:/i);
  });

  it("permite markdown estándar (negrita, cursiva, listas)", () => {
    const { container } = renderMd(
      "**negrita** *cursiva*\n\n- ítem 1\n- ítem 2",
    );
    expect(container.querySelector("strong")).not.toBeNull();
    expect(container.querySelector("em")).not.toBeNull();
    expect(container.querySelector("li")).not.toBeNull();
  });

  it("permite hrefs https normales", () => {
    const { container } = renderMd("[enlace](https://example.com)");
    const anchor = container.querySelector("a");
    expect(anchor?.getAttribute("href")).toBe("https://example.com");
  });
});
