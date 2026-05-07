import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import Credentials from "next-auth/providers/credentials"
import type { NextAuthConfig } from "next-auth"

const googleId = process.env.GOOGLE_CLIENT_ID;
const googleSecret = process.env.GOOGLE_CLIENT_SECRET;
const nextAuthSecret = process.env.NEXTAUTH_SECRET;

// Only register Google provider when real credentials are configured
const providers: NextAuthConfig["providers"] = [];

if (googleId && googleSecret && googleId !== "" && googleSecret !== "") {
  providers.push(
    Google({
      clientId: googleId,
      clientSecret: googleSecret,
      authorization: {
        params: {
          scope: "openid profile email",
        },
      },
    })
  );
}

// Always provide Developer Login for local development
providers.push(
  Credentials({
    name: "Developer Account",
    credentials: {
      username: { label: "Username", type: "text", placeholder: "admin" },
      password: { label: "Password", type: "password" }
    },
    async authorize(credentials) {
      if (credentials?.username === "admin" && credentials?.password === "admin") {
        return {
          id: "1",
          name: "Divyansh Rawat",
          email: "divyanshthakur594@gmail.com",
          image: "https://api.dicebear.com/7.x/avataaars/svg?seed=Lucky"
        };
      }
      return null;
    }
  })
);

export const config = {
  providers,
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
