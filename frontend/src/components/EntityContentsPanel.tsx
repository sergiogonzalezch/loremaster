import { useEffect, useState, useCallback } from "react";
import { Alert, Card, Form, Nav } from "react-bootstrap";
import ContentCard from "./ContentCard";
import { PageSizeSelect } from "./FilterBar";
import LoadingSpinner from "./LoadingSpinner";
import PaginationControls from "./PaginationControls";
import { useEntityContents } from "../hooks/useEntityContents";
import type { EntityContent } from "../types";
import type { ContentCategory } from "../utils/enums";
import { CATEGORY_LABELS } from "../utils/constants";

interface Props {
  collectionId: string;
  entityId: string;
  availableCategories: ContentCategory[];
  selectedCategory: ContentCategory | "";
  refreshTrigger: number;
  onRefreshEntity: () => void;
  onPendingCountChange: (count: number) => void;
  onOpenImagePanel?: (content: EntityContent) => void;
}

export default function EntityContentsPanel({
  collectionId,
  entityId,
  availableCategories,
  selectedCategory,
  refreshTrigger,
  onRefreshEntity,
  onPendingCountChange,
  onOpenImagePanel,
}: Props) {
  const {
    contents,
    meta,
    loading,
    error,
    refresh,
    applyOptimisticUpdate,
    fetchPendingCount,
    clearError,
  } = useEntityContents(collectionId, entityId);

  const [categoryFilter, setCategoryFilter] = useState<ContentCategory | "">(
    "",
  );
  const [statusFilter, setStatusFilter] = useState<
    "pending" | "confirmed" | "discarded"
  >("pending");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Consulta al servidor el total real de pendientes en la categoría seleccionada.
  // Evita el bug de contar solo los ítems de la página visible cuando hay >pageSize pendientes.
  useEffect(() => {
    if (!selectedCategory) {
      onPendingCountChange(0);
      return;
    }
    fetchPendingCount(selectedCategory as ContentCategory).then(
      onPendingCountChange,
    );
  }, [selectedCategory, refreshTrigger, fetchPendingCount, onPendingCountChange]);

  useEffect(() => {
    const controller = new AbortController();
    refresh({
      signal: controller.signal,
      category: categoryFilter || undefined,
      status: statusFilter,
      page,
      page_size: pageSize,
    });
    return () => controller.abort();
  }, [categoryFilter, statusFilter, page, pageSize, refresh, refreshTrigger]);

  const handleContentAction = useCallback(async () => {
    await Promise.all([
      refresh({
        silent: true,
        category: categoryFilter || undefined,
        status: statusFilter,
        page,
        page_size: pageSize,
      }),
      onRefreshEntity(),
    ]);
  }, [categoryFilter, statusFilter, page, pageSize, refresh, onRefreshEntity]);

  return (
    <>
      <p className="lm-section-title">Contenidos generados</p>
      <Nav
        variant="tabs"
        activeKey={statusFilter}
        className="mb-3"
        onSelect={(key) => {
          if (!key) return;
          setStatusFilter(key as "pending" | "confirmed" | "discarded");
          setPage(1);
        }}
      >
        <Nav.Item>
          <Nav.Link eventKey="pending">Borradores</Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link eventKey="confirmed">Confirmados</Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link eventKey="discarded">Descartados</Nav.Link>
        </Nav.Item>
      </Nav>
      <Card className="mb-3">
        <Card.Body>
          <div className="d-flex justify-content-between flex-wrap align-items-end">
            <Form.Group style={{ minWidth: 240 }}>
              <Form.Label>Filtrar por categoría</Form.Label>
              <Form.Select
                value={categoryFilter}
                onChange={(e) => {
                  setCategoryFilter(e.target.value as ContentCategory | "");
                  setPage(1);
                }}
              >
                <option value="">Todas</option>
                {availableCategories.map((cat) => (
                  <option key={cat} value={cat}>
                    {CATEGORY_LABELS[cat]}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
            <PageSizeSelect
              value={pageSize}
              onChange={(size) => {
                setPageSize(size);
                setPage(1);
              }}
            />
          </div>
        </Card.Body>
      </Card>
      {error && (
        <Alert variant="danger" onClose={clearError} dismissible>
          {error}
        </Alert>
      )}
      {loading ? (
        <LoadingSpinner text="Cargando contenidos..." />
      ) : contents.length === 0 ? (
        <div className="lm-empty">
          <span className="lm-empty-glyph">✦</span>
          <p>No hay contenidos todavía.</p>
          <p>Genera el primero usando el formulario de arriba.</p>
        </div>
      ) : (
        <>
          {contents.map((content) => (
            <ContentCard
              key={content.id}
              content={content}
              collectionId={collectionId}
              entityId={entityId}
              onAction={handleContentAction}
              onOptimisticUpdate={applyOptimisticUpdate}
              onOpenImagePanel={onOpenImagePanel}
            />
          ))}
          <PaginationControls
            page={page}
            totalPages={meta.total_pages}
            onPageChange={setPage}
          />
        </>
      )}
    </>
  );
}
