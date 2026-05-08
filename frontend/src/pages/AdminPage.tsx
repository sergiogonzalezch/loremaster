import { useEffect, useState, useCallback } from "react";
import {
  Table,
  Badge,
  Button,
  Alert,
  Spinner,
  Pagination,
  Card,
} from "react-bootstrap";
import { getAdminUsers, adminDeleteUser } from "../api/admin";
import ConfirmModal from "../components/ConfirmModal";
import { parseApiError } from "../utils/errors";
import { formatDate } from "../utils/formatters";
import type { UserAdminRecord } from "../types/user";

const PAGE_SIZE = 20;

export default function AdminPage() {
  const [users, setUsers] = useState<UserAdminRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<UserAdminRecord | null>(
    null,
  );
  const [deleting, setDeleting] = useState(false);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAdminUsers({ page, page_size: PAGE_SIZE });
      setUsers(res.data);
      setTotal(res.meta.total);
    } catch (e) {
      setError(parseApiError(e).text);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await adminDeleteUser(deleteTarget.id);
      setDeleteTarget(null);
      await fetchUsers();
    } catch (e) {
      setError(parseApiError(e).text);
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="lm-page">
      <div className="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h2 className="mb-0" style={{ fontFamily: "var(--lm-font-head)" }}>
            Panel de{" "}
            <span style={{ color: "var(--lm-accent)" }}>administración</span>
          </h2>
          {!loading && (
            <small className="text-muted">{total} usuarios registrados</small>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="warning" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Card>
        <Card.Body className="p-0">
          {loading ? (
            <div className="d-flex justify-content-center py-5">
              <Spinner
                animation="border"
                style={{ color: "var(--lm-accent)" }}
              />
            </div>
          ) : users.length === 0 ? (
            <p className="text-muted text-center py-4 mb-0">No hay usuarios.</p>
          ) : (
            <Table
              hover
              responsive
              className="mb-0"
              style={{ fontSize: "0.875rem" }}
            >
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
                  <th className="ps-4">Usuario</th>
                  <th>Email</th>
                  <th>Rol</th>
                  <th>Estado</th>
                  <th>Registrado</th>
                  <th className="pe-4"></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr
                    key={u.id}
                    style={{
                      opacity: u.is_deleted ? 0.45 : 1,
                    }}
                  >
                    <td className="ps-4 py-3">
                      <div style={{ fontWeight: 600 }}>{u.username}</div>
                      {u.display_name && (
                        <small className="text-muted">{u.display_name}</small>
                      )}
                    </td>
                    <td className="py-3 text-muted">
                      {u.email ?? <span style={{ opacity: 0.4 }}>—</span>}
                    </td>
                    <td className="py-3">
                      {u.is_admin ? (
                        <Badge
                          style={{
                            backgroundColor: "var(--lm-accent)",
                            color: "#000",
                          }}
                        >
                          Admin
                        </Badge>
                      ) : (
                        <Badge bg="secondary">Usuario</Badge>
                      )}
                    </td>
                    <td className="py-3">
                      {u.is_deleted ? (
                        <Badge bg="danger">Eliminado</Badge>
                      ) : (
                        <Badge bg="success">Activo</Badge>
                      )}
                    </td>
                    <td className="py-3 text-muted">
                      {formatDate(u.created_at)}
                    </td>
                    <td className="pe-4 py-3 text-end">
                      {!u.is_deleted && (
                        <Button
                          variant="outline-danger"
                          size="sm"
                          onClick={() => setDeleteTarget(u)}
                        >
                          Eliminar
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>

      {totalPages > 1 && (
        <div className="d-flex justify-content-center mt-4">
          <Pagination>
            <Pagination.Prev
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            />
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <Pagination.Item
                key={p}
                active={p === page}
                onClick={() => setPage(p)}
              >
                {p}
              </Pagination.Item>
            ))}
            <Pagination.Next
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            />
          </Pagination>
        </div>
      )}

      <ConfirmModal
        show={deleteTarget !== null}
        title="Eliminar usuario"
        message={`¿Eliminar a "${deleteTarget?.username}"? El usuario quedará desactivado y no podrá iniciar sesión.`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        loading={deleting}
        variant="danger"
      />
    </div>
  );
}
