import type { NextConfig } from "next";

const backendProxyTarget =
  process.env.BACKEND_PROXY_TARGET?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${backendProxyTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;
