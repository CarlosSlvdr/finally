"use client";

import { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { WatchlistPanel } from "@/components/WatchlistPanel";
import { ChartPanel } from "@/components/ChartPanel";
import { HeatmapPanel } from "@/components/HeatmapPanel";
import { PnlChart } from "@/components/PnlChart";
import { PositionsTable } from "@/components/PositionsTable";
import { TradeBar } from "@/components/TradeBar";
import { ChatPanel } from "@/components/ChatPanel";
import { api } from "@/lib/apiClient";
import { generateId } from "@/lib/id";
import { usePrices } from "@/lib/usePrices";
import type { ChatMessage, Portfolio, PortfolioSnapshot, TradeSide } from "@/lib/types";
import { DEFAULT_TICKERS } from "@/lib/config";

export default function Home() {
  const { prices, status } = usePrices();
  const [tickers, setTickers] = useState<string[]>(DEFAULT_TICKERS);
  const [selected, setSelected] = useState<string | null>(DEFAULT_TICKERS[0] ?? null);
  const [portfolio, setPortfolio] = useState<Portfolio>({ cash_balance: 0, positions: [], total_value: 0 });
  const [history, setHistory] = useState<PortfolioSnapshot[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatCollapsed, setChatCollapsed] = useState(false);

  const refreshPortfolio = useCallback(async () => {
    const [p, h] = await Promise.all([api.getPortfolio(), api.getHistory()]);
    setPortfolio(p);
    setHistory(h);
  }, []);

  const refreshWatchlist = useCallback(async () => {
    const entries = await api.getWatchlist();
    setTickers(entries.map((e) => e.ticker));
    return entries.map((e) => e.ticker);
  }, []);

  useEffect(() => {
    refreshWatchlist();
    refreshPortfolio();
    const interval = setInterval(refreshPortfolio, 5000);
    return () => clearInterval(interval);
  }, [refreshPortfolio, refreshWatchlist]);

  const handleAdd = async (ticker: string) => {
    await api.addTicker(ticker);
    await refreshWatchlist();
  };

  const handleRemove = async (ticker: string) => {
    await api.removeTicker(ticker);
    const remaining = await refreshWatchlist();
    setSelected((prev) => (prev === ticker ? remaining[0] ?? null : prev));
  };

  const handleTrade = async (ticker: string, side: TradeSide, quantity: number) => {
    await api.trade(ticker, side, quantity);
    await refreshPortfolio();
  };

  const handleSend = async (content: string) => {
    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setChatLoading(true);
    try {
      const response = await api.chat(content);
      const trades = response.actions?.trades ?? [];
      const watchlistChanges = response.actions?.watchlist_changes ?? [];
      const actions = [
        ...trades.map((t) => ({
          type: "trade" as const,
          detail: t.error
            ? `${t.side.toUpperCase()} ${t.quantity} ${t.ticker} failed: ${t.error}`
            : `${t.side.toUpperCase()} ${t.quantity} ${t.ticker}`,
          failed: Boolean(t.error),
        })),
        ...watchlistChanges.map((w) => ({
          type: (w.action === "add" ? ("watchlist_add" as const) : ("watchlist_remove" as const)),
          detail: w.error ? `Watchlist ${w.action} failed for ${w.ticker}: ${w.error}` : `Watchlist ${w.action}: ${w.ticker}`,
          failed: Boolean(w.error),
        })),
      ];
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          role: "assistant",
          content: response.message,
          actions,
          created_at: new Date().toISOString(),
        },
      ]);
      if (trades.some((t) => !t.error) || watchlistChanges.some((w) => !w.error)) {
        refreshPortfolio();
        refreshWatchlist();
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          role: "assistant",
          content: `Something went wrong: ${(err as Error).message}`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-bg-app">
      <Header status={status} totalValue={portfolio.total_value} cashBalance={portfolio.cash_balance} />

      <div className="grid min-h-0 flex-1 grid-cols-[280px_1fr_auto]">
        <WatchlistPanel
          tickers={tickers}
          prices={prices}
          selected={selected}
          onSelect={setSelected}
          onAdd={handleAdd}
          onRemove={handleRemove}
        />

        <div className="grid min-h-0 grid-rows-[1fr_auto_220px_260px]">
          <ChartPanel ticker={selected} state={selected ? prices[selected] : undefined} />
          <TradeBar defaultTicker={selected} onTrade={handleTrade} />
          <div className="grid min-h-0 grid-cols-2 border-b border-border-subtle">
            <HeatmapPanel positions={portfolio.positions} />
            <PnlChart snapshots={history} />
          </div>
          <PositionsTable positions={portfolio.positions} />
        </div>

        <div className={chatCollapsed ? "w-10" : "w-80"}>
          <ChatPanel
            messages={messages}
            loading={chatLoading}
            collapsed={chatCollapsed}
            onToggleCollapsed={() => setChatCollapsed((c) => !c)}
            onSend={handleSend}
          />
        </div>
      </div>
    </div>
  );
}
