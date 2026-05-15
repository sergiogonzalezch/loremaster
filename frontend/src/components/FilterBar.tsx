import { Form } from "react-bootstrap";

interface PageSizeSelectProps {
  value: number;
  onChange: (size: number) => void;
  sizes?: number[];
}

export function PageSizeSelect({
  value,
  onChange,
  sizes = [5, 10, 20, 50],
}: PageSizeSelectProps) {
  return (
    <Form.Group style={{ minWidth: 130 }}>
      <Form.Label>Page size</Form.Label>
      <Form.Select
        value={String(value)}
        onChange={(e) => {
          onChange(Number(e.target.value));
        }}
      >
        {sizes.map((size) => (
          <option key={size} value={size}>
            {size}
          </option>
        ))}
      </Form.Select>
    </Form.Group>
  );
}

interface OrderSelectProps {
  value: "asc" | "desc";
  onChange: (order: "asc" | "desc") => void;
}

export function OrderSelect({ value, onChange }: OrderSelectProps) {
  return (
    <Form.Group style={{ minWidth: 160 }}>
      <Form.Label>Orden</Form.Label>
      <Form.Select
        value={value}
        onChange={(e) => onChange(e.target.value as "asc" | "desc")}
      >
        <option value="desc">Más recientes</option>
        <option value="asc">Más antiguos</option>
      </Form.Select>
    </Form.Group>
  );
}
