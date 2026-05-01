export interface GenerateTextRequest {
  query: string;
  extra_context?: string;
}

export interface GenerateTextResponse {
  answer: string;
  query: string;
  sources_count: number;
}
