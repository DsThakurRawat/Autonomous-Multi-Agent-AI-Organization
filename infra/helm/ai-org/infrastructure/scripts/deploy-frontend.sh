#!/bin/bash
# Proximus-Nova Frontend Deployment Script (Vercel)

set -e

echo "==============================================="
echo " Deploying Proximus-Nova Dashboard to Vercel   "
echo "==============================================="

# Navigate to the dashboard directory
cd "../../dashboard" || { echo "Dashboard directory not found"; exit 1; }

echo "[*] Verifying Node/Vercel CLI availability..."
if ! command -v npx &> /dev/null; then
    echo "[!] npm/npx is not installed. Please install Node.js."
    exit 1
fi

# Need to make sure API route is set correctly for Vercel. 
# Depending on how Vercel environment is provided, we might prompt the user.
if [[ -z "$NEXT_PUBLIC_API_URL" ]]; then
    echo "[!] Warning: NEXT_PUBLIC_API_URL is not set externally. Vercel will need this configured."
fi

echo "[*] Triggering Vercel deployment..."
# Using npx to ensure vercel is invoked
npx vercel --prod

echo "[*] Vercel deployment triggered successfully."
