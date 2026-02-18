import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  generateBuildId: () => `build-${Date.now()}`,
};

export default nextConfig;
