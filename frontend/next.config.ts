import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // "standalone" is for Docker/Render self-hosted deployments.
  // Vercel sets VERCEL=1 and handles its own output — skip standalone there.
  ...(process.env.VERCEL ? {} : { output: "standalone" }),
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
