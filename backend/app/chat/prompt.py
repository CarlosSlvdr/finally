"""System prompt and message construction for the chat LLM call (PLAN.md section 9)."""

from __future__ import annotations

from .deps import ChatHistoryEntry, PortfolioContext

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant for a simulated brokerage terminal.

- Analyze the user's portfolio composition, risk concentration, and P&L when relevant.
- Suggest trades with clear reasoning grounded in the data given to you.
- Execute trades when the user asks for one or agrees to a suggestion, by including them in `trades`.
- Manage the user's watchlist proactively when it helps.
- Be concise and data-driven. No filler.
- Always respond with valid structured JSON matching the required schema."""


def format_portfolio_context(ctx: PortfolioContext) -> str:
    lines = [
        f"Cash balance: ${ctx.cash_balance:,.2f}",
        f"Total portfolio value: ${ctx.total_value:,.2f}",
    ]

    if ctx.positions:
        lines.append("Positions:")
        for p in ctx.positions:
            lines.append(
                f"  {p.ticker}: {p.quantity:g} sh @ avg ${p.avg_cost:.2f}, "
                f"current ${p.current_price:.2f}, "
                f"P&L ${p.unrealized_pnl:,.2f} ({p.unrealized_pnl_percent:+.2f}%)"
            )
    else:
        lines.append("Positions: none")

    if ctx.watchlist:
        watch = ", ".join(
            f"{w.ticker} (${w.current_price:.2f})" if w.current_price is not None else f"{w.ticker} (no price yet)"
            for w in ctx.watchlist
        )
        lines.append(f"Watchlist: {watch}")
    else:
        lines.append("Watchlist: empty")

    return "\n".join(lines)


def build_messages(
    ctx: PortfolioContext, history: list[ChatHistoryEntry], user_message: str
) -> list[dict[str, str]]:
    system_content = f"{SYSTEM_PROMPT}\n\nCurrent portfolio state:\n{format_portfolio_context(ctx)}"
    messages = [{"role": "system", "content": system_content}]
    messages.extend({"role": h.role, "content": h.content} for h in history)
    messages.append({"role": "user", "content": user_message})
    return messages
