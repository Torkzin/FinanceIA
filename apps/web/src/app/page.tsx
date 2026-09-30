import { HealthStatus } from "@/components/health-status";

const capabilities = [
  { title: "Operações centralizadas", text: "Fornecedores, centros de custo e faturas em um fluxo auditável." },
  { title: "IA com supervisão", text: "Extração estruturada e revisão humana antes de qualquer persistência." },
  { title: "Decisões explicáveis", text: "Consultas seguras, fontes rastreáveis e anomalias baseadas em regras." },
];

const milestones = ["Base técnica", "Dados e acesso", "Operações", "Inteligência"];

export default function Home() {
  return (
    <main className="min-h-screen px-5 py-6 sm:px-8 lg:px-12">
      <nav className="mx-auto flex max-w-7xl items-center justify-between border-b border-[#dce5e1] pb-5">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-[#0b6b4f] text-sm font-black text-white shadow-lg shadow-emerald-900/15">
            F
          </div>
          <div>
            <p className="font-bold tracking-tight">FinanceAI</p>
            <p className="text-xs text-[#697a73]">Financial operations platform</p>
          </div>
        </div>
        <a
          className="hidden rounded-full border border-[#cbd8d2] bg-white px-4 py-2 text-sm font-semibold transition hover:border-[#0b6b4f] sm:block"
          href="http://localhost:8000/docs"
        >
          Explorar API
        </a>
      </nav>

      <section className="mx-auto grid max-w-7xl gap-12 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-24">
        <div>
          <div className="mb-7 flex flex-wrap items-center gap-3">
            <span className="rounded-full bg-[#e4f6bd] px-3 py-2 text-xs font-bold uppercase tracking-[0.16em] text-[#31520f]">
              Fases 1–6 · Operacional
            </span>
            <HealthStatus />
          </div>
          <h1 className="max-w-3xl text-5xl font-black leading-[0.98] tracking-[-0.055em] text-[#102a21] sm:text-6xl lg:text-7xl">
            Finanças mais claras. IA sob controle.
          </h1>
          <p className="mt-7 max-w-2xl text-lg leading-8 text-[#5b6d66]">
            Uma plataforma de operações financeiras construída para transformar documentos, dados e políticas internas em decisões confiáveis — sem esconder regras de negócio em prompts.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <a className="rounded-xl bg-[#0b6b4f] px-5 py-3.5 text-sm font-bold text-white shadow-lg shadow-emerald-950/15 transition hover:bg-[#07553f]" href="/workspace">
              Abrir workspace
            </a>
            <a className="rounded-xl bg-[#0b6b4f] px-5 py-3.5 text-sm font-bold text-white shadow-lg shadow-emerald-950/15 transition hover:bg-[#07553f]" href="http://localhost:8000/docs">
              Ver documentação da API
            </a>
            <a className="rounded-xl border border-[#cbd8d2] bg-white px-5 py-3.5 text-sm font-bold transition hover:border-[#0b6b4f]" href="#architecture">
              Conhecer a arquitetura
            </a>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-[2rem] border border-white/80 bg-[#102a21] p-6 text-white shadow-2xl shadow-emerald-950/20 sm:p-8">
          <div className="absolute -right-20 -top-20 size-64 rounded-full bg-[#c8f266]/20 blur-3xl" />
          <div className="relative">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-emerald-100/70">Visão do produto</p>
                <p className="mt-1 text-xl font-bold">Arquitetura responsável</p>
              </div>
              <div className="rounded-xl bg-white/10 px-3 py-2 text-xs font-bold text-[#c8f266]">v0.1</div>
            </div>
            <div className="mt-8 space-y-3" id="architecture">
              {[
                ["Next.js", "Experiência B2B responsiva"],
                ["FastAPI", "Casos de uso e ferramentas seguras"],
                ["PostgreSQL", "Dados transacionais + pgvector"],
              ].map(([name, description], index) => (
                <div className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.07] p-4" key={name}>
                  <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-[#c8f266] text-sm font-black text-[#19310e]">0{index + 1}</span>
                  <div>
                    <p className="font-bold">{name}</p>
                    <p className="mt-0.5 text-sm text-emerald-50/60">{description}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 rounded-2xl bg-[#c8f266] p-5 text-[#19310e]">
              <p className="text-xs font-black uppercase tracking-[0.16em]">Princípio central</p>
              <p className="mt-2 text-lg font-bold leading-6">Código decide. IA interpreta. Pessoas confirmam.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl border-t border-[#dce5e1] py-14">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-[#0b6b4f]">Projetado para demonstrar</p>
        <div className="mt-7 grid gap-4 md:grid-cols-3">
          {capabilities.map((capability, index) => (
            <article className="rounded-2xl border border-[#dfe7e3] bg-white/80 p-6 shadow-sm" key={capability.title}>
              <p className="text-sm font-black text-[#0b6b4f]">0{index + 1}</p>
              <h2 className="mt-8 text-xl font-bold tracking-tight">{capability.title}</h2>
              <p className="mt-3 leading-7 text-[#66766f]">{capability.text}</p>
            </article>
          ))}
        </div>
      </section>

      <footer className="mx-auto flex max-w-7xl flex-col gap-5 border-t border-[#dce5e1] py-8 text-sm text-[#697a73] sm:flex-row sm:items-center sm:justify-between">
        <p>FinanceAI · Portfolio project</p>
        <div className="flex flex-wrap gap-2">
          {milestones.map((milestone) => (
            <span className="rounded-full bg-[#dff4b5] px-3 py-1.5 font-bold text-[#31520f]" key={milestone}>
              {milestone}
            </span>
          ))}
        </div>
      </footer>
    </main>
  );
}

