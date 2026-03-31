import type { NextAuthOptions } from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import CredentialsProvider from "next-auth/providers/credentials"

const googleId = process.env.GOOGLE_CLIENT_ID;
const googleSecret = process.env.GOOGLE_CLIENT_SECRET;
const nextAuthSecret = process.env.NEXTAUTH_SECRET;

if (process.env.NODE_ENV === 'production' && (!googleId || !googleSecret || !nextAuthSecret)) {
  console.warn('Missing authentication environment variables in production. Falling back to mock values.');
}

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: googleId || "mock_client_id",
      clientSecret: googleSecret || "mock_client_secret",
    }),
    CredentialsProvider({
      name: "Developer Account",
      credentials: {
        username: { label: "Username", type: "text", placeholder: "developer" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (process.env.NODE_ENV !== 'production') {
          if (credentials?.username === "admin" && credentials?.password === "admin") {
             return { id: "1", name: "Demo User", email: "demo@proximus.ai", image: "https://api.dicebear.com/7.x/avataaars/svg?seed=Lucky" };
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
      if (token?.user) { session.user = token.user; }
      return session;
    }
  }
}
