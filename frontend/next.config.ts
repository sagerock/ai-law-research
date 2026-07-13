import type { NextConfig } from "next";
import { CANONICAL_SITE_URL, LEGACY_HOST } from "./lib/site";

const nextConfig: NextConfig = {
  generateBuildId: () => `build-${Date.now()}`,
  async redirects() {
    return [
      {
        source: '/:path*',
        has: [{ type: 'host', value: LEGACY_HOST }],
        destination: `${CANONICAL_SITE_URL}/:path*`,
        permanent: true,
      },
      {
        source: '/:path*',
        has: [{ type: 'host', value: 'www.tortwell.com' }],
        destination: `${CANONICAL_SITE_URL}/:path*`,
        permanent: true,
      },
    ]
  },
};

export default nextConfig;
