import { useEffect, useState } from "react";
import { Form } from "react-bootstrap";
import { getModels } from "../api/models";
import type { ModelInfo } from "../api/models";

const STORAGE_KEY = "lm_selected_model";

interface Props {
  disabled?: boolean;
  onChange: (model: string | undefined) => void;
}

function formatSize(bytes: number): string {
  const gb = bytes / 1_073_741_824;
  return gb >= 1
    ? `${gb.toFixed(1)} GB`
    : `${(bytes / 1_048_576).toFixed(0)} MB`;
}

// phase tri-state evita el "pop" del null→render: durante "loading"
// renderiza un Select deshabilitado con placeholder (reserva el espacio).
// Si la API falla → "hidden" (no ocupa espacio; backend usa su default).
type Phase = "loading" | "ready" | "hidden";

type ModelSelectorState = {
  phase: Phase;
  models: ModelInfo[];
  selected: string;
};

export default function ModelSelector({ disabled, onChange }: Props) {
  const [state, setState] = useState<ModelSelectorState>({
    phase: "loading",
    models: [],
    selected: "",
  });

  useEffect(() => {
    getModels()
      .then((list) => {
        if (!list.length) {
          setState({ phase: "hidden", models: [], selected: "" });
          return;
        }
        const stored = localStorage.getItem(STORAGE_KEY);
        const initial =
          (stored && list.find((m) => m.name === stored)?.name) ||
          list.find((m) => m.is_default)?.name ||
          list[0].name;

        setState({ phase: "ready", models: list, selected: initial });

        // Only propagate non-default selection to avoid adding noise to requests
        const defaultModel = list.find((m) => m.is_default)?.name;
        onChange(initial !== defaultModel ? initial : undefined);
      })
      .catch(() => {
        // Si Ollama no responde, el selector se oculta y el backend usa su default
        setState({ phase: "hidden", models: [], selected: "" });
      });
  }, [onChange]);

  if (state.phase === "hidden") return null;

  function handleChange(name: string) {
    setState((prev) => ({ ...prev, selected: name }));
    localStorage.setItem(STORAGE_KEY, name);
    const defaultModel = state.models.find((m) => m.is_default)?.name;
    onChange(name !== defaultModel ? name : undefined);
  }

  const isLoading = state.phase === "loading";

  return (
    <Form.Group style={{ minWidth: 220 }}>
      <Form.Label className="fw-semibold">Modelo</Form.Label>
      <Form.Select
        value={state.selected}
        onChange={(e) => handleChange(e.target.value)}
        disabled={disabled || isLoading}
        size="sm"
      >
        {isLoading ? (
          <option>Cargando modelos…</option>
        ) : (
          state.models.map((m) => (
            <option key={m.name} value={m.name}>
              {m.name}
              {m.is_default ? " (predeterminado)" : ""}
              {m.size ? ` — ${formatSize(m.size)}` : ""}
            </option>
          ))
        )}
      </Form.Select>
    </Form.Group>
  );
}
