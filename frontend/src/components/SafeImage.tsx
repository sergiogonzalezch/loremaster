import { isImageUrlAllowed } from "../utils/strings";

import type { CSSProperties } from "react";

interface SafeImageProps {
  /** URL de la imagen a mostrar. */
  src: string | null | undefined;
  /** Texto alternativo para accesibilidad. */
  alt: string;
  /** Clases CSS adicionales. */
  className?: string;
  /** Estilos CSS inline. */
  style?: CSSProperties;
  /** Handler de click opcional. */
  onClick?: () => void;
}

/**
 * Componente seguro para renderizar imágenes con validación de origen.
 *
 * Implementa L-9: validación de URLs de imágenes para prevenir
 * loading de recursos desde orígenes no confiables.
 *
 * Si la URL no pasa la validación, muestra un placeholder en lugar
 * de la imagen, previniendo potenciales ataques (XSS via img src,
 * tracking pixels, etc.).
 *
 * @example
 * ```tsx
 * <SafeImage src={avatarUrl} alt="Avatar" className="rounded-circle" />
 * ```
 */
export default function SafeImage({
  src,
  alt,
  className,
  style,
  onClick,
}: SafeImageProps) {
  if (!isImageUrlAllowed(src)) {
    // Placeholder transparente que respeta las dimensiones del contenedor
    return (
      <div
        className={`bg-secondary bg-opacity-25 d-flex align-items-center justify-content-center ${className || ""}`}
        style={{ width: "100%", height: "100%", minHeight: 60, ...style }}
      >
        <span className="text-muted small">Imagen no disponible</span>
      </div>
    );
  }

  return (
    // eslint-disable-next-line jsx-a11y/alt-text
    <img
      src={src ?? undefined}
      alt={alt}
      className={className}
      style={style}
      onClick={onClick}
      loading="lazy"
    />
  );
}
