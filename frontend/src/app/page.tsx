"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";

/* ─── Publicus SVG Logo (reused from brand assets) ─── */
function PublicusLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 539 105" fill="none">
      <path
        d="M.9 102.489V.379h16.82v102.11H.9Zm36.64-36.19H13.06V52.78h23.57c7.01 0 12.41-1.75 16.22-5.25 3.8-3.5 5.71-8.21 5.71-14.12 0-5.91-1.9-10.76-5.71-14.27-3.81-3.5-9.06-5.25-15.77-5.25H13.05V.37h24.18c8.01 0 14.89 1.33 20.65 3.98 5.76 2.66 10.19 6.41 13.29 11.26 3.1 4.86 4.65 10.74 4.65 17.64 0 10.51-3.48 18.65-10.44 24.4-6.96 5.76-16.24 8.64-27.85 8.64l.01.01Zm101.211 3.011h6.16c-.4 7.91-1.93 14.46-4.58 19.67-2.65 5.21-6.16 9.08-10.51 11.639-4.35 2.55-9.34 3.83-14.94 3.83s-10.11-1.08-14.11-3.23c-4.01-2.15-7.08-5.33-9.24-9.53-2.15-4.21-3.23-9.46-3.23-15.77V22.46h16.07v50.16c0 3.8.55 7.11 1.65 9.91 1.1 2.8 2.8 4.93 5.11 6.38 2.3 1.45 5.2 2.18 8.71 2.18 2.9 0 5.53-.6 7.88-1.8 2.35-1.2 4.33-2.83 5.93-4.88 1.6-2.05 2.85-4.38 3.75-6.99.9-2.6 1.35-5.3 1.35-8.11Zm15.91-46.86v80.039h-15.92v-80.04h15.92Zm29.59 80.039h-16.07V.359h16.07v102.13Zm21.77-82.14c7.01 0 13.04 1.68 18.09 5.03 5.05 3.36 8.94 8.16 11.64 14.42 2.7 6.26 4.06 13.74 4.06 22.45 0 13.62-3.06 24.05-9.16 31.31-6.11 7.26-14.32 10.89-24.63 10.89-9.11 0-16.34-3.6-21.7-10.81-5.36-7.21-8.03-17.67-8.03-31.39 0-8.51 1.22-15.91 3.68-22.22 2.45-6.31 5.91-11.16 10.36-14.56 4.45-3.41 9.69-5.11 15.69-5.11v-.01Zm-2.1 13.52c-6.51 0-11.41 2.43-14.72 7.28-3.31 4.85-4.96 11.89-4.96 21.1s1.7 16.29 5.11 21.25c3.4 4.96 8.26 7.43 14.57 7.43 6.31 0 11.13-2.45 14.49-7.36 3.36-4.91 5.03-12.01 5.03-21.32s-1.7-16.11-5.11-21.02c-3.4-4.9-8.21-7.36-14.41-7.36Zm45.489 68.62V.359h16.07v102.13h-16.07ZM278.851 16.3V.36h16.07V16.3h-16.07Zm0 86.189v-80.04h16.07v80.04h-16.07ZM379 50.39h-16.07c-1-5.71-3.18-9.89-6.53-12.54-3.36-2.65-7.39-3.98-12.09-3.98-6.71 0-11.81 2.45-15.32 7.36s-5.25 12.01-5.25 21.32 1.82 16.14 5.48 21.1c3.65 4.96 8.83 7.43 15.54 7.43 4.8 0 8.83-1.3 12.09-3.9 3.25-2.6 5.48-6.46 6.68-11.56h15.92c-1.7 10.01-5.73 17.32-12.09 21.92-6.36 4.61-13.99 6.91-22.9 6.91-7.71 0-14.32-1.68-19.82-5.03-5.51-3.35-9.76-8.18-12.76-14.49-3-6.31-4.51-13.76-4.51-22.38 0-9.11 1.5-16.79 4.51-23.05 3-6.25 7.26-11.01 12.76-14.27 5.51-3.25 12.06-4.88 19.67-4.88 6.01 0 11.46 1.13 16.37 3.38 4.9 2.25 8.96 5.58 12.16 9.98 3.2 4.41 5.25 9.96 6.16 16.67v.01Zm62.921 18.92h6.16c-.4 7.91-1.93 14.46-4.58 19.67-2.65 5.21-6.16 9.08-10.51 11.639-4.35 2.55-9.34 3.83-14.94 3.83s-10.11-1.08-14.11-3.23c-4.01-2.15-7.08-5.33-9.24-9.53-2.15-4.21-3.23-9.46-3.23-15.77V22.46h16.07v50.16c0 3.8.55 7.11 1.65 9.91 1.1 2.8 2.8 4.93 5.11 6.38 2.3 1.45 5.2 2.18 8.71 2.18 2.9 0 5.53-.6 7.88-1.8 2.35-1.2 4.33-2.83 5.93-4.88 1.6-2.05 2.85-4.38 3.75-6.99.9-2.6 1.35-5.3 1.35-8.11Zm15.92-46.86v80.039h-15.92v-80.04h15.92Zm29.279 21.03c0 2.9.9 5.13 2.7 6.68 1.8 1.55 4.25 2.75 7.36 3.6 3.1.85 6.48 1.56 10.14 2.1 3.65.55 7.281 1.25 10.891 2.11 3.6.85 6.93 2.05 9.99 3.6 3.05 1.56 5.499 3.73 7.359 6.53 1.85 2.8 2.781 6.56 2.781 11.26 0 5.01-1.4 9.41-4.2 13.21-2.8 3.8-6.681 6.73-11.641 8.78-4.96 2.05-10.69 3.08-17.19 3.08-9.61 0-17.639-2.28-24.099-6.83-6.46-4.55-10.44-11.64-11.94-21.25h16.07c.8 5.01 3 8.86 6.61 11.56 3.6 2.7 8.209 4.05 13.809 4.05s9.51-1.1 12.31-3.3c2.8-2.2 4.211-4.95 4.211-8.26 0-2.8-.9-5.01-2.7-6.61-1.8-1.6-4.231-2.78-7.281-3.53-3.06-.75-6.38-1.43-9.99-2.02-3.6-.6-7.19-1.33-10.74-2.18-3.55-.85-6.83-2.08-9.84-3.68-3-1.6-5.409-3.83-7.209-6.68-1.8-2.86-2.701-6.63-2.701-11.34 0-4.2 1.08-8.13 3.23-11.78 2.15-3.65 5.451-6.61 9.911-8.86 4.45-2.25 10.079-3.38 16.889-3.38 6.01 0 11.36.98 16.07 2.93 4.7 1.95 8.61 5.01 11.71 9.16 3.1 4.15 5.06 9.54 5.86 16.14h-16.07c-.9-5.61-2.9-9.58-6.01-11.94-3.1-2.35-7.21-3.53-12.31-3.53-4.41 0-7.84.97-10.29 2.92-2.45 1.96-3.68 4.43-3.68 7.43l-.01.03Z"
        fill="currentColor"
      />
    </svg>
  );
}

