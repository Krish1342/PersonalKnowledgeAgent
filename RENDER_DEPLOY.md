# 🚀 Deploy Backend to Render.com

Complete step-by-step guide to deploy the Second Brain backend to Render.

---

## 📋 Prerequisites

- GitHub account with your code pushed
- Render.com account (free) - [Sign up here](https://render.com)
- Groq API key - [Get from console.groq.com](https://console.groq.com)
- Clerk keys (optional) - [Get from dashboard.clerk.com](https://dashboard.clerk.com)

---

## 🔧 Step 1: Prepare Your Repository

Make sure your code is pushed to GitHub:

```bash
cd PersonalKnowledgeAgent
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

---

## 🌐 Step 2: Create Web Service on Render

1. **Go to Render Dashboard**

   ```
   → Visit https://dashboard.render.com
   → Click "New +" button (top right)
   → Select "Web Service"
   ```

2. **Connect GitHub Repository**

   ```
   → Click "Connect account" if first time
   → Authorize Render to access your repos
   → Find and select "PersonalKnowledgeAgent" repo
   → Click "Connect"
   ```

3. **Configure Web Service**

   Fill in these settings:

   | Setting            | Value                                                                                                 |
   | ------------------ | ----------------------------------------------------------------------------------------------------- |
   | **Name**           | `second-brain-backend`                                                                                |
   | **Region**         | `Oregon (US West)` or closest to you                                                                  |
   | **Branch**         | `main`                                                                                                |
   | **Root Directory** | `backend`                                                                                             |
   | **Runtime**        | `Python 3`                                                                                            |
   | **Build Command**  | `pip install -r requirements.txt`                                                                     |
   | **Start Command**  | `gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT` |
   | **Instance Type**  | `Free` (or `Starter $7/mo` for better performance)                                                    |

---

## 🔐 Step 3: Add Environment Variables

Scroll down to "Environment Variables" section and add these:

### Required Variables

```bash
# Groq API for LLM (REQUIRED)
GROQ_API_KEY=gsk_your_actual_groq_api_key_here

# Environment
ENVIRONMENT=production
```

### Optional - Clerk Authentication

```bash
# Add these if you want protected APIs
CLERK_PUBLISHABLE_KEY=pk_live_your_key_here
CLERK_SECRET_KEY=sk_live_your_key_here
```

### CORS Configuration

```bash
# Add your frontend URL (update after frontend deployment)
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000
```

### Optional - Custom Database Paths

```bash
# Leave these as default or customize
VECTOR_DB_PATH=/opt/render/project/src/data/vector_store
SQLITE_DB_PATH=/opt/render/project/src/data/episodic.db
MODEL_NAME=all-MiniLM-L6-v2
GROQ_MODEL_NAME=llama-3.1-8b-instant
```

**Click "Add" for each variable**

---

## 💾 Step 4: Add Persistent Disk (CRITICAL!)

This step is crucial to prevent losing your data on every deploy.

1. **Scroll to "Disks" section**

   ```
   → Click "Add Disk"
   ```

2. **Configure Disk**

   ```
   Name: backend-data
   Mount Path: /opt/render/project/src/data
   Size: 1 GB (Free tier)
   ```

3. **Click "Add Disk"**

---

## 🚀 Step 5: Deploy

1. **Review Settings**
   - Double-check all environment variables
   - Verify disk is added
   - Ensure build and start commands are correct

2. **Click "Create Web Service"**

3. **Wait for Deployment** (5-10 minutes first time)

   ```
   → Render will:
     1. Clone your repository
     2. Install Python dependencies
     3. Start the service
   ```

4. **Watch the Logs**
   ```
   → You'll see live build output
   → Look for "Application startup complete"
   → Any errors will appear here
   ```

---

## ✅ Step 6: Verify Deployment

Once deployed, you'll see "Live" status with a green checkmark.

### Get Your Backend URL

```
Your URL: https://second-brain-backend-xxxx.onrender.com
(Copy this URL - you'll need it!)
```

### Test Endpoints

1. **Health Check**

   ```
   Visit: https://your-app.onrender.com/health

   Should return:
   {
     "status": "healthy",
     "vector_db_path": "/opt/render/project/src/data/vector_store",
     "sqlite_db_path": "/opt/render/project/src/data/episodic.db",
     "embedding_model": "all-MiniLM-L6-v2",
     "llm_configured": true,
     "auth_enabled": false,
     "environment": "production"
   }
   ```

2. **API Documentation**

   ```
   Visit: https://your-app.onrender.com/docs

   Should show Swagger UI with all API endpoints
   ```

3. **Test Simple Endpoint**

   ```bash
   curl https://your-app.onrender.com/

   Should return:
   {
     "status": "healthy",
     "service": "Personal Knowledge Base Agent",
     "version": "2.0.0",
     "auth_enabled": false,
     "environment": "production"
   }
   ```

---

## 🔗 Step 7: Connect to Frontend

Now update your frontend (Vercel) with the backend URL:

1. **Go to Vercel Dashboard**

   ```
   → Select your frontend project
   → Go to "Settings" → "Environment Variables"
   ```

2. **Update/Add Variable**

   ```
   Name: NEXT_PUBLIC_API_URL
   Value: https://second-brain-backend-xxxx.onrender.com
   ```

3. **Redeploy Frontend**
   ```
   → Go to "Deployments" tab
   → Click "..." menu on latest deployment
   → Click "Redeploy"
   ```

---

## 🔄 Step 8: Update CORS (If you already deployed frontend)

1. **Go back to Render dashboard**

   ```
   → Click on your backend service
   → Go to "Environment" tab
   ```

2. **Update CORS_ORIGINS**

   ```
   CORS_ORIGINS=https://your-actual-frontend.vercel.app
   ```

3. **Service will auto-redeploy**

---

## ⚠️ Important: Free Tier Limitations

### Render Free Tier:

**Pros:**

- ✅ Free forever
- ✅ 750 hours/month (enough for 1 service)
- ✅ Automatic HTTPS
- ✅ Persistent disk storage

**Cons:**

- ⚠️ **Sleeps after 15 minutes of inactivity**
- ⚠️ Takes ~30 seconds to wake up (cold start)
- ⚠️ Limited to 512MB RAM
- ⚠️ Shared CPU

### Solutions for Cold Starts:

**Option 1: Keep-Alive Service (Free)**

- Use [Cron-job.org](https://cron-job.org) to ping your backend every 14 minutes
- Endpoint to ping: `https://your-app.onrender.com/health`

**Option 2: Upgrade to Starter ($7/month)**

- No sleep/cold starts
- More RAM (512MB → 2GB)
- Better performance

---

## 📊 Monitoring Your Backend

### View Logs

```
→ Render Dashboard → Your Service
→ Click "Logs" tab
→ See real-time application logs
→ Filter by log level (Info, Error, etc.)
```

### Check Metrics

```
→ Click "Metrics" tab
→ View CPU usage
→ View Memory usage
→ View HTTP requests
→ View Response times
```

### Check Disk Usage

```
→ Go to "Disks" tab
→ See storage usage
→ Monitor free space
```

---

## 🛠️ Troubleshooting

### Build Fails

**Error: "pip install failed"**

```bash
# Fix in requirements.txt
# Make sure all package versions are compatible
# Check build logs for specific package errors
```

**Error: "Module not found"**

```bash
# Missing package in requirements.txt
# Add it and redeploy
```

### Service Won't Start

**Error: "Application failed to start"**

```
→ Check start command is correct
→ Verify gunicorn is in requirements.txt
→ Check logs for Python errors
```

**Error: "Port already in use"**

```
→ Make sure start command uses $PORT
→ Don't hardcode port 8000
→ Render provides PORT env var automatically
```

### Database/Storage Issues

**Error: "Permission denied writing to /data"**

```
→ Check disk mount path is correct: /opt/render/project/src/data
→ Don't use /app/data (that's for Docker)
```

**Data Lost After Deploy**

```
→ Make sure disk is added and mounted
→ Check disk mount path matches your code
→ Verify data is being written to mounted path
```

### CORS Errors

**Error: "CORS policy blocked"**

```
→ Add your frontend URL to CORS_ORIGINS
→ Include protocol (https://)
→ Redeploy after changing
```

### Slow Responses / Timeouts

**Cold Start (Free Tier)**

```
→ Service was asleep
→ First request takes ~30s
→ Use keep-alive service
→ Or upgrade to Starter plan
```

**Slow LLM Responses**

```
→ Normal - Groq API can take 2-10s
→ Check Groq API status
→ Verify API key is working
```

---

## 🔄 Updating Your Backend

### Auto-Deploy from GitHub

Render automatically deploys when you push to main:

```bash
# Make changes locally
git add .
git commit -m "Update backend"
git push origin main

# Render will automatically:
# 1. Detect the push
# 2. Start a new build
# 3. Deploy if successful
```

### Manual Deploy

```
→ Render Dashboard → Your Service
→ Click "Manual Deploy" → "Deploy latest commit"
```

### Rollback

```
→ Go to "Events" tab
→ Find previous successful deploy
→ Click "..." → "Rollback to this version"
```

---

## 💰 Cost Breakdown

### Free Tier

- **Cost:** $0/month
- **Includes:** 750 hours, 512MB RAM, 1GB disk
- **Best for:** Personal projects, testing

### Starter Tier

- **Cost:** $7/month
- **Includes:** No sleep, 2GB RAM, better CPU
- **Best for:** Production apps, always-on services

---

## ✨ Next Steps

After backend is deployed:

1. ✅ Save your backend URL
2. ✅ Update frontend with backend URL
3. ✅ Test all API endpoints
4. ✅ Set up keep-alive (if using free tier)
5. ✅ Configure monitoring/alerts
6. ✅ Set up regular backups (export data weekly)

---

## 🆘 Need Help?

**Render Support:**

- [Render Docs](https://render.com/docs)
- [Community Forum](https://community.render.com)
- [Status Page](https://status.render.com)

**Check Issues:**

1. Review deployment logs
2. Test endpoints manually
3. Verify environment variables
4. Check disk is mounted
5. Review CORS settings

---

**🎉 Your backend is now live on Render!**

Backend URL: `https://second-brain-backend-xxxx.onrender.com`
API Docs: `https://second-brain-backend-xxxx.onrender.com/docs`
