import { Check, CircleDashed, Minus, X, type LucideIcon } from "lucide-react";

import type { ControlStatus } from "@/lib/types";

/** Answer states. Colour only marks the two meaningful outcomes (in place / missing);
 *  every state also has an icon and a label, so nothing relies on colour alone. */
export const CONTROL_STATUS: Record<
  ControlStatus,
  { label: string; short: string; icon: LucideIcon; cell: string; mark: string; hint: string }
> = {
  yes: {
    label: "In place",
    short: "Yes",
    icon: Check,
    cell: "border-risk-low/40 bg-risk-low/10 text-risk-low-ink",
    mark: "bg-risk-low",
    hint: "The control is implemented. Note how you verified it.",
  },
  no: {
    label: "Missing",
    short: "No",
    icon: X,
    cell: "border-risk-critical/40 bg-risk-critical/10 text-risk-critical-ink",
    mark: "bg-risk-critical",
    hint: "Known gap: counts against the risk score until fixed.",
  },
  na: {
    label: "Not applicable",
    short: "N/A",
    icon: Minus,
    cell: "border-border bg-muted text-muted-foreground",
    mark: "bg-muted-foreground/60",
    hint: "Does not apply to this kind of device (e.g. antivirus on a camera).",
  },
  unknown: {
    label: "Not confirmed",
    short: "?",
    icon: CircleDashed,
    cell: "border-dashed border-border text-muted-foreground",
    mark: "bg-muted-foreground/20",
    hint: "Nobody has checked yet: counts against the risk score.",
  },
};

export const STATUS_ORDER: ControlStatus[] = ["yes", "no", "na", "unknown"];

/** Short column headers for the matrix (full label + description in the tooltip). */
export const SHORT_LABELS: Record<string, string> = {
  firewall: "Firewall",
  antivirus: "Antivirus",
  disk_encryption: "Encryption",
  mfa: "MFA",
  patch_policy: "Patching",
  default_credentials: "Default creds",
};
