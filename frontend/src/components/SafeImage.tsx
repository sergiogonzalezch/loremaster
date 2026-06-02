import { useState } from "react";
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
function ImagePlaceholder({
  className,
  style,
}: {
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      className={`bg-secondary bg-opacity-25 d-flex align-items-center justify-content-center ${className || ""}`}
      style={style}
    >
      <i className="bi bi-image text-muted" />
    </div>
  );
}

export default function SafeImage({
  src,
  alt,
  className,
  style,
  onClick,
}: SafeImageProps) {
  const [failed, setFailed] = useState(false);

  if (!isImageUrlAllowed(src) || failed) {
    return <ImagePlaceholder className={className} style={style} />;
  }

  if (onClick) {
    return (
      <button
        type="button"
        aria-label={alt}
        onClick={onClick}
        className={`p-0 border-0 bg-transparent d-block ${className || ""}`}
        style={{ cursor: "pointer", ...style }}
      >
        <img
          src={src ?? undefined}
          alt=""
          loading="lazy"
          onError={() => setFailed(true)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
          }}
        />
      </button>
    );
  }

  return (
    <img
      src={src ?? undefined}
      alt={alt}
      className={className}
      style={style}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
