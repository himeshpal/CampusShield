"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { BAND_ORDER, BANDS } from "@/lib/risk";
import type { RiskTrendPoint } from "@/lib/types";

const shortDate = (iso: string) =>
  new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

/** Campus average after each scoring event: one series (the card title names it, so no
 *  legend), band thresholds as hairlines, crosshair + tooltip with the band mix. */
export function CampusTrend({ points }: { points: RiskTrendPoint[] }) {
  const data = points.map((p, i) => ({ ...p, index: i }));
  return (
    <div className="h-52 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" strokeWidth={1} />
          {[25, 50, 75].map((y) => (
            <ReferenceLine key={y} y={y} stroke="var(--border)" strokeWidth={1} />
          ))}
          <XAxis
            dataKey="index"
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            ticks={data.length > 1 ? [0, data.length - 1] : [0]}
            tickFormatter={(i) => (data[i] ? shortDate(data[i].at) : "")}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          />
          <Tooltip
            cursor={{ stroke: "var(--muted-foreground)", strokeWidth: 1 }}
            content={({ active, payload }) => {
              const point = active && (payload?.[0]?.payload as RiskTrendPoint | undefined);
              if (!point) return null;
              return (
                <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-md">
                  <p className="font-medium">Average {point.average} / 100</p>
                  <p className="mb-1.5 text-muted-foreground">
                    {shortDate(point.at)} · {point.assessed} devices
                  </p>
                  <ul className="space-y-0.5">
                    {[...BAND_ORDER].reverse().map((b) => (
                      <li key={b} className="flex items-center gap-2">
                        <span className={`size-2 rounded-sm ${BANDS[b].mark}`} aria-hidden />
                        <span className="text-muted-foreground">{BANDS[b].label}</span>
                        <span className="ml-auto pl-4 font-medium tabular-nums">{point.bands[b]}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            }}
          />
          <Line
            type="monotone"
            dataKey="average"
            stroke="var(--primary)"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            dot={data.length <= 30 ? { r: 4, fill: "var(--primary)", stroke: "var(--card)", strokeWidth: 2 } : false}
            activeDot={{ r: 6, fill: "var(--primary)", stroke: "var(--card)", strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
