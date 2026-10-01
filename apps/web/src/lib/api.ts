export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type User = {
  id: string;
  company_id: string;
  full_name: string;
  email: string;
  role: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
};

export type Supplier = {
  id: string;
  name: string;
  document_number: string;
  email: string | null;
  category: string | null;
  status: string;
};

export type CostCenter = { id: string; name: string; code: string; description: string | null };

export type Invoice = {
  id: string;
  supplier_id: string;
  cost_center_id: string | null;
  invoice_number: string;
  description: string;
  category: string;
  due_date: string;
  amount: string;
  currency: string;
  status: string;
};

export type FinancialDocument = {
  id: string;
  original_name: string;
  media_type: string;
  size_bytes: number;
  status: string;
  uploaded_at: string;
};

export type ExtractedInvoiceData = {
  document_type: string | null;
  supplier_name: string | null;
  supplier_document_number: string | null;
  invoice_number: string | null;
  amount: number | null;
  currency: string | null;
  issue_date: string | null;
  due_date: string | null;
  description: string | null;
  category: string | null;
  cost_center_name: string | null;
  confidence: number;
  warnings: string[];
};

export type DocumentExtraction = {
  document_id: string;
  status: string;
  provider: string | null;
  model: string | null;
  data: ExtractedInvoiceData | null;
  suggested_supplier_id: string | null;
  suggested_cost_center_id: string | null;
  confirmed_invoice_id: string | null;
  extracted_at: string | null;
  error: string | null;
};

export type Dashboard = {
  month_spend: string;
  pending: { count: number; amount: string };
  overdue: { count: number; amount: string };
  upcoming: Array<{ id: string; invoice_number: string; supplier_name: string; due_date: string; amount: string }>;
  by_category: Array<{ label: string; amount: string; count: number }>;
  by_cost_center: Array<{ label: string; amount: string; count: number }>;
  top_suppliers: Array<{ label: string; amount: string; count: number }>;
  monthly_evolution: Array<{ month: string; amount: string }>;
  anomaly_count: number;
  insights: string[];
};

export type FinancialChatResponse = {
  answer: string;
  tool: string;
  data: Record<string, unknown>;
  provider: string;
  model: string;
};

export type KnowledgeDocument = {
  id: string;
  original_name: string;
  media_type: string;
  size_bytes: number;
  status: string;
  uploaded_at: string;
  indexed_at: string | null;
  page_count: number | null;
  chunk_count: number;
  embedding_provider: string | null;
  embedding_model: string | null;
  processing_error: string | null;
};

export type KnowledgeSource = {
  document_id: string;
  document_name: string;
  excerpt: string;
  page_number: number | null;
  similarity: number;
};

export type KnowledgeQueryResponse = {
  answer: string;
  sources: KnowledgeSource[];
  grounded: boolean;
  provider: string;
  model: string;
};

export type Anomaly = {
  id: string;
  related_invoice_id: string;
  anomaly_type: string;
  severity: "low" | "medium" | "high";
  explanation: string;
  metrics: Record<string, unknown>;
  status: "open" | "reviewed" | "dismissed";
  detected_at: string;
  ai_analysis: string | null;
  ai_provider: string | null;
  ai_model: string | null;
  analyzed_at: string | null;
};

export type AnomalyAnalysisResponse = {
  anomaly_id: string;
  analysis: string;
  provider: string;
  model: string;
  analyzed_at: string;
};

export type WorkflowQueryResponse = {
  answer: string;
  route: "finance" | "knowledge" | "anomalies" | "documents";
  trace: string[];
  sources: KnowledgeSource[];
  metadata: Record<string, unknown>;
  validated: boolean;
};

export type ERPSyncCounts = {
  received: number;
  created: number;
  updated: number;
  skipped: number;
};

export type ERPPreview = {
  source: string;
  generated_at: string;
  vendor_count: number;
  invoice_count: number;
  connection: {
    adapter: string;
    status: string;
    checkpoint: string | null;
    last_sync_at: string | null;
    last_sync_status: string | null;
  } | null;
};

export type ERPSyncResponse = {
  run_id: string;
  source: string;
  checkpoint: string;
  vendors: ERPSyncCounts;
  invoices: ERPSyncCounts;
  warnings: string[];
  completed_at: string;
};

export type ERPSyncRun = {
  id: string;
  status: string;
  started_at: string;
  completed_at: string;
  summary: Record<string, unknown>;
  error_message: string | null;
};

export async function apiFetch<T>(path: string, token?: string | null, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Falha na API (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
