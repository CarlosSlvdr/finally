import type { Position } from "@/lib/types";

interface HeatmapPanelProps {
  positions: Position[];
}

export function HeatmapPanel({ positions }: HeatmapPanelProps) {
  const totalWeight = positions.reduce((sum, p) => sum + p.quantity * p.current_price, 0) || 1;

  return (
    <section className="flex h-full flex-col border-r border-border-subtle bg-bg-panel">
      <div className="border-b border-border-subtle px-4 py-3">
        <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-text-muted">
          Exposure
        </h2>
      </div>
      <div className="flex flex-1 flex-wrap content-start gap-1.5 overflow-y-auto p-3">
        {positions.length === 0 && (
          <div className="flex w-full items-center justify-center font-mono text-sm text-text-muted">
            No open positions
          </div>
        )}
        {positions.map((p) => {
          const weight = (p.quantity * p.current_price) / totalWeight;
          const pnlPositive = p.unrealized_pnl >= 0;
          const size = Math.max(64, Math.round(Math.sqrt(weight) * 220));
          const intensity = Math.min(1, Math.abs(p.unrealized_pnl_percent) / 8);
          const bg = pnlPositive
            ? `rgba(47, 214, 122, ${0.12 + intensity * 0.35})`
            : `rgba(255, 84, 112, ${0.12 + intensity * 0.35})`;

          return (
            <div
              key={p.ticker}
              data-testid={`heatmap-${p.ticker}`}
              style={{ width: size, height: size, backgroundColor: bg }}
              className={`flex flex-col justify-between rounded border p-2 ${
                pnlPositive ? "border-up/40" : "border-down/40"
              }`}
            >
              <span className="font-mono text-xs font-semibold text-text-primary">{p.ticker}</span>
              <span className={`font-mono text-xs tabular-nums ${pnlPositive ? "text-up" : "text-down"}`}>
                {p.unrealized_pnl_percent >= 0 ? "+" : ""}
                {p.unrealized_pnl_percent.toFixed(1)}%
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
