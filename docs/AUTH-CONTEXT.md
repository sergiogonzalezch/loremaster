
## Revisión de seguridad: AuthContext + ProtectedRoute

*Nota previa:** Este código no usa Clerk en `AuthContext.tsx`. Usa un sistema JWT+cookie propio. Clerk solo aparece en `ProtectedRoute.tsx` como modo alternativo. Esa dualidad genera varios de los problemas siguientes.



### 1. Race condition en inicialización — sin AbortController

**`AuthContext.tsx:74-96`**

```tsx
useEffect(() => {
  getMyProfile()               // ← promesa en vuelo
    .then((profile) => {
      setUser({...});
      return getMyAvatar()
        .then((r) => setAvatarUrl(...))
        .catch(() => {});
    })
    .catch(() => { setUser(null); })
    .finally(() => { setLoading(false); });  // ← siempre se ejecuta
  return () => {
    if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
    // ← NO cancela la petición HTTP
  };
}, []);
```

**Problema A:** En React 18 Strict Mode el efecto se monta, desmonta y vuelve a montar. La limpieza cancela el timer pero no la petición en vuelo. Dos llamadas a `getMyProfile()` corren en paralelo; la segunda puede pisar el estado dejado por la primera.

**Problema B:** `loading` no baja a `false` hasta que `getMyAvatar()` también termina (línea 83). Un avatar lento mantiene el spinner más tiempo del necesario y bloquea el acceso de rutas protegidas aunque el perfil ya esté resuelto.

**Fix:** Usar `AbortController` + separar `loading` del avatar.

---

### 2. Desincronización garantizada en logout

**`AuthContext.tsx:59`**

```tsx
void logoutApi().catch(() => {});   // ← fire-and-forget
setUser(null);
setAvatarUrl(null);
```

Si `logoutApi()` falla (red, 5xx), el frontend limpia su estado pero la cookie HttpOnly sigue válida en el servidor. En el siguiente refresh, `getMyProfile()` tendrá éxito y el usuario volverá a estar autenticado sin haber hecho login. El usuario creyó haber cerrado sesión.

**Fix:** Esperar la confirmación del backend antes de limpiar el estado, o al menos mostrar error si falla.

---

### 3. Login borra el usuario en error transitorio

**`AuthContext.tsx:111-113`**

```tsx
.catch(() => {
  setUser(null);  // ← logout forzado por un parpadeo de red
});
```

Si la red falla transitoriamente durante `login()`, cualquier usuario ya autenticado queda deslogueado sin razón. También: `login()` no tiene su propio `loading` state; durante la petición, `user` mantiene el valor anterior (puede ser `null` si se llama tras un reload), lo cual hace que ProtectedRoute redirija al login mientras `login()` está aún resolviendo en LoginPage.

---

### 4. ProtectedRoute en modo Clerk no verifica la sesión del backend

**`ProtectedRoute.tsx:18-27`**

```tsx
function ProtectedRouteClerk() {
  const { isSignedIn, isLoaded } = useUser();  // ← solo estado Clerk
  if (!isLoaded) return <LoadingSpinner />;
  if (!isSignedIn) return <Navigate to="/login" .../>;
  return <Outlet />;
}
```

Este guard solo verifica que Clerk tenga sesión activa. Un usuario con token Clerk válido pero con sesión backend expirada/revocada pasa el gate. El propio comentario del archivo reconoce "el breve intervalo entre el login con Clerk y la finalización del sync de cookies" — pero ese intervalo no tiene límite superior garantizado.

---

### 5. Desincronización estructural entre Clerk y AuthContext

**`ProtectedRoute.tsx:42` + `AuthContext.tsx:49`**

```tsx
export default function ProtectedRoute() {
  return clerkKey ? <ProtectedRouteClerk /> : <ProtectedRouteLocal />;
}
```

En modo Clerk, `AuthContext` igualmente ejecuta `getMyProfile()` al montar (línea 75). Si el sync de cookies aún no ocurrió, `setUser(null)` (línea 88). Cualquier componente dentro de la ruta protegida que llame `useAuth().user` recibirá `null` aunque `isSignedIn === true` en Clerk. Código que dependa de `user.is_admin` (por ejemplo, para mostrar controles de admin) tomará decisiones incorrectas.

