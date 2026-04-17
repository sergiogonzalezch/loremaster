import { Spinner } from "react-bootstrap";

interface LoadingSpinnerProps {
  text?: string;
}

export default function LoadingSpinner({ text = "Cargando..." }: LoadingSpinnerProps) {
  return (
    <div className="d-flex align-items-center justify-content-center gap-2 py-5">
      <Spinner animation="border" role="status" />
      <span>{text}</span>
    </div>
  );
}