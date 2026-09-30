"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/auth-provider";
import {
  apiFetch,
  CostCenter,
  Dashboard,
  DocumentExtraction,
  FinancialDocument,
  Invoice,
  Supplier,
} from "@/lib/api";

type Tab = "dashboard" | "invoices" | "suppliers" | "cost-centers" | "documents";
type ListResponse<T> = { items: T[]; total: number };

const tabs: Array<{ id: Tab; label: string }> = [
  { id: "dashboard", label: "Visão geral" },
  { id: "invoices", label: "Faturas" },
  { id: "suppliers", label: "Fornecedores" },
  { id: "cost-centers", label: "Centros de custo" },
  { id: "documents", label: "Documentos" },
];

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const date = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" });

function brl(value: string | number) {
  return money.format(Number(value));
}

function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("admin@aurora.demo");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível entrar");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-5 py-10">
      <div className="w-full max-w-md rounded-[2rem] border border-white bg-white/90 p-8 shadow-2xl shadow-emerald-950/10">
        <Link href="/" className="text-sm font-bold text-[#0b6b4f]">← Voltar ao início</Link>
        <div className="mt-8 grid size-12 place-items-center rounded-2xl bg-[#0b6b4f] text-lg font-black text-white">F</div>
        <h1 className="mt-5 text-3xl font-black tracking-tight">Acesse o FinanceAI</h1>
        <p className="mt-2 text-sm leading-6 text-[#66766f]">Use uma conta da empresa para acessar dados financeiros protegidos.</p>
        <form className="mt-7 space-y-4" onSubmit={submit}>
          <label className="block text-sm font-bold">E-mail
            <input className="mt-2 w-full rounded-xl border border-[#cbd8d2] bg-white px-4 py-3 font-normal outline-none focus:border-[#0b6b4f]" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label className="block text-sm font-bold">Senha
            <input className="mt-2 w-full rounded-xl border border-[#cbd8d2] bg-white px-4 py-3 font-normal outline-none focus:border-[#0b6b4f]" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} />
          </label>
          {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}
          <button className="w-full rounded-xl bg-[#0b6b4f] px-5 py-3.5 font-bold text-white disabled:opacity-60" disabled={busy}>{busy ? "Entrando…" : "Entrar"}</button>
        </form>
        <p className="mt-5 rounded-xl bg-[#f1f7e8] p-3 text-xs leading-5 text-[#4b5f3b]">Ambiente de demonstração: admin@aurora.demo · senha definida no seed do projeto.</p>
      </div>
    </main>
  );
}

