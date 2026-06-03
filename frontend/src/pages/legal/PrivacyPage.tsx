import LegalLayout from "../../components/LegalLayout";

const LAST_UPDATED = "3 de junio de 2026";

const CONTENT = `
Esta Política describe qué datos trata **Lore Master** ("el Servicio"), con qué
fin y cómo se almacenan. Lore Master es un proyecto de código abierto y
demostrativo.

## 1. Datos que recogemos

- **Datos de cuenta:** nombre de usuario y correo electrónico. Si te autenticas
  con un proveedor externo (Clerk), tu identidad la gestiona dicho proveedor y
  recibimos un identificador y tu email para vincular la cuenta.
- **Contenido que subes:** documentos (PDF/TXT) y el texto extraído de ellos,
  que se fragmenta y se convierte en *embeddings* para la búsqueda semántica.
- **Contenido que generas:** textos e imágenes producidos por el Servicio y sus
  metadatos (prompts, *seed*, categoría, etc.).
- **Datos de perfil opcionales:** nombre para mostrar, biografía y avatar.
- **Registros de moderación:** fragmentos breves del texto bloqueado por los
  filtros de contenido, con fines de seguridad.

## 2. Finalidad del tratamiento

Tratamos estos datos únicamente para:

- Prestarte el Servicio (autenticación, generación RAG, gestión de entidades).
- Mostrar tu contenido público cuando tú decides compartirlo.
- Mantener la seguridad y aplicar la moderación de contenido.

No vendemos tus datos ni los usamos para publicidad.

## 3. Dónde se almacenan

- **Metadatos** (cuentas, colecciones, entidades, registros): base de datos
  relacional (PostgreSQL).
- **Vectores de los documentos:** base de datos vectorial (Qdrant).
- **Imágenes y archivos:** almacenamiento compatible con S3 (Cloudflare R2).
- **Inferencia de IA:** los modelos de texto e imagen pueden ejecutarse de forma
  local (Ollama, ComfyUI) o, opcionalmente, en un proveedor de GPU en la nube
  (RunPod) cuando se activa ese modo.

## 4. Terceros y encargados

- **Clerk** — proveedor de autenticación (si usas ese modo de inicio de sesión).
- **Cloudflare** — almacenamiento de objetos (R2) y exposición del Servicio
  mediante túnel con TLS.
- **RunPod** — solo si el backend de imágenes en la nube está activado; en ese
  caso, el *prompt* y el resultado de la imagen se procesan en su infraestructura.

Cuando la inferencia se ejecuta localmente, tu contenido **no** sale hacia
terceros para ser procesado por modelos de IA.

## 5. Cookies

El Servicio usa cookies estrictamente necesarias para la sesión:

- Una cookie **HttpOnly** con el token de sesión (no accesible desde JavaScript).
- Una cookie de protección **CSRF**.

No se usan cookies de seguimiento ni de publicidad.

## 6. Retención y eliminación

- El contenido se elimina mediante *soft-delete*: se marca como borrado y deja
  de mostrarse.
- Puedes solicitar la eliminación de tu cuenta y tu contenido a través del
  [repositorio del proyecto](https://github.com/sergiogonzalezch/loremaster).
- Al ser un proyecto demostrativo, los datos podrían eliminarse si el Servicio
  se discontinúa.

## 7. Seguridad

Aplicamos medidas razonables: tokens en cookies HttpOnly, protección CSRF en las
mutaciones, cifrado en tránsito (TLS), control de acceso por propietario y
validación de los archivos subidos. Ningún sistema es completamente seguro.

## 8. Tus derechos

Puedes solicitar acceso, rectificación o supresión de tus datos personales, así
como oponerte a determinados tratamientos, contactando por el canal indicado en
la sección de contacto.

## 9. Menores

El Servicio no está dirigido a menores de edad. Si crees que un menor nos ha
proporcionado datos, contáctanos para eliminarlos.

## 10. Cambios

Esta Política puede actualizarse. La fecha de "última actualización" refleja la
versión vigente.

## 11. Contacto

Para ejercer tus derechos o resolver dudas, abre una incidencia en el
[repositorio del proyecto](https://github.com/sergiogonzalezch/loremaster).
`;

/** Página pública de Política de Privacidad. */
export default function PrivacyPage() {
  return (
    <LegalLayout
      title="Política de Privacidad"
      lastUpdated={LAST_UPDATED}
      content={CONTENT}
    />
  );
}
