/** @type {import('next').NextConfig} */
const nextConfig = {
    experimental: {
        serverComponentsExternalPackages: ['pdf-parse', 'xlsx'],
    },
};

export default nextConfig;
