# 🚀 Complete Deployment Guide - Second Brain

Deploy your Personal Knowledge Base Agent with **Vercel** (Frontend) and **Render** (Backend).

---

## 📋 Prerequisites

Before starting, ensure you have:

1. **GitHub Account** - Push your code to a GitHub repository
2. **Vercel Account** - Sign up at [vercel.com](https://vercel.com) (free tier available)
3. **Render Account** - Sign up at [render.com](https://render.com) (free tier available)
4. **Clerk Account** - Sign up at [clerk.com](https://clerk.com) for authentication
5. **Groq API Key** - Get from [console.groq.com](https://console.groq.com)

---

## 📦 Step 1: Prepare Your Code

### 1.1 Create a GitHub Repository

```powershell
# Navigate to project root
cd c:\Users\drket\OneDrive\Desktop\Codes\PersonalKnowledgeAgent

# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "Prepare for deployment"

# Add remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/PersonalKnowledgeAgent.git

# Push to GitHub
git push -u origin main
```

### 1.2 Verify Project Structure

Your project should have this structure:
```
PersonalKnowledgeAgent/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── memory/
│   │   ├── utils/
│   │   ├── config.py
│   │   └── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── middleware.ts
│   ├── package.json
│   ├── next.config.js
│   └── .env.example
├── render.yaml
└── README.md
```

---

## 🖥️ Step 2: Deploy Backend to Render

### 2.1 Create a New Web Service

1. Go to [render.com/dashboard](https://render.com/dashboard)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select your `PersonalKnowledgeAgent` repository

### 2.2 Configure Build Settings

| Setting | Value |
|---------|-------|
| **Name** | `second-brain-api` |
| **Region** | Oregon (US West) or closest to you |
| **Branch** | `main` |
| **Root Directory** | `backend` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free |

### 2.3 Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"** and add:

| Key | Value |
|-----|-------|
| `GROQ_API_KEY` | `gsk_your_groq_api_key_here` |
| `CLERK_PUBLISHABLE_KEY` | `pk_test_your_clerk_key` |
| `CLERK_SECRET_KEY` | `sk_test_your_clerk_secret` |
| `CORS_ORIGINS` | `https://your-app.vercel.app` (update after frontend deploy) |
| `ENVIRONMENT` | `production` |
| `PYTHON_VERSION` | `3.11.0` |

### 2.4 Deploy

1. Click **"Create Web Service"**
2. Wait for the build to complete (3-5 minutes)
3. Copy your backend URL: `https://second-brain-api.onrender.com`

### 2.5 Test Backend Health

Open in browser: `https://your-backend-url.onrender.com/health`

You should see:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "auth_enabled": true,
  "environment": "production"
}
```

---

## 🌐 Step 3: Deploy Frontend to Vercel

### 3.1 Import Project

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Click **"Add New..."** → **"Project"**
3. Click **"Import"** next to your GitHub repository

### 3.2 Configure Project Settings

| Setting | Value |
|---------|-------|
| **Project Name** | `second-brain` (or your choice) |
| **Framework Preset** | `Next.js` (auto-detected) |
| **Root Directory** | `frontend` ← **IMPORTANT!** Click "Edit" and set this |
| **Build Command** | `next build` (default) |
| **Output Directory** | `.next` (default) |

### 3.3 Add Environment Variables

In the **Environment Variables** section, add:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://second-brain-api.onrender.com` (your Render URL) |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `pk_test_your_clerk_key` |
| `CLERK_SECRET_KEY` | `sk_test_your_clerk_secret` |
| `NEXT_PUBLIC_CLERK_SIGN_IN_URL` | `/sign-in` |
| `NEXT_PUBLIC_CLERK_SIGN_UP_URL` | `/sign-up` |
| `NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL` | `/` |
| `NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL` | `/` |

### 3.4 Deploy

1. Click **"Deploy"**
2. Wait for the build (2-3 minutes)
3. Copy your frontend URL: `https://second-brain.vercel.app`

---

## 🔄 Step 4: Update CORS Settings

After frontend deployment, update the backend CORS:

1. Go to Render Dashboard → Your Web Service → **Environment**
2. Update `CORS_ORIGINS`:
   ```
   https://second-brain.vercel.app,https://your-custom-domain.com
   ```
3. Click **"Save Changes"** - service will auto-redeploy

---

## 🔐 Step 5: Configure Clerk Authentication

### 5.1 Update Clerk Dashboard

1. Go to [dashboard.clerk.com](https://dashboard.clerk.com)
2. Select your application
3. Go to **"Domains"** → **"Production"**
4. Add your Vercel domain: `second-brain.vercel.app`

### 5.2 Update Redirect URLs

In Clerk Dashboard → **"Paths"**:
- **Sign-in URL**: `/sign-in`
- **Sign-up URL**: `/sign-up`
- **After sign-in URL**: `/`
- **After sign-up URL**: `/`

### 5.3 Production Keys (Optional)

For production, switch from test to live keys:
1. Toggle to **"Production"** in Clerk Dashboard
2. Copy new `CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY`
3. Update both Vercel and Render environment variables

---

## ✅ Step 6: Verify Deployment

### 6.1 Test Frontend
1. Open your Vercel URL
2. You should see the login page
3. Sign up/Sign in with Clerk

### 6.2 Test Backend Connection
1. After login, navigate to **"Ingest"**
2. Add some test content
3. Navigate to **"Query"** and search
4. Check **"Settings"** to see storage stats

### 6.3 Test API Directly
```bash
curl https://your-backend.onrender.com/health
curl https://your-backend.onrender.com/api/v2/memory/stats
```

---

## 🛠️ Troubleshooting

### Frontend Build Fails

**Error: "Type 'Set<unknown>' can only be iterated..."**
- Already fixed in the codebase
- Make sure you pushed the latest changes

**Error: "Module not found: @clerk/themes"**
- Already fixed - push latest changes

### Backend Issues

**CORS Errors**
- Ensure `CORS_ORIGINS` includes your exact Vercel URL
- Don't include trailing slash

**Database Errors on Render Free Tier**
- Free tier has ephemeral storage - data resets on redeploy
- For persistent data, use Render's paid tier or external database

### Clerk Authentication

**"Clerk: Invalid API key"**
- Verify keys match between Clerk Dashboard and env vars
- Check you're using the right environment (development/production)

---

## 📊 Environment Variables Summary

### Backend (Render)
```env
GROQ_API_KEY=gsk_your_key_here
CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx
CORS_ORIGINS=https://your-app.vercel.app
ENVIRONMENT=production
PYTHON_VERSION=3.11.0
```

### Frontend (Vercel)
```env
NEXT_PUBLIC_API_URL=https://your-api.onrender.com
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/
```

---

## 🎉 You're Done!

Your Second Brain is now live at:
- **Frontend**: `https://your-app.vercel.app`
- **Backend API**: `https://your-api.onrender.com`

### Next Steps
1. Set up a custom domain (optional)
2. Enable Clerk production mode for better security
3. Consider Render paid tier for persistent storage
4. Monitor logs in Render and Vercel dashboards

---

## 📞 Need Help?

- **Vercel Docs**: [vercel.com/docs](https://vercel.com/docs)
- **Render Docs**: [render.com/docs](https://render.com/docs)
- **Clerk Docs**: [clerk.com/docs](https://clerk.com/docs)
- **Next.js Docs**: [nextjs.org/docs](https://nextjs.org/docs)
