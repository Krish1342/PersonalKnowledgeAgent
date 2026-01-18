# 🚀 Deployment Guide - Second Brain

Complete step-by-step guide to deploy your Second Brain to production.

---

## 📋 Prerequisites

Before you start, you'll need:

1. **GitHub Account** - To store your code
2. **Clerk Account** - [Sign up free at dashboard.clerk.com](https://dashboard.clerk.com)
3. **Groq API Key** - [Get free key at console.groq.com](https://console.groq.com)
4. **Vercel Account** (for frontend) - [Sign up at vercel.com](https://vercel.com)
5. **Railway/Render Account** (for backend) - Choose one:
   - [Railway.app](https://railway.app) (easiest, $5/month free credit)
   - [Render.com](https://render.com) (free tier available)

---

## 🔐 Step 1: Set Up Clerk Authentication

1. **Create Clerk Application**

   ```
   → Go to https://dashboard.clerk.com
   → Click "Add application"
   → Name it "Second Brain"
   → Choose authentication methods (Email, Google, GitHub, etc.)
   → Click "Create application"
   ```

2. **Get Your API Keys**

   ```
   → In Clerk Dashboard, go to "API Keys"
   → Copy these values:
     - Publishable key (starts with pk_)
     - Secret key (starts with sk_)
   ```

3. **Configure URLs** (you'll update these after deployment)
   ```
   → Go to "Paths" in Clerk Dashboard
   → Sign-in URL: /sign-in
   → Sign-up URL: /sign-up
   → After sign-in: /query
   → After sign-up: /query
   ```

---

## 🎨 Step 2: Deploy Frontend (Vercel)

### A. Push Code to GitHub

```bash
cd PersonalKnowledgeAgent

# Initialize git if not already done
git init
git add .
git commit -m "Initial commit - Second Brain v2.0"

# Create GitHub repo and push
git remote add origin https://github.com/YOUR_USERNAME/second-brain.git
git branch -M main
git push -u origin main
```

### B. Deploy to Vercel

1. **Import Project**

   ```
   → Go to https://vercel.com
   → Click "Add New" → "Project"
   → Import your GitHub repository
   → Select "PersonalKnowledgeAgent"
   ```

2. **Configure Build Settings**

   ```
   Framework Preset: Next.js
   Root Directory: frontend
   Build Command: npm run build
   Output Directory: .next
   Install Command: npm install
   ```

3. **Add Environment Variables**

   ```
   Click "Environment Variables" and add:

   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = pk_test_... (from Clerk)
   CLERK_SECRET_KEY = sk_test_... (from Clerk)
   NEXT_PUBLIC_API_URL = https://your-backend-url.railway.app (add this later)
   ```

4. **Deploy**
   ```
   → Click "Deploy"
   → Wait 2-3 minutes
   → Your frontend URL: https://your-app.vercel.app
   ```

---

## 🔧 Step 3: Deploy Backend (Railway)

### Option A: Railway (Recommended)

1. **Create New Project**

   ```
   → Go to https://railway.app
   → Click "New Project"
   → Choose "Deploy from GitHub repo"
   → Select your repository
   → Select "backend" folder as root
   ```

2. **Configure Service**

   ```
   → Click on your service
   → Go to "Settings"
   → Set Root Directory: /backend
   → Set Start Command: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT
   ```

3. **Add Environment Variables**

   ```
   → Go to "Variables" tab
   → Add these variables:

   GROQ_API_KEY = gsk_... (from console.groq.com)
   CLERK_PUBLISHABLE_KEY = pk_test_... (from Clerk)
   CLERK_SECRET_KEY = sk_test_... (from Clerk)
   CORS_ORIGINS = https://your-app.vercel.app
   ENVIRONMENT = production
   PORT = 8000
   ```

4. **Add Persistent Storage (Important!)**

   ```
   → Go to "Volumes" tab
   → Click "New Volume"
   → Mount Path: /app/data
   → Size: 1GB (free tier)
   → This persists your database and vector store
   ```

5. **Deploy**

   ```
   → Railway will auto-deploy
   → Get your backend URL: https://your-app.railway.app
   → Copy this URL!
   ```

6. **Update Frontend Environment**
   ```
   → Go back to Vercel
   → Settings → Environment Variables
   → Update NEXT_PUBLIC_API_URL = https://your-app.railway.app
   → Redeploy your frontend
   ```

### Option B: Render

1. **Create Web Service**

   ```
   → Go to https://render.com
   → Click "New" → "Web Service"
   → Connect your GitHub repo
   → Name: second-brain-backend
   → Root Directory: backend
   → Runtime: Python 3.11
   → Build Command: pip install -r requirements.txt
   → Start Command: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT
   ```

2. **Environment Variables**

   ```
   Add the same variables as Railway (above)
   ```

3. **Add Disk Storage**

   ```
   → Go to "Disks"
   → Add Disk
   → Mount Path: /app/data
   → Size: 1GB
   ```

4. **Deploy and Get URL**
   ```
   → Click "Create Web Service"
   → Wait for deployment
   → Get URL: https://your-app.onrender.com
   → Update Vercel frontend with this URL
   ```

---

## 🔄 Step 4: Update Clerk with Production URLs

```
→ Go to Clerk Dashboard
→ Click your application
→ Go to "Domains"
→ Add production domain: your-app.vercel.app
→ Go to "Paths" and verify redirect URLs
→ Save changes
```

---

## ✅ Step 5: Test Your Deployment

1. **Test Frontend**

   ```
   → Visit https://your-app.vercel.app
   → Should see homepage
   → Click "Sign In" - Clerk modal should appear
   ```

2. **Test Authentication**

   ```
   → Sign up with email or OAuth
   → Should redirect to /query
   → Check user button in top right
   ```

3. **Test Backend Connection**

   ```
   → Try ingesting content in /ingest page
   → Try querying in /query page
   → Check /memory page for stored data
   ```

4. **Check Backend Health**
   ```
   Visit: https://your-backend-url.railway.app/health
   Should return:
   {
     "status": "healthy",
     "auth_enabled": true,
     "environment": "production"
   }
   ```

---

## 🛠️ Troubleshooting

### Frontend Issues

**"Module not found" errors**

```bash
cd frontend
npm install
git add .
git commit -m "Update dependencies"
git push
# Vercel will auto-redeploy
```

**Clerk not working**

- Verify all Clerk env vars are set in Vercel
- Check Clerk Dashboard → Domains includes your Vercel URL
- Make sure middleware.ts has correct public routes

### Backend Issues

**502 Bad Gateway**

- Check Railway/Render logs
- Verify start command is correct
- Check if GROQ_API_KEY is set

**CORS errors**

- Update CORS_ORIGINS in backend env vars
- Include your Vercel URL
- Redeploy backend

**Database/Storage errors**

- Verify volume/disk is mounted at /app/data
- Check logs for permission errors
- Make sure volume has enough space

### Authentication Issues

**Infinite redirect loop**

- Check Clerk URLs are configured correctly
- Verify middleware.ts publicRoutes list
- Clear browser cookies and try again

**401 Unauthorized on API calls**

- Check backend CLERK_SECRET_KEY is set
- Verify frontend is sending auth token
- Check backend logs for JWT errors

---

## 📊 Monitoring Your Deployment

### Railway Dashboard

```
→ View real-time logs
→ Monitor CPU/Memory usage
→ Check storage usage
→ View request metrics
```

### Vercel Analytics

```
→ Go to your project → Analytics
→ See page views, performance
→ Monitor build times
```

### Clerk Dashboard

```
→ See active users
→ Monitor authentication events
→ Check failed login attempts
```

---

## 💰 Cost Estimate

**Free Tier (Suitable for personal use):**

- Vercel: Free (Hobby plan)
- Railway: $5/month credit (enough for light use)
- Render: Free tier (sleeps after inactivity)
- Clerk: Free up to 10,000 MAUs
- Groq: Free tier (generous limits)

**Total: $0-5/month for personal use**

**Paid Tier (For production/team use):**

- Vercel Pro: $20/month
- Railway: ~$15-30/month (usage-based)
- Clerk Pro: $25/month
- Groq: Pay-as-you-go

**Total: ~$60-75/month**

---

## 🔒 Security Checklist

- [ ] All API keys stored in environment variables (not in code)
- [ ] CORS_ORIGINS restricted to your frontend domain
- [ ] Clerk authentication enabled on all protected routes
- [ ] HTTPS enabled (automatic on Vercel/Railway/Render)
- [ ] Database backups configured
- [ ] Regular dependency updates scheduled

---

## 📚 Additional Resources

- [Next.js Deployment Docs](https://nextjs.org/docs/deployment)
- [Clerk Deployment Guide](https://clerk.com/docs/deployments/overview)
- [Railway Docs](https://docs.railway.app)
- [Render Docs](https://render.com/docs)

---

## 🆘 Need Help?

If you encounter issues:

1. Check the troubleshooting section above
2. Review deployment logs in Railway/Render/Vercel
3. Verify all environment variables are set correctly
4. Check Clerk Dashboard for auth issues

---

**🎉 Congratulations! Your Second Brain is now live in production!**

Access your app at: `https://your-app.vercel.app`
