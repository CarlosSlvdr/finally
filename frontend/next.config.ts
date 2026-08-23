import type { NextConfig } from "next";

// Static export: FastAPI serves this build's output/ directory directly on
// the same origin as /api/*, so no rewrites/redirects/headers are used here
// (those aren't supported with output: "export" and would break `next build`).
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
