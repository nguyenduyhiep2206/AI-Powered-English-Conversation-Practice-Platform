import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Playwright and local browsers often hit the container via 127.0.0.1
  // while Next binds as localhost — allow both in development.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
