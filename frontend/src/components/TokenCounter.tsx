import { estimateTokens, QUERY_TOKEN_WARN_AT } from "../utils/tokens";

interface TokenCounterProps {
  text: string;
  warnAt?: number;
}

export default function TokenCounter({ text, warnAt = QUERY_TOKEN_WARN_AT }: TokenCounterProps) {
  const tokens = estimateTokens(text);
  const warn = tokens >= warnAt;
  return (
    <small className={warn ? "text-warning" : "text-muted"}>
      ≈ {tokens} tokens
      {warn && " (query larga, considera acortarla)"}
    </small>
  );
}
