# Deployment Guide for AI Service on Render.com

## Quick Deploy Steps

### 1. Create GitHub Repository

```bash
# Navigate to AI service directory
cd F:\vercal\Suraksha-Yatra-SIH25\ai-service

# Initialize git repository
git init
git add .
git commit -m "Initial AI service setup for Suraksha Yatra"

# Add GitHub remote (replace with your username)
git remote add origin https://github.com/YOUR_USERNAME/suraksha-ai-service.git
git branch -M main
git push -u origin main
```

### 2. Render.com Setup

1. **Sign up/Login to Render**: Go to [render.com](https://render.com)

2. **Create New Web Service**:
   - Click "New" → "Web Service"
   - Connect your GitHub account
   - Select the `suraksha-ai-service` repository
   - Configure settings:

3. **Render Configuration**:
   ```
   Name: suraksha-ai-service
   Region: Choose closest to your users
   Branch: main
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python app.py
   ```

4. **Environment Variables** (Add in Render dashboard):
   ```
   AI_HOST=0.0.0.0
   AI_PORT=5000
   DEBUG=false
   MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/suraksha
   MONGODB_DATABASE=suraksha
   PYTHON_VERSION=3.9.16
   ```

### 3. Production Environment Variables

```bash
# Example production .env (DON'T commit this file)
AI_HOST=0.0.0.0
AI_PORT=5000
DEBUG=false
MONGODB_URL=mongodb+srv://suraksha:yourpassword@cluster0.xxxxx.mongodb.net/suraksha?retryWrites=true&w=majority
MONGODB_DATABASE=suraksha
```

### 4. Deploy Commands

```bash
# Make sure you're in the AI service directory
cd F:\vercal\Suraksha-Yatra-SIH25\ai-service

# Stage all files
git add .

# Commit changes
git commit -m "Ready for production deployment"

# Push to GitHub (triggers Render deployment)
git push origin main
```

### 5. Verify Deployment

1. **Check Render Logs**: Monitor the deployment in Render dashboard
2. **Test Health Endpoint**: Visit `https://your-ai-service.onrender.com/api/health`
3. **Test AI APIs**: Use Postman or curl to test ML endpoints

### 6. Update Backend Configuration

After AI service is deployed, update your backend to use the new AI service URL:

```bash
# In your backend .env or Render environment variables
AI_SERVICE_URL=https://your-ai-service.onrender.com
```

### 7. Common Issues & Solutions

**Python Version Issues**:
- Set `PYTHON_VERSION=3.9.16` in Render environment variables
- Ensure requirements.txt has compatible versions

**Memory Issues**:
- ML models can be memory intensive
- Consider upgrading to a paid plan if needed
- Optimize model loading in code

**Cold Start Issues**:
- Free tier services sleep after 15 minutes
- First request after sleep takes longer
- Consider keeping service warm with periodic health checks

### 8. Performance Optimization

- Use caching for ML model predictions
- Implement connection pooling for MongoDB
- Add request rate limiting
- Monitor memory usage and optimize as needed

---

## Quick Reference Commands

```bash
# Git setup
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/suraksha-ai-service.git
git push -u origin main

# Test locally
python app.py

# Test API endpoints
curl http://localhost:5000/api/health
```

Need help? Check the [Render documentation](https://render.com/docs) or create an issue in the repository.