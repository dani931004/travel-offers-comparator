import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  basePath: '/travel-offers-comparator',
  images: {
    unoptimized: true,
  },
  /* config options here */
};

export default nextConfig;
