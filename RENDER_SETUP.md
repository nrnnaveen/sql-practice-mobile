# Render.com Deployment Setup Guide

This guide walks you through deploying your SQL Practice Mobile app to Render.com while keeping Railway running simultaneously.

---

## Prerequisites

- GitHub repository: `nrnnaveen/sql-practice-mobile`
- Railway already running (keep it as-is)

---

## Step 1: Create a Render Account

1. Go to [https://render.com](https://render.com)
2. Click **"Get Started for Free"**
3. Sign up with your **GitHub account** (recommended for easy repo access)
4. Authorize Render to access your GitHub repositories

---

## Step 2: Connect Your GitHub Repository

1. In the Render dashboard, click **"New +"**
2. Select **"Web Service"**
3. Click **"Connect account"** next to GitHub (if not already connected)
4. Search for and select: `nrnnaveen/sql-practice-mobile`
5. Click **"Connect"**

---

## Step 3: Configure the Web Service

Fill in the service settings:

| Setting | Value |
|---------|-------|
| **Name** | `sql-practice-mobile` |
| **Region** | Choose closest to your users |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |
| **Plan** | `Free` |

Click **"Create Web Service"** to proceed.

---

## Step 4: Get Your Deploy Keys

Once the service is created:

1. Go to your service in the Render dashboard
2. Click **"Settings"** in the left sidebar
3. Scroll down to **"Deploy Hook"**
4. You will see a URL like:
   ```
   https://api.render.com/deploy/srv-XXXXXXXXXXXX?key=YYYYYYYYYYYY
   ```
5. Extract the two values:
   - **Service ID**: `srv-XXXXXXXXXXXX` (everything after `/deploy/` and before `?key=`)
   - **Deploy Key**: `YYYYYYYYYYYY` (everything after `key=`)

---

## Step 5: Add GitHub Secrets

1. Go to your GitHub repository: `https://github.com/nrnnaveen/sql-practice-mobile`
2. Click **"Settings"** → **"Secrets and variables"** → **"Actions"**
3. Click **"New repository secret"** and add the following two secrets:

**Secret 1:**
- **Name**: `RENDER_SERVICE_ID`
- **Value**: `srv-XXXXXXXXXXXX` (your Service ID from Step 4)

**Secret 2:**
- **Name**: `RENDER_DEPLOY_KEY`
- **Value**: `YYYYYYYYYYYY` (your Deploy Key from Step 4)

---

## Step 6: Add Environment Variables to Render

1. In the Render dashboard, go to your service
2. Click **"Environment"** in the left sidebar
3. Add all variables from your `.env` file. Common variables:

| Variable | Value |
|----------|-------|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | your secret key |
| `DATABASE_URL` | your database connection URL |
| `MYSQL_HOST` | your MySQL host (if applicable) |
| `MYSQL_USER` | your MySQL username |
| `MYSQL_PASSWORD` | your MySQL password |
| `MYSQL_DATABASE` | your database name |

> **Tip**: Check your `.env.example` file in the repo for the full list of required variables.

4. Click **"Save Changes"**

---

## Step 7: Test the Deployment

1. Once the service is deployed, Render will give you a URL:
   ```
   https://sql-practice-mobile.onrender.com
   ```
2. Open the URL in your browser and test the app
3. Check the **"Logs"** tab in Render if anything goes wrong

---

## Step 8: Verify Auto-Deploy Works

1. Make a small change to any file in your repo
2. Commit and push to `main`:
   ```bash
   git add .
   git commit -m "Test Render auto-deploy"
   git push origin main
   ```
3. Go to **GitHub Actions** tab in your repo to see the workflow running
4. Check the Render dashboard to see the new deployment triggered

---

## Running Both Railway and Render Simultaneously

Both services can run at the same time with no conflicts:

| Service | Status | URL | Notes |
|---------|--------|-----|-------|
| **Railway** | ✅ Running | Your Railway URL | 26 days remaining |
| **Render** | ✅ Running | `https://sql-practice-mobile.onrender.com` | Free forever |

**No changes needed to Railway** — they are completely independent deployments.

---

## Troubleshooting

### Deployment fails with `gunicorn: command not found`
- Make sure `gunicorn>=21.0` is in your `requirements.txt` (already included ✅)

### App crashes on startup
- Check the **Logs** tab in Render dashboard
- Ensure all environment variables from Step 6 are set correctly

### GitHub Actions workflow not triggering
- Confirm secrets `RENDER_SERVICE_ID` and `RENDER_DEPLOY_KEY` are set (Step 5)
- Ensure you are pushing to the `main` branch

### Free tier limitations
- Render free tier spins down after 15 minutes of inactivity
- First request after spin-down may take ~30 seconds to respond
- Upgrade to a paid plan to avoid spin-downs

---

## Additional Resources

- [Render Documentation](https://render.com/docs)
- [Render Python/Flask Guide](https://render.com/docs/deploy-flask)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
