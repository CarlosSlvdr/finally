import "@testing-library/jest-dom/vitest";

// jsdom doesn't implement scrollTo; ChatPanel uses it to autoscroll on new messages.
if (typeof Element !== "undefined" && !Element.prototype.scrollTo) {
  Element.prototype.scrollTo = () => {};
}