function Status({ value }: { value: string }) {
  const green = ["paid", "approved", "active", "uploaded", "completed"].includes(value);
  const red = ["overdue", "rejected", "failed"].includes(value);
  return <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${green ? "bg-emerald-50 text-emerald-700" : red ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>{value}</span>;
}

export function WorkspaceClient() {
  const { token, user, ready, logout } = useAuth();
  const [tab, setTab] = useState<Tab>("dashboard");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [invoices, setInvoices] = useState<ListResponse<Invoice> | null>(null);
  const [suppliers, setSuppliers] = useState<ListResponse<Supplier> | null>(null);
  const [costCenters, setCostCenters] = useState<ListResponse<CostCenter> | null>(null);
  const [documents, setDocuments] = useState<ListResponse<FinancialDocument> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const [dashboardData, invoiceData, supplierData, costCenterData, documentData] = await Promise.all([
        apiFetch<Dashboard>("/api/v1/dashboard", token),
        apiFetch<ListResponse<Invoice>>("/api/v1/invoices?page_size=100", token),
        apiFetch<ListResponse<Supplier>>("/api/v1/suppliers?page_size=100", token),
        apiFetch<ListResponse<CostCenter>>("/api/v1/cost-centers?page_size=100", token),
        apiFetch<ListResponse<FinancialDocument>>("/api/v1/documents", token),
      ]);
      setDashboard(dashboardData);
      setInvoices(invoiceData);
      setSuppliers(supplierData);
      setCostCenters(costCenterData);
      setDocuments(documentData);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Erro ao carregar workspace");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  if (!ready) return <main className="grid min-h-screen place-items-center font-bold text-[#0b6b4f]">Validando sessão…</main>;
  if (!token || !user) return <Login />;

  return (
    <main className="min-h-screen bg-[#eef3f1] lg:grid lg:grid-cols-[260px_1fr]">
      <aside className="bg-[#102a21] p-5 text-white lg:min-h-screen lg:p-7">
        <div className="flex items-center justify-between lg:block">
          <Link className="flex items-center gap-3" href="/"><span className="grid size-10 place-items-center rounded-xl bg-[#c8f266] font-black text-[#19310e]">F</span><span className="font-black">FinanceAI</span></Link>
          <button className="text-xs text-emerald-100/70 lg:hidden" onClick={() => void logout()}>Sair</button>
        </div>
        <nav className="mt-6 flex gap-2 overflow-x-auto lg:mt-10 lg:block lg:space-y-2">
          {tabs.map((item) => <button className={`shrink-0 rounded-xl px-4 py-3 text-left text-sm font-bold lg:w-full ${tab === item.id ? "bg-white text-[#102a21]" : "text-emerald-50/70 hover:bg-white/10"}`} key={item.id} onClick={() => setTab(item.id)}>{item.label}</button>)}
        </nav>
        <div className="mt-10 hidden border-t border-white/10 pt-5 lg:block">
          <p className="text-sm font-bold">{user.full_name}</p><p className="mt-1 text-xs text-emerald-100/60">{user.role} · {user.email}</p>
          <button className="mt-4 text-xs font-bold text-[#c8f266]" onClick={() => void logout()}>Encerrar sessão</button>
        </div>
      </aside>
      <section className="min-w-0 p-5 sm:p-8 lg:p-10">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div><p className="text-xs font-black uppercase tracking-[0.16em] text-[#0b6b4f]">Aurora Comércio</p><h1 className="mt-1 text-3xl font-black tracking-tight">{tabs.find((item) => item.id === tab)?.label}</h1></div>
          <button className="rounded-xl border border-[#cbd8d2] bg-white px-4 py-2.5 text-sm font-bold" onClick={() => void load()} disabled={loading}>{loading ? "Atualizando…" : "Atualizar dados"}</button>
        </header>
        {error && <p className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-700" role="alert">{error}</p>}
        <div className="mt-7">
          {tab === "dashboard" && <DashboardView data={dashboard} />}
          {tab === "invoices" && <InvoicesView data={invoices} suppliers={suppliers?.items ?? []} />}
          {tab === "suppliers" && <SuppliersView data={suppliers} token={token} refresh={load} />}
          {tab === "cost-centers" && <CostCentersView data={costCenters} />}
          {tab === "documents" && <DocumentsView data={documents} suppliers={suppliers?.items ?? []} costCenters={costCenters?.items ?? []} token={token} refresh={load} />}
        </div>
      </section>
    </main>
  );
}

function DashboardView({ data }: { data: Dashboard | null }) {
  if (!data) return <Empty />;
  const cards = [
    ["Gasto no mês", brl(data.month_spend), "Total financeiro no período"],
    ["Pendentes", brl(data.pending.amount), `${data.pending.count} faturas`],
    ["Vencidas", brl(data.overdue.amount), `${data.overdue.count} faturas`],
    ["Anomalias", String(data.anomaly_count), "Sinais para revisão"],
  ];
  const maxCategory = Math.max(...data.by_category.map((item) => Number(item.amount)), 1);
  return <div className="space-y-5">
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(([label, value, hint]) => <article className="rounded-2xl border border-[#dfe7e3] bg-white p-5" key={label}><p className="text-sm text-[#66766f]">{label}</p><p className="mt-3 text-2xl font-black">{value}</p><p className="mt-2 text-xs text-[#84918c]">{hint}</p></article>)}</div>
    <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
      <article className="rounded-2xl border border-[#dfe7e3] bg-white p-6"><h2 className="font-black">Despesas por categoria</h2><div className="mt-6 space-y-5">{data.by_category.slice(0, 6).map((item) => <div key={item.label}><div className="mb-2 flex justify-between text-sm"><span className="font-bold">{item.label}</span><span>{brl(item.amount)}</span></div><div className="h-2 rounded-full bg-[#edf2ef]"><div className="h-2 rounded-full bg-[#0b6b4f]" style={{ width: `${Math.max(4, Number(item.amount) / maxCategory * 100)}%` }} /></div></div>)}</div></article>
      <article className="rounded-2xl bg-[#102a21] p-6 text-white"><h2 className="font-black">Insights operacionais</h2><div className="mt-5 space-y-3">{data.insights.map((insight) => <p className="rounded-xl bg-white/10 p-4 text-sm leading-6 text-emerald-50/80" key={insight}>{insight}</p>)}</div></article>
    </div>
    <article className="rounded-2xl border border-[#dfe7e3] bg-white p-6"><h2 className="font-black">Próximos vencimentos</h2><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="text-[#708078]"><tr><th className="py-3">Fatura</th><th>Fornecedor</th><th>Vencimento</th><th className="text-right">Valor</th></tr></thead><tbody>{data.upcoming.map((item) => <tr className="border-t border-[#edf1ef]" key={item.id}><td className="py-4 font-bold">{item.invoice_number}</td><td>{item.supplier_name}</td><td>{date.format(new Date(item.due_date))}</td><td className="text-right font-bold">{brl(item.amount)}</td></tr>)}</tbody></table></div></article>
  </div>;
}

function InvoicesView({ data, suppliers }: { data: ListResponse<Invoice> | null; suppliers: Supplier[] }) {
  const supplierNames = useMemo(() => Object.fromEntries(suppliers.map((item) => [item.id, item.name])), [suppliers]);
  if (!data) return <Empty />;
  return <Table headers={["Fatura", "Fornecedor", "Categoria", "Vencimento", "Status", "Valor"]}>{data.items.map((item) => <tr className="border-t border-[#edf1ef]" key={item.id}><td className="py-4 font-bold">{item.invoice_number}<span className="block max-w-56 truncate text-xs font-normal text-[#7b8882]">{item.description}</span></td><td>{supplierNames[item.supplier_id] ?? "—"}</td><td>{item.category}</td><td>{date.format(new Date(item.due_date))}</td><td><Status value={item.status} /></td><td className="text-right font-bold">{brl(item.amount)}</td></tr>)}</Table>;
}

function SuppliersView({ data, token, refresh }: { data: ListResponse<Supplier> | null; token: string; refresh: () => Promise<void> }) {
  const [open, setOpen] = useState(false); const [error, setError] = useState("");
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const form = new FormData(event.currentTarget);
    try { await apiFetch("/api/v1/suppliers", token, { method: "POST", body: JSON.stringify({ name: form.get("name"), document_number: form.get("document"), email: form.get("email") || null, category: form.get("category") || null }) }); event.currentTarget.reset(); setOpen(false); await refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Erro ao salvar"); }
  }
  if (!data) return <Empty />;
  return <div className="space-y-5"><div className="flex justify-end"><button className="rounded-xl bg-[#0b6b4f] px-4 py-2.5 text-sm font-bold text-white" onClick={() => setOpen(!open)}>{open ? "Cancelar" : "+ Novo fornecedor"}</button></div>{open && <form className="grid gap-4 rounded-2xl border border-[#dfe7e3] bg-white p-5 md:grid-cols-4" onSubmit={create}><input className="field" name="name" placeholder="Razão social" required minLength={2} /><input className="field" name="document" placeholder="CNPJ/documento" required minLength={4} /><input className="field" name="email" type="email" placeholder="E-mail" /><input className="field" name="category" placeholder="Categoria" />{error && <p className="text-sm text-red-700 md:col-span-3">{error}</p>}<button className="rounded-xl bg-[#102a21] px-4 py-3 font-bold text-white md:col-start-4">Salvar fornecedor</button></form>}<Table headers={["Fornecedor", "Documento", "Categoria", "E-mail", "Status"]}>{data.items.map((item) => <tr className="border-t border-[#edf1ef]" key={item.id}><td className="py-4 font-bold">{item.name}</td><td>{item.document_number}</td><td>{item.category ?? "—"}</td><td>{item.email ?? "—"}</td><td><Status value={item.status} /></td></tr>)}</Table></div>;
}

function CostCentersView({ data }: { data: ListResponse<CostCenter> | null }) {
  if (!data) return <Empty />;
  return <Table headers={["Código", "Centro de custo", "Descrição"]}>{data.items.map((item) => <tr className="border-t border-[#edf1ef]" key={item.id}><td className="py-4 font-black text-[#0b6b4f]">{item.code}</td><td className="font-bold">{item.name}</td><td>{item.description ?? "—"}</td></tr>)}</Table>;
}

function DocumentsView({ data, suppliers, costCenters, token, refresh }: { data: ListResponse<FinancialDocument> | null; suppliers: Supplier[]; costCenters: CostCenter[]; token: string; refresh: () => Promise<void> }) {
  const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  const [extractingId, setExtractingId] = useState<string | null>(null);
  const [extraction, setExtraction] = useState<DocumentExtraction | null>(null);
  async function upload(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); setBusy(true); setMessage(""); try { await apiFetch("/api/v1/documents", token, { method: "POST", body: form }); event.currentTarget.reset(); setMessage("Documento enviado com segurança."); await refresh(); } catch (cause) { setMessage(cause instanceof Error ? cause.message : "Erro no upload"); } finally { setBusy(false); } }
  async function openExtraction(document: FinancialDocument) {
    setExtractingId(document.id); setMessage("");
    try {
      const method = document.status === "review" || document.status === "completed" ? "GET" : "POST";
      const path = method === "GET" ? `/api/v1/documents/${document.id}/extraction` : `/api/v1/documents/${document.id}/extract`;
      setExtraction(await apiFetch<DocumentExtraction>(path, token, { method }));
      await refresh();
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "Não foi possível extrair o documento"); }
    finally { setExtractingId(null); }
  }
  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!extraction) return; setBusy(true); setMessage(""); const form = new FormData(event.currentTarget);
    try {
      await apiFetch(`/api/v1/documents/${extraction.document_id}/confirm`, token, { method: "POST", body: JSON.stringify({ supplier_id: form.get("supplier_id"), cost_center_id: form.get("cost_center_id") || null, invoice_number: form.get("invoice_number"), description: form.get("description"), category: form.get("category"), issue_date: form.get("issue_date"), due_date: form.get("due_date"), amount: Number(form.get("amount")), currency: form.get("currency"), status: "pending" }) });
      setMessage("Revisão confirmada e fatura criada."); setExtraction(null); await refresh();
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "Não foi possível confirmar"); }
    finally { setBusy(false); }
  }
  if (!data) return <Empty />;
  const extracted = extraction?.data;
  return <div className="space-y-5"><form className="rounded-2xl border border-dashed border-[#9bb0a7] bg-white p-6" onSubmit={upload}><h2 className="font-black">Enviar documento financeiro</h2><p className="mt-2 text-sm text-[#66766f]">PDF, PNG ou JPEG, até 10 MB. Após o upload, use a extração com IA e revise todos os campos antes de confirmar.</p><div className="mt-5 flex flex-wrap items-center gap-3"><input className="text-sm" name="file" type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" required /><button className="rounded-xl bg-[#0b6b4f] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-60" disabled={busy}>{busy ? "Enviando…" : "Enviar"}</button></div>{message && <p className="mt-4 text-sm font-bold text-[#0b6b4f]">{message}</p>}</form>
    {extraction?.status === "review" && extracted && <form className="rounded-2xl border border-[#b8d4c9] bg-white p-6 shadow-lg shadow-emerald-950/5" key={extraction.document_id} onSubmit={confirm}><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-black uppercase tracking-[0.15em] text-[#0b6b4f]">Revisão humana obrigatória</p><h2 className="mt-1 text-xl font-black">Dados extraídos do documento</h2></div><span className="rounded-full bg-[#eef7d9] px-3 py-1.5 text-xs font-bold text-[#49621f]">Confiança {Math.round(extracted.confidence * 100)}% · {extraction.model}</span></div>
      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4"><label className="text-xs font-bold">Fornecedor<select className="field mt-2 w-full text-sm" name="supplier_id" defaultValue={extraction.suggested_supplier_id ?? ""} required><option value="">Selecione</option>{suppliers.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label className="text-xs font-bold">Centro de custo<select className="field mt-2 w-full text-sm" name="cost_center_id" defaultValue={extraction.suggested_cost_center_id ?? ""}><option value="">Sem centro</option>{costCenters.map((item) => <option value={item.id} key={item.id}>{item.code} · {item.name}</option>)}</select></label><ReviewField label="Número da fatura" name="invoice_number" value={extracted.invoice_number} required /><ReviewField label="Valor" name="amount" value={extracted.amount} type="number" required /><ReviewField label="Emissão" name="issue_date" value={extracted.issue_date} type="date" required /><ReviewField label="Vencimento" name="due_date" value={extracted.due_date} type="date" required /><ReviewField label="Categoria" name="category" value={extracted.category} required /><ReviewField label="Moeda" name="currency" value={extracted.currency ?? "BRL"} required /><label className="text-xs font-bold md:col-span-2 xl:col-span-4">Descrição<textarea className="field mt-2 min-h-24 w-full text-sm" name="description" defaultValue={extracted.description ?? ""} required /></label></div>
      {extracted.warnings.length > 0 && <div className="mt-4 rounded-xl bg-amber-50 p-4 text-xs leading-5 text-amber-800">{extracted.warnings.join(" ")}</div>}<div className="mt-5 flex justify-end gap-3"><button className="rounded-xl border border-[#cbd8d2] px-4 py-2.5 text-sm font-bold" type="button" onClick={() => setExtraction(null)}>Cancelar</button><button className="rounded-xl bg-[#0b6b4f] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-60" disabled={busy}>Confirmar e criar fatura</button></div></form>}
    <Table headers={["Arquivo", "Tipo", "Tamanho", "Enviado em", "Status", "Ação"]}>{data.items.map((item) => <tr className="border-t border-[#edf1ef]" key={item.id}><td className="py-4 font-bold">{item.original_name}</td><td>{item.media_type}</td><td>{(item.size_bytes / 1024).toFixed(1)} KB</td><td>{new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(item.uploaded_at))}</td><td><Status value={item.status} /></td><td className="text-right"><button className="rounded-lg border border-[#b9c9c2] px-3 py-2 text-xs font-bold text-[#0b6b4f] disabled:opacity-50" disabled={extractingId === item.id || item.status === "processing" || item.status === "completed"} onClick={() => void openExtraction(item)}>{extractingId === item.id ? "Extraindo…" : item.status === "review" ? "Revisar" : item.status === "failed" ? "Tentar novamente" : item.status === "completed" ? "Concluído" : "Extrair com IA"}</button></td></tr>)}</Table></div>;
}

function ReviewField({ label, name, value, type = "text", required = false }: { label: string; name: string; value: string | number | null; type?: string; required?: boolean }) { return <label className="text-xs font-bold">{label}<input className="field mt-2 w-full text-sm" name={name} type={type} step={type === "number" ? "0.01" : undefined} defaultValue={value ?? ""} required={required} /></label>; }

function Table({ headers, children }: { headers: string[]; children: React.ReactNode }) { return <div className="overflow-x-auto rounded-2xl border border-[#dfe7e3] bg-white px-5"><table className="w-full min-w-[720px] text-left text-sm"><thead className="text-xs uppercase tracking-wide text-[#708078]"><tr>{headers.map((header, index) => <th className={`py-4 ${index === headers.length - 1 ? "text-right" : ""}`} key={header}>{header}</th>)}</tr></thead><tbody>{children}</tbody></table></div>; }
function Empty() { return <div className="rounded-2xl border border-[#dfe7e3] bg-white p-10 text-center text-sm text-[#66766f]">Carregando dados…</div>; }