/* ─── SVG Icon Components ─── */

function IconDatabase({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4.03 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" />
    </svg>
  );
}

function IconFilter({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16l-6 7.5V18l-4 2v-8.5L4 4z" />
    </svg>
  );
}

function IconCpu({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <rect x="9" y="9" width="6" height="6" />
      <path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3" />
    </svg>
  );
}

function IconRadar({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 12l4.5-4.5" />
      <path d="M20.49 15a9 9 0 1 0-5.49 5.49" />
      <path d="M15.54 15.54a5 5 0 1 0-3.54 1.46" />
      <circle cx="12" cy="12" r="1" fill="currentColor" />
    </svg>
  );
}

function IconDollar({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  );
}

function IconCalendar({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
    </svg>
  );
}

function IconBuilding({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="2" width="16" height="20" rx="1" />
      <path d="M9 22V12h6v10M8 6h.01M12 6h.01M16 6h.01M8 10h.01M12 10h.01M16 10h.01" />
    </svg>
  );
}

function IconGitMerge({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="18" r="3" />
      <circle cx="6" cy="6" r="3" />
      <path d="M6 21V9a9 9 0 0 0 9 9" />
    </svg>
  );
}

function IconClock({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  );
}

function IconCompass({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" fill="currentColor" opacity="0.15" stroke="currentColor" />
    </svg>
  );
}

function IconTrendDown({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" />
      <polyline points="17 18 23 18 23 12" />
    </svg>
  );
}

function IconHourglass({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 22h14M5 2h14M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2" />
    </svg>
  );
}

function IconTarget({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  );
}

function IconBolt({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
    </svg>
  );
}

/* ─── Data ─── */

const HOW_STEPS = [
  {
    icon: <IconDatabase className="w-7 h-7 text-[#634086]" />,
    title: "Ingest & Clean",
    desc: "Pull grants from Open Canada sorted newest-first, stopping as soon as we hit records we already have. Each record is cleaned: departments matched to standard names, amounts parsed from messy formats, recipients categorized, and duplicates removed at three levels before anything is saved.",
  },
  {
    icon: <IconTarget className="w-7 h-7 text-[#634086]" />,
    title: "Score & Filter",
    desc: "Every grant is scored across six factors: type of agreement, who received it, what it\u2019s for, industry code, how long it lasts, and how much money is involved. Only grants with a real chance of generating procurement move forward. The rest are filtered out before any expensive AI classification.",
  },
  {
    icon: <IconCpu className="w-7 h-7 text-[#634086]" />,
    title: "Classify",
    desc: "Grants that pass scoring go through a four-step classifier. It tries simple rules first (department name, keywords, patterns learned from past runs) and only calls the LLM for the ones it can\u2019t figure out. Each time the LLM classifies something new, those patterns are saved so it won\u2019t need the LLM next time.",
  },
  {
    icon: <IconRadar className="w-7 h-7 text-[#634086]" />,
    title: "Predict & Signal",
    desc: "Each classified grant gets mapped to specific RFP types it\u2019s likely to produce \u2014 with predicted timelines and the kinds of companies that should bid. Grants are then grouped into procurement signals by theme and region to surface broader spending trends.",
  },
];

const PIPELINE_STAGES = [
  {
    icon: <IconDatabase className="w-6 h-6 text-[#634086]" />,
    name: "Data Ingestion",
    detail:
      "Five source adapters (Open Canada is the primary one). Fetches grants sorted newest-first in large pages. Stops automatically once it reaches records older than the cutoff date. Tracks when each source was last fetched so re-runs only grab new data.",
  },
  {
    icon: <IconFilter className="w-6 h-6 text-[#634086]" />,
    name: "Data Cleaning",
    detail:
      'Strips HTML and encoding artifacts. Parses amounts from multiple formats: "$1,234,567", French spacing "250 000", shorthand "1.2M", accounting negatives. Handles French dates (janvier, f\u00E9vrier...). Extracts fiscal year (April\u2013March cycle). Every function returns a value plus quality flags \u2014 never crashes the pipeline.',
  },
  {
    icon: <IconBuilding className="w-6 h-6 text-[#634086]" />,
    name: "Dept. & Recipient",
    detail:
      "Matches department names against ~50 known bilingual variants, with fuzzy matching as fallback. Normalizes recipient names (strips legal suffixes like Inc., Ltd.) and maps them into 13 categories: municipality, crown corporation, hospital, university, etc. When no explicit type is provided, it infers from the name.",
  },
  {
    icon: <IconGitMerge className="w-6 h-6 text-[#634086]" />,
    name: "Deduplication",
    detail:
      "Three layers to catch duplicates. First: in-memory check within the current batch. Second: batch lookup against existing database records. Third: if a duplicate still slips through, the richer record wins on insert. Each record is hashed from its department, recipient, amount range, and fiscal year.",
  },
  {
    icon: <IconTarget className="w-6 h-6 text-[#634086]" />,
    name: "Scoring",
    detail:
      "Scores each grant on six factors to decide if it\u2019s worth classifying. Contributions to municipalities and hospitals score high (they hire vendors). Transfer payments to individuals are filtered as noise. Only grants scoring above the threshold move on to the classifier \u2014 the rest skip the LLM entirely.",
  },
  {
    icon: <IconCpu className="w-6 h-6 text-[#634086]" />,
    name: "Classification",
    detail:
      "Four-pass hybrid system. Tries department-based rules first, then keyword matching, then patterns learned from past LLM runs. Only calls the LLM for grants that don\u2019t match any rule. Each new LLM result is saved as a rule for future runs. Business relevance is scored after classification.",
  },
  {
    icon: <IconBolt className="w-6 h-6 text-[#634086]" />,
    name: "RFP Prediction",
    detail:
      "Maps each classified grant to specific RFP types it will likely produce. A cybersecurity grant might yield predictions for penetration testing (3\u20136 months), security architecture (4\u20139 months), and managed SOC (6\u201312 months). Each prediction includes timing, likelihood, and who should bid. Stored per-grant for frontend display.",
  },
];

