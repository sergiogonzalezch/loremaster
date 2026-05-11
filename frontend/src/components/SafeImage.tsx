import { isImageUrlAllowed } from "../utils/strings";

interface SafeImageProps {
  src: string | null | undefined;
  alt: string;
  className?: string;
  onClick?: () => void;
}

export function SafeImage({ src, alt, className, onClick }: SafeImageProps) {
  if (!isImageUrlAllowed(src)) {
    return (
      <div className={`bg-secondary text-white d-flex align-items-center justify-content-center ${className || ""}`} style={{ minHeight: "100px" }}>
        <span>Imagen no disponible</span>
      </div>
    );
  }

  return (
    // eslint-disable-next-line jsx-a11y/alt-text
    <img src={src} alt={alt} className={className} onClick={onClick} loading="lazy" />
  );
}