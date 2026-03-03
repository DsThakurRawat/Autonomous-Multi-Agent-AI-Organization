import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";

const handler = NextAuth({
    providers: [
        GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID || "mock_client_id_for_demo",
            clientSecret: process.env.GOOGLE_CLIENT_SECRET || "mock_client_secret_for_demo",
        })
    ],
    secret: process.env.NEXTAUTH_SECRET || "super-secret-default-key-for-dev",
    pages: {
        signIn: "/",
    }
});

export { handler as GET, handler as POST };
