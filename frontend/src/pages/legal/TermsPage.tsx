import LegalLayout from "../../components/LegalLayout";

const LAST_UPDATED = "3 de junio de 2026";

const CONTENT = `
## 1. Aceptación de los términos

Al crear una cuenta o utilizar **Lore Master** (en adelante, "el Servicio"),
aceptas estos Términos y Condiciones. Si no estás de acuerdo, no utilices el
Servicio.

Lore Master es un proyecto de código abierto (licencia MIT) de carácter
demostrativo y de portafolio. No se ofrece con garantías comerciales ni
acuerdos de nivel de servicio (SLA).

## 2. Descripción del servicio

Lore Master es una herramienta de *worldbuilding* asistido por IA. Permite:

- Subir documentos (PDF/TXT) que se procesan mediante RAG (recuperación aumentada).
- Generar texto narrativo fundamentado en esos documentos.
- Generar imágenes a partir del contenido confirmado.
- Gestionar entidades (personajes, criaturas, escenarios, facciones, ítems).
- Compartir de forma selectiva textos e imágenes en un feed público y en tu perfil.

## 3. Cuentas de usuario

- Puedes registrarte con credenciales locales o mediante un proveedor de
  autenticación externo (Clerk).
- Eres responsable de mantener la confidencialidad de tus credenciales y de
  toda la actividad que ocurra bajo tu cuenta.
- Cada colección pertenece a su creador; otros usuarios no pueden acceder a tus
  colecciones, contenidos ni imágenes privadas.

## 4. Contenido del usuario

- Conservas la titularidad de los documentos que subes y del contenido que creas.
- Declaras que tienes los derechos necesarios sobre el material que subes y que
  este no infringe derechos de terceros ni la ley aplicable.
- Concedes a Lore Master una licencia limitada y no exclusiva para almacenar y
  procesar tu contenido (extracción de texto, *chunking*, *embeddings* y
  almacenamiento vectorial) con el único fin de prestarte el Servicio.

## 5. Contenido generado por IA

El texto y las imágenes generados por el Servicio se producen mediante modelos
de IA. Su uso está sujeto adicionalmente al [Aviso de uso de IA](/ai-notice).
El contenido generado puede ser inexacto y se proporciona "tal cual".

## 6. Uso aceptable

Te comprometes a **no** utilizar el Servicio para:

- Subir o generar contenido ilegal, sexual explícito con menores, violento,
  de odio, acosador o que facilite daños (armas, explosivos, drogas).
- Intentar eludir los mecanismos de moderación o de seguridad.
- Vulnerar la privacidad o los derechos de propiedad intelectual de terceros.
- Realizar ingeniería inversa maliciosa, abusar de los límites de uso o
  interrumpir el Servicio.

## 7. Moderación de contenido

El Servicio aplica moderación automática sobre el contenido de entrada, los
documentos y las salidas del modelo. Nos reservamos el derecho de bloquear,
ocultar o eliminar contenido, así como de suspender cuentas, cuando se infrinjan
estos términos. La moderación automática no es infalible (ver el Aviso de IA).

## 8. Contenido compartido públicamente

Cuando marcas un texto o una imagen como compartido, este pasa a ser visible
para cualquier persona en el feed público y en tu perfil público. Eres
responsable de lo que decides compartir.

## 9. Propiedad intelectual del Servicio

El código de Lore Master se distribuye bajo licencia MIT. El nombre, el logotipo
y la identidad visual del proyecto pertenecen a su autor. Esta licencia no te
otorga derechos sobre dichas marcas.

## 10. Disponibilidad y limitación de responsabilidad

- El Servicio se presta "tal cual" y "según disponibilidad", sin garantías de
  ningún tipo. Al ser un proyecto demostrativo, puede interrumpirse, cambiar o
  discontinuarse en cualquier momento, y los datos podrían perderse.
- En la máxima medida permitida por la ley, el autor no será responsable de
  daños directos, indirectos o consecuentes derivados del uso del Servicio o de
  la pérdida de datos o contenido.

## 11. Modificaciones

Estos términos pueden actualizarse. La fecha de "última actualización" refleja
la versión vigente. El uso continuado del Servicio tras un cambio implica su
aceptación.

## 12. Contacto

Para cualquier consulta sobre estos términos, puedes abrir una incidencia en el
[repositorio del proyecto](https://github.com/sergiogonzalezch/loremaster).
`;

/** Página pública de Términos y Condiciones. */
export default function TermsPage() {
  return (
    <LegalLayout
      title="Términos y Condiciones"
      lastUpdated={LAST_UPDATED}
      content={CONTENT}
    />
  );
}
