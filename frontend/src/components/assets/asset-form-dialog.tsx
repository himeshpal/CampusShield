"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { CriticalityBadge } from "@/components/assets/asset-badges";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSaveAsset } from "@/hooks/use-assets";
import {
  ASSET_TYPES,
  CRITERIA,
  criticalityLevel,
  criticalityTotal,
  LEVELS,
} from "@/lib/assets";
import type { Asset, AssetFields, AssetType } from "@/lib/types";
import { cn } from "@/lib/utils";

const optional = z
  .string()
  .trim()
  .max(120)
  .transform((v) => v || null);

const schema = z.object({
  name: z.string().trim().min(2, "Give the asset a recognisable name").max(120),
  hostname: optional,
  asset_type: z.enum(ASSET_TYPES.map((t) => t.value) as [AssetType, ...AssetType[]]),
  ip_address: z
    .string()
    .trim()
    .refine((v) => !v || /^(\d{1,3}\.){3}\d{1,3}$/.test(v), "Enter a valid IPv4 address")
    .transform((v) => v || null),
  mac_address: z
    .string()
    .trim()
    .refine(
      (v) => !v || /^([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$/i.test(v),
      "MAC address looks like 3c:d9:2b:10:00:10",
    )
    .transform((v) => v || null),
  os_name: optional,
  department: optional,
  location: optional,
  owner: optional,
  notes: z
    .string()
    .trim()
    .max(2000)
    .transform((v) => v || null),
  data_sensitivity: z.number().int().min(1).max(3),
  service_dependency: z.number().int().min(1).max(3),
  users_affected: z.number().int().min(1).max(3),
  replaceability: z.number().int().min(1).max(3),
  baseline_ports: z
    .string()
    .trim()
    .refine(
      (v) => !v || v.split(/[\s,]+/).every((p) => /^\d+$/.test(p) && +p >= 1 && +p <= 65535),
      "Comma-separated port numbers, e.g. 22, 80, 443",
    )
    .transform((v) => (v ? [...new Set(v.split(/[\s,]+/).map(Number))].sort((a, b) => a - b) : [])),
});

type FormInput = z.input<typeof schema>;
type FormOutput = z.output<typeof schema>;

function defaults(asset?: Asset | null): FormInput {
  return {
    name: asset?.name ?? "",
    hostname: asset?.hostname ?? "",
    asset_type: asset?.asset_type ?? "server",
    ip_address: asset?.ip_address ?? "",
    mac_address: asset?.mac_address ?? "",
    os_name: asset?.os_name ?? "",
    department: asset?.department ?? "",
    location: asset?.location ?? "",
    owner: asset?.owner ?? "",
    notes: asset?.notes ?? "",
    data_sensitivity: asset?.data_sensitivity ?? 2,
    service_dependency: asset?.service_dependency ?? 2,
    users_affected: asset?.users_affected ?? 2,
    replaceability: asset?.replaceability ?? 2,
    baseline_ports: (asset?.observed_ports?.length && asset.status === "unregistered"
      ? asset.observed_ports.map((p) => p.port)
      : (asset?.baseline_ports ?? [])
    ).join(", "),
  };
}

const COPY = {
  create: {
    title: "Add asset",
    description: "Record a campus device in the inventory.",
    submit: "Add asset",
  },
  edit: { title: "Edit asset", description: "Update the inventory record.", submit: "Save changes" },
  register: {
    title: "Register device",
    description: "Confirm what this device is and who is responsible for it.",
    submit: "Register device",
  },
};

/** Mount it only while open (`{dialog && <AssetFormDialog open … />}`), so every use
 *  starts from a fresh form for the asset it was opened with. */
export function AssetFormDialog({
  mode,
  asset,
  open,
  onOpenChange,
}: {
  mode: "create" | "edit" | "register";
  asset?: Asset | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const save = useSaveAsset();
  const [error, setError] = useState<string | null>(null);
  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(schema),
    defaultValues: defaults(asset),
  });
  const { errors } = form.formState;

  const criteria = useWatch({ control: form.control, name: CRITERIA.map((c) => c.key) });
  const total = criticalityTotal(
    Object.fromEntries(CRITERIA.map((c, i) => [c.key, criteria[i] ?? 2])) as Pick<
      AssetFields,
      (typeof CRITERIA)[number]["key"]
    >,
  );

  function onSubmit(values: FormOutput) {
    setError(null);
    save.mutate(
      { mode, id: asset?.id, fields: values },
      {
        onSuccess: (saved) => {
          toast.success(
            mode === "register"
              ? `${saved.asset_tag} registered`
              : mode === "create"
                ? `${saved.asset_tag} added`
                : "Changes saved",
            { description: saved.name ?? undefined },
          );
          onOpenChange(false);
        },
        onError: (e) => setError(e.message),
      },
    );
  }

  const copy = COPY[mode];
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {copy.title}
            {asset && <span className="ml-2 font-mono text-sm text-muted-foreground">{asset.asset_tag}</span>}
          </DialogTitle>
          <DialogDescription>{copy.description}</DialogDescription>
        </DialogHeader>

        {mode === "register" && asset && (
          <div className="rounded-lg border border-risk-high/30 bg-risk-high/5 px-3 py-2 text-sm">
            Discovered on the network as <span className="font-mono">{asset.ip_address}</span>
            {asset.mac_vendor && <> ({asset.mac_vendor})</>}. Its open ports are pre-filled as
            the expected baseline. Remove any that should not be there.
          </div>
        )}

        <form id="asset-form" onSubmit={form.handleSubmit(onSubmit)} className="space-y-5" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Name" error={errors.name?.message} className="sm:col-span-2">
              <Input id="name" placeholder="e.g. Library Kiosk 2" {...form.register("name")} />
            </Field>
            <Field label="Type">
              <Controller
                control={form.control}
                name="asset_type"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="asset_type" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ASSET_TYPES.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          <t.icon />
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </Field>
            <Field label="Hostname">
              <Input id="hostname" placeholder="optional" {...form.register("hostname")} />
            </Field>
            <Field label="IP address" error={errors.ip_address?.message}>
              <Input id="ip_address" className="font-mono" {...form.register("ip_address")} />
            </Field>
            <Field label="MAC address" error={errors.mac_address?.message}>
              <Input id="mac_address" className="font-mono" {...form.register("mac_address")} />
            </Field>
            <Field label="Department">
              <Input id="department" placeholder="e.g. Computer Engineering" {...form.register("department")} />
            </Field>
            <Field label="Location">
              <Input id="location" placeholder="e.g. Computer Lab 3" {...form.register("location")} />
            </Field>
            <Field label="Owner">
              <Input id="owner" placeholder="Responsible person or team" {...form.register("owner")} />
            </Field>
            <Field label="Operating system">
              <Input id="os_name" placeholder="optional" {...form.register("os_name")} />
            </Field>
            <Field
              label="Expected open ports"
              error={errors.baseline_ports?.message}
              className="sm:col-span-2"
            >
              <Input id="baseline_ports" className="font-mono" placeholder="22, 80, 443" {...form.register("baseline_ports")} />
            </Field>
          </div>

          <div className="space-y-3 rounded-lg border p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Criticality</p>
                <p className="text-xs text-muted-foreground">
                  Rated on four objective criteria; feeds the risk score.
                </p>
              </div>
              <CriticalityBadge level={criticalityLevel(total)} total={total} />
            </div>
            {CRITERIA.map((c) => (
              <Controller
                key={c.key}
                control={form.control}
                name={c.key}
                render={({ field }) => (
                  <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-sm">{c.label}</p>
                      <p className="text-xs text-muted-foreground">{c.hint}</p>
                    </div>
                    <div role="radiogroup" aria-label={c.label} className="flex rounded-lg border p-0.5">
                      {LEVELS.map((level, i) => (
                        <button
                          key={level}
                          type="button"
                          role="radio"
                          aria-checked={field.value === i + 1}
                          onClick={() => field.onChange(i + 1)}
                          className={cn(
                            "rounded-md px-3 py-1 text-xs font-medium transition-colors",
                            field.value === i + 1
                              ? "bg-primary text-primary-foreground"
                              : "text-muted-foreground hover:text-foreground",
                          )}
                        >
                          {level}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              />
            ))}
          </div>

          <Field label="Notes">
            <Input id="notes" placeholder="optional" {...form.register("notes")} />
          </Field>

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="asset-form" disabled={save.isPending}>
            {save.isPending && <Loader2 className="animate-spin" />}
            {copy.submit}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  error,
  className,
  children,
}: {
  label: string;
  error?: string;
  className?: string;
  children: React.ReactElement<{ id?: string }>;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={children.props.id}>{label}</Label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
