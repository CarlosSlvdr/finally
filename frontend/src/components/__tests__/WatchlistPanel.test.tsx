import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { WatchlistPanel } from "../WatchlistPanel";
import type { TickerState } from "@/lib/usePrices";

function makeState(overrides: Partial<TickerState> = {}): TickerState {
  return {
    price: 101,
    previousPrice: 100,
    direction: "up",
    history: [99, 100, 101],
    lastUpdated: Date.now(),
    ...overrides,
  };
}

describe("WatchlistPanel", () => {
  it("flashes green when a price ticks up", () => {
    render(
      <WatchlistPanel
        tickers={["AAPL"]}
        prices={{ AAPL: makeState({ direction: "up" }) }}
        selected={null}
        onSelect={vi.fn()}
        onAdd={vi.fn()}
        onRemove={vi.fn()}
      />,
    );
    expect(screen.getByTestId("watchlist-row-AAPL")).toHaveClass("flash-up");
  });

  it("flashes red when a price ticks down", () => {
    render(
      <WatchlistPanel
        tickers={["AAPL"]}
        prices={{ AAPL: makeState({ price: 98, previousPrice: 100, direction: "down" }) }}
        selected={null}
        onSelect={vi.fn()}
        onAdd={vi.fn()}
        onRemove={vi.fn()}
      />,
    );
    expect(screen.getByTestId("watchlist-row-AAPL")).toHaveClass("flash-down");
  });

  it("does not flash when the price is unchanged", () => {
    render(
      <WatchlistPanel
        tickers={["AAPL"]}
        prices={{ AAPL: makeState({ price: 100, previousPrice: 100, direction: "flat" }) }}
        selected={null}
        onSelect={vi.fn()}
        onAdd={vi.fn()}
        onRemove={vi.fn()}
      />,
    );
    const row = screen.getByTestId("watchlist-row-AAPL");
    expect(row).not.toHaveClass("flash-up");
    expect(row).not.toHaveClass("flash-down");
  });

  it("adds a ticker from the input", async () => {
    const onAdd = vi.fn();
    render(
      <WatchlistPanel
        tickers={[]}
        prices={{}}
        selected={null}
        onSelect={vi.fn()}
        onAdd={onAdd}
        onRemove={vi.fn()}
      />,
    );
    await userEvent.type(screen.getByLabelText("Add ticker"), "pypl");
    await userEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(onAdd).toHaveBeenCalledWith("PYPL");
  });

  it("removes a ticker via its remove button", async () => {
    const onRemove = vi.fn();
    render(
      <WatchlistPanel
        tickers={["AAPL"]}
        prices={{ AAPL: makeState() }}
        selected={null}
        onSelect={vi.fn()}
        onAdd={vi.fn()}
        onRemove={onRemove}
      />,
    );
    await userEvent.click(screen.getByLabelText("Remove AAPL"));
    expect(onRemove).toHaveBeenCalledWith("AAPL");
  });

  it("selects a ticker on row click", async () => {
    const onSelect = vi.fn();
    render(
      <WatchlistPanel
        tickers={["AAPL"]}
        prices={{ AAPL: makeState() }}
        selected={null}
        onSelect={onSelect}
        onAdd={vi.fn()}
        onRemove={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByTestId("watchlist-row-AAPL"));
    expect(onSelect).toHaveBeenCalledWith("AAPL");
  });
});
