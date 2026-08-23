"use client";

import { useState } from "react";
import type { TradeSide } from "@/lib/types";

interface TradeBarProps {
  defaultTicker: string | null;
  onTrade: (ticker: string, side: TradeSide, quantity: number) => Promise<void>;
}

export function TradeBar({ defaultTicker, onTrade }: TradeBarProps) {
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("1");

  // Selecting a different watchlist row re-targets the trade bar unless the
  // user has already typed a ticker of their own for this trade. Adjusting
  // state during render (React's documented pattern) avoids an extra effect.
  const [trackedDefault, setTrackedDefault] = useState(defaultTicker);
  if (defaultTicker !== trackedDefault) {
    setTrackedDefault(defaultTicker);
    setTicker("");
  }
  const [pending, setPending] = useState<TradeSide | null>(null);
  const [error, setError] = useState<string | null>(null);

  const effectiveTicker = (ticker || defaultTicker || "").toUpperCase();

  const submit = async (side: TradeSide) => {
    const qty = Number(quantity);
    if (!effectiveTicker || !qty || qty <= 0) {
      setError("Enter a ticker and a positive quantity");
      return;
    }
    setError(null);
    setPending(side);
    try {
      await onTrade(effectiveTicker, side, qty);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="flex items-center gap-2 border-t border-border-subtle bg-bg-panel-raised px-4 py-2.5">
      <input
        value={ticker}
        onChange={(e) => setTicker(e.target.value)}
        placeholder={defaultTicker ?? "TICKER"}
        aria-label="Trade ticker"
        className="w-24 rounded border border-border-subtle bg-bg-app px-2 py-1.5 font-mono text-sm uppercase text-text-primary placeholder:text-text-muted focus:border-accent-blue focus:outline-none"
      />
      <input
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        type="number"
        min="0"
        step="any"
        aria-label="Trade quantity"
        className="w-20 rounded border border-border-subtle bg-bg-app px-2 py-1.5 font-mono text-sm text-text-primary focus:border-accent-blue focus:outline-none"
      />
      <button
        type="button"
        disabled={pending !== null}
        onClick={() => submit("buy")}
        className="rounded bg-accent-purple px-4 py-1.5 font-mono text-xs font-semibold uppercase text-white transition hover:brightness-110 disabled:opacity-50"
      >
        {pending === "buy" ? "Buying…" : "Buy"}
      </button>
      <button
        type="button"
        disabled={pending !== null}
        onClick={() => submit("sell")}
        className="rounded border border-down px-4 py-1.5 font-mono text-xs font-semibold uppercase text-down transition hover:bg-down-dim disabled:opacity-50"
      >
        {pending === "sell" ? "Selling…" : "Sell"}
      </button>
      {error && <span className="font-mono text-xs text-down">{error}</span>}
    </div>
  );
}
