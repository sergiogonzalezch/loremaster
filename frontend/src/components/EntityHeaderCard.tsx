import { Badge, Button, Card } from "react-bootstrap";
import type { Entity } from "../types";
import { ENTITY_TYPE_BADGE, ENTITY_TYPE_LABELS } from "../utils/constants";
import { formatDate } from "../utils/formatters";
import MarkdownContent from "./MarkdownContent";

interface Props {
  entity: Entity;
  onEdit: () => void;
}

export default function EntityHeaderCard({ entity, onEdit }: Props) {
  return (
    <Card className="mb-4">
      <Card.Body>
        <div className="d-flex justify-content-between align-items-start">
          <div>
            <div className="mb-2">
              <Badge bg={ENTITY_TYPE_BADGE[entity.type]} className="me-2">
                {ENTITY_TYPE_LABELS[entity.type]}
              </Badge>
            </div>
            <h3 className="mb-1">{entity.name}</h3>
            {entity.description ? (
              <MarkdownContent>{entity.description}</MarkdownContent>
            ) : (
              <p className="text-muted mb-0">
                <em>Sin descripción</em>
              </p>
            )}
            <div className="mt-2 d-flex gap-3">
              <small className="text-muted">
                Creada: {formatDate(entity.created_at)}
              </small>
              {entity.updated_at && (
                <small className="text-muted">
                  Editada: {formatDate(entity.updated_at, true)}
                </small>
              )}
            </div>
          </div>
          <Button variant="outline-secondary" size="sm" onClick={onEdit}>
            Editar
          </Button>
        </div>
      </Card.Body>
    </Card>
  );
}
