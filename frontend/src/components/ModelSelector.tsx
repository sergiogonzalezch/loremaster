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

type ModelSelectorState = {
  models: ModelInfo[];
  selected: string;
  visible: boolean;
};

export default function ModelSelector({ disabled, onChange }: Props) {
  // Agrupar models/selected/visible — los 3 se transicionan juntos al cargar.
  const [state, setState] = useState<ModelSelectorState>({
    models: [],
    selected: "",
    visible: false,
  });

  useEffect(() => {
    getModels()
      .then((list) => {
        if (!list.length) return;
        const stored = localStorage.getItem(STORAGE_KEY);
        const initial =
          (stored && list.find((m) => m.name === stored)?.name) ||
          list.find((m) => m.is_default)?.name ||
          list[0].name;

        // Una sola transición — evita 3 renders consecutivos.
        setState({ models: list, selected: initial, visible: true });

        // Only propagate non-default selection to avoid adding noise to requests
        const defaultModel = list.find((m) => m.is_default)?.name;
        onChange(initial !== defaultModel ? initial : undefined);
      })
      .catch(() => {
        // Si Ollama no responde, el selector permanece oculto y el backend usa su default
      });
  }, [onChange]);

  if (!state.visible) return null;

  function handleChange(name: string) {
    setState((prev) => ({ ...prev, selected: name }));
    localStorage.setItem(STORAGE_KEY, name);
    const defaultModel = state.models.find((m) => m.is_default)?.name;
    onChange(name !== defaultModel ? name : undefined);
  }

  return (
    <Form.Group style={{ minWidth: 220 }}>
      <Form.Label className="fw-semibold">Modelo</Form.Label>
      <Form.Select
        value={state.selected}
        onChange={(e) => handleChange(e.target.value)}
        disabled={disabled}
        size="sm"
      >
        {state.models.map((m) => (
          <option key={m.name} value={m.name}>
            {m.name}
            {m.is_default ? " (predeterminado)" : ""}
            {m.size ? ` — ${formatSize(m.size)}` : ""}
          </option>
        ))}
      </Form.Select>
    </Form.Group>
  );
}
