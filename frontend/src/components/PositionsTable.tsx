import type { Position } from "@/lib/types";

interface PositionsTableProps {
  positions: Position[];
}

export function PositionsTable({ positions }: PositionsTableProps) {
  return (
    <section className="flex h-full flex-col border-t border-border-subtle bg-bg-panel">
      <div className="border-b border-border-subtle px-4 py-3">
        <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-text-muted">
          Positions
        </h2>
      </div>
      <div className="flex-1 overflow-auto">
        <table className="w-full border-collapse font-mono text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-left text-xs uppercase tracking-wide text-text-muted">
              <th className="px-4 py-2 font-medium">Ticker</th>
              <th className="px-4 py-2 font-medium text-right">Qty</th>
              <th className="px-4 py-2 font-medium text-right">Avg Cost</th>
              <th className="px-4 py-2 font-medium text-right">Price</th>
              <th className="px-4 py-2 font-medium text-right">P&amp;L</th>
              <th className="px-4 py-2 font-medium text-right">%</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-text-muted">
                  No open positions yet
                </td>
              </tr>
            )}
            {positions.map((p) => {
              const positive = p.unrealized_pnl >= 0;
              return (
                <tr key={p.ticker} className="border-b border-border-subtle/60">
                  <td className="px-4 py-2 font-semibold text-text-primary">{p.ticker}</td>
                  <td className="px-4 py-2 text-right tabular-nums text-text-secondary">{p.quantity}</td>
                  <td className="px-4 py-2 text-right tabular-nums text-text-secondary">
                    ${p.avg_cost.toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-text-primary">
                    ${p.current_price.toFixed(2)}
                  </td>
                  <td className={`px-4 py-2 text-right tabular-nums ${positive ? "text-up" : "text-down"}`}>
                    {positive ? "+" : "-"}${Math.abs(p.unrealized_pnl).toFixed(2)}
                  </td>
                  <td className={`px-4 py-2 text-right tabular-nums ${positive ? "text-up" : "text-down"}`}>
                    {positive ? "+" : ""}
                    {p.unrealized_pnl_percent.toFixed(2)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
