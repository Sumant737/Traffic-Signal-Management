# 🚦 Adaptive AI-Based Traffic Signal Control

Real-time traffic signal optimization using YOLOv8 vehicle detection and adaptive 4-way intersection logic.

---

## 📁 Project Structure

```
traffic-ai/
├── backend/               ← FastAPI (deployed on Render)
│   ├── main.py
│   ├── requirements.txt
│   ├── render.yaml
│   ├── supabase_schema.sql
│   └── .env.example
├── frontend/              ← React (deployed on Vercel)
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── api/traffic.js
│   │   └── pages/
│   │       ├── UploadPage.jsx
│   │       ├── ResultPage.jsx
│   │       └── HistoryPage.jsx
│   ├── index.html
│   ├── package.json
│   └── .env.example
└── colab/
    └── traffic_ai_colab.py  ← YOLOv8 AI (run on Google Colab)
```

---

## 🚀 Setup Guide (Step by Step)

### STEP 1 — Create Free Accounts

| Service | URL | What For |
|---------|-----|----------|
| Supabase | supabase.com | Database |
| Cloudinary | cloudinary.com | Video storage |
| Render | render.com | Backend hosting |
| Vercel | vercel.com | Frontend hosting |
| ngrok | ngrok.com | Expose Colab |
| GitHub | github.com | Code repository |

---

### STEP 2 — Setup Supabase Database

1. Go to **supabase.com** → Create new project
2. Go to **SQL Editor** → New Query
3. Paste the contents of `backend/supabase_schema.sql` and run it
4. Go to **Settings → API** → copy `Project URL` and `anon/public` key

---

### STEP 3 — Setup Cloudinary

1. Go to **cloudinary.com** → Sign up free
2. From Dashboard copy: `Cloud Name`, `API Key`, `API Secret`

---

### STEP 4 — Setup ngrok

1. Go to **ngrok.com** → Sign up free
2. Copy your **Authtoken** from the dashboard
3. You'll paste it in the Colab notebook

---

### STEP 5 — Run Google Colab (AI Backend)

1. Go to **colab.research.google.com**
2. Create a new notebook
3. Set Runtime: **Runtime → Change runtime type → T4 GPU**
4. Copy the code from `colab/traffic_ai_colab.py` into cells
5. Fill in your Cloudinary credentials at the top
6. Uncomment and add your ngrok auth token:
   ```python
   ngrok.set_auth_token("YOUR_NGROK_TOKEN")
   ```
7. Run all cells → Copy the printed ngrok URL (e.g. `https://xxxx.ngrok-free.app`)

---

### STEP 6 — Deploy Backend on Render

1. Push your code to **GitHub**
2. Go to **render.com** → New → Web Service → Connect your repo
3. Set root directory to `backend/`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add Environment Variables:
   ```
   CLOUDINARY_CLOUD_NAME = your_cloud_name
   CLOUDINARY_API_KEY    = your_api_key
   CLOUDINARY_API_SECRET = your_api_secret
   SUPABASE_URL          = https://xxx.supabase.co
   SUPABASE_KEY          = your_anon_key
   COLAB_API_URL         = https://xxxx.ngrok-free.app  ← from Step 5
   ```
7. Deploy → Copy your Render URL (e.g. `https://traffic-ai.onrender.com`)

---

### STEP 7 — Deploy Frontend on Vercel

1. Go to **vercel.com** → New Project → Import GitHub repo
2. Set root directory to `frontend/`
3. Add Environment Variable:
   ```
   VITE_API_URL = https://traffic-ai.onrender.com  ← your Render URL
   ```
4. Deploy → Your app is live! 🎉

---

## 🔄 Daily Usage (Demo Day)

Every time you want to use the system:

1. Open Google Colab → Run all cells → Copy new ngrok URL
2. Update `COLAB_API_URL` in Render environment variables
3. Your app is ready to demo!

---

## 🧠 How The AI Works

```
Video uploaded
      ↓
Split into frames (5 per second)
      ↓
YOLOv8 detects: cars, trucks, buses, motorcycles
      ↓
Frame divided into 4 quadrants (North/South/East/West)
      ↓
Vehicle count per quadrant
      ↓
Signal timing formula:
  green_time = 10 + (lane_count / total_count) × 50
  Min: 10s | Max: 60s
      ↓
Lane with most vehicles → GREEN
Others → RED
      ↓
Annotated video + stats returned
```

---

## 🚦 Signal Logic

- **Minimum green time**: 10 seconds
- **Maximum green time**: 60 seconds  
- **Priority levels**: HIGH (>35% traffic), NORMAL (>20%), LOW (<20%)
- **Decision**: Busiest lane gets GREEN, others get RED with proportional wait times

---

## 📦 Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | React + Recharts |
| Frontend Host | Vercel (free) |
| Backend | FastAPI (Python) |
| Backend Host | Render.com (free) |
| AI Model | YOLOv8n (pretrained) |
| AI Host | Google Colab + ngrok (free GPU) |
| Database | Supabase PostgreSQL (free) |
| File Storage | Cloudinary (free) |
| Total Cost | ₹0 |

---

## 🔮 Stage 2 Upgrade (Live Camera)

When ready for live camera, only change ONE line in Colab:

```python
# Stage 1 (current)
cap = cv2.VideoCapture(video_path)

# Stage 2 (live cam)
cap = cv2.VideoCapture(0)  # or IP camera URL
```

Everything else stays the same!