const DECISIONS = [
  {
    title: "Score first, classify only what matters",
    what: "Every grant is scored on six factors before any AI is involved. Only grants with a real chance of generating procurement (scored HIGH or MEDIUM) move to classification. Everything else \u2014 scholarships, transfer payments, individual benefits \u2014 is filtered out automatically.",
    why: "AI classification is the most expensive step. Scoring first eliminates 40\u201360% of records that would never produce an RFP anyway. This keeps costs low and ensures the classifier focuses on grants that actually matter for procurement intelligence.",
  },
  {
    title: "Fetch newest first, stop early",
    what: "Instead of downloading the entire grants database or using the search portal, we fetch records sorted newest-first and stop as soon as we reach data we\u2019ve already seen. Each source tracks when it was last fetched.",
    why: "The government search portal crashes on deep pagination. Downloading everything wastes time on re-runs. Our approach gives us the newest data first and makes incremental updates fast \u2014 the second run is dramatically cheaper than the first.",
  },
  {
    title: "Quarantine, never delete",
    what: "Records that fail validation go to a quarantine table with documented reasons \u2014 they\u2019re never silently dropped. Common issues like scrambled recipients or unparseable dates are flagged and tracked.",
    why: "Today\u2019s bad record might be fixable tomorrow when we improve the cleaning logic. Deleting it means losing that data permanently. Quarantine with an audit trail lets us reprocess old records whenever the pipeline gets smarter.",
  },
  {
    title: "Self-improving classifier",
    what: "The classifier tries simple rules before resorting to the LLM. When the LLM does classify something, those patterns are automatically saved as rules for next time. The system gets smarter with every run.",
    why: "Each LLM call costs money and adds latency. By learning from its own outputs, the system handles more and more grants with instant rules instead of expensive API calls. After a few runs, most grants classify without the LLM at all.",
  },
];

const FAQ_ITEMS = [
  {
    tag: "Technical",
    tagClass: "bg-[rgba(99,64,134,0.1)] text-[#634086]",
    question: "How does the prediction model actually work?",
    answer: `<strong>Three stages, all rule-based and deterministic. No ML model \u2014 and that's intentional.</strong><br/><br/>
      <strong>Stage 1 \u2014 Scoring.</strong> Every grant is scored on six factors: what type of agreement it is, who received the money (municipalities and hospitals hire vendors; individuals don\u2019t), what the description says, industry code, how long the grant lasts, and how large it is. Grants that clearly won\u2019t produce RFPs (scholarships, transfer payments) are filtered out here.<br/><br/>
      <strong>Stage 2 \u2014 Classification.</strong> Grants that pass scoring are assigned a funding theme (like "Cybersecurity Modernization" or "Clean Energy Infrastructure") using a hybrid classifier that tries rules first and only calls the LLM when needed. Business relevance is also scored at this stage.<br/><br/>
      <strong>Stage 3 \u2014 RFP Prediction.</strong> Based on the theme, the engine predicts specific RFP types. For example, a cybersecurity grant typically produces penetration testing RFPs in 3\u20136 months, security architecture in 4\u20139 months, and managed SOC contracts in 6\u201312 months. Each prediction includes timing, likelihood, and the types of companies that should bid.<br/><br/>
      Once Publicus accumulates confirmed grant\u2192RFP pairs, the rule weights can be replaced with learned ones \u2014 same structure, better accuracy.`,
  },
  {
    tag: "Technical",
    tagClass: "bg-[rgba(99,64,134,0.1)] text-[#634086]",
    question: "Why not use the grants search portal directly?",
    answer: `The Open Canada search portal runs on <strong>Apache Solr</strong>, which gets slower the deeper you paginate \u2014 page 10 is as expensive as pages 1 through 10 combined. It effectively crashes after a few thousand records.<br/><br/>
      Instead, we use the <strong>CKAN datastore API</strong> to fetch records sorted newest-first. We stop as soon as we hit records older than our cutoff date, so we never waste API calls on data we already have.<br/><br/>
      The pipeline has <strong>five source adapters</strong> (Open Canada, Innovation Canada, Proactive Disclosure, CSV upload, and a mock source for testing). Each source tracks when it was last fetched. <strong>The first run pulls everything since 2025. Every run after that only grabs what\u2019s new.</strong>`,
  },
  {
    tag: "Data",
    tagClass: "bg-[#fef3c7] text-[#92400e]",
    question: "How do you handle the messiness of government data?",
    answer: `No cleaning function is allowed to crash the pipeline. Every one returns the cleaned value plus quality flags, so every record reaches the end with a documented history. Three outcomes:
      <ul>
        <li><strong>Clean:</strong> Passes validation and is saved with any minor flags noted</li>
        <li><strong>Fixable:</strong> Has problems we can solve (French dates, bilingual department names, shorthand amounts) \u2014 cleaned, flagged, and still saved</li>
        <li><strong>Quarantined:</strong> Too many critical issues \u2014 sent to a quarantine table with reasons, never silently dropped</li>
      </ul>
      Specific things we handle: ~50 bilingual department name variants, 13 recipient categories (with name-based guessing when no type is provided \u2014 e.g., "City of Ottawa" \u2192 municipality), multiple amount formats including French spacing and accounting negatives, and three-level deduplication to prevent the same grant from appearing twice.`,
  },
  {
    tag: "Technical",
    tagClass: "bg-[rgba(99,64,134,0.1)] text-[#634086]",
    question: "How do you prevent bad AI outputs from corrupting the data?",
    answer: `Multiple layers of protection, most of which run before the AI is even involved:
      <ul>
        <li><strong>Pre-filter:</strong> The scoring step removes noise (scholarships, transfer payments, individual benefits) so the LLM never sees low-quality input</li>
        <li><strong>Rules first:</strong> The classifier tries deterministic rules before calling the LLM. Most grants never need an AI call at all</li>
        <li><strong>Strict categories:</strong> Every classification must match one of 12 predefined themes. If the LLM returns something outside that list, it\u2019s rejected</li>
        <li><strong>Confidence gate:</strong> Low-confidence results are saved but excluded from signal detection and forecasting</li>
        <li><strong>Guarded learning:</strong> Only high-confidence, valid LLM results get their patterns saved as rules. Bad outputs are never learned from</li>
      </ul>`,
  },
  {
    tag: "Product",
    tagClass: "bg-[#dcfce7] text-[#166534]",
    question: "How does this connect to Publicus\u2019s existing product?",
    answer: `Publicus today shows users what RFPs are <strong>currently live</strong>. This engine shows what RFPs are <strong>coming in the next 3\u201318 months</strong>. Integration points:
      <ul>
        <li><strong>"Coming Soon" opportunities:</strong> Every classified grant has predicted RFP types, timelines, and target bidders stored in the database \u2014 ready to surface alongside live RFPs</li>
        <li><strong>Relevance filtering:</strong> Each grant is scored for business relevance, so the frontend can show users only opportunities that matter to them</li>
        <li><strong>Context for live RFPs:</strong> Signal data can explain <em>why</em> an RFP exists \u2014 linking it back to the underlying grant funding</li>
        <li><strong>Smarter matching:</strong> Predicted categories can feed into Publicus\u2019s AI matching engine as forward-looking signals, so recommendations factor in what\u2019s coming, not just what\u2019s live</li>
      </ul>
      This is additive \u2014 it extends Publicus\u2019s timeline upstream without replacing anything they\u2019ve built.`,
  },
  {
    tag: "Product",
    tagClass: "bg-[#dcfce7] text-[#166534]",
    question: "What would you build next with more time?",
    answer: `In priority order:
      <ul>
        <li><strong>Back-testing:</strong> Take 5 years of historical grants and match them against actual contracts that followed. Measure how accurate the predictions are per theme and replace rule-based weights with data-driven ones.</li>
        <li><strong>Feedback loop:</strong> When a live RFP matches a prediction, record the actual timing and outcome. Over 12\u201318 months, this builds validated accuracy rates that no competitor can replicate.</li>
        <li><strong>Vendor intelligence:</strong> Cross-reference grant recipients with contract winners to build maps of who\u2019s been winning in each category, per department.</li>
        <li><strong>Municipal expansion:</strong> 50+ Canadian city portals are completely unserved. The grant\u2192RFP pattern is even stronger at the municipal level, and the existing source adapter architecture makes adding new feeds straightforward.</li>
      </ul>`,
  },
];

