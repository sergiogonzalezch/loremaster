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

export default function ModelSelector({ disabled, onChange }: Props) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    getModels()
      .then((list) => {
        if (!list.length) return;
        setModels(list);
        setVisible(true);

        const stored = localStorage.getItem(STORAGE_KEY);
        const initial =
          (stored && list.find((m) => m.name === stored)?.name) ||
          list.find((m) => m.is_default)?.name ||
          list[0].name;

        setSelected(initial);
        // Only propagate non-default selection to avoid adding noise to requests
        const defaultModel = list.find((m) => m.is_default)?.name;
        onChange(initial !== defaultModel ? initial : undefined);
      })
      .catch(() => {
        // Si Ollama no responde, el selector permanece oculto y el backend usa su default
      });
  }, [onChange]);

  if (!visible) return null;

  function handleChange(name: string) {
    setSelected(name);
    localStorage.setItem(STORAGE_KEY, name);
    const defaultModel = models.find((m) => m.is_default)?.name;
    onChange(name !== defaultModel ? name : undefined);
  }

  return (
    <Form.Group style={{ minWidth: 220 }}>
      <Form.Label className="fw-semibold">Modelo</Form.Label>
      <Form.Select
        value={selected}
        onChange={(e) => handleChange(e.target.value)}
        disabled={disabled}
        size="sm"
      >
        {models.map((m) => (
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