---

### 6. scheduleLogout sin awareness de refresh de sesión

**`AuthContext.tsx:64-70`**

```tsx
function scheduleLogout(expiresAt: string | null | undefined) {
  const ms = new Date(expiresAt).getTime() - Date.now();
  logoutTimerRef.current = setTimeout(logout, ms);
}
```

El timer se calcula una sola vez con el `expires_at` del perfil inicial. Si el backend implementa sesiones deslizantes (refresh transparente de cookie), el timer dispara un logout prematuro con una sesión aún válida. El frontend desloguea al usuario en la UI mientras su cookie sigue siendo válida en el servidor — vuelta al problema del punto 2 pero en sentido inverso.

---

### Resumen de severidad

| # | Ubicación | Tipo | Severidad |
|---|-----------|------|-----------|
| 1 | `AuthContext.tsx:74` | Race condition / doble mount | Media |
| 2 | `AuthContext.tsx:59` | Sesión viva tras logout | Alta |
| 3 | `AuthContext.tsx:111` | Logout involuntario por error transitorio | Media |
| 4 | `ProtectedRoute.tsx:18` | Bypass de auth backend en modo Clerk | Alta |
| 5 | `ProtectedRoute.tsx:42` | Desync Clerk↔AuthContext (`user` null) | Media |
| 6 | `AuthContext.tsx:64` | Timer de logout sin refresh awareness | Baja |

Los tokens en sí están bien: la cookie HttpOnly impide acceso desde JS. El mayor riesgo es la combinación de los puntos 2 y 4, que permiten acceder a rutas protegidas con sesiones backend inválidas.

---

## Validación contra código fuente

> Revisión realizada el 2026-05-17 sobre `frontend/src/contexts/AuthContext.tsx` y `frontend/src/components/ProtectedRoute.tsx`.

Todos los issues están **confirmados** tal como se describieron:

| # | Validación |
|---|-----------|
| 1 | `useEffect` (línea 74) no crea `AbortController`. Cleanup en línea 93-95 solo limpia timer. `setLoading(false)` en `.finally()` a línea 90, después de que la cadena de `getMyAvatar()` resuelva → bloquea spinner innecesariamente. |
| 2 | `void logoutApi().catch(() => {})` en línea 59 seguido inmediatamente de `setUser(null)` + `setAvatarUrl(null)`. Fire-and-forget confirmado. |
| 3 | `.catch(() => { setUser(null); })` en líneas 111-113 dentro de `login()`. No distingue si había un usuario previo. Sin loading state propio para `login()`. |
| 4 | `ProtectedRouteClerk` (líneas 18-27) solo consulta `useUser()` de Clerk. Sin verificación de sesión backend. |
| 5 | `AuthProvider` corre `getMyProfile()` al montar independientemente del modo (Clerk o local). En modo Clerk, si el sync de cookie no terminó, `user` queda `null` mientras `isSignedIn === true`. |
| 6 | `scheduleLogout` (líneas 64-70) calcula `ms` una sola vez desde `profile.expires_at`. No se actualiza si el backend renueva la sesión. |

---

## Plan de acción

### Principios
- Corregir sin cambiar la interfaz pública de `AuthContext` (mismos campos en `AuthContextValue`).
- Mantener compatibilidad con ambos modos (local y Clerk).
- Priorizar primero los issues de severidad **Alta**, luego **Media**, por último **Baja**.
- Cada fix es atómico y puede commitearse de forma independiente para facilitar rollback.

---

### Fase 1 — Críticos (Alta severidad)

#### Fix #2: Logout síncrono con propagación de error

**Archivo:** `AuthContext.tsx`

**Cambio:** Convertir `logout` en `async`. Esperar `logoutApi()` antes de limpiar estado. Si falla, propagar el error para que el llamador pueda mostrarlo.

