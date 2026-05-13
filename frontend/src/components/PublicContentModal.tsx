import { Modal, Badge } from "react-bootstrap";
import { Link } from "react-router-dom";
import MarkdownContent from "./MarkdownContent";
import { formatDate } from "../utils/formatters";
import { CATEGORY_LABELS, ENTITY_TYPE_LABELS } from "../utils/constants";

interface Props {
  show: boolean;
  onHide: () => void;
  content: string;
  category: string;
  entityName: string;
  entityType: string;
  ownerUsername: string;
  ownerDisplayName: string | null;
  confirmedAt: string | null;
  createdAt: string;
}

export default function PublicContentModal({
  show,
  onHide,
  content,
  category,
  entityName,
  entityType,
  ownerUsername,
  confirmedAt,
  createdAt,
}: Props) {
  return (
    <Modal show={show} onHide={onHide} size="lg" centered scrollable>
      <Modal.Header
        closeButton
        style={{ borderBottom: "1px solid var(--lm-border)" }}
      >
        <div className="d-flex flex-column gap-1">
          <div className="d-flex align-items-center gap-2 flex-wrap">
            <Badge bg="dark" style={{ fontSize: "0.65rem" }}>
              {CATEGORY_LABELS[category as keyof typeof CATEGORY_LABELS] ??
                category}
            </Badge>
            <Badge
              style={{
                background: "var(--lm-accent-glow)",
                color: "var(--lm-accent)",
                border: "1px solid var(--lm-border-accent)",
                fontSize: "0.6rem",
              }}
            >
              {ENTITY_TYPE_LABELS[
                entityType as keyof typeof ENTITY_TYPE_LABELS
              ] ?? entityType}
            </Badge>
          </div>
          <Modal.Title
            style={{ fontFamily: "var(--lm-font-head)", fontSize: "1.1rem" }}
          >
            {entityName}
          </Modal.Title>
          <div style={{ fontSize: "0.78rem" }}>
            <Link
              to={`/users/${ownerUsername}`}
              onClick={onHide}
              style={{ color: "var(--lm-accent)", textDecoration: "none" }}
            >
              @{ownerUsername}
            </Link>
            <span className="text-muted ms-2">
              {confirmedAt ? formatDate(confirmedAt) : formatDate(createdAt)}
            </span>
          </div>
        </div>
      </Modal.Header>
      <Modal.Body style={{ fontSize: "0.9rem" }}>
        <MarkdownContent>{content}</MarkdownContent>
      </Modal.Body>
    </Modal>
  );
}
