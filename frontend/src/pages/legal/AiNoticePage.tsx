import LegalLayout from "../../components/LegalLayout";

const LAST_UPDATED = "3 de junio de 2026";

const CONTENT = `
**Lore Master** genera texto e imágenes mediante modelos de inteligencia
artificial. Este aviso explica las limitaciones de ese contenido.

## 1. Contenido generado automáticamente

- El **texto** se genera con modelos de lenguaje (p. ej. Llama o Mistral vía
  Ollama) a partir del contexto recuperado de tus documentos.
- Las **imágenes** se generan con modelos de difusión (Flux.2 Klein) ejecutados
  en ComfyUI local o, opcionalmente, en RunPod.

## 2. Puede contener errores

El contenido generado por IA puede ser **inexacto, incompleto o inventado**
("alucinaciones"), incluso cuando suena convincente. No debe considerarse una
fuente de verdad factual ni utilizarse como asesoramiento profesional (legal,
médico, financiero u otro).

**Verifica siempre** la información antes de basar decisiones en ella.

## 3. La moderación no es perfecta

El Servicio aplica varias capas de moderación (filtros léxicos y un clasificador
semántico). Estas capas funcionan en modo *fail-open*: ante un fallo técnico,
priorizan la disponibilidad y dejan pasar el contenido. En consecuencia:

- Puede colarse contenido inapropiado que la moderación no detectó.
- Puede bloquearse contenido legítimo por un falso positivo.

Si encuentras contenido inapropiado, repórtalo por el canal del repositorio.

## 4. Responsabilidad sobre el uso

Eres responsable de cómo utilizas y publicas el contenido generado, incluida la
comprobación de que no infringe derechos de terceros ni la ley aplicable al
publicarlo o reutilizarlo fuera del Servicio.

## 5. Propiedad del contenido generado

La titularidad y los derechos sobre las imágenes y textos generados por modelos
de IA pueden variar según la legislación de tu jurisdicción. Lore Master no
reclama la propiedad del contenido que generas, pero tampoco garantiza que dicho
contenido sea protegible o libre de reclamaciones de terceros.

## 6. Más información

Este aviso complementa los [Términos y Condiciones](/terms) y la
[Política de Privacidad](/privacy).
`;

/** Página pública con el aviso de uso de inteligencia artificial. */
export default function AiNoticePage() {
  return (
    <LegalLayout
      title="Aviso de uso de IA"
      lastUpdated={LAST_UPDATED}
      content={CONTENT}
    />
  );
}
