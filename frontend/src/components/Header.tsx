import type { ConnectionStatus } from "@/lib/types";

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  connected: "Live",
  reconnecting: "Reconnecting",
  disconnected: "Offline",
};

const STATUS_COLOR: Record<ConnectionStatus, string> = {
  connected: "var(--up)",
  reconnecting: "var(--accent-yellow)",
  disconnected: "var(--down)",
};

interface HeaderProps {
  status: ConnectionStatus;
  totalValue: number;
  cashBalance: number;
}

export function Header({ status, totalValue, cashBalance }: HeaderProps) {
  return (
    <header className="flex items-center justify-between border-b border-border-subtle bg-bg-panel px-5 py-3">
      <div className="flex items-center gap-3">
        <span className="font-display text-lg font-semibold tracking-tight text-text-primary">
          Fin<span className="text-accent-yellow">Ally</span>
        </span>
        <span className="hidden font-mono text-xs uppercase tracking-widest text-text-muted sm:inline">
          AI Trading Workstation
        </span>
      </div>

      <div className="flex items-center gap-6">
        <div className="text-right">
          <div className="font-mono text-xs uppercase tracking-wide text-text-muted">Portfolio</div>
          <div className="font-mono text-base font-semibold tabular-nums text-text-primary">
            ${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono text-xs uppercase tracking-wide text-text-muted">Cash</div>
          <div className="font-mono text-base font-semibold tabular-nums text-accent-blue">
            ${cashBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-border-subtle bg-bg-panel-raised px-3 py-1.5">
          <span
            data-testid="connection-dot"
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: STATUS_COLOR[status], boxShadow: `0 0 6px ${STATUS_COLOR[status]}` }}
          />
          <span className="font-mono text-xs uppercase tracking-wide text-text-secondary">
            {STATUS_LABEL[status]}
          </span>
        </div>
      </div>
    </header>
  );
}
