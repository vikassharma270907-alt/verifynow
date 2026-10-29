import { useState, useCallback } from "react";

export interface Evidence {
  source_type: string;
  source_url: string | null;
  source_title: string | null;
  content: string;
  supports_claim: boolean;
  stance: "supports" | "contradicts" | "irrelevant" | "rejected" | "unjudged";
  quote: string | null;
  relevance_score: number;
  retrieved_at: string;
}

export interface DocumentFinding {
  kind: string;
  severity: "HIGH" | "MEDIUM";
  quote: string;
  explanation: string;
  claim_id: string | null;
}

export interface Claim {
  id: string;
  text: string;
  category: string;
  source_location: string;
  confidence: number;
  status: string;
  verification_reason: string | null;
  entities: string[];
}

export interface ClaimVerification {
  claim: Claim;
  evidence: Evidence[];
  verdict: string;
}

export interface VerificationReport {
  document_name: string;
  document_type: string;
  total_claims: number;
  verified_count: number;
  unverifiable_count: number;
  contradicted_count: number;
  risk_level: string;
  trust_score: number;
  claim_verifications: ClaimVerification[];
  findings: DocumentFinding[];
  analysis_notes: string[];
  summary: string;
  model_tier_usage: Record<string, number>;
  processing_time_ms: number;
}

export interface Challenge {
  id: string;
  name: string;
  description: string;
  document_text?: string;
  expected_flags?: string[];
}

export function useVerification() {
  const [report, setReport] = useState<VerificationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const verifyFile = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    setReport(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await fetch("/api/verify", { method: "POST", body: formData });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(body.detail || `HTTP ${resp.status}`);
      }
      const data: VerificationReport = await resp.json();
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const verifyText = useCallback(async (text: string, filename: string) => {
    const blob = new Blob([text], { type: "text/plain" });
    const file = new File([blob], filename);
    await verifyFile(file);
  }, [verifyFile]);

  const reset = useCallback(() => {
    setReport(null);
    setError(null);
    setLoading(false);
  }, []);

  return { report, loading, error, verifyFile, verifyText, reset };
}
