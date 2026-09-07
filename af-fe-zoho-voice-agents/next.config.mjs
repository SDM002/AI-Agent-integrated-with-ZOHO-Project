/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    const backend = (process.env.BACKEND_URL || "").replace(/\/$/, "");
    return [
      { source: "/auth/:path*", destination: `${backend}/auth/:path*` },
    ];
  },
};

export default nextConfig;
