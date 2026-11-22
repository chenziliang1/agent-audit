const { withBotId } = require('botid/next/config');

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Performance optimizations
  compiler: {
    // Remove console.* in production, except console.error: it is the only
    // record /api/chat leaves of a failed call to the agent.
    removeConsole: process.env.NODE_ENV === 'production' ? { exclude: ['error'] } : false,
  },

  // No `images.remotePatterns`: every image this app renders is local. Add the
  // host here if that ever stops being true.

  // No `rewrites` of our own: there is no separate backend process to proxy
  // /api to. `withBotId` below adds the ones Vercel BotID's challenge script is
  // served through, from this site's own origin so that a content blocker does
  // not stop it (see lib/agent/guard.ts).

  // Reduce bundle size
  productionBrowserSourceMaps: false,
};

module.exports = withBotId(nextConfig);