```tsx
// ANTES
const logout = useCallback(() => {
  if (logoutTimerRef.current) { clearTimeout(logoutTimerRef.current); logoutTimerRef.current = null; }
  void logoutApi().catch(() => {});
  setUser(null);
  setAvatarUrl(null);
}, []);

// DESPUÉS
const logout = useCallback(async () => {
  if (logoutTimerRef.current) { clearTimeout(logoutTimerRef.current); logoutTimerRef.current = null; }
  await logoutApi();   // lanza si falla; el llamador decide qué mostrar
  setUser(null);
  setAvatarUrl(null);
}, []);
```

**Impacto en `AuthContextValue`:** `logout: () => Promise<void>` — cambio de firma. Actualizar todos los call-sites (buscar `logout()` en el proyecto).

**Criterio de aceptación:** Si `logoutApi()` retorna 5xx, el estado del frontend no se limpia y el usuario ve un mensaje de error.

---

#### Fix #4: ProtectedRoute Clerk verifica sesión backend

**Archivo:** `ProtectedRoute.tsx`

**Cambio:** `ProtectedRouteClerk` debe consultar también `useAuth()` para validar que `AuthContext` tiene `user` no nulo. El spinner se muestra mientras `loading === true` (sync en progreso).

```tsx
// ANTES
function ProtectedRouteClerk() {
  const { isSignedIn, isLoaded } = useUser();
  const location = useLocation();
  if (!isLoaded) return <LoadingSpinner />;
  if (!isSignedIn) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  return <Outlet />;
}

// DESPUÉS
function ProtectedRouteClerk() {
  const { isSignedIn, isLoaded } = useUser();
  const { user, loading } = useAuth();
  const location = useLocation();

  if (!isLoaded || loading) return <LoadingSpinner />;
  // isSignedIn cubre el caso de sesión Clerk expirada;
  // !user cubre sesión backend expirada/revocada tras el sync.
  if (!isSignedIn || !user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return <Outlet />;
}
```

**Riesgo:** Si el sync de cookies tarda más de lo esperado, el spinner puede aparecer brevemente. Aceptable y preferible a dejar pasar sesiones inválidas.

**Criterio de aceptación:** Un token Clerk válido con sesión backend revocada redirige a `/login`.

---

### Fase 2 — Estabilidad (Media severidad)

#### Fix #1: AbortController + loading desacoplado del avatar

**Archivo:** `AuthContext.tsx`

**Cambio A:** Añadir `AbortController` en el `useEffect` de inicialización para cancelar la petición si el componente desmonta antes de resolver.

**Cambio B:** Bajar `loading` a `false` en cuanto `getMyProfile()` resuelva, independientemente de `getMyAvatar()`. El avatar puede cargarse después sin bloquear rutas protegidas.

```tsx
useEffect(() => {
  const controller = new AbortController();

  getMyProfile({ signal: controller.signal })
    .then((profile) => {
      setUser({ id: profile.id, username: profile.username, is_admin: profile.is_admin ?? false });
      scheduleLogout(profile.expires_at);
      setLoading(false);                        // ← desbloquea rutas protegidas ya
      return getMyAvatar({ signal: controller.signal })
        .then((r) => setAvatarUrl(r.avatar_url ?? null))
        .catch(() => {});                       // avatar falla en silencio
    })
    .catch((err) => {
      if (err.name === 'AbortError') return;   // desmonte limpio, no actualizar estado
      setUser(null);
      setLoading(false);
    });

  return () => {
    controller.abort();
    if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
  };
}, []);
```

**Precondición:** `getMyProfile` y `getMyAvatar` deben aceptar `{ signal: AbortSignal }`. Verificar en `api/users.ts` que `apiFetch` forwarded la señal.

**Criterio de aceptación:** En Strict Mode, solo un `setUser` efectivo; `loading` baja sin esperar avatar.

---

#### Fix #3: Login no resetea usuario en error

**Archivo:** `AuthContext.tsx`

**Cambio:** En el `.catch()` de `login()`, no llamar a `setUser(null)` incondicionalmente. Si ya había un usuario autenticado, mantenerlo. Relanzar el error para que `LoginPage` lo gestione.

