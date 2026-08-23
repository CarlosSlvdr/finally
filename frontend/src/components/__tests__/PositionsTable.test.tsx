import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PositionsTable } from "../PositionsTable";
import type { Position } from "@/lib/types";

describe("PositionsTable", () => {
  it("shows an empty state with no positions", () => {
    render(<PositionsTable positions={[]} />);
    expect(screen.getByText("No open positions yet")).toBeInTheDocument();
  });

  it("renders P&L and % change for a profitable position", () => {
    const position: Position = {
      ticker: "AAPL",
      quantity: 10,
      avg_cost: 100,
      current_price: 110,
      market_value: 1100,
      unrealized_pnl: 100,
      unrealized_pnl_percent: 10,
    };
    render(<PositionsTable positions={[position]} />);
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("+$100.00")).toBeInTheDocument();
    expect(screen.getByText("+10.00%")).toBeInTheDocument();
  });

  it("renders P&L for a losing position without a leading plus", () => {
    const position: Position = {
      ticker: "TSLA",
      quantity: 2,
      avg_cost: 250,
      current_price: 200,
      market_value: 400,
      unrealized_pnl: -100,
      unrealized_pnl_percent: -20,
    };
    render(<PositionsTable positions={[position]} />);
    expect(screen.getByText("-$100.00")).toBeInTheDocument();
    expect(screen.getByText("-20.00%")).toBeInTheDocument();
  });
});
