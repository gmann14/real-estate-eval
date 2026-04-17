export interface EvalRecord {
  slug: string;
  date: string;
  address: string;
  price: number;
  type: string;
  verdict: string;
  notes?: string;
}

export class IndexMdParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "IndexMdParseError";
  }
}

const HEADER = "# Watchlist";
const COLUMNS = ["Date", "Address", "Price", "Type", "Verdict", "Link"] as const;

export function appendOrUpdate(existing: string, record: EvalRecord): string {
  const rows = existing.trim() === "" ? [] : parseRows(existing);
  const incoming = toRow(record);

  const idx = rows.findIndex((r) => r.slug === record.slug);
  if (idx === -1) rows.push(incoming);
  else rows[idx] = incoming;

  rows.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  return render(rows);
}

interface Row {
  slug: string;
  date: string;
  address: string;
  priceCell: string;
  type: string;
  verdictCell: string;
  linkCell: string;
}

function toRow(r: EvalRecord): Row {
  const verdictCell = r.notes ? `${r.verdict} — ${r.notes}` : r.verdict;
  return {
    slug: r.slug,
    date: r.date,
    address: r.address,
    priceCell: formatMoney(r.price),
    type: r.type,
    verdictCell,
    linkCell: `[→](./${r.slug}/analysis.md)`,
  };
}

function parseRows(md: string): Row[] {
  if (!md.includes(HEADER)) {
    throw new IndexMdParseError("Missing '# Watchlist' header");
  }

  const tableMatch = md.match(
    /(\|[^\n]+\|)\s*\n(\|[-\s|:]+\|)\s*\n((?:\|[^\n]+\|\s*\n?)*)/,
  );
  if (!tableMatch) return [];

  const headerLine = tableMatch[1] ?? "";
  const headerCols = splitCells(headerLine);
  if (headerCols.length !== COLUMNS.length) {
    throw new IndexMdParseError(
      `Expected ${COLUMNS.length} columns, found ${headerCols.length}`,
    );
  }

  const body = tableMatch[3] ?? "";
  const rows: Row[] = [];
  for (const line of body.split("\n")) {
    if (!line.trim().startsWith("|")) continue;
    const cells = splitCells(line);
    if (cells.length !== COLUMNS.length) {
      throw new IndexMdParseError(
        `Row has ${cells.length} columns, expected ${COLUMNS.length}: ${line}`,
      );
    }
    const [date, address, priceCell, type, verdictCell, linkCell] = cells as [
      string, string, string, string, string, string,
    ];
    rows.push({
      slug: slugFromLink(linkCell),
      date,
      address,
      priceCell,
      type,
      verdictCell,
      linkCell,
    });
  }
  return rows;
}

function splitCells(line: string): string[] {
  const trimmed = line.trim();
  if (!trimmed.startsWith("|") || !trimmed.endsWith("|")) return [];
  return trimmed
    .slice(1, -1)
    .split("|")
    .map((c) => c.trim());
}

function slugFromLink(linkCell: string): string {
  const m = linkCell.match(/\.\/([^/]+)\/analysis\.md/);
  return m?.[1] ?? "";
}

function render(rows: Row[]): string {
  const headerLine = `| ${COLUMNS.join(" | ")} |`;
  const divider = `|${COLUMNS.map(() => "------").join("|")}|`;
  const bodyLines = rows.map(
    (r) =>
      `| ${r.date} | ${r.address} | ${r.priceCell} | ${r.type} | ${r.verdictCell} | ${r.linkCell} |`,
  );
  return [HEADER, "", headerLine, divider, ...bodyLines, ""].join("\n");
}

function formatMoney(n: number): string {
  return `$${n.toLocaleString("en-US")}`;
}
