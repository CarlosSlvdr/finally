import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatPanel } from "../ChatPanel";
import type { ChatMessage } from "@/lib/types";

describe("ChatPanel", () => {
  it("renders conversation history and inline action confirmations", () => {
    const messages: ChatMessage[] = [
      { id: "1", role: "user", content: "Buy 5 AAPL", created_at: new Date().toISOString() },
      {
        id: "2",
        role: "assistant",
        content: "Done.",
        actions: [{ type: "trade", detail: "BUY 5 AAPL" }],
        created_at: new Date().toISOString(),
      },
    ];
    render(
      <ChatPanel
        messages={messages}
        loading={false}
        collapsed={false}
        onToggleCollapsed={vi.fn()}
        onSend={vi.fn()}
      />,
    );
    expect(screen.getByText("Buy 5 AAPL")).toBeInTheDocument();
    expect(screen.getByText("Done.")).toBeInTheDocument();
    expect(screen.getByText("✓ BUY 5 AAPL")).toBeInTheDocument();
  });

  it("shows a loading indicator while waiting for a response", () => {
    render(
      <ChatPanel messages={[]} loading={true} collapsed={false} onToggleCollapsed={vi.fn()} onSend={vi.fn()} />,
    );
    expect(screen.getByText("FinAlly is thinking…")).toBeInTheDocument();
  });

  it("sends a message and clears the input", async () => {
    const onSend = vi.fn();
    render(
      <ChatPanel messages={[]} loading={false} collapsed={false} onToggleCollapsed={vi.fn()} onSend={onSend} />,
    );
    const input = screen.getByLabelText("Chat message");
    await userEvent.type(input, "What's my P&L?");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(onSend).toHaveBeenCalledWith("What's my P&L?");
    expect(input).toHaveValue("");
  });

  it("collapses to a rail and reopens on click", async () => {
    const onToggle = vi.fn();
    render(
      <ChatPanel messages={[]} loading={false} collapsed={true} onToggleCollapsed={onToggle} onSend={vi.fn()} />,
    );
    await userEvent.click(screen.getByLabelText("Open AI chat"));
    expect(onToggle).toHaveBeenCalled();
  });
});
