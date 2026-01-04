# 🚀 Vercel Deployment Guide

This guide will help you deploy the Arbitrage Bot frontend to Vercel with automatic builds and deployments from GitHub.

## Prerequisites

- [GitHub Account](https://github.com)
- [Vercel Account](https://vercel.com) (free tier works)
- Git installed locally
- Backend API deployed and accessible via HTTPS

## Step 1: Push to GitHub

### 1.1 Create a GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Create a new repository:
   - **Name**: `arbitrage-bot` (or your preference)
   - **Description**: Sports arbitrage betting dashboard
   - **Visibility**: Public (required for Vercel free tier) or Private
   - **Add .gitignore**: Already included
   - **Add LICENSE**: MIT recommended

3. Click **Create Repository**

### 1.2 Push Code to GitHub

```bash
cd c:\Users\major\arbitragebot

# Initialize git (if not already done)
git init

# Add all files
git add -A

# Create initial commit
git commit -m "Initial commit: Arbitrage bot frontend and backend"

# Add remote origin
git remote add origin https://github.com/YOUR_USERNAME/arbitrage-bot.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Note**: Replace `YOUR_USERNAME` with your actual GitHub username.

## Step 2: Deploy to Vercel

### 2.1 Connect Vercel to GitHub

1. Go to [vercel.com](https://vercel.com)
2. Click **New Project**
3. Select **Import Git Repository**
4. Authorize Vercel to access your GitHub account
5. Select your `arbitrage-bot` repository
6. Click **Import**

### 2.2 Configure Project Settings

In the **Project Settings** page:

**Framework Preset**: Next.js (auto-detected)

**Build & Output Settings**:
- **Build Command**: `npm run build`
- **Output Directory**: `.next`
- **Install Command**: `npm install`

**Environment Variables** (Add these):

```
NEXT_PUBLIC_API_BASE_URL=https://your-backend-api.com
```

Replace `https://your-backend-api.com` with your actual backend URL.

### 2.3 Deploy

1. Click **Deploy**
2. Wait for build to complete (2-3 minutes)
3. Get your Vercel URL: `https://arbitrage-bot-xxx.vercel.app`
4. Share this URL - it's your live dashboard!

## Step 3: Configure Backend URL

### Option A: Update Environment Variables in Vercel Dashboard

1. Go to your Vercel project
2. **Settings** → **Environment Variables**
3. Add/Update:
   - **Key**: `NEXT_PUBLIC_API_BASE_URL`
   - **Value**: Your backend URL (must be HTTPS)
   - **Environments**: Production, Preview, Development

4. Click **Add**
5. Rerun the deployment or push a new commit to trigger rebuild

### Option B: Update .env.local Locally

Edit `web/frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend-api.com
```

Then commit and push:

```bash
git add web/frontend/.env.local
git commit -m "Update API base URL"
git push
```

## Step 4: Verify Deployment

### Test the Dashboard

1. Open your Vercel URL: `https://arbitrage-bot-xxx.vercel.app`
2. Verify the dashboard loads
3. Check the browser console (F12) for errors
4. Verify WebSocket connection (should see "WS /ws" in Network tab)

### Test API Connection

Check that API calls work:

1. Open **Developer Tools** (F12)
2. Go to **Network** tab
3. Refresh the page
4. Look for requests to your backend URL
5. Should see `GET /odds`, `GET /metrics`, etc.

### Troubleshoot Connection Issues

**If you see "Failed to load dashboard data":**

1. Check backend URL in Vercel environment variables
2. Verify backend is running and accessible
3. Check backend CORS settings
4. Verify backend responds to `GET /docs`

```bash
# Test backend from terminal
curl https://your-backend-api.com/docs
```

## Step 5: Enable HTTPS (Automatic)

Vercel automatically provides **HTTPS** for all deployed apps:

- **Your Dashboard**: `https://arbitrage-bot-xxx.vercel.app`
- **Auto-renewed SSL certificate**: Yes
- **Security headers**: Automatically added by vercel.json

No additional setup required!

## Step 6: Custom Domain (Optional)

### Add a Custom Domain

1. In Vercel **Settings** → **Domains**
2. Click **Add Domain**
3. Enter your domain (e.g., `arb-bot.com`)
4. Follow DNS configuration instructions
5. Point DNS to Vercel nameservers

Example DNS records:
```
arb-bot.com          CNAME    cname.vercel-dns.com
```

## Step 7: Continuous Deployment

Every time you push to GitHub, Vercel **automatically rebuilds and deploys**:

```bash
# Make changes locally
cd web/frontend
# ... edit files ...

# Commit and push
git add .
git commit -m "Update dashboard UI"
git push origin main

# Vercel automatically:
# 1. Detects the push
# 2. Runs npm install
# 3. Runs npm run build
# 4. Deploys to production
# (Takes ~2-3 minutes)
```

You can monitor build progress in Vercel Dashboard → **Deployments**

## Step 8: Environment Configuration by Deployment

### Development (localhost)

```env
# web/frontend/.env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Staging (Vercel Preview)

```
Automatic when you create a pull request
Environment variables can differ from production
```

### Production (Vercel Main)

```
Triggered when you merge to main branch
Uses production environment variables
```

## Step 9: Monitoring & Logs

### View Build Logs

1. In Vercel Dashboard
2. Click **Deployments**
3. Click the deployment
4. Click **Build Logs**
5. Check for errors

### View Runtime Logs

1. Click **Logs** in top menu
2. Select **Function Logs** or **Edge Middleware**
3. Monitor real-time activity

### Performance Analytics

1. **Analytics** tab shows:
   - Page load times
   - Core Web Vitals
   - Traffic patterns
   - Error rates

## API Integration Best Practices

### 1. Use Environment Variables

✅ **DO:**
```javascript
const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
fetch(`${API_URL}/odds`);
```

❌ **DON'T:**
```javascript
fetch('http://localhost:8000/odds'); // Hardcoded!
```

### 2. Handle HTTPS Redirects

Backend must be accessible via HTTPS:

```javascript
// This will fail if backend is HTTP only
const API_URL = 'https://api.example.com'; // ✅ HTTPS only

// Browsers block mixed content (HTTPS page → HTTP API)
```

### 3. Configure CORS on Backend

Backend `web/backend/backend.env`:

```env
FRONTEND_ORIGINS=https://arbitrage-bot-xxx.vercel.app,https://arb-bot.com
```

### 4. Update API Calls for Production

The frontend automatically uses `NEXT_PUBLIC_API_BASE_URL`, so no code changes needed!

## Troubleshooting

### Build Fails

**Error**: `npm ERR! Missing script: "build"`

**Fix**: Ensure package.json has build script:
```json
"scripts": {
  "build": "next build"
}
```

### Dashboard Shows Blank Page

**Error**: Page loads but shows nothing

**Solutions**:
1. Clear browser cache (Ctrl+Shift+Del)
2. Check browser console for errors (F12)
3. Verify `next/image` imports if using images
4. Check build logs in Vercel

### API Connection Fails

**Error**: "Failed to load dashboard data" or WebSocket errors

**Solutions**:
1. Verify backend URL in `.env`
2. Check backend CORS headers
3. Ensure backend is HTTPS
4. Test with curl:
   ```bash
   curl https://your-backend-api.com/docs
   ```

### Environment Variables Not Applied

**Issue**: Changes to env vars not reflected

**Fix**:
1. Update in Vercel Dashboard
2. Click **Deployments**
3. Click the most recent deployment
4. Click **Redeploy** (if needed)
5. Or push a new commit to trigger rebuild

## Performance Optimization

### 1. Enable Caching

Vercel's `vercel.json` includes cache headers:

```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=3600, s-maxage=3600"
        }
      ]
    }
  ]
}
```

### 2. Image Optimization

Next.js automatically optimizes images. Use:

```jsx
import Image from 'next/image';

