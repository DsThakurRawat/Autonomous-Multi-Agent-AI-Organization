import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import Credentials from "next-auth/providers/credentials"
import type { NextAuthConfig } from "next-auth"

const googleId = process.env.GOOGLE_CLIENT_ID;
const googleSecret = process.env.GOOGLE_CLIENT_SECRET;
const nextAuthSecret = process.env.NEXTAUTH_SECRET;

if (process.env.NODE_ENV === 'production' && (!googleId || !googleSecret || !nextAuthSecret)) {
  console.warn('Missing authentication environment variables in production. Falling back to mock values.');
}

export const config = {
  providers: [
    Google({
      clientId: googleId || "mock_client_id",
      clientSecret: googleSecret || "mock_client_secret",
    }),
    Credentials({
      name: "Developer Account",
      credentials: {
        username: { label: "Username", type: "text", placeholder: "developer" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (process.env.NODE_ENV !== 'production') {
          if (credentials?.username === "admin" && credentials?.password === "admin") {
             return { id: "1", name: "Demo User", email: "demo@sarang.ai", image: "https://api.dicebear.com/7.x/avataaars/svg?seed=Lucky" };
          }
        }
        return null;
      }
    })
  ],
  secret: nextAuthSecret || "super-secret-default-key-for-dev",
  pages: {
    signIn: "/",
  },
  callbacks: {
    async jwt({ token, user }: any) {
      if (user) { token.user = user; }
      return token;
    },
    async session({ session, token }: any) {
      if (token?.user) { session.user = token.user as any; }
      return session;
    }
  }
} satisfies NextAuthConfig

export const { handlers, auth, signIn, signOut } = NextAuth(config)
