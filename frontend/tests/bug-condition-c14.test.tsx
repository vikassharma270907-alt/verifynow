/**
 * Bug condition exploration tests for C14 (frontend error handling, abort, accessibility).
 * Property 1: Bug Condition. These encode EXPECTED behavior and are meant to FAIL on unfixed code.
 * Validates: Requirements 1.24, 1.25, 1.26 (expected: 2.18, 2.19, 2.20)
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

import App from "../src/App";
import ChallengeMode from "../src/components/ChallengeMode";
import DropZone from "../src/components/DropZone";

const LIST = [{ id: "prompt-injection", name: "Prompt injection", description: "d" }];

function jsonResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, statusText: ok ? "OK" : "Error", json: async () => body } as Response;
}

function fileOfSize(name: string, bytes: number, type = "text/plain") {
  const f = new File(["x"], name, { type });
  Object.defineProperty(f, "size", { value: bytes });
  return f;
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("C14: ChallengeMode response handling", () => {
  it("shows a visible error when the challenge detail request fails", async () => {
    const fetchMock = vi.fn(async (url: string) =>
      url === "/api/challenges" ? jsonResponse(LIST) : jsonResponse({ detail: "boom" }, false, 500),
    );
    vi.stubGlobal("fetch", fetchMock);
    const onRun = vi.fn();
    render(<ChallengeMode onRun={onRun} />);

    fireEvent.click(await screen.findByText("Prompt injection"));

    expect(await screen.findByRole("alert", {}, { timeout: 1000 })).toBeInTheDocument();
    expect(onRun).not.toHaveBeenCalled();
  });

  it("shows a visible error when the challenge list request fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ detail: "down" }, false, 503)));
    render(<ChallengeMode onRun={vi.fn()} />);
    expect(await screen.findByRole("alert", {}, { timeout: 1000 })).toBeInTheDocument();
  });
});

describe("C14: in-flight request abort on tab switch", () => {
  let signals: (AbortSignal | undefined)[];
  let resolveVerify: (r: Response) => void;

  beforeEach(() => {
    signals = [];
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url === "/api/verify") {
        signals.push(init?.signal ?? undefined);
        return new Promise<Response>((resolve, reject) => {
          resolveVerify = resolve;
          init?.signal?.addEventListener("abort", () =>
            reject(new DOMException("Aborted", "AbortError")),
          );
        });
      }
      return Promise.resolve(jsonResponse(LIST));
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  function startUpload() {
    const { container } = render(<App />);
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["Rent is $2,500"], "lease.txt", { type: "text/plain" })] } });
  }

  it("aborts the in-flight verification when the user switches tabs", async () => {
    startUpload();
    await waitFor(() => expect(signals.length).toBe(1));
    fireEvent.click(screen.getByRole("button", { name: /challenge/i }));
    expect(signals[0]).toBeDefined();
    expect(signals[0]?.aborted).toBe(true);
  });

  it("ignores a late response after the user switched tabs", async () => {
    startUpload();
    await waitFor(() => expect(signals.length).toBe(1));
    fireEvent.click(screen.getByRole("button", { name: /challenge/i }));
    const report = {
      document_name: "lease.txt", document_type: "lease_agreement", total_claims: 0,
      verified_count: 0, unverifiable_count: 0, contradicted_count: 0, risk_level: "low",
      trust_score: 100, claim_verifications: [], findings: [], analysis_notes: [],
      summary: "stale", model_tier_usage: { nano: 0, super: 0, ultra: 0 }, processing_time_ms: 1,
    };
    await act(async () => {
      resolveVerify(jsonResponse(report));
    });
    expect(screen.queryByText("Results")).not.toBeInTheDocument();
  });
});

describe("C14: DropZone validation and keyboard support", () => {
  it("rejects an unsupported file type with a visible message", () => {
    const onFileDrop = vi.fn();
    const { container } = render(<DropZone onFileDrop={onFileDrop} />);
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [fileOfSize("malware.exe", 100, "application/octet-stream")] } });
    expect(onFileDrop).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("rejects a dropped file over 20 MB with a visible message", () => {
    const onFileDrop = vi.fn();
    const { container } = render(<DropZone onFileDrop={onFileDrop} />);
    const zone = container.querySelector(".border-dashed") as HTMLElement;
    fireEvent.drop(zone, { dataTransfer: { files: [fileOfSize("big.pdf", 21 * 1024 * 1024, "application/pdf")] } });
    expect(onFileDrop).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("opens the file picker with Enter and Space on the focusable drop area", () => {
    const clickSpy = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => {});
    render(<DropZone onFileDrop={vi.fn()} />);
    const zone = screen.getByRole("button", { name: /drop/i });
    expect(zone).toHaveAttribute("tabindex", "0");
    fireEvent.keyDown(zone, { key: "Enter" });
    fireEvent.keyDown(zone, { key: " " });
    expect(clickSpy).toHaveBeenCalledTimes(2);
  });

  it("opens the file picker when the drop area is clicked", () => {
    const clickSpy = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => {});
    render(<DropZone onFileDrop={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /drop/i }));
    expect(clickSpy).toHaveBeenCalled();
  });
});
