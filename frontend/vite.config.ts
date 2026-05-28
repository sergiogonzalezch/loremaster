import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Hostnames de media extra (S3/R2/CDN) configurados en VITE_MEDIA_HOST
const mediaHostCsp = process.env.VITE_MEDIA_HOST
  ? process.env.VITE_MEDIA_HOST.split(",")
      .map((h) => h.trim())
      .filter(Boolean)
      .map((h) => `https://${h}`)
      .join(" ")
  : "";

export default defineConfig({
  plugins: [react()],
  server: {
    // CSP del servidor de desarrollo — 'unsafe-inline' en script-src es necesario
    // para el HMR de Vite. En producción, la build no genera scripts inline.
    headers: {
      "Content-Security-Policy": [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com",
        `img-src 'self' data: blob: http://localhost:* ${mediaHostCsp}`.trim(),
        "connect-src 'self' http://localhost:* ws://localhost:*",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
      ].join("; "),
    },
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/media": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
