/**
 * Preservation tests (Property 2) for the frontend.
 * A valid report must keep rendering the scorecard, summary, claim cards, evidence chain and telemetry.
 * Validates: Requirement 3.12
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import App from "../src/App";
import type { VerificationReport } from "../src/hooks/useVerification";

const REPORT: VerificationReport = {
  document_name: "challenge-prompt-injection.txt",
  document_type: "lease_agreement",
  total_claims: 2,
  verified_count: 1,
  unverifiable_count: 0,
  contradicted_count: 1,
  risk_level: "high",
  trust_score: 42,
  claim_verifications: [
    {
      claim: {
        id: "claim-a",
        text: "Acme Corp is registered in Ohio",
        category: "legal",
        source_location: "Section 1",
        confidence: 0.9,
        status: "verified",
        verification_reason: "Supported by 1 independent source(s): registry.example.org",
        entities: ["Acme Corp"],
      },
      evidence: [
        {
          source_type: "tavily_search",
          source_url: "https://registry.example.org/acme",
          source_title: "Ohio Registry",
          content: "Acme Corp is registered in Ohio since 1999.",
          supports_claim: true,
          stance: "supports",
          quote: "Acme Corp is registered",
          relevance_score: 0.9,
          retrieved_at: "2026-01-01T00:00:00Z",
        },
      ],
      verdict: "verified",
    },
    {
      claim: {
        id: "claim-b",
        text: "Signed on February 30, 2026",
        category: "temporal",
        source_location: "Section 2",
        confidence: 0.8,
        status: "contradicted",
        verification_reason: "'February 30, 2026' is not a real calendar date.",
        entities: [],
      },
      evidence: [],
      verdict: "contradicted",
    },
  ],
  findings: [],
  analysis_notes: [],
  summary: "A short factual summary of the lease.",
  model_tier_usage: { nano: 1234, super: 567, ultra: 89 },
  processing_time_ms: 2500,
};

function jsonResponse(body: unknown) {
  return { ok: true, status: 200, statusText: "OK", json: async () => body } as Response;
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("preservation: valid report rendering", () => {
  it("renders scorecard, summary, claim cards, evidence chain and telemetry", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url === "/api/challenges")
          return jsonResponse([{ id: "prompt-injection", name: "Prompt injection", description: "d" }]);
        if (url.startsWith("/api/challenges/"))
          return jsonResponse({ id: "prompt-injection", name: "Prompt injection", description: "d", document_text: "text" });
        if (url === "/api/verify") return jsonResponse(REPORT);
        throw new Error(`unexpected fetch ${url}`);
      }),
    );

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /Challenge/ }));
    fireEvent.click(await screen.findByText("Prompt injection"));

    // Scorecard
    expect(await screen.findByText("Evidence Trust Scorecard")).toBeInTheDocument();
    expect(screen.getByText("High risk")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText("Unverifiable")).toBeInTheDocument();
    expect(screen.getByText("Contradicted")).toBeInTheDocument();
    expect(screen.getByText(/challenge-prompt-injection\.txt/)).toBeInTheDocument();

    // Summary
    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.getByText(REPORT.summary)).toBeInTheDocument();

    // Claim cards
    expect(screen.getByText("Acme Corp is registered in Ohio")).toBeInTheDocument();
    expect(screen.getByText("Signed on February 30, 2026")).toBeInTheDocument();
    expect(screen.getByText(/Supported by 1 independent source/)).toBeInTheDocument();

    // Evidence chain appears when a card with evidence is expanded
    expect(screen.queryByText("SUPPORTS")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Acme Corp is registered in Ohio"));
    expect(screen.getByText("SUPPORTS")).toBeInTheDocument();
    expect(screen.getByText(/“Acme Corp is registered”/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Ohio Registry" });
    expect(link).toHaveAttribute("href", "https://registry.example.org/acme");

    // Telemetry
    expect(screen.getByText("1,234")).toBeInTheDocument();
    expect(screen.getByText("567")).toBeInTheDocument();
    expect(screen.getByText("89")).toBeInTheDocument();
    expect(screen.getByText("2.5s")).toBeInTheDocument();
  });
});
