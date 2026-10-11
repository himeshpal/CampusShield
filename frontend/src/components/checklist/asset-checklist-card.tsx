"use client";

import Link from "next/link";

import { ChecklistCell } from "@/components/checklist/checklist-cell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useChecklist } from "@/hooks/use-checklist";

/** The six controls of one asset, editable in place (same editor as the matrix). */
export function AssetChecklistCard({
  assetId,
  assetLabel,
  canEdit,
}: {
  assetId: number;
  assetLabel: string;
  canEdit: boolean;
}) {
  const { data: matrix } = useChecklist();
  const row = matrix?.rows.find((r) => r.asset_id === assetId);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Security checklist</CardTitle>
        <CardDescription>
          {row ? `${row.answered} of ${matrix!.items.length} controls answered.` : "Controls a scan cannot see."}{" "}
          <Link href="/checklist" className="text-primary hover:underline">
            All assets
          </Link>
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!matrix || !row ? (
          <Skeleton className="h-40 w-full" />
        ) : (
          <ul className="divide-y">
            {matrix.items.map((item) => (
              <li key={item.key} className="flex items-center justify-between gap-3 py-2">
                <span className="text-sm">{item.label}</span>
                <ChecklistCell
                  assetId={assetId}
                  assetLabel={assetLabel}
                  item={item}
                  entry={row.entries[item.key]!}
                  canEdit={canEdit}
                  variant="row"
                />
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
