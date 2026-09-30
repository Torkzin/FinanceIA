"use client";

import { useEffect, useState } from "react";

type HealthState = "checking" | "ready" | "unavailable";

const labels: Record<HealthState, string> = {
  checking: "Verificando ambiente",
  ready: "API e banco conectados",
  unavailable: "Ambiente indisponível",
};

export function HealthStatus() {
  const [state, setState] = useState<HealthState>("checking");

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 5000);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    fetch(`${apiUrl}/api/v1/health/ready`, { signal: controller.signal })
      .then((response) => setState(response.ok ? "ready" : "unavailable"))
      .catch(() => setState("unavailable"))
      .finally(() => window.clearTimeout(timeout));

    return () => {
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, []);

  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-[#d7e3dd] bg-white/80 px-3 py-2 text-sm font-medium text-[#355047] shadow-sm backdrop-blur">
      <span
        aria-hidden="true"
        className={`size-2 rounded-full ${
          state === "ready"
            ? "bg-emerald-500"
            : state === "checking"
              ? "animate-pulse bg-amber-400"
              : "bg-rose-500"
        }`}
      />
      {labels[state]}
    </div>
  );
}

