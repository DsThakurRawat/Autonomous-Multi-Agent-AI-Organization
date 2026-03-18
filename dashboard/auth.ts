import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import Credentials from "next-auth/providers/credentials"

const googleId = process.env.GOOGLE_CLIENT_ID;
const googleSecret = process.env.GOOGLE_CLIENT_SECRET;
const nextAuthSecret = process.env.NEXTAUTH_SECRET;

if (process.env.NODE_ENV === 'production' && (!googleId || !googleSecret || !nextAuthSecret)) {
  throw new Error('Missing authentication environment variables in production.');
}

export const { handlers, auth, signIn, signOut } = NextAuth({
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
        // Safeguard: Only allow mock login in development
        if (process.env.NODE_ENV === 'development') {
          if (credentials?.username === "admin" && credentials?.password === "admin") {
            return { 
              id: "1", 
              name: "Demo User", 
              email: "demo@proximus-nova.ai", 
              image: "https://api.dicebear.com/7.x/avataaars/svg?seed=Lucky" 
            };
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
    async jwt({ token, user }) {
      if (user) {
        token.user = user;
      }
      return token;
    },
    async session({ session, token }: any) {
      if (token?.user) {
        session.user = token.user;
      }
      return session;
    }
  }
})
