import "@testing-library/jest-dom";

// Mock ResizeObserver for Recharts
(globalThis as any).ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
