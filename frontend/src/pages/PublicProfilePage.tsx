import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Container, Row, Col, Card, Alert, Spinner } from "react-bootstrap";
import { getPublicProfile } from "../api/users";
import StarfieldCanvas from "../components/StarfieldCanvas";
import { useAuth } from "../hooks/useAuth";
import { parseApiError } from "../utils/errors";
import type { PublicProfile } from "../types/user";

export default function PublicProfilePage() {
  const { username } = useParams<{ username: string }>();
  const { user } = useAuth();
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!username) return;
    setLoading(true);
    setError(null);
    getPublicProfile(username)
      .then(setProfile)
      .catch((e) => setError(parseApiError(e).text))
      .finally(() => setLoading(false));
  }, [username]);

  const initials = (profile?.display_name ?? profile?.username ?? "?")
    .slice(0, 2)
    .toUpperCase();

  function collectionHref(id: string) {
    return user ? `/collections/${id}` : "/login";
  }

  function collectionState(id: string) {
    return user ? undefined : { from: `/collections/${id}` };
  }

  return (
    <>
      <StarfieldCanvas />
      <div style={{ position: "relative", zIndex: 1, minHeight: "100vh" }}>
        <nav
          style={{
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            backdropFilter: "blur(8px)",
            backgroundColor: "rgba(10,10,18,0.7)",
          }}
          className="py-3"
        >
          <Container
            fluid="lg"
            className="d-flex align-items-center justify-content-between"
          >
            <Link to="/feed" style={{ textDecoration: "none" }}>
              <span className="lm-brand-glyph" style={{ fontSize: "1.1rem" }}>
                ✦
              </span>{" "}
              <span
                style={{
                  fontFamily: "var(--lm-font-head)",
                  fontSize: "1.1rem",
                }}
              >
                <span style={{ color: "var(--lm-accent)" }}>Lore</span>Master
              </span>
            </Link>
            {user ? (
              <Link
                to="/"
                className="btn btn-sm btn-warning"
                style={{ fontFamily: "var(--lm-font-head)" }}
              >
                Mis colecciones
              </Link>
            ) : (
              <Link
                to="/login"
                className="btn btn-sm btn-warning"
                style={{ fontFamily: "var(--lm-font-head)" }}
              >
                Iniciar sesión
              </Link>
            )}
          </Container>
        </nav>

        <Container fluid="lg" className="py-5">
          {loading ? (
            <div className="d-flex justify-content-center py-5">
              <Spinner
                animation="border"
                style={{ color: "var(--lm-accent)" }}
              />
            </div>
          ) : error ? (
            <Alert variant="warning">{error}</Alert>
          ) : profile ? (
            <>
              <div className="d-flex align-items-center gap-4 mb-5">
                <div
                  style={{
                    width: 72,
                    height: 72,
                    borderRadius: "50%",
                    background:
                      "linear-gradient(135deg, var(--lm-accent) 0%, rgba(255,200,50,0.3) 100%)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "1.5rem",
                    fontFamily: "var(--lm-font-head)",
                    fontWeight: 700,
                    color: "#000",
                    flexShrink: 0,
                  }}
                >
                  {initials}
                </div>
                <div>
                  <h1
                    style={{
                      fontFamily: "var(--lm-font-head)",
                      fontSize: "clamp(1.4rem, 3vw, 2.2rem)",
                      marginBottom: 2,
                    }}
                  >
                    {profile.display_name ?? profile.username}
                  </h1>
                  {profile.display_name && (
                    <p
                      className="text-muted mb-1"
                      style={{ fontSize: "0.9rem" }}
                    >
                      @{profile.username}
                    </p>
                  )}
                  {profile.bio && (
                    <p className="text-muted mb-0" style={{ maxWidth: 520 }}>
                      {profile.bio}
                    </p>
                  )}
                </div>
              </div>

              <h2
                style={{
                  fontFamily: "var(--lm-font-head)",
                  fontSize: "1.1rem",
                  color: "var(--lm-accent)",
                  textTransform: "uppercase",
                  letterSpacing: "0.12em",
                  marginBottom: "1.5rem",
                }}
              >
                Colecciones públicas ({profile.public_collections.length})
              </h2>

              {profile.public_collections.length === 0 ? (
                <p className="text-muted">
                  Este usuario no tiene colecciones públicas.
                </p>
              ) : (
                <Row className="g-4">
                  {profile.public_collections.map((col) => (
                    <Col key={col.id} sm={6} lg={4}>
                      <Card className="h-100 lm-collection-card">
                        <Card.Body>
                          <Card.Title style={{ fontSize: "1rem" }}>
                            {col.name}
                          </Card.Title>
                          <Card.Text
                            className="text-muted"
                            style={{
                              fontSize: "0.85rem",
                              overflow: "hidden",
                              display: "-webkit-box",
                              WebkitLineClamp: 3,
                              WebkitBoxOrient: "vertical",
                            }}
                          >
                            {col.description || "Sin descripción"}
                          </Card.Text>
                        </Card.Body>
                        <Card.Footer>
                          <Link
                            to={collectionHref(col.id)}
                            state={collectionState(col.id)}
                            className="btn btn-sm w-100"
                            style={{
                              borderColor: "var(--lm-accent)",
                              color: "var(--lm-accent)",
                            }}
                          >
                            Explorar →
                          </Link>
                        </Card.Footer>
                      </Card>
                    </Col>
                  ))}
                </Row>
              )}
            </>
          ) : null}
        </Container>
      </div>
    </>
  );
}
