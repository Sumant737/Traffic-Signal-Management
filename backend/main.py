from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import os
import shutil
import uuid
import cloudinary
import cloudinary.uploader
from supabase import create_client, Client
from dotenv import load_dotenv
import tempfile

load_dotenv()

app = FastAPI(title="Traffic Signal Control API")

# CORS - allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your Vercel URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cloudinary config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# Supabase config
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Google Colab ngrok URL (update this every time you run Colab)
COLAB_API_URL = os.getenv("COLAB_API_URL", "http://localhost:8001")


@app.get("/")
def root():
    return {"message": "Traffic Signal Control API is running"}


@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """
    1. Receive video from frontend
    2. Upload to Cloudinary
    3. Send video URL to Colab for YOLOv8 processing
    4. Save results to Supabase
    5. Return results to frontend
    """
    # Validate file type
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Only video files are allowed")

    # Save temporarily
    temp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_{file.filename}")
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            temp_path,
            resource_type="video",
            folder="traffic-ai"
        )
        video_url = upload_result["secure_url"]
        video_public_id = upload_result["public_id"]

        # Send to Colab for processing
        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=30.0)) as client:
            colab_response = await client.post(
                f"{COLAB_API_URL}/process-video",
                json={"video_url": video_url}
            )

        if colab_response.status_code != 200:
            raise HTTPException(status_code=500, detail="AI processing failed")

        result = colab_response.json()

        # Save to Supabase
        db_record = {
            "video_url": video_url,
            "video_public_id": video_public_id,
            "filename": file.filename,
            "lane_counts": result["lane_counts"],
            "signal_decisions": result["signal_decisions"],
            "frame_data": result["frame_data"],
            "processed_video_url": result.get("processed_video_url", ""),
            "total_vehicles": result["total_vehicles"],
        }
        supabase.table("traffic_analysis").insert(db_record).execute()

        return JSONResponse(content={
            "success": True,
            "video_url": video_url,
            **result
        })

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Colab server not running. Please start the Colab notebook."
        )
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.get("/history")
async def get_history():
    """Get past analysis results"""
    response = supabase.table("traffic_analysis") \
        .select("*") \
        .order("created_at", desc=True) \
        .limit(20) \
        .execute()
    return {"history": response.data}


@app.get("/history/{record_id}")
async def get_record(record_id: int):
    """Get specific analysis result"""
    response = supabase.table("traffic_analysis") \
        .select("*") \
        .eq("id", record_id) \
        .execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Record not found")
    return response.data[0]
