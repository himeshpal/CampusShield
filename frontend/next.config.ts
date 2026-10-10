import type { NextConfig } from "next";

// FastAPI runs in Docker on localhost:8000. The browser only ever talks to Next.js;
// /api/* is proxied server-side, so there is no CORS setup and the auth cookie stays first-party.
const API_ORIGIN = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

// Baseline browser hardening for every response, including proxied /api ones.
// (A full script CSP is left out on purpose: Next.js dev mode relies on inline scripts.)
const SECURITY_HEADERS = [
  { key: "X-Frame-Options", value: "DENY" }, // no clickjacking via iframes
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  cacheComponents: true,
  devIndicators: false, // the floating "N" badge covers the sidebar user menu in demos
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
