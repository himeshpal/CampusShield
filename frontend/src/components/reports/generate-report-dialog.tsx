"use client";

import { FileText, Loader2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { reportPdfUrl, useGenerateReport } from "@/hooks/use-reports";
import { cn } from "@/lib/utils";

const SCOPES = [
  {
    value: "full",
    label: "Full report",
    description: "Summary, recommendations and registers, plus one section per device with its evidence.",
  },
  {
    value: "summary",
    label: "Summary only",
    description: "Everything except the per-device evidence: shorter, for management.",
  },
] as const;

function defaultTitle(): string {
  const month = new Date().toLocaleString("en-IN", { month: "long", year: "numeric" });
  return `Campus security audit, ${month}`;
}

export function GenerateReportDialog({ size = "default" }: { size?: "default" | "lg" }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [scope, setScope] = useState<(typeof SCOPES)[number]["value"]>("full");
  const generate = useGenerateReport();

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!generate.isPending) setOpen(next);
        if (next) generate.reset();
      }}
    >
      <DialogTrigger asChild>
        <Button size={size}>
          <FileText />
          Generate report
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Generate audit report</DialogTitle>
          <DialogDescription>
            A PDF snapshot of the current inventory, risk scores and checklist. It is kept in the
            report history.
          </DialogDescription>
        </DialogHeader>

        <form
          id="generate-report"
          className="space-y-5"
          onSubmit={(e) => {
            e.preventDefault();
            generate.mutate(
              { title: title.trim() || null, include_details: scope === "full" },
              {
                onSuccess: (report) => {
                  setOpen(false);
                  setTitle("");
                  toast.success(`${report.number} generated`, {
                    description: `${report.pages} pages`,
                    action: {
                      label: "Open",
                      onClick: () => window.open(reportPdfUrl(report.id), "_blank", "noopener"),
                    },
                  });
                },
              },
            );
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="report-title">Title</Label>
            <Input
              id="report-title"
              value={title}
              maxLength={200}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={open ? defaultTitle() : undefined} // not at prerender: needs today
            />
          </div>

          <div className="space-y-2">
            <Label>Contents</Label>
            <RadioGroup
              value={scope}
              onValueChange={(v) => setScope(v as typeof scope)}
              className="gap-2"
            >
              {SCOPES.map((s) => (
                <Label
                  key={s.value}
                  htmlFor={`scope-${s.value}`}
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-lg border p-3 font-normal transition-colors hover:bg-muted/50",
                    scope === s.value && "border-primary/50 bg-primary/5 hover:bg-primary/5",
                  )}
                >
                  <RadioGroupItem id={`scope-${s.value}`} value={s.value} className="mt-0.5" />
                  <div className="grid flex-1 gap-0.5">
                    <span className="font-medium">{s.label}</span>
                    <span className="text-xs leading-relaxed text-muted-foreground">
                      {s.description}
                    </span>
                  </div>
                </Label>
              ))}
            </RadioGroup>
          </div>

          {generate.error && (
            <p role="alert" className="text-sm text-destructive">
              {generate.error.message}
            </p>
          )}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={generate.isPending}>
            Cancel
          </Button>
          <Button type="submit" form="generate-report" disabled={generate.isPending}>
            {generate.isPending ? <Loader2 className="animate-spin" /> : <FileText />}
            {generate.isPending ? "Generating…" : "Generate PDF"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
