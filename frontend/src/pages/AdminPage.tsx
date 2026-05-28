import { useEffect, useState, useCallback, useReducer } from "react";
import type { Reducer } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
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
import SafeImage from "../components/SafeImage";
import { parseApiError } from "../utils/errors";
import { formatDate } from "../utils/formatters";
import type { UserAdminRecord } from "../types/user";

const PAGE_SIZE = 20;

type ListState = {
  users: UserAdminRecord[];
  total: number;
  loading: boolean;
  error: string | null;
};

type ListAction =
  | { type: "FETCH_START" }
  | { type: "FETCH_SUCCESS"; users: UserAdminRecord[]; total: number }
  | { type: "FETCH_ERROR"; error: string }
  | { type: "DISMISS_ERROR" };

const listReducer: Reducer<ListState, ListAction> = (state, action) => {
  switch (action.type) {
    case "FETCH_START":
      return { ...state, loading: true, error: null };
    case "FETCH_SUCCESS":
      return {
        users: action.users,
        total: action.total,
        loading: false,
        error: null,
      };
    case "FETCH_ERROR":
      return { ...state, loading: false, error: action.error };
    case "DISMISS_ERROR":
      return { ...state, error: null };
  }
};

type DeleteState = {
  target: UserAdminRecord | null;
  deleting: boolean;
};

type DeleteAction =
  | { type: "OPEN"; target: UserAdminRecord }
  | { type: "CANCEL" }
  | { type: "START" }
  | { type: "DONE" };

const deleteReducer: Reducer<DeleteState, DeleteAction> = (state, action) => {
  switch (action.type) {
    case "OPEN":
      return { target: action.target, deleting: false };
    case "CANCEL":
      return { target: null, deleting: false };
    case "START":
      return { ...state, deleting: true };
    case "DONE":
      return { target: null, deleting: false };
  }
};

/**
 * Panel de administración para gestionar usuarios del sistema.
 *
 * Muestra un listado paginado de todos los usuarios registrados
 * con información de roles, estados y fechas. Permite a los
 * administradores eliminar (desactivar) cuentas de usuario.
 */
export default function AdminPage() {
  const { user: currentUser } = useAuth();
  const [list, dispatchList] = useReducer(listReducer, {
    users: [],
    total: 0,
    loading: true,
    error: null,
  });
  const { users, total, loading, error } = list;
  const [page, setPage] = useState(1);
  const [del, dispatchDel] = useReducer(deleteReducer, {
    target: null,
    deleting: false,
  });

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const fetchUsers = useCallback(async () => {
    dispatchList({ type: "FETCH_START" });
    try {
      const res = await getAdminUsers({ page, page_size: PAGE_SIZE });
      dispatchList({
        type: "FETCH_SUCCESS",
        users: res.data,
        total: res.meta.total,
      });
    } catch (e) {
      dispatchList({ type: "FETCH_ERROR", error: parseApiError(e).text });
    }
  }, [page]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  async function handleDelete() {
    if (!del.target) return;
    dispatchDel({ type: "START" });
    try {
      await adminDeleteUser(del.target.id);
      dispatchDel({ type: "DONE" });
      await fetchUsers();
    } catch (e) {
      dispatchList({ type: "FETCH_ERROR", error: parseApiError(e).text });
      dispatchDel({ type: "DONE" });
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
        <Alert
          variant="warning"
          dismissible
          onClose={() => dispatchList({ type: "DISMISS_ERROR" })}
        >
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
                  <th className="pe-4" aria-label="Acciones"></th>
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
                      <div className="d-flex align-items-center gap-2">
                        {u.avatar_url ? (
                          <SafeImage
                            src={u.avatar_url}
                            alt={u.username}
                            style={{
                              width: 32,
                              height: 32,
                              borderRadius: "50%",
                              objectFit: "cover",
                              flexShrink: 0,
                            }}
                          />
                        ) : (
                          <div
                            className="lm-avatar-initials"
                            style={{
                              width: 32,
                              height: 32,
                              fontSize: "0.75rem",
                            }}
                          >
                            {u.username.slice(0, 2).toUpperCase()}
                          </div>
                        )}
                        <div>
                          <div className="d-flex align-items-center gap-1">
                            <Link
                              to={`/users/${u.username}`}
                              style={{
                                fontWeight: 600,
                                color: "var(--lm-text)",
                                textDecoration: "none",
                              }}
                              onMouseEnter={(e) =>
                                (e.currentTarget.style.color =
                                  "var(--lm-accent)")
                              }
                              onMouseLeave={(e) =>
                                (e.currentTarget.style.color = "var(--lm-text)")
                              }
                            >
                              {u.username}
                            </Link>
                            {u.id === currentUser?.id && (
                              <small
                                style={{
                                  color: "var(--lm-accent)",
                                  fontSize: "0.75rem",
                                }}
                              >
                                (tú)
                              </small>
                            )}
                          </div>
                          {u.display_name && (
                            <div>
                              <small className="text-muted">
                                {u.display_name}
                              </small>
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="py-3 text-muted">
                      {u.email ?? <span style={{ opacity: 0.4 }}>-</span>}
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
                      {!u.is_deleted && u.id !== currentUser?.id && (
                        <Button
                          variant="outline-danger"
                          size="sm"
                          onClick={() =>
                            dispatchDel({ type: "OPEN", target: u })
                          }
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
        show={del.target !== null}
        title="Eliminar usuario"
        message={`¿Eliminar a "${del.target?.username}"? El usuario quedará desactivado y no podrá iniciar sesión.`}
        onConfirm={handleDelete}
        onCancel={() => dispatchDel({ type: "CANCEL" })}
        loading={del.deleting}
        variant="danger"
      />
    </div>
  );
}
