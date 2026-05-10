/**
 * Configuración de Vitest: importa matchers adicionales de jest-dom.
 */

import "@testing-library/jest-dom";

class MockEventSource {
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
}

Object.defineProperty(globalThis, "EventSource", {
  writable: true,
  value: vi.fn().mockImplementation(() => new MockEventSource()),
});
