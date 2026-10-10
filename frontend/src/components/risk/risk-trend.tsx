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

import { BANDS, formatScore } from "@/lib/risk";
import type { RiskPoint } from "@/lib/types";

/** Score over time: one series (no legend), 2px line, ringed markers, band
 *  thresholds as hairlines, crosshair + tooltip on hover. */
export function RiskTrend({ history }: { history: RiskPoint[] }) {
  const data = history.map((p, i) => ({ ...p, index: i + 1 }));
  return (
    <div className="h-48 w-full">
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
            tickFormatter={(i) => `#${i}`}
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
              const point = active && payload?.[0]?.payload;
              if (!point) return null;
              return (
                <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-md">
                  <p className="font-medium">
                    {formatScore(point.score)} / 100 · {BANDS[point.band as keyof typeof BANDS].label}
                  </p>
                  <p className="text-muted-foreground">
                    {new Date(point.computed_at).toLocaleString("en-IN", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                    {point.scan_id ? ` · scan #${point.scan_id}` : ""}
                  </p>
                </div>
              );
            }}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="var(--primary)"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            dot={{ r: 4, fill: "var(--primary)", stroke: "var(--card)", strokeWidth: 2 }}
            activeDot={{ r: 6, fill: "var(--primary)", stroke: "var(--card)", strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
