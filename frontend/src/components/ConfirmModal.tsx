import { Modal, Button, Spinner } from "react-bootstrap";

interface ConfirmModalProps {
  show: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  variant?: string;
  loading?: boolean;
}

export default function ConfirmModal({
  show,
  title,
  message,
  onConfirm,
  onCancel,
  variant = "danger",
  loading = false,
}: ConfirmModalProps) {
  return (
    <Modal show={show} onHide={onCancel} centered>
      <Modal.Header closeButton={!loading}>
        <Modal.Title>{title}</Modal.Title>
      </Modal.Header>
      <Modal.Body>{message}</Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onCancel} disabled={loading}>
          Cancelar
        </Button>
        <Button variant={variant} onClick={onConfirm} disabled={loading}>
          {loading ? (
            <>
              <Spinner animation="border" size="sm" className="me-2" />
              Eliminando…
            </>
          ) : (
            "Confirmar"
          )}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
