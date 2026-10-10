"use client";

import { ExternalLink } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useRiskModel } from "@/hooks/use-assets";
import { BANDS } from "@/lib/risk";
import { cn } from "@/lib/utils";

/** The whole scoring model, read from the API (so it can never drift from the code). */
export function RiskModelPanel() {
  const { data: model } = useRiskModel();
  if (!model) return <Skeleton className="h-96 w-full rounded-xl" />;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Scoring formula</CardTitle>
          <CardDescription>Model version {model.version}. Every score in CampusShield is computed with these rules.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <p className="rounded-lg bg-muted/60 px-3 py-2 font-mono text-xs">{model.formula}</p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Component</TableHead>
                <TableHead>Rule</TableHead>
                <TableHead className="text-right">Max points</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {model.components.map((c) => (
                <TableRow key={c.key}>
                  <TableCell className="font-medium">{c.label}</TableCell>
                  <TableCell className="whitespace-normal text-muted-foreground">
                    {c.rule ??
                      (c.key === "exposure"
                        ? "weight of each reachable service (table below)"
                        : "matched CVEs, end-of-life software and NSE findings")}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{c.cap}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2 text-sm">
              <p className="font-medium">Criticality multiplier</p>
              <p className="text-muted-foreground">{model.multiplier}</p>
              <p className="pt-2 font-medium">CVSS to points</p>
              <ul className="text-muted-foreground">
                {model.cvss_points.map((c) => (
                  <li key={c.cvss_from}>
                    CVSS ≥ {c.cvss_from.toFixed(1)}: {c.points} points
                  </li>
                ))}
              </ul>
            </div>
            <div className="space-y-2 text-sm">
              <p className="font-medium">Bands</p>
              <ul className="space-y-1">
                {[...model.bands].reverse().map((b) => (
                  <li key={b.band} className="flex items-center gap-2">
                    <span className={cn("size-2.5 rounded-sm", BANDS[b.band].mark)} aria-hidden />
                    <span className="w-16">{BANDS[b.band].label}</span>
                    <span className="text-muted-foreground tabular-nums">score ≥ {b.from}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Service exposure weights</CardTitle>
            <CardDescription>Any other open port adds {model.other_port_points} points.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Service</TableHead>
                  <TableHead>Why it matters</TableHead>
                  <TableHead className="text-right">Points</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {model.service_weights.map((w) => (
                  <TableRow key={w.service}>
                    <TableCell className="font-mono text-xs">{w.service}</TableCell>
                    <TableCell className="whitespace-normal text-muted-foreground">{w.label}</TableCell>
                    <TableCell className="text-right tabular-nums">{w.points}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Other findings</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {model.end_of_life.map((r) => (
                  <li key={r.title} className="flex justify-between gap-4">
                    <span>
                      {r.title} <span className="text-muted-foreground">(version {r.version_spec})</span>
                    </span>
                    <span className="tabular-nums">+{r.points}</span>
                  </li>
                ))}
                {model.script_findings.map((r) => (
                  <li key={r.title} className="flex justify-between gap-4">
                    <span>
                      {r.title} <span className="text-muted-foreground">(NSE {r.script})</span>
                    </span>
                    <span className="tabular-nums">+{r.points}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Known limitations</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-disc space-y-2 pl-4 text-sm text-muted-foreground">
                {model.limitations.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Vulnerability reference list</CardTitle>
          <CardDescription>
            {model.cves.length} CVEs matched against detected product versions. Scores verified
            against NIST NVD.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>CVE</TableHead>
                <TableHead>Product</TableHead>
                <TableHead>Affected versions</TableHead>
                <TableHead>CVSS</TableHead>
                <TableHead>Summary</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {model.cves.map((c) => (
                <TableRow key={`${c.cve_id}-${c.product}`}>
                  <TableCell>
                    <a
                      href={`https://nvd.nist.gov/vuln/detail/${c.cve_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 font-mono text-xs font-medium hover:underline"
                    >
                      {c.cve_id}
                      <ExternalLink className="size-3 text-muted-foreground" />
                    </a>
                  </TableCell>
                  <TableCell>{c.product}</TableCell>
                  <TableCell className="font-mono text-xs">{c.version_spec}</TableCell>
                  <TableCell>
                    <span className="inline-flex items-center gap-1.5 tabular-nums">
                      <span
                        className={cn(
                          "size-2 rounded-full",
                          BANDS[c.severity === "medium" ? "medium" : c.severity === "high" ? "high" : c.severity === "low" ? "low" : "critical"].mark,
                        )}
                        aria-hidden
                      />
                      {c.cvss.toFixed(1)}
                      <span className="text-xs capitalize text-muted-foreground">{c.severity}</span>
                    </span>
                  </TableCell>
                  <TableCell className="min-w-64 whitespace-normal text-muted-foreground">{c.summary}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
