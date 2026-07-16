import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Worker URL for future CAD pipeline (local or remote)
  env: {
    NEXT_PUBLIC_WORKER_URL: process.env.NEXT_PUBLIC_WORKER_URL ?? "",
  },
};

export default nextConfig;