```tsx
// ANTES
.catch(() => {
  setUser(null);
});

// DESPUÉS
.catch((err) => {
  // Solo limpiar si no había sesión previa (primer login, no revalidación)
  setUser((prev) => (prev ? prev : null));
  throw err;  // el llamador (LoginPage) muestra el error de red al usuario
});
```

**Alternativa más simple** si login() solo se llama desde LoginPage (cuando `user === null`): simplemente relanzar el error sin tocar `user`.

```tsx
.catch((err) => { throw err; });
```

Verificar los call-sites de `login()` para confirmar cuál aplica.

**Criterio de aceptación:** Un error 503 durante `login()` no desloguea a un usuario ya autenticado.

---

#### Fix #5: AuthContext en modo Clerk — estado coherente durante sync

**Archivos:** `AuthContext.tsx`, `ProtectedRoute.tsx`

Este issue queda **parcialmente mitigado por Fix #4**: al hacer que `ProtectedRouteClerk` espere a `loading === false`, el usuario ya tendrá `user` resuelto antes de acceder a la ruta protegida.

**Riesgo residual:** Componentes dentro de la ruta protegida que lean `useAuth().user` durante el mount inicial (antes de que `ProtectedRoute` haya bloqueado el acceso) podrían recibir `null` en el primer render. Solución: leer `loading` junto con `user` en esos componentes y mostrar skeleton/spinner hasta que `loading === false`.

**No requiere cambio de código adicional** si Fix #4 se implementa correctamente.

---

### Fase 3 — Mejora preventiva (Baja severidad)

#### Fix #6: scheduleLogout con refresh awareness

**Archivo:** `AuthContext.tsx`

**Cambio:** Exponer `refreshSession()` en `AuthContextValue` que vuelva a llamar `getMyProfile()` y re-calcule el timer. Llamar esta función desde el interceptor de respuestas HTTP cuando el backend renueve la cookie.

```tsx
const refreshSession = useCallback(async () => {
  const profile = await getMyProfile();
  scheduleLogout(profile.expires_at);
}, []);
```

**Precondición:** El cliente HTTP (`api/client.ts`) debe detectar la renovación de sesión (p.ej. header `X-Session-Renewed: true`) y llamar `refreshSession()`. Esto requiere que `AuthContext` exponga `refreshSession` y que `apiFetch` tenga acceso al contexto — normalmente vía un callback registrado al montar.

**Prioridad:** Diferir hasta que se confirme que el backend implementa sesiones deslizantes. Si no lo hace, este fix no aporta valor.

---

### Orden de implementación recomendado

```
Fix #2  →  Fix #4  →  Fix #1  →  Fix #3  →  Fix #5 (implícito)  →  Fix #6 (si aplica)
```

| Orden | Fix | Razón |
|-------|-----|-------|
| 1 | #2 Logout síncrono | Cambia la firma de `logout`; mejor hacerlo antes de que otros fixes dependan de ella |
| 2 | #4 ProtectedRoute Clerk | Alta severidad; depende de `loading` que Fix #1 mejora, pero funciona también antes |
| 3 | #1 AbortController + loading | Mejora correctitud React 18; habilita que Fix #4 sea más rápido |
| 4 | #3 Login sin reset | Requiere entender call-sites; poco riesgo, alta legibilidad |
| 5 | #5 Desync Clerk | Implícito por Fix #4; verificar tras implementarlo |
| 6 | #6 Timer refresh | Solo si backend usa sesiones deslizantes |

---

### Archivos afectados

| Archivo | Fixes |
|---------|-------|
| `frontend/src/contexts/AuthContext.tsx` | #1, #2, #3, #6 |
| `frontend/src/components/ProtectedRoute.tsx` | #4, #5 |
| `frontend/src/api/users.ts` | #1 (añadir soporte a `signal`) |
| `frontend/src/api/client.ts` | #6 (si aplica, añadir detección de renovación) |
| Call-sites de `logout()` | #2 (actualizar a `await logout()`) |
| Call-sites de `login()` | #3 (gestionar error relanzado) |