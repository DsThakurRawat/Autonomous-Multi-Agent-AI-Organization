import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import Credentials from "next-auth/providers/credentials"

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID || "mock_client_id",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "mock_client_secret",
    }),
    Credentials({
      name: "Developer Account",
      credentials: {
        username: { label: "Username", type: "text", placeholder: "developer" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        // Mock login for local demo purposes
        if (credentials?.username === "admin" && credentials?.password === "admin") {
          return { 
            id: "1", 
            name: "Demo User", 
            email: "demo@proximus-nova.ai", 
            image: "https://api.dicebear.com/7.x/avataaars/svg?seed=Lucky" 
          };
        }
        return null;
      }
    })
  ],
  secret: process.env.NEXTAUTH_SECRET || "super-secret-default-key-for-dev",
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
