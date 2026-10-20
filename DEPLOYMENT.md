# 🚀 Deployment Guide: Frontend & Backend

This guide provides step-by-step instructions for deploying both the **Frontend** and **Backend** of the **Appointment Slot Booker** application.

---

## 📌 Architecture Choices

You can deploy this project in one of two ways:

| Deployment Model | Best For | Complexity | CORS Setup |
|---|---|---|---|
| **Option 1: Unified Full-Stack (Recommended)** | Render, Railway, Fly.io, or VPS | 🟢 Easiest | None required (Same origin) |
| **Option 2: Separated Deployment** | Frontend on Vercel/Netlify + Backend on Render/Railway | 🟡 Intermediate | Automatic via `config.js` or UI settings |
| **Option 3: Docker Container** | Any Linux VPS (DigitalOcean, AWS EC2, Linode) | 🟢 1 Command | Self-contained |

---

## 🌟 Option 1: Unified Deployment on Render (Recommended & Free)

In this approach, the Flask backend serves both the REST API and the frontend static files (`index.html`, `style.css`, `app.js`) on a single live URL with zero CORS configuration.

### Prerequisites
1. A free account on [GitHub](https://github.com)
2. A free account on [Render.com](https://render.com)

### Steps

#### 1. Push Your Code to GitHub
If you haven't already pushed your code to GitHub:
```bash
git init
git add .
git commit -m "Prepare deployment for Appointment Slot Booker"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

#### 2. Create Web Service on Render
1. Log into your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** and select **Web Service**.
3. Choose **Build and deploy from a Git repository** and select your repository.
4. Configure the settings:
   - **Name**: `appointment-slot-booker` (or your preferred name)
   - **Region**: Choose the closest region to you (e.g., Singapore, Frankfurt, Oregon)
   - **Branch**: `main`
   - **Root Directory**: Leave blank (root)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan Type**: `Free`

#### 3. Configure Environment Variables (Optional)
In the **Environment Variables** section on Render, you can configure:
- `DEBUG`: `False`
- `SECRET_KEY`: Enter a random secret string (e.g. `prod-secret-9843849348`)
- `AUTO_FALLBACK_SQLITE`: `True` *(Allows immediate operation without an external database)*

*(Optional Database)*:
If you want persistent storage via a free managed database:
- Click **New +** -> **PostgreSQL** on Render.
- Copy the **Internal Database URL**.
- In your Web Service settings, add an environment variable `DATABASE_URL` with that value. The backend will automatically connect to it and initialize the schema.

#### 4. Deploy!
- Click **Create Web Service**.
- Render will install dependencies and launch your application.
- Once deployed, open your Render URL (e.g., `https://appointment-slot-booker.onrender.com`).
- Both your frontend and backend will be live and fully functional!

---

## ⚡ Option 2: Separated Deployment (Vercel Frontend + Render Backend)

### Part A: Deploy Backend on Render or Railway

1. Follow the steps in **Option 1** above to deploy the backend on Render.
2. Note your backend URL (e.g., `https://appointment-backend.onrender.com`).
3. Verify that `https://appointment-backend.onrender.com/api/health` returns:
   ```json
   { "status": "healthy", "database": "connected" }
   ```

### Part B: Deploy Frontend on Vercel

1. Log into [Vercel.com](https://vercel.com).
2. Click **Add New...** -> **Project**.
3. Select your GitHub repository.
4. In **Project Settings**:
   - **Root Directory**: Click edit and select `frontend` (or leave as root; `vercel.json` will route to `frontend`).
   - **Framework Preset**: `Other`
   - **Build & Output Settings**: Leave defaults.
5. Click **Deploy**.

### Part C: Link Frontend to Backend

You have two convenient methods to link the Vercel frontend to your Render backend:

#### Method A: Via `frontend/config.js` (Permanent)
Edit `frontend/config.js`:
```javascript
window.BACKEND_API_URL = "https://appointment-backend.onrender.com";
```
Commit and push to GitHub. Vercel will automatically redeploy with the backend connected.

#### Method B: Live via UI (No redeployment needed!)
1. Open your deployed Vercel website.
2. Click the **⚙️ API Server** button in the top right header.
3. Paste your backend URL (`https://appointment-backend.onrender.com`).
4. Click **Test Connection**, then **Save & Connect**.
5. The application will instantly connect and load your slots and bookings!

---

## 🐳 Option 3: Docker & Docker Compose (Self-Hosted VPS / Cloud)

If you have a Linux VPS (DigitalOcean Droplet, AWS EC2, Linode, Hetzner, etc.):

### 1. Run with Docker Compose (Flask + MySQL 8.0)
```bash
# Clone your repo onto the server
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>

# Launch both Flask web app and MySQL container
docker compose up -d --build
```
Your application will be live at `http://<your-server-ip>:5000` with automated MySQL persistence.

### 2. Run with Standalone Docker
```bash
docker build -t appointment-booker .
docker run -d -p 5000:5000 -e AUTO_FALLBACK_SQLITE=True appointment-booker
```

---

## 🐍 Option 4: PythonAnywhere Deployment

1. Register at [PythonAnywhere.com](https://www.pythonanywhere.com).
2. Open a **Bash Console** and clone your repository:
   ```bash
   git clone https://github.com/<your-username>/<your-repo-name>.git
   cd <your-repo-name>
   pip install -r requirements.txt --user
   ```
3. Go to the **Web** tab and click **Add a new web app** (choose Manual Configuration, Python 3.10).
4. In the **WSGI configuration file** (`/var/www/<username>_pythonanywhere_com_wsgi.py`), replace contents with:
   ```python
   import sys
   import os

   path = '/home/<username>/<your-repo-name>'
   if path not in sys.path:
       sys.path.append(path)

   backend_path = os.path.join(path, 'backend')
   if backend_path not in sys.path:
       sys.path.append(backend_path)

   from app import app as application
   ```
5. Click **Reload <username>.pythonanywhere.com** and visit your site!

---

## 🩺 Production Health Check & Verification

Once deployed, verify your setup:

1. **System Health Check**:
   Visit `https://<your-domain>/api/health`
   Expected response:
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "slots_count": 8,
     "bookings_count": 1
   }
   ```

2. **Frontend UI Status**:
   The status indicator in the top right header should show a pulsing green dot and **"System Online"**.

3. **Concurrency Test**:
   Click on the **"⚡ Concurrency Test"** tab in the UI:
   - Select an available slot.
   - Choose 5 or 10 simulated users.
   - Click **"Launch Concurrency Test"**.
   - Verify that exactly 1 booking succeeds (`201 Created`) and all others receive `409 Conflict`.
