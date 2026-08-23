"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PortfolioSnapshot } from "@/lib/types";

interface PnlChartProps {
  snapshots: PortfolioSnapshot[];
}

export function PnlChart({ snapshots }: PnlChartProps) {
  const data = snapshots.map((s) => ({
    time: new Date(s.recorded_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    value: s.total_value,
  }));
  const first = data[0]?.value ?? 0;
  const last = data[data.length - 1]?.value ?? 0;
  const positive = last >= first;

  return (
    <section className="flex h-full flex-col bg-bg-panel">
      <div className="border-b border-border-subtle px-4 py-3">
        <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-text-muted">
          Portfolio Value
        </h2>
      </div>
      <div className="min-h-0 flex-1 p-2">
        {data.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="pnlFill" x1="0" y1="0" x2="0" y2="1">
                  <stop
                    offset="0%"
                    stopColor={positive ? "var(--up)" : "var(--down)"}
                    stopOpacity={0.35}
                  />
                  <stop
                    offset="100%"
                    stopColor={positive ? "var(--up)" : "var(--down)"}
                    stopOpacity={0}
                  />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" hide />
              <YAxis domain={["auto", "auto"]} hide />
              <Tooltip
                contentStyle={{
                  background: "var(--bg-panel-raised)",
                  border: "1px solid var(--border-strong)",
                  borderRadius: 4,
                  fontSize: 12,
                  fontFamily: "var(--font-mono)",
                }}
                formatter={(value) => [`$${Number(value).toFixed(2)}`, "Value"]}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={positive ? "var(--up)" : "var(--down)"}
                strokeWidth={1.5}
                fill="url(#pnlFill)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center font-mono text-sm text-text-muted">
            Building history…
          </div>
        )}
      </div>
    </section>
  );
}
