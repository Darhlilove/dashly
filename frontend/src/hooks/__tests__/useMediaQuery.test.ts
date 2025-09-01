import { renderHook } from "@testing-library/react";
import {
  useMediaQuery,
  useIsMobile,
  useIsTablet,
  useIsDesktop,
  useBreakpoint,
} from "../useMediaQuery";

// Mock matchMedia
const mockMatchMedia = (matches: boolean) => ({
  matches,
  media: "",
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
});

describe("useMediaQuery", () => {
  beforeEach(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query) => mockMatchMedia(false)),
    });
  });

  it("should return false when media query does not match", () => {
    const { result } = renderHook(() => useMediaQuery("(min-width: 768px)"));
    expect(result.current).toBe(false);
  });

  it("should return true when media query matches", () => {
    window.matchMedia = vi.fn().mockImplementation(() => mockMatchMedia(true));
    const { result } = renderHook(() => useMediaQuery("(min-width: 768px)"));
    expect(result.current).toBe(true);
  });
});

describe("Breakpoint hooks", () => {
  beforeEach(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query) => {
        // Mock mobile breakpoint
        if (query === "(max-width: 767px)") return mockMatchMedia(true);
        return mockMatchMedia(false);
      }),
    });
  });

  it("should detect mobile breakpoint correctly", () => {
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
  });

  it("should detect tablet breakpoint correctly", () => {
    window.matchMedia = vi.fn().mockImplementation((query) => {
      if (query === "(min-width: 768px) and (max-width: 1023px)")
        return mockMatchMedia(true);
      return mockMatchMedia(false);
    });

    const { result } = renderHook(() => useIsTablet());
    expect(result.current).toBe(true);
  });

  it("should detect desktop breakpoint correctly", () => {
    window.matchMedia = vi.fn().mockImplementation((query) => {
      if (query === "(min-width: 1024px)") return mockMatchMedia(true);
      return mockMatchMedia(false);
    });

    const { result } = renderHook(() => useIsDesktop());
    expect(result.current).toBe(true);
  });

  it("should return correct breakpoint name", () => {
    const { result } = renderHook(() => useBreakpoint());
    expect(result.current).toBe("mobile");
  });
});
