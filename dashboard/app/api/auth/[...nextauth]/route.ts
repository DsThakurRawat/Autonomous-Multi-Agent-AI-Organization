export const runtime = 'edge';

import NextAuth from "next-auth"
import { authOptions } from "@/auth"

// NextAuth v4 relies on Node.js APIs and cannot run purely on Edge runtime.
// For Cloudflare deployments, use a Docker container, Cloudflare Tunnels, or migrate to NextAuth v5 (Auth.js).

const handler = NextAuth(authOptions)
export { handler as GET, handler as POST }
