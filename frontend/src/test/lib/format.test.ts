import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  formatDateTime,
  formatFileSize,
  formatRelativeOrDate,
  sentenceCase,
} from "@/lib/format";

describe("sentenceCase", () => {
  it("capitalises first letter of each word", () => {
    expect(sentenceCase("hello world")).toBe("Hello World");
  });

  it("replaces underscores with spaces", () => {
    expect(sentenceCase("snake_case_value")).toBe("Snake Case Value");
  });

  it("handles single word", () => {
    expect(sentenceCase("standard")).toBe("Standard");
  });

  it("handles already capitalised input", () => {
    expect(sentenceCase("Already Done")).toBe("Already Done");
  });
});

describe("formatFileSize", () => {
  it("returns bytes for values under 1 KB", () => {
    expect(formatFileSize(512)).toBe("512 B");
  });

  it("returns KB for values between 1 KB and 1 MB", () => {
    expect(formatFileSize(2048)).toBe("2.0 KB");
  });

  it("returns MB for values 1 MB and above", () => {
    expect(formatFileSize(1024 * 1024 * 3)).toBe("3.0 MB");
  });

  it("returns 0 B for zero bytes", () => {
    expect(formatFileSize(0)).toBe("0 B");
  });
});

describe("formatDateTime", () => {
  it("returns em dash for null", () => {
    expect(formatDateTime(null)).toBe("—");
  });

  it("returns em dash for undefined", () => {
    expect(formatDateTime(undefined)).toBe("—");
  });

  it("returns original value for invalid date string", () => {
    expect(formatDateTime("not-a-date")).toBe("not-a-date");
  });

  it("returns a formatted string for a valid ISO date", () => {
    const result = formatDateTime("2024-01-15T10:30:00Z");
    expect(typeof result).toBe("string");
    expect(result).not.toBe("—");
    expect(result.length).toBeGreaterThan(0);
  });
});

describe("formatRelativeOrDate", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns em dash for null", () => {
    expect(formatRelativeOrDate(null)).toBe("—");
  });

  it("returns 'just now' for dates under 1 minute ago", () => {
    const now = new Date("2024-06-01T12:00:00Z");
    vi.setSystemTime(now);
    const thirtySecondsAgo = new Date(now.getTime() - 30_000).toISOString();
    expect(formatRelativeOrDate(thirtySecondsAgo)).toBe("just now");
  });

  it("returns minutes ago for dates under 60 minutes ago", () => {
    const now = new Date("2024-06-01T12:00:00Z");
    vi.setSystemTime(now);
    const tenMinutesAgo = new Date(now.getTime() - 10 * 60_000).toISOString();
    expect(formatRelativeOrDate(tenMinutesAgo)).toBe("10 min ago");
  });

  it("returns hours ago for dates under 24 hours ago", () => {
    const now = new Date("2024-06-01T12:00:00Z");
    vi.setSystemTime(now);
    const threeHoursAgo = new Date(now.getTime() - 3 * 3600_000).toISOString();
    expect(formatRelativeOrDate(threeHoursAgo)).toBe("3 hours ago");
  });

  it("returns days ago for dates under 7 days ago", () => {
    const now = new Date("2024-06-01T12:00:00Z");
    vi.setSystemTime(now);
    const twoDaysAgo = new Date(now.getTime() - 2 * 86400_000).toISOString();
    expect(formatRelativeOrDate(twoDaysAgo)).toBe("2 days ago");
  });

  it("returns formatted date for dates older than 7 days", () => {
    const now = new Date("2024-06-20T12:00:00Z");
    vi.setSystemTime(now);
    const twoWeeksAgo = new Date(now.getTime() - 14 * 86400_000).toISOString();
    const result = formatRelativeOrDate(twoWeeksAgo);
    expect(result).not.toBe("—");
    expect(result).not.toContain("ago");
  });
});
