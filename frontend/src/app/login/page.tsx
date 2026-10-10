import { FileCheck2, Gauge, Radar } from "lucide-react";
import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "@/components/auth/login-form";
import { Brand, BrandMark } from "@/components/brand";

export const metadata: Metadata = { title: "Sign in" };

const FEATURES = [
  {
    icon: Radar,
    title: "Automated discovery",
    text: "Nmap scans map every live device and flag the ones nobody registered.",
  },
  {
    icon: Gauge,
    title: "Explainable risk scores",
    text: "Scan findings, asset criticality and manual controls combined into one score you can audit.",
  },
  {
    icon: FileCheck2,
    title: "Audit-ready reporting",
    text: "Change alerts as they happen and a PDF report for the institution on demand.",
  },
];

export default function LoginPage() {
  return (
    <div className="grid min-h-svh lg:grid-cols-[1.1fr_1fr]">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-zinc-950 p-10 text-zinc-50 lg:flex">
        {/* emerald glow + faint grid */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(60% 50% at 15% 10%, oklch(0.596 0.145 163.225 / 0.35), transparent 70%)," +
              "radial-gradient(45% 40% at 90% 95%, oklch(0.696 0.17 162.48 / 0.18), transparent 70%)," +
              "linear-gradient(to right, oklch(1 0 0 / 0.04) 1px, transparent 1px)," +
              "linear-gradient(to bottom, oklch(1 0 0 / 0.04) 1px, transparent 1px)",
            backgroundSize: "auto, auto, 44px 44px, 44px 44px",
          }}
        />

        <div className="relative flex items-center gap-2.5">
          <BrandMark />
          <span className="text-lg font-semibold tracking-tight">CampusShield</span>
        </div>

        <div className="relative max-w-md space-y-8">
          <div className="space-y-3">
            <h1 className="text-4xl font-semibold leading-tight tracking-tight text-balance">
              Know every device on your campus network.
            </h1>
            <p className="text-zinc-400 text-pretty">
              One continuously updated view of what is connected, what is exposed and what to fix
              first.
            </p>
          </div>
          <ul className="space-y-5">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <li key={title} className="flex gap-3.5">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-emerald-400">
                  <Icon className="size-4.5" />
                </div>
                <div>
                  <p className="font-medium">{title}</p>
                  <p className="text-sm text-zinc-400">{text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-zinc-500">
          B.Tech CSE Major Project · Bharati Vidyapeeth (Deemed University), Navi Mumbai
        </p>
      </aside>

      <main className="flex flex-col items-center justify-center bg-background px-4 py-12 sm:px-10">
        <div className="w-full max-w-sm space-y-8">
          <div className="lg:hidden">
            <Brand />
          </div>
          <div className="space-y-1.5">
            <h2 className="text-2xl font-semibold tracking-tight">Sign in</h2>
            <p className="text-sm text-muted-foreground">
              Use your CampusShield account to continue.
            </p>
          </div>
          <Suspense>
            <LoginForm />
          </Suspense>
        </div>
      </main>
    </div>
  );
}
