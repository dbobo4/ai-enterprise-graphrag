const backend = process.env.BACKEND_URL || "http://backend:8000";

export default {
  output: "standalone",
  experimental: { proxyTimeout: 600_000, proxyClientMaxBodySize: "11mb" }, // Allow evaluation runs and 10 MB uploads with form headers.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};
