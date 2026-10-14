import { describe, it, expect } from "vitest";
import {
  h,
  relTime,
  fmtDateTime,
  getFillColor,
  priorityBadge,
  fillBar,
  bigFillBar,
  healthBadge,
  deviceState,
  simBadge,
  binStatusBadge,
  PRIORITY_LABEL,
  PRIORITY_CLASS,
} from "../utils/helpers.js";

describe("Frontend Helper Utilities", () => {
  describe("h (HTML escaping)", () => {
    it("escapes special characters properly", () => {
      expect(h("<script>alert('xss')</script>")).toBe("&lt;script&gt;alert('xss')&lt;/script&gt;");
      expect(h("AT&T & Sons")).toBe("AT&amp;T &amp; Sons");
    });

    it("handles null, undefined and numbers safely", () => {
      expect(h(null)).toBe("");
      expect(h(undefined)).toBe("");
      expect(h(42)).toBe("42");
      expect(h(0)).toBe("0");
    });
  });

  describe("relTime (relative time formatter)", () => {
    const fixedNow = 1700000000000;

    it("returns null for missing or invalid dates", () => {
      expect(relTime(null)).toBeNull();
      expect(relTime("not-a-date")).toBeNull();
    });

    it("formats seconds, minutes, and hours accurately", () => {
      const tenSecsAgo = new Date(fixedNow - 10000).toISOString();
      expect(relTime(tenSecsAgo, fixedNow)).toBe("10s ago");

      const fiveMinsAgo = new Date(fixedNow - 5 * 60 * 1000).toISOString();
      expect(relTime(fiveMinsAgo, fixedNow)).toBe("5m ago");

      const twoHoursAgo = new Date(fixedNow - 2 * 3600 * 1000).toISOString();
      expect(relTime(twoHoursAgo, fixedNow)).toBe("2h ago");
    });

    it("handles future timestamps gracefully", () => {
      const future = new Date(fixedNow + 5000).toISOString();
      expect(relTime(future, fixedNow)).toBe("just now");
    });
  });

  describe("fmtDateTime", () => {
    it("returns dash for empty/invalid timestamp", () => {
      expect(fmtDateTime(null)).toBe("—");
      expect(fmtDateTime("invalid")).toBe("—");
    });

    it("formats valid date string", () => {
      const formatted = fmtDateTime("2026-10-14T10:00:00Z");
      expect(formatted).not.toBe("—");
      expect(typeof formatted).toBe("string");
    });
  });

  describe("getFillColor & Fill Thresholds", () => {
    it("returns correct color according to threshold hierarchy", () => {
      expect(getFillColor(96)).toBe("#B42318"); // Critical > 95%
      expect(getFillColor(95)).toBe("#C2410C"); // High > 85%
      expect(getFillColor(86)).toBe("#C2410C"); // High > 85%
      expect(getFillColor(75)).toBe("#8F5F10"); // Amber >= 70%
      expect(getFillColor(70)).toBe("#8F5F10"); // Amber >= 70%
      expect(getFillColor(50)).toBe("#16A34A"); // Green < 70%
      expect(getFillColor(0)).toBe("#16A34A");  // Green
    });

    it("handles null and boundary values", () => {
      expect(getFillColor(null)).toBe("#64748B");
      expect(getFillColor(-10)).toBe("#16A34A"); // clamped
      expect(getFillColor(150)).toBe("#B42318"); // clamped
    });
  });

  describe("priorityBadge", () => {
    it("renders valid badges for all defined priority levels", () => {
      const critical = priorityBadge("CRITICAL");
      expect(critical).toContain("badge-critical");
      expect(critical).toContain("Critical");

      const high = priorityBadge("HIGH");
      expect(high).toContain("badge-high");
      expect(high).toContain("High");

      const normal = priorityBadge("NORMAL");
      expect(normal).toContain("badge-normal");
      expect(normal).toContain("Normal");
    });

    it("falls back gracefully for unknown priority", () => {
      const unknown = priorityBadge("NON_EXISTENT");
      expect(unknown).toContain("badge-unknown");
      expect(unknown).toContain("NON_EXISTENT");
    });
  });

  describe("fillBar and bigFillBar", () => {
    it("renders unavailable placeholder when fill percentage is null", () => {
      expect(fillBar(null)).toContain("— Unavailable");
      expect(bigFillBar(null)).toContain("— No valid reading");
    });

    it("clamps percentages between 0 and 100", () => {
      const under = fillBar(-5);
      expect(under).toContain("width:0.0%");
      expect(under).toContain("0%");

      const over = fillBar(105);
      expect(over).toContain("width:100.0%");
      expect(over).toContain("100%");
    });
  });

  describe("Status & Health badges", () => {
    it("renders health badges", () => {
      expect(healthBadge("OK")).toContain("badge-ok");
      expect(healthBadge("FAULT")).toContain("badge-fault");
      expect(healthBadge(null)).toContain("—");
    });

    it("renders device state indicators", () => {
      expect(deviceState("ONLINE")).toContain("online");
      expect(deviceState("OFFLINE")).toContain("offline");
    });

    it("renders simulation badge only when true", () => {
      expect(simBadge(true)).toContain("SIM");
      expect(simBadge(false)).toBe("");
    });

    it("renders bin operational status badge", () => {
      expect(binStatusBadge("ACTIVE")).toContain("badge-active");
      expect(binStatusBadge("MAINTENANCE")).toContain("badge-maintenance");
    });
  });
});
