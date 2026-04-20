export interface GenerateTextRequest {
  query: string;
}

export interface GenerateTextResponse {
  answer: string;
  query: string;
  sources_count: number;
}