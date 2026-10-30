import type { ReactNode } from "react";

const PDF_URL = "/VerifyFlow_AI_Document_Verification.pdf";

const card = { background: "var(--card)", borderColor: "var(--border)" } as const;
const muted = { color: "var(--text-secondary)" } as const;
const faint = { color: "var(--text-tertiary)" } as const;

const stages = [
  { n: 1, name: "Extract", tech: "Nemotron-3-Nano", color: "#0070F3", text: "Reads the document and returns structured claims with category, confidence and named entities." },
  { n: 2, name: "Search", tech: "Tavily API", color: "#F5A623", text: "Runs an advanced web search per claim and returns URLs, quotes and relevance scores." },
  { n: 3, name: "Analyze", tech: "Nemotron-3-Super", color: "#8B5CF6", text: "Judges whether evidence supports or contradicts a claim. Only for high-stakes claims." },
  { n: 4, name: "Verify", tech: "Code gate", color: "#50E3C2", text: "Deterministic rules decide the verdict. No LLM is involved at this step." },
  { n: 5, name: "Synthesize", tech: "Nemotron-3-Ultra", color: "#EDEDED", text: "Writes the executive summary from verdicts that are already final." },
];

const tiers = [
  { name: "Nano", size: "30B", price: "$0.06", share: "~85%", role: "Claim extraction and classification", id: "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B" },
  { name: "Super", size: "120B", price: "$0.30", share: "~10%", role: "Evidence judgment and contradiction detection for legal, financial, regulatory and identity claims", id: "nvidia/nemotron-3-super-120b-a12b" },
  { name: "Ultra", size: "550B", price: "$1.00", share: "~5%", role: "Final summary only, called once per document", id: "nvidia/Nemotron-3-Ultra-550b-a55b" },
];

const steps = [
  "Open the Verify tab and drop a PDF, TXT or MD file (up to 4 MB on the hosted site).",
  "Wait while the pipeline extracts claims, searches the web and applies the trust gate.",
  "Read the trust score and risk level, then open any claim to see its verdict and cited sources.",
  "Check the Findings panel for document-level issues such as look-alike URLs or prompt injection.",
  "Open the Challenge tab to run adversarial documents and watch the gate catch them.",
];

const envExample = `NEBIUS_API_KEY=your_nebius_key
TAVILY_API_KEY=your_tavily_key

docker compose up --build`;

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h3 className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>{title}</h3>
      {children}
    </section>
  );
}

export default function HowItWorks() {
  return (
    <div className="space-y-10">
      <div className="text-center space-y-2">
        <h2 className="text-[20px] sm:text-[22px] font-bold">How VerifyFlow works</h2>
        <p className="text-[15px]" style={muted}>The model can think. The evidence gets the final say.</p>
      </div>

      <Section title="The idea">
        <p className="text-[14px]" style={muted}>
          Language models hallucinate, so every model output is treated as an untrusted claim. Models
          extract and analyze. A deterministic code verifier issues every final verdict, using only
          retrieved evidence.
        </p>
      </Section>

      <Section title="The 5-stage pipeline">
        <ol className="space-y-2">
          {stages.map((s) => (
            <li key={s.n} className="rounded-lg border p-3 flex gap-3" style={card}>
              <span
                className="w-7 h-7 shrink-0 rounded-md flex items-center justify-center text-[13px] font-bold"
                style={{ background: s.color, color: "#000" }}
                aria-hidden="true"
              >
                {s.n}
              </span>
              <div>
                <p className="text-sm font-semibold">
                  {s.name} <span className="font-normal" style={faint}>· {s.tech}</span>
                </p>
                <p className="text-[13px] mt-0.5" style={muted}>{s.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section title="Nebius Token Factory and NVIDIA Nemotron">
        <p className="text-[14px]" style={muted}>
          All model calls go through Nebius Token Factory, which exposes an OpenAI-compatible API. The
          backend uses the standard openai SDK pointed at the Nebius base URL, with JSON mode for
          structured output. Each task is routed to the cheapest NVIDIA Nemotron tier that can do it.
        </p>
        <div className="grid gap-2 sm:grid-cols-3">
          {tiers.map((t) => (
            <div key={t.name} className="rounded-lg border p-3 space-y-1.5" style={card}>
              <p className="text-sm font-semibold">
                {t.name} <span className="font-normal" style={faint}>({t.size})</span>
              </p>
              <p className="text-[12px]" style={faint}>{t.price} / 1M input tokens · {t.share} of calls</p>
              <p className="text-[13px]" style={muted}>{t.role}</p>
              <code className="block text-[10px] break-all" style={faint}>{t.id}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Tavily live web grounding">
        <p className="text-[14px]" style={muted}>
          For each claim a web source could confirm or refute, VerifyFlow builds a search query from
          the claim text and its entities, then calls Tavily with advanced search depth. Each result
          returns a URL, content and a relevance score from 0 to 1. Those become the citations shown
          under every claim. Claims about the document itself skip the search.
        </p>
      </Section>

      <Section title="The deterministic trust gate">
        <ul className="text-[14px] space-y-1.5 list-disc pl-5" style={muted}>
          <li><b style={{ color: "var(--verified)" }}>Verified</b>: a source scores at least 0.5 relevance, supports the claim, and quotes text that really appears in the source.</li>
          <li><b style={{ color: "var(--contradicted)" }}>Contradicted</b>: a relevant source with a verifiable quote disagrees with the claim.</li>
          <li><b style={{ color: "var(--unverifiable)" }}>Unverifiable</b>: everything else. Missing evidence is never treated as proof.</li>
        </ul>
        <p className="text-[13px]" style={faint}>
          The trust score is plain arithmetic over verdict counts and document findings. The summary
          model cannot change any verdict.
        </p>
      </Section>

      <Section title="How to use it">
        <ol className="text-[14px] space-y-1.5 list-decimal pl-5" style={muted}>
          {steps.map((s) => <li key={s}>{s}</li>)}
        </ol>
      </Section>

      <Section title="Run it yourself">
        <p className="text-[14px]" style={muted}>
          Put your keys in a <code>.env</code> file, then start everything with Docker.
        </p>
        <pre className="rounded-lg border p-3 text-[12px] overflow-x-auto" style={card}>{envExample}</pre>
      </Section>

      <Section title="Project deck (PDF)">
        <div className="rounded-lg border overflow-hidden" style={card}>
          <object
            data={`${PDF_URL}#view=FitH`}
            type="application/pdf"
            className="w-full h-[360px] sm:h-[460px]"
            aria-label="VerifyFlow project deck"
          >
            <p className="p-4 text-[13px]" style={muted}>Your browser can't display the PDF inline.</p>
          </object>
        </div>
        <div className="flex gap-2">
          <a
            href={PDF_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[13px] font-medium px-3 py-1.5 rounded-md border no-underline"
            style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
          >
            Open in new tab
          </a>
          <a
            href={PDF_URL}
            download
            className="text-[13px] font-medium px-3 py-1.5 rounded-md no-underline"
            style={{ background: "var(--brand)", color: "#fff" }}
          >
            Download PDF
          </a>
        </div>
      </Section>
    </div>
  );
}
