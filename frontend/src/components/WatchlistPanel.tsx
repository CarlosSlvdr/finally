"use client";

import { useState } from "react";
import { Sparkline } from "./Sparkline";
import type { TickerState } from "@/lib/usePrices";

interface WatchlistPanelProps {
  tickers: string[];
  prices: Record<string, TickerState>;
  selected: string | null;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

export function WatchlistPanel({ tickers, prices, selected, onSelect, onAdd, onRemove }: WatchlistPanelProps) {
  const [draft, setDraft] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft.trim()) return;
    onAdd(draft.trim().toUpperCase());
    setDraft("");
  };

  return (
    <section className="flex h-full flex-col border-r border-border-subtle bg-bg-panel">
      <div className="border-b border-border-subtle px-4 py-3">
        <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-text-muted">
          Watchlist
        </h2>
      </div>

      <form onSubmit={submit} className="flex gap-2 border-b border-border-subtle px-4 py-3">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add ticker"
          aria-label="Add ticker"
          className="min-w-0 flex-1 rounded border border-border-subtle bg-bg-panel-raised px-2 py-1.5 font-mono text-sm uppercase text-text-primary placeholder:text-text-muted focus:border-accent-blue focus:outline-none"
        />
        <button
          type="submit"
          className="rounded bg-accent-blue px-3 py-1.5 font-mono text-xs font-semibold uppercase text-white transition hover:brightness-110"
        >
          Add
        </button>
      </form>

      <ul className="flex-1 overflow-y-auto">
        {tickers.map((ticker) => {
          const state = prices[ticker];
          const isSelected = ticker === selected;
          const changed = state && state.price !== state.previousPrice;
          const flashClass = changed ? (state!.direction === "down" ? "flash-down" : "flash-up") : "";
          const positive = state ? state.price >= state.previousPrice : true;
          const changePct =
            state && state.previousPrice
              ? ((state.price - state.previousPrice) / state.previousPrice) * 100
              : 0;

          return (
            <li key={ticker}>
              <div
                key={state?.lastUpdated}
                role="button"
                tabIndex={0}
                onClick={() => onSelect(ticker)}
                onKeyDown={(e) => e.key === "Enter" && onSelect(ticker)}
                data-testid={`watchlist-row-${ticker}`}
                className={`group flex cursor-pointer items-center gap-3 border-b border-border-subtle px-4 py-2.5 transition-colors ${
                  isSelected ? "bg-bg-panel-raised" : ""
                } ${flashClass}`}
              >
                <div className="w-16 shrink-0">
                  <div className="font-mono text-sm font-semibold text-text-primary">{ticker}</div>
                  <div className={`font-mono text-xs tabular-nums ${positive ? "text-up" : "text-down"}`}>
                    {changePct >= 0 ? "+" : ""}
                    {changePct.toFixed(2)}%
                  </div>
                </div>

                <Sparkline values={state?.history ?? []} positive={positive} />

                <div className="ml-auto text-right">
                  <div className="font-mono text-sm tabular-nums text-text-primary">
                    {state ? state.price.toFixed(2) : "—"}
                  </div>
                </div>

                <button
                  type="button"
                  aria-label={`Remove ${ticker}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove(ticker);
                  }}
                  className="ml-1 shrink-0 text-text-muted opacity-0 transition group-hover:opacity-100 hover:text-down"
                >
                  ×
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