<Image src="/chart.png" width={800} height={600} />
```

### 3. Bundle Analysis

Check bundle size:

```bash
npm install --save-dev @next/bundle-analyzer

# Add to next.config.js:
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
})

module.exports = withBundleAnalyzer({
  // ... your config
})

# Run analysis:
ANALYZE=true npm run build
```

## Security Checklist

✅ **DO**:
- Use HTTPS (automatic with Vercel)
- Store secrets in environment variables
- Update Next.js regularly: `npm update next`
- Enable Vercel security headers (automatic)
- Use `NEXT_PUBLIC_` prefix only for public vars

❌ **DON'T**:
- Hardcode API keys or secrets
- Commit `.env.local` to git
- Use HTTP for production
- Expose sensitive environment variables in client code

## Updating Your Deployment

### Update Dependencies

```bash
cd web/frontend

# Check for updates
npm outdated

# Update all packages
npm update

# Or update specific packages
npm install next@latest

# Test locally
npm run dev

# Commit and push
git add package.json package-lock.json
git commit -m "Update dependencies"
git push
```

### Update Code

```bash
# Make changes
# Test locally with npm run dev
# Commit and push
git add .
git commit -m "Feature: add alert notifications"
git push origin main

# Vercel automatically rebuilds and deploys!
```

## Next Steps

1. ✅ Push code to GitHub
2. ✅ Import project into Vercel
3. ✅ Configure environment variables
4. ✅ Deploy
5. ✅ Verify HTTPS working
6. ✅ Test API connectivity
7. ✅ Share your live dashboard!

---

**Your Live Dashboard**: `https://arbitrage-bot-xxx.vercel.app`

**Vercel Dashboard**: `https://vercel.com/dashboard`

**Documentation**: 
- [Vercel Docs](https://vercel.com/docs)
- [Next.js Docs](https://nextjs.org/docs)
- [Environment Variables Guide](https://vercel.com/docs/concepts/projects/environment-variables)

---

**Status**: ✅ Ready for Vercel Deployment  
**Last Updated**: 2026-01-03  
**Version**: 0.3.0
