import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    useWasmBinary: true
  }
};

export default nextConfig;
