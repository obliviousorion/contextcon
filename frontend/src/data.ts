import demoCasefileData from "../fixtures/demo_casefile.json";
import demoRefusalsData from "../fixtures/demo_refusals.json";
import { CaseFile, FixtureOutcome, ResolveResult, AttestLine } from "./types";

// Type assertions for loaded fixtures
export const demoCasefile: CaseFile = demoCasefileData as unknown as CaseFile;
export const demoRefusals = demoRefusalsData as unknown as {
  cases: {
    C02: {
      case_id: string;
      description: string;
      request: Record<string, any>;
      line: AttestLine;
      case_file: CaseFile;
    };
    C07: {
      case_id: string;
      description: string;
      request: Record<string, any>;
      line: AttestLine;
      case_file: CaseFile;
    };
    C08: {
      case_id: string;
      description: string;
      request: Record<string, any>;
      resolve: ResolveResult;
    };
  };
};

// Fixture outcomes for the date slider and preset switching
export const FIXTURE_OUTCOMES: FixtureOutcome[] = [
  {
    id: "outcome-c02",
    date: "2022-06-01",
    title: "Past Dispute (NOT_YET_RECORDED)",
    companyName: "Delhivery",
    domain: "delhivery.com",
    tool: "dispute",
    description: "C02: As of 2022-06-01, headcount series starts later (2022-11-28) → cannot attest headcount.",
    caseFile: demoRefusals.cases.C02.case_file,
    attestLine: demoRefusals.cases.C02.line,
  },
  {
    id: "outcome-c07",
    date: "2026-10-15",
    title: "Mid-date Dispute (STALE_DATA)",
    companyName: "TCI Express",
    domain: "tciexpress.in",
    tool: "dispute",
    description: "C07: As of 2026-10-15, last headcount point is 38 days old (> 14-day limit) → STALE_DATA.",
    caseFile: demoRefusals.cases.C07.case_file,
    attestLine: demoRefusals.cases.C07.line,
  },
  {
    id: "outcome-clearance",
    date: "2026-11-22",
    title: "Today Clearance (All Attested)",
    companyName: "Delhivery",
    domain: "delhivery.com",
    tool: "clear",
    description: "Delhivery clearance: all 5 fields attested (existence, listing, headcount, revenue_band, domains).",
    caseFile: demoCasefile,
  },
  {
    id: "outcome-c08",
    date: "2026-11-22",
    title: "Resolve Refusal (CANNOT_RESOLVE)",
    companyName: "Shree Balaji Logistics",
    domain: "",
    tool: "resolve",
    description: "C08: Unmatched company name without domain returns 25 candidates → CANNOT_RESOLVE.",
    resolveResult: demoRefusals.cases.C08.resolve,
  },
];

const API_BASE_URL = import.meta.env.VITE_API_URL;

export async function fetchCaseFileData(
  tool: string,
  domain: string,
  asOf: string
): Promise<{ caseFile?: CaseFile; resolve?: ResolveResult }> {
  if (API_BASE_URL) {
    const res = await fetch(`${API_BASE_URL}/api/casefile?tool=${tool}&domain=${encodeURIComponent(domain)}&as_of=${asOf}`);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `API error: ${res.statusText}`);
    }
    return await res.json();
  }

  // Fallback to fixture matching
  if (tool === "resolve" || !domain) {
    return { resolve: demoRefusals.cases.C08.resolve };
  }

  if (asOf <= "2022-06-01") {
    return { caseFile: demoRefusals.cases.C02.case_file };
  } else if (asOf <= "2026-10-15" || domain.includes("tciexpress")) {
    return { caseFile: demoRefusals.cases.C07.case_file };
  }

  return { caseFile: demoCasefile };
}
