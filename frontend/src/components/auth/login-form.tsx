"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Eye, EyeOff, Loader2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

const schema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Email is required")
    .regex(/^[^@\s]+@[^@\s]+\.[^@\s]+$/, "Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
type Values = z.infer<typeof schema>;

// Click-to-fill accounts for the project demo. Off unless NEXT_PUBLIC_DEMO_HINTS=1.
const DEMO_ACCOUNTS = [
  { label: "Admin", email: "admin@campusshield.local", password: "Admin@123" },
  { label: "Auditor", email: "auditor@campusshield.local", password: "Auditor@123" },
];
const SHOW_DEMO = process.env.NEXT_PUBLIC_DEMO_HINTS === "1";

function safeNext(next: string | null): string {
  // only same-site paths, never "//evil.com"
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard";
}

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const queryClient = useQueryClient();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  // Already signed in (valid cookie)? Skip the form.
  useEffect(() => {
    api<User>("/auth/me", { redirectOn401: false })
      .then(() => router.replace(safeNext(params.get("next"))))
      .catch(() => {});
  }, [router, params]);

  async function onSubmit(values: Values) {
    setError(null);
    try {
      // 401 here means wrong credentials, not an expired session: show it, don't redirect.
      const user = await api<User>("/auth/login", {
        method: "POST",
        json: values,
        redirectOn401: false,
      });
      queryClient.setQueryData(["me"], user);
      router.replace(safeNext(params.get("next")));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed");
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5" noValidate>
      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2.5 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          autoComplete="username"
          placeholder="you@college.edu.in"
          className="h-10"
          aria-invalid={!!errors.email}
          {...form.register("email")}
        />
        {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <div className="relative">
          <Input
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            className="h-10 pr-10"
            aria-invalid={!!errors.password}
            {...form.register("password")}
          />
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground"
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        </div>
        {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
      </div>

      <Button type="submit" className="h-10 w-full" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="animate-spin" />}
        {isSubmitting ? "Signing in…" : "Sign in"}
      </Button>

      {SHOW_DEMO && (
        <div className="rounded-lg border border-dashed p-3">
          <p className="mb-2 text-xs font-medium text-muted-foreground">Demo accounts</p>
          <div className="flex gap-2">
            {DEMO_ACCOUNTS.map((account) => (
              <Button
                key={account.label}
                type="button"
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={() => {
                  form.setValue("email", account.email, { shouldValidate: true });
                  form.setValue("password", account.password, { shouldValidate: true });
                }}
              >
                {account.label}
              </Button>
            ))}
          </div>
        </div>
      )}
    </form>
  );
}
