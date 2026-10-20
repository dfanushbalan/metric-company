/**
 * Frontend Deployment Configuration
 * 
 * 1. Unified Deployment (e.g., Render, Railway, Docker, or local Flask server):
 *    Leave BACKEND_API_URL empty (""). The app will automatically connect
 *    to the current host/origin.
 * 
 * 2. Separated Deployment (e.g., Frontend on Vercel / Netlify & Backend on Render / Railway):
 *    Set your live backend API URL below:
 *    Example: window.BACKEND_API_URL = "https://appointment-booker-api.onrender.com";
 */
window.BACKEND_API_URL = "";
