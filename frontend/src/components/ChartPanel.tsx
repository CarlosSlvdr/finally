"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TickerState } from "@/lib/usePrices";

interface ChartPanelProps {
  ticker: string | null;
  state: TickerState | undefined;
}

export function ChartPanel({ ticker, state }: ChartPanelProps) {
  const history = state?.history ?? [];
  const data = history.map((price, i) => ({ i, price }));
  const positive = state ? state.price >= state.previousPrice : true;

  return (
    <section className="flex h-full flex-col border-b border-border-subtle bg-bg-panel">
      <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
        <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-text-muted">
          {ticker ?? "Select a ticker"}
        </h2>
        {state && (
          <span className={`font-mono text-lg font-semibold tabular-nums ${positive ? "text-up" : "text-down"}`}>
            ${state.price.toFixed(2)}
          </span>
        )}
      </div>
      <div className="min-h-0 flex-1 p-2">
        {data.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <XAxis dataKey="i" hide />
              <YAxis domain={["auto", "auto"]} hide />
              <Tooltip
                contentStyle={{
                  background: "var(--bg-panel-raised)",
                  border: "1px solid var(--border-strong)",
                  borderRadius: 4,
                  fontSize: 12,
                  fontFamily: "var(--font-mono)",
                }}
                labelFormatter={() => ""}
                formatter={(value) => [`$${Number(value).toFixed(2)}`, "Price"]}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke={positive ? "var(--up)" : "var(--down)"}
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center font-mono text-sm text-text-muted">
            {ticker ? "Waiting for price data…" : "Click a ticker in the watchlist"}
          </div>
        )}
      </div>
    </section>
  );
}
