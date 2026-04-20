/**
 * Estimación rápida de tokens. Regla de 4 chars ≈ 1 token, razonable para
 * español/inglés pero no exacta. Suficiente para mostrar al usuario un orden
 * de magnitud y advertir cuando una query crezca demasiado.
 */
export function estimateTokens(text: string): number {
  if (!text) return 0;
  return Math.ceil(text.length / 4);
}

export const QUERY_TOKEN_WARN_AT = 400;
