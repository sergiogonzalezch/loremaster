import { Spinner } from "react-bootstrap";

interface LoadingSpinnerProps {
  text?: string;
}

export default function LoadingSpinner({
  text = "Cargando...",
}: LoadingSpinnerProps) {
  return (
    <div className="d-flex align-items-center justify-content-center gap-2 py-5 text-muted">
      <Spinner animation="border" role="status" size="sm" />
      <span
        style={{
          fontFamily: "'Cinzel', serif",
          fontSize: "0.72rem",
          letterSpacing: "0.15em",
          textTransform: "uppercase",
        }}
      >
        {text}
      </span>
    </div>
  );
}