const NEXT_STEPS = [
  { title: "Back-test with real data", desc: "Match 5 years of historical grants against actual contracts that followed. Measure prediction accuracy per theme and replace rule-based weights with data-driven ones." },
  { title: "Close the feedback loop", desc: "When a live RFP matches a prediction, record the actual timing. Over 12\u201318 months this builds validated accuracy rates no competitor can replicate." },
  { title: "Vendor intelligence", desc: "Cross-reference grant recipients with contract winners to build maps of who\u2019s been winning, per department, per category." },
  { title: "Municipal expansion", desc: "50+ Canadian city portals are completely unserved. The grant-to-RFP pattern is even stronger at the municipal level." },
  { title: "Inline Publicus integration", desc: "\u201CThis RFP likely exists because of $18.4M in Ontario cybersecurity grants\u201D + predicted RFP types with timelines. Context nobody else can offer, directly on the RFP card." },
  { title: "Alert personalization", desc: "User sets sector + region \u2192 weekly signal digest with predicted RFP types. Same infrastructure as Publicus\u2019s existing email briefings. Zero new delivery infra needed." },
];

/* ─── Main Landing Page Component ─── */

export default function LandingPage() {
  const [activeHow, setActiveHow] = useState(0);
  const [activePipe, setActivePipe] = useState(0);
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [activeSection, setActiveSection] = useState("");
  const howIntervalRef = useRef<NodeJS.Timeout | null>(null);

  /* Scroll reveal: hide elements below viewport, then animate them in on scroll */
  useEffect(() => {
    const els = document.querySelectorAll(".l-reveal, .tl-item, .pain-card");

    els.forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.top > window.innerHeight * 0.85) {
        el.classList.add("l-hidden");
      }
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            const delay = parseInt((e.target as HTMLElement).dataset.delay || "0") * 100;
            setTimeout(() => e.target.classList.remove("l-hidden"), delay);
            observer.unobserve(e.target);
          }
        });
      },
      { threshold: 0.08 }
    );
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  /* Active nav link tracking */
  useEffect(() => {
    const handler = () => {
      const sections = document.querySelectorAll("section[id]");
      let current = "";
      sections.forEach((s) => {
        if (window.scrollY >= (s as HTMLElement).offsetTop - 100) {
          current = s.id;
        }
      });
      setActiveSection(current);
    };
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  /* Auto-cycle how-it-works */
  const startHowCycle = useCallback(() => {
    if (howIntervalRef.current) clearInterval(howIntervalRef.current);
    howIntervalRef.current = setInterval(() => {
      setActiveHow((prev) => (prev + 1) % HOW_STEPS.length);
    }, 3000);
  }, []);

  useEffect(() => {
    startHowCycle();
    return () => {
      if (howIntervalRef.current) clearInterval(howIntervalRef.current);
    };
  }, [startHowCycle]);

  const handleHowClick = (i: number) => {
    setActiveHow(i);
    startHowCycle();
  };

  /* Count-up animation for stats */
  useEffect(() => {
    const statsBar = document.querySelector(".stats-bar-landing");
    if (!statsBar) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.querySelectorAll("[data-count]").forEach((el) => {
              const target = parseInt((el as HTMLElement).dataset.count || "0");
              let n = 0;
              const step = target / 60;
              const timer = setInterval(() => {
                n = Math.min(n + step, target);
                (el as HTMLElement).textContent =
                  Math.floor(n) + (target > 20 ? "+" : "");
                if (n >= target) clearInterval(timer);
              }, 16);
            });
            observer.unobserve(e.target);
          }
        });
      },
      { threshold: 0.5 }
    );
    observer.observe(statsBar);
    return () => observer.disconnect();
  }, []);

  const navLinks = [
    { href: "#problem", label: "Problem" },
    { href: "#how", label: "How It Works" },
    { href: "#value", label: "Business Value" },
    { href: "#pipeline", label: "Data Pipeline" },
    { href: "#decisions", label: "Decisions" },
    { href: "#faq", label: "FAQ" },
  ];

  return (
    <div className="landing-page">
      {/* ──── NAV ──── */}
      <nav className="landing-nav">
        <a href="#top" className="flex items-center gap-3 no-underline">
          <PublicusLogo className="h-6 w-auto text-[#634086]" />
          <span className="bg-[#f3eef8] text-[#634086] text-[10px] font-semibold tracking-wider uppercase px-2.5 py-[3px] rounded-full border border-[rgba(99,64,134,0.2)]">
            Signal Engine
          </span>
        </a>
        <ul className="landing-nav-links">
          {navLinks.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className={activeSection === link.href.slice(1) ? "active" : ""}
              >
                {link.label}
              </a>
            </li>
          ))}
          <li>
            <Link
              href="/dashboard"
              className="!bg-[#634086] !text-white px-5 py-2 rounded-lg text-sm !font-medium hover:!bg-[#4e3169] transition-all hover:-translate-y-[1px]"
            >
              View Dashboard &rarr;
            </Link>
          </li>
        </ul>
      </nav>

      {/* ──── HERO ──── */}
      <div id="top" className="max-w-[1200px] mx-auto">
        <div className="pt-[140px] pb-[100px] px-12 grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
          {/* Left */}
          <div>
            <div className="inline-flex items-center gap-2 bg-[#f3eef8] text-[#634086] text-xs font-semibold tracking-wide px-3.5 py-1.5 rounded-full mb-7 border border-[rgba(99,64,134,0.15)]">
              <span className="hero-tag-dot" />
              Pre-Procurement Intelligence &middot; Technical Assessment
            </div>
            <h1 className="text-[56px] lg:text-[64px] font-extrabold leading-[1.05] tracking-[-2.5px] text-black mb-6">
              Grants are the signal.
              <br />
              RFPs are the{" "}
              <span className="text-[#634086] relative">
                echo
                <span className="absolute bottom-1 left-0 right-0 h-[3px] bg-[#C9FFDA] rounded opacity-80" />
              </span>
              .
            </h1>
            <p className="text-[#4a4a4a] text-[17px] leading-[1.75] mb-9 max-w-[480px]">
              Canadian government grants are published 3&ndash;18 months before the procurement
              they fund. We built a pipeline that cleans messy government data, scores each grant
              for procurement potential, and predicts the specific RFPs that will follow &mdash; so
              businesses selling to government can{" "}<strong>anticipate, not just react</strong>.
            </p>
            <div className="flex gap-3 items-center flex-wrap">
              <a
                href="#how"
                className="bg-[#634086] text-white px-7 py-3 rounded-lg text-[15px] font-medium no-underline hover:bg-[#4e3169] hover:-translate-y-[1px] hover:shadow-[0_4px_16px_rgba(99,64,134,0.3)] transition-all inline-flex items-center gap-2"
              >
                See How It Works &rarr;
              </a>
              <a
                href="#pipeline"
                className="bg-white text-[#634086] px-7 py-3 rounded-lg text-[15px] font-medium no-underline border-[1.5px] border-[rgba(99,64,134,0.3)] hover:border-[#634086] hover:bg-[#faf7fd] transition-all"
              >
                Data Pipeline
              </a>
            </div>
          </div>

          {/* Right — Signal Card */}
          <div className="hero-card-float">
            <div className="bg-white border border-[#e8e8e8] rounded-xl shadow-[0_4px_6px_rgba(0,0,0,0.04),0_20px_60px_rgba(99,64,134,0.10)] overflow-hidden">
              <div className="bg-[#634086] px-5 py-4 flex justify-between items-center">
                <span className="text-xs font-semibold text-white tracking-wide">
                  LIVE PROCUREMENT SIGNALS
                </span>
                <span className="flex items-center gap-1.5 text-[11px] text-white/80">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#C9FFDA] animate-pulse" />
                  Updating now
                </span>
              </div>
              <div className="p-5 space-y-2.5">
                <div className="signal-row strong">
                  <div className="text-[13px] font-semibold text-black mb-1">
                    Ontario Cybersecurity Wave
                  </div>
                  <div className="text-[11px] text-[#717171] flex gap-3">
                    <span>$18.4M &middot; 14 grants</span>
                    <span>6&ndash;9 months out</span>
                  </div>
                  <span className="absolute top-3 right-3 text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide bg-[#dcfce7] text-[#16a34a]">
                    Strong
                  </span>
                </div>
                <div className="signal-row moderate">
                  <div className="text-[13px] font-semibold text-black mb-1">
                    Federal AI Modernization
                  </div>
                  <div className="text-[11px] text-[#717171] flex gap-3">
                    <span>$31.2M &middot; 9 grants</span>
                    <span>3&ndash;6 months out</span>
                  </div>
                  <span className="absolute top-3 right-3 text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide bg-[#fef3c7] text-[#d97706]">
                    Moderate
                  </span>
                </div>
                <div className="signal-row moderate">
                  <div className="text-[13px] font-semibold text-black mb-1">
                    Healthcare Digitization Wave
                  </div>
                  <div className="text-[11px] text-[#717171] flex gap-3">
                    <span>$22.1M &middot; 11 grants</span>
                    <span>6&ndash;12 months out</span>
                  </div>
                  <span className="absolute top-3 right-3 text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide bg-[#fef3c7] text-[#d97706]">
                    Moderate
                  </span>
                </div>
              </div>
              <div className="px-5 py-3 border-t border-[#e8e8e8] text-[11px] text-[#717171] flex justify-between">
                <span>IT Security &middot; Software Dev &middot; Health IT</span>
                <span>Updated 4 min ago</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="h-px bg-[#e8e8e8] max-w-[1200px] mx-auto" />

      {/* ──── PROBLEM ──── */}
      <section className="py-24 px-12 bg-[#faf7fd]" id="problem">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-xs font-semibold tracking-[1.5px] uppercase text-[#634086] mb-3">
            The Problem
          </div>
          <h2 className="l-reveal text-[44px] font-extrabold tracking-[-1.5px] leading-[1.1] text-black mb-4">
            Government spends on a script.
            <br />
            Nobody is reading it.
          </h2>
          <p className="l-reveal text-base text-[#4a4a4a] leading-[1.75] max-w-[560px]">
            Every RFP is preceded by a predictable chain of funding events. Most businesses only
            see the last step &mdash; when it&apos;s already too late to position.
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 mt-14 items-start">
            {/* Timeline */}
            <div className="landing-timeline">
              {[
                { step: "Step 1", title: "Budget Announced", desc: "Federal or provincial budget allocates funding to a policy priority area.", special: false },
                { step: "Step 2", title: "Grant Program Created", desc: "Department builds a grant stream to distribute the allocated funds to eligible recipients.", special: false },
                { step: "Step 3", title: "Grants Awarded", desc: "Municipalities, hospitals, universities receive funding. They now have a mandate to act.", special: false },
                { step: "Step 4 \u2190 We detect here", title: "Recipients Need Vendors", desc: "Funded organizations lack internal capacity. They need to hire vendors to implement. This is the signal.", special: true },
                { step: "Step 5", title: "RFP Published", desc: "The opportunity appears on a portal. Incumbents are already in conversations. You\u2019re writing a proposal in 3 weeks.", special: false },
              ].map((item, i) => (
                <div
                  key={i}
                  className={`tl-item ${item.special ? "special" : ""}`}
                  data-delay={i}
                >
                  <div className="text-[10px] font-semibold tracking-wider uppercase text-[#717171] mb-1">
                    {item.step}
                  </div>
                  <div className={`text-[15px] font-semibold mb-1 ${item.special ? "text-[#634086]" : "text-black"}`}>
                    {item.title}
                  </div>
                  <div className="text-[13px] text-[#717171] leading-relaxed">
                    {item.special ? (
                      <>
                        Funded organizations lack internal capacity.{" "}
                        <strong className="text-[#634086]">
                          They need to hire vendors to implement.
                        </strong>{" "}
                        This is the signal.
                      </>
                    ) : (
                      item.desc
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Pain Cards */}
            <div className="flex flex-col gap-3.5">
              {[
                { icon: <IconClock className="w-5 h-5 text-[#634086]" />, title: "\u201CWe\u2019re always too late.\u201D", body: "By the time an RFP drops, incumbents are already known to the buyer. 3-week response windows don\u2019t leave time to build relationships from scratch." },
                { icon: <IconCompass className="w-5 h-5 text-[#634086]" />, title: "\u201CWe don\u2019t know where government is heading.\u201D", body: "BD teams waste months targeting wrong departments and sectors \u2014 because there\u2019s no forward-looking intelligence about where funding is flowing." },
                { icon: <IconTrendDown className="w-5 h-5 text-[#634086]" />, title: "\u201CWe can\u2019t allocate BD resources strategically.\u201D", body: "Without knowing what\u2019s coming, firms spread BD spend too thin. They\u2019re reactive by necessity, not by choice." },
                { icon: <IconHourglass className="w-5 h-5 text-[#634086]" />, title: "\u201CWe need 6 months of runway, not 6 weeks.\u201D", body: "Winning government work requires pre-positioning \u2014 thought leadership, past performance, relationships. That takes months. This gives them those months." },
              ].map((card, i) => (
                <div
                  key={i}
                  className="pain-card bg-white border border-[#e8e8e8] rounded-lg px-5 py-[18px] flex gap-3.5 items-start shadow-[0_1px_3px_rgba(0,0,0,0.04)] hover:border-[rgba(99,64,134,0.3)] hover:shadow-[0_4px_12px_rgba(99,64,134,0.08)] transition-all"
                  data-delay={i}
                >
                  <span className="shrink-0 mt-0.5">{card.icon}</span>
                  <div>
                    <div className="text-sm font-semibold text-black mb-1">{card.title}</div>
                    <div className="text-[13px] text-[#717171] leading-relaxed">{card.body}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="h-px bg-[#e8e8e8] max-w-[1200px] mx-auto" />

      {/* ──── HOW IT WORKS ──── */}
      <section className="py-24 px-12" id="how">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-xs font-semibold tracking-[1.5px] uppercase text-[#634086] mb-3">
            How It Works
          </div>
          <h2 className="l-reveal text-[44px] font-extrabold tracking-[-1.5px] leading-[1.1] text-black mb-4">
            Four stages from raw data
            <br />
            to actionable intelligence
          </h2>
          <p className="l-reveal text-base text-[#4a4a4a] leading-[1.75] max-w-[560px]">
            From messy government portals to a procurement forecast in your dashboard.
            Every stage is automated, auditable, and designed to get smarter over time.
          </p>

          <div className="l-reveal grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px bg-[#e8e8e8] border border-[#e8e8e8] rounded-xl overflow-hidden mt-14">
            {HOW_STEPS.map((step, i) => (
              <div
                key={i}
                onClick={() => handleHowClick(i)}
                className={`bg-white p-7 cursor-pointer transition-colors relative ${
                  activeHow === i ? "!bg-[#faf7fd]" : "hover:bg-[#faf7fd]"
                }`}
              >
                {activeHow === i && (
                  <div className="absolute top-0 left-0 right-0 h-[3px] bg-[#634086]" />
                )}
                <div className="text-[11px] font-semibold text-[#634086] tracking-wider mb-3">
                  0{i + 1}
                </div>
                <span className="mb-3 block">{step.icon}</span>
                <div className="text-base font-bold text-black mb-2.5">{step.title}</div>
                <div className="text-[13px] text-[#717171] leading-relaxed">{step.desc}</div>
                <div className="h-0.5 bg-[#e8e8e8] mt-5 rounded overflow-hidden">
                  <div
                    className="how-bar-fill"
                    style={{ width: activeHow === i ? "100%" : "0%" }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="h-px bg-[#e8e8e8] max-w-[1200px] mx-auto" />

      {/* ──── BUSINESS VALUE ──── */}
      <section className="py-24 px-12 bg-[#f8f8f8]" id="value">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-xs font-semibold tracking-[1.5px] uppercase text-[#634086] mb-3">
            Business Value
          </div>
          <h2 className="l-reveal text-[44px] font-extrabold tracking-[-1.5px] leading-[1.1] text-black mb-4">
            How this creates value for Publicus
          </h2>
          <p className="l-reveal text-base text-[#4a4a4a] leading-[1.75] max-w-[560px]">
            This isn&apos;t a standalone product &mdash; it&apos;s a strategic intelligence layer
            that changes what Publicus is. From reactive feed to forward-looking platform.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-14">
            {[
              {
                tag: "01 \u2014 Retention",
                metric: "\u2191",
                label: "Dramatically stickier platform",
                body: "Reactive feeds get checked when RFPs drop. Forward-looking signals get checked weekly \u2014 because the intelligence is always moving. Users with a weekly habit are dramatically harder to churn.",
              },
              {
                tag: "02 \u2014 Revenue",
                metric: "$+",
                label: "Natural premium tier",
                body: "\u201CEarly Signal Alerts\u201D for BD teams at mid-to-large firms is a clear premium upsell. A 6-month advance warning on a $2M government contract saves tens of thousands in BD costs.",
              },
              {
                tag: "03 \u2014 Acquisition",
                metric: "\u2192",
                label: "New top-of-funnel entry point",
                body: "A free grants signal feed attracts businesses researching the government market who don\u2019t know Publicus exists yet. Different entry point, same platform. Widens the addressable audience.",
              },
            ].map((card, i) => (
              <div
                key={i}
                className="l-reveal group bg-white border border-[#e8e8e8] rounded-xl p-8 transition-all hover:border-[rgba(99,64,134,0.3)] hover:-translate-y-1 hover:shadow-[0_12px_32px_rgba(99,64,134,0.1)] relative overflow-hidden"
              >
                <div className="text-[10px] font-bold tracking-[2px] uppercase text-[#717171] mb-5">
                  {card.tag}
                </div>
                <div className="text-[52px] font-black tracking-[-2px] text-[#634086] leading-none mb-2">
                  {card.metric}
                </div>
                <div className="text-base font-semibold text-black mb-3">{card.label}</div>
                <div className="text-sm text-[#717171] leading-[1.65]">{card.body}</div>
                <div className="value-card-bar" />
              </div>
            ))}
          </div>

          {/* Stats Bar */}
          <div className="stats-bar-landing l-reveal grid grid-cols-2 lg:grid-cols-4 border border-[#e8e8e8] rounded-xl overflow-hidden mt-8 bg-white">
            <div className="p-7 border-r border-b lg:border-b-0 border-[#e8e8e8]">
              <div
                className="text-4xl font-extrabold tracking-tight text-[#634086] leading-none mb-1.5"
                data-count="12"
              >
                0
              </div>
              <div className="text-sm font-medium text-black mb-0.5">Procurement themes</div>
              <div className="text-xs text-[#717171]">From cybersecurity to clean energy</div>
            </div>
            <div className="p-7 border-r-0 lg:border-r border-b lg:border-b-0 border-[#e8e8e8]">
              <div
                className="text-4xl font-extrabold tracking-tight text-[#634086] leading-none mb-1.5"
                data-count="55"
              >
                0
              </div>
              <div className="text-sm font-medium text-black mb-0.5">RFP types predicted</div>
              <div className="text-xs text-[#717171]">Specific opportunities per grant</div>
            </div>
            <div className="p-7 border-r border-[#e8e8e8]">
              <div
                className="text-4xl font-extrabold tracking-tight text-[#634086] leading-none mb-1.5"
                data-count="5"
              >
                0
              </div>
              <div className="text-sm font-medium text-black mb-0.5">Data sources</div>
              <div className="text-xs text-[#717171]">Open Canada &middot; Innovation &middot; CSV &middot; more</div>
            </div>
            <div className="p-7">
              <div
                className="text-4xl font-extrabold tracking-tight text-[#634086] leading-none mb-1.5"
                data-count="7"
              >
                0
              </div>
              <div className="text-sm font-medium text-black mb-0.5">Pipeline stages</div>
              <div className="text-xs text-[#717171]">
                Ingest &rarr; Clean &rarr; Score &rarr; Classify &rarr; Predict
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="h-px bg-[#e8e8e8] max-w-[1200px] mx-auto" />

      {/* ──── DATA PIPELINE ──── */}
      <section className="py-24 px-12" id="pipeline">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-xs font-semibold tracking-[1.5px] uppercase text-[#634086] mb-3">
            Data Pipeline
          </div>
          <h2 className="l-reveal text-[44px] font-extrabold tracking-[-1.5px] leading-[1.1] text-black mb-4">
            Built on the hardest part
          </h2>
          <p className="l-reveal text-base text-[#4a4a4a] leading-[1.75] max-w-[560px]">
            A good UI on top of clean data is table stakes. Getting government data clean is the
            actual engineering problem. Click each stage to see what happens inside.
          </p>

          <div className="l-reveal flex flex-col lg:flex-row gap-px bg-[#e8e8e8] border border-[#e8e8e8] rounded-xl overflow-hidden mt-14">
            {PIPELINE_STAGES.map((stage, i) => (
              <div
                key={i}
                onClick={() => setActivePipe(i)}
                className={`flex-1 bg-white p-[18px] lg:p-5 cursor-pointer transition-colors relative min-w-0 ${
                  activePipe === i ? "!bg-[#faf7fd]" : "hover:bg-[#faf7fd]"
                }`}
              >
                {activePipe === i && (
                  <div className="absolute top-0 left-0 right-0 h-[3px] bg-[#634086]" />
                )}
                <div className="text-[10px] font-semibold text-[#634086] tracking-wider mb-2.5">
                  0{i + 1}
                </div>
                <span className="mb-2.5 block">{stage.icon}</span>
                <div className="text-[13px] font-semibold text-black">{stage.name}</div>
                <div
                  className={`pipe-detail text-xs text-[#717171] leading-relaxed ${
                    activePipe === i ? "open" : ""
                  }`}
                >
                  {stage.detail}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="h-px bg-[#e8e8e8] max-w-[1200px] mx-auto" />

      {/* ──── KEY DECISIONS ──── */}
      <section className="py-24 px-12 bg-[#f8f8f8]" id="decisions">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-xs font-semibold tracking-[1.5px] uppercase text-[#634086] mb-3">
            Key Decisions
          </div>
          <h2 className="l-reveal text-[44px] font-extrabold tracking-[-1.5px] leading-[1.1] text-black mb-4">
            What we built and why
          </h2>
          <p className="l-reveal text-base text-[#4a4a4a] leading-[1.75] max-w-[560px]">
            Every architectural choice has a reason. Here are the four decisions that shaped the system.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-14">
            {DECISIONS.map((d, i) => (
              <div
                key={i}
                className="l-reveal border border-[#e8e8e8] rounded-xl p-7 bg-white transition-all hover:border-[rgba(99,64,134,0.3)] hover:shadow-[0_4px_16px_rgba(99,64,134,0.08)]"
              >
                <div className="text-[11px] font-bold tracking-wider text-[#634086] mb-2.5">
                  DECISION 0{i + 1}
                </div>
                <div className="text-[17px] font-bold text-black mb-2">{d.title}</div>
                <div className="text-[13px] font-semibold text-[#717171] uppercase tracking-wide mb-1">
                  What
                </div>
                <div className="text-sm text-[#4a4a4a] leading-[1.65] mb-3.5">{d.what}</div>
                <div className="decision-why">{d.why}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="h-px bg-[#e8e8e8] max-w-[1200px] mx-auto" />

      {/* ──── FAQ ──── */}
      <section className="py-24 px-12" id="faq">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-xs font-semibold tracking-[1.5px] uppercase text-[#634086] mb-3">
            Technical FAQ
          </div>
          <h2 className="l-reveal text-[44px] font-extrabold tracking-[-1.5px] leading-[1.1] text-black mb-4">
            Questions you&apos;ll probably ask
          </h2>
          <p className="l-reveal text-base text-[#4a4a4a] leading-[1.75] max-w-[560px]">
            Detailed answers to the technical, data, and product questions that come up in a demo.
          </p>

          <div className="l-reveal flex flex-col gap-2 mt-14">
            {FAQ_ITEMS.map((faq, i) => {
              const isOpen = openFaq === i;
              return (
                <div
                  key={i}
                  className={`faq-item border border-[#e8e8e8] rounded-lg overflow-hidden bg-white transition-colors ${
                    isOpen ? "open !border-[rgba(99,64,134,0.3)]" : ""
                  }`}
                >
                  <div
                    onClick={() => setOpenFaq(isOpen ? null : i)}
                    className="flex justify-between items-center px-6 py-5 cursor-pointer hover:bg-[#faf7fd] transition-colors gap-4"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <span
                        className={`text-[10px] font-bold tracking-wider uppercase px-2.5 py-[3px] rounded-full shrink-0 ${faq.tagClass}`}
                      >
                        {faq.tag}
                      </span>
                      <span className="text-[15px] font-medium text-black truncate">
                        {faq.question}
                      </span>
                    </div>
                    <div
                      className={`w-7 h-7 rounded-md border flex items-center justify-center text-lg shrink-0 transition-all font-light ${
                        isOpen
                          ? "bg-[#634086] border-[#634086] text-white"
                          : "border-[#e8e8e8] text-[#717171]"
                      }`}
                    >
                      {isOpen ? "\u2212" : "+"}
                    </div>
                  </div>
                  <div className="faq-answer">
                    <div
                      className="faq-answer-body px-6 pb-6 text-sm text-[#4a4a4a] leading-[1.8] border-t border-[#f0f0f0] pt-[18px]"
                      dangerouslySetInnerHTML={{ __html: faq.answer }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <div className="h-px bg-[#e8e8e8] max-w-[1200px] mx-auto" />

      {/* ──── NEXT STEPS ──── */}
      <section className="py-24 px-12 bg-[#634086]" id="next">
        <div className="max-w-[1200px] mx-auto">
          <div className="text-xs font-semibold tracking-[1.5px] uppercase text-[#C9FFDA] mb-3">
            What&apos;s Next
          </div>
          <h2 className="text-[44px] font-extrabold tracking-[-1.5px] leading-[1.1] text-white mb-4">
            The roadmap is already written.
          </h2>
          <p className="text-base text-white/70 leading-[1.75] max-w-[560px]">
            Each next step is a natural extension of the data pipeline we&apos;ve already built. The
            infrastructure compounds.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-12">
            {NEXT_STEPS.map((ns, i) => (
              <div
                key={i}
                className="bg-white/[0.08] border border-white/[0.15] rounded-lg p-6 transition-all hover:bg-white/[0.14] hover:border-white/25 hover:-translate-y-0.5"
              >
                <div className="text-[28px] font-black text-[#C9FFDA] mb-3 tracking-tight">
                  0{i + 1}
                </div>
                <div className="text-[15px] font-semibold text-white mb-2">{ns.title}</div>
                <div className="text-[13px] text-white/60 leading-relaxed">{ns.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──── FOOTER ──── */}
      <footer className="bg-black px-12 py-10 flex flex-col sm:flex-row justify-between items-center gap-4">
        <PublicusLogo className="h-5 w-auto text-white" />
        <div className="text-[13px] text-white/40 flex flex-wrap gap-6 justify-center">
          <span>Technical Assessment Prototype &middot; 2026</span>
          <span>FastAPI &middot; Next.js &middot; Supabase &middot; Multi-LLM</span>
        </div>
      </footer>
    </div>
  );
}
