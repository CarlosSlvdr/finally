"use client";

import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "@/lib/types";

interface ChatPanelProps {
  messages: ChatMessage[];
  loading: boolean;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onSend: (message: string) => void;
}

export function ChatPanel({ messages, loading, collapsed, onToggleCollapsed, onSend }: ChatPanelProps) {
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft.trim() || loading) return;
    onSend(draft.trim());
    setDraft("");
  };

  if (collapsed) {
    return (
      <button
        type="button"
        onClick={onToggleCollapsed}
        aria-label="Open AI chat"
        className="flex h-full w-10 flex-col items-center justify-center gap-3 border-l border-border-subtle bg-bg-panel text-text-muted hover:text-accent-yellow"
      >
        <span className="rotate-180 font-mono text-xs uppercase tracking-widest [writing-mode:vertical-rl]">
          AI Copilot
        </span>
      </button>
    );
  }

  return (
    <section className="flex h-full w-full flex-col border-l border-border-subtle bg-bg-panel">
      <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
        <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-text-muted">
          AI Copilot
        </h2>
        <button
          type="button"
          onClick={onToggleCollapsed}
          aria-label="Collapse AI chat"
          className="text-text-muted hover:text-text-primary"
        >
          ⟩⟩
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.length === 0 && (
          <p className="font-mono text-xs text-text-muted">
            Ask FinAlly about your portfolio, or tell it to buy, sell, or manage your watchlist.
          </p>
        )}
        {messages.map((m) => (
          <div key={m.id} className={m.role === "user" ? "text-right" : "text-left"}>
            <div
              className={`inline-block max-w-[90%] rounded-lg px-3 py-2 text-left text-sm ${
                m.role === "user"
                  ? "bg-accent-blue/20 text-text-primary"
                  : "bg-bg-panel-raised text-text-primary"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.actions && m.actions.length > 0 && (
                <ul className="mt-2 space-y-1 border-t border-border-subtle pt-2">
                  {m.actions.map((a, i) => (
                    <li key={i} className="font-mono text-xs text-accent-yellow">
                      ✓ {a.detail}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="text-left">
            <div className="inline-block rounded-lg bg-bg-panel-raised px-3 py-2 font-mono text-xs text-text-muted">
              FinAlly is thinking…
            </div>
          </div>
        )}
      </div>

      <form onSubmit={submit} className="flex gap-2 border-t border-border-subtle px-3 py-3">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask FinAlly…"
          aria-label="Chat message"
          className="min-w-0 flex-1 rounded border border-border-subtle bg-bg-panel-raised px-2 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-blue focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-accent-purple px-3 py-1.5 font-mono text-xs font-semibold uppercase text-white transition hover:brightness-110 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </section>
  );
}
