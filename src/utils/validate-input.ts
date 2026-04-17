export type ValidationErrorCode =
  | "ADDRESS_MISSING"
  | "PRICE_MISSING"
  | "TYPE_MISSING"
  | "MUNICIPALITY_MISSING"
  | "PROVINCE_MISSING"
  | "UNITS_TABLE_MALFORMED"
  | "UNITS_TABLE_MISSING"
  | "SECTION_MISSING";

export interface ValidationError {
  code: ValidationErrorCode;
  message: string;
  field?: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

interface RequiredField {
  label: string;
  code: ValidationErrorCode;
}

const REQUIRED_FIELDS: RequiredField[] = [
  { label: "Address", code: "ADDRESS_MISSING" },
  { label: "Asking Price", code: "PRICE_MISSING" },
  { label: "Type", code: "TYPE_MISSING" },
  { label: "Municipality", code: "MUNICIPALITY_MISSING" },
  { label: "Province", code: "PROVINCE_MISSING" },
];

const REQUIRED_SECTIONS = ["Listing Details", "Units", "Municipal"];

export function validateInput(markdown: string): ValidationResult {
  const errors: ValidationError[] = [];

  for (const section of REQUIRED_SECTIONS) {
    if (!hasSection(markdown, section)) {
      errors.push({
        code: "SECTION_MISSING",
        message: `Missing ${section} section`,
        field: section,
      });
    }
  }

  for (const { label, code } of REQUIRED_FIELDS) {
    if (!hasFieldValue(markdown, label)) {
      errors.push({
        code,
        message: `${label} is empty, missing, or still a placeholder`,
        field: label,
      });
    }
  }

  const unitsIssue = validateUnitsTable(markdown);
  if (unitsIssue) errors.push(unitsIssue);

  return { valid: errors.length === 0, errors };
}

function hasSection(md: string, name: string): boolean {
  const regex = new RegExp(`^#{1,3}\\s+${escapeRegex(name)}\\s*$`, "m");
  return regex.test(md);
}

function hasFieldValue(md: string, name: string): boolean {
  const regex = new RegExp(
    `\\*\\*${escapeRegex(name)}\\\\?\\*?:\\*\\*\\s*([^\\n]*)`,
    "i",
  );
  const match = md.match(regex);
  if (!match) return false;
  const raw = match[1]?.trim() ?? "";
  return isMeaningfulValue(raw);
}

function isMeaningfulValue(value: string): boolean {
  if (!value) return false;
  if (value === "$" || /^\$\s*$/.test(value)) return false;
  if (/^\$\s*\/\s*yr$/i.test(value)) return false;
  if (/^\[[^\]]*\]$/.test(value)) return false;
  if (/^\$\s*\[[^\]]*\]/.test(value)) return false;
  return true;
}

function validateUnitsTable(md: string): ValidationError | null {
  const section = extractSection(md, "Units");
  if (!section) return null;

  const tableMatch = section.match(
    /(\|[^\n]+\|)\s*\n(\|[-\s|:]+\|)\s*\n((?:\|[^\n]+\|\s*\n?)+)/,
  );
  if (!tableMatch) {
    return {
      code: "UNITS_TABLE_MISSING",
      message: "Units section has no markdown table",
    };
  }

  const headerLine = tableMatch[1] ?? "";
  const rowsBlock = tableMatch[3] ?? "";
  const headerCols = countTableColumns(headerLine);
  const rowLines = rowsBlock.split("\n").filter((l) => l.trim().startsWith("|"));

  for (let i = 0; i < rowLines.length; i++) {
    const rowLine = rowLines[i];
    if (!rowLine) continue;
    const rowCols = countTableColumns(rowLine);
    if (rowCols !== headerCols) {
      return {
        code: "UNITS_TABLE_MALFORMED",
        message: `Row ${i + 1} has ${rowCols} columns, expected ${headerCols}`,
      };
    }
  }

  return null;
}

function extractSection(md: string, name: string): string | null {
  const regex = new RegExp(
    `(?:^|\\n)##\\s+${escapeRegex(name)}\\s*\\n([\\s\\S]*?)(?=\\n##\\s|$)`,
  );
  const match = md.match(regex);
  return match?.[1] ?? null;
}

function countTableColumns(line: string): number {
  const trimmed = line.trim();
  if (!trimmed.startsWith("|") || !trimmed.endsWith("|")) return 0;
  return trimmed.split("|").length - 2;
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
