/** @type {import('next').NextConfig} */
const nextConfig = {
  // Rewrite API calls to backend in production to avoid CORS issues
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    
    // Only add rewrites if we have a production API URL
    if (apiUrl && !apiUrl.includes('localhost')) {
      return [
        { source: '/api/:path*', destination: `${apiUrl}/api/:path*` },
        { source: '/health', destination: `${apiUrl}/health` },
      ];
    }
    
    return [];
  },
}

module.exports = nextConfig
