# ============================================================
# ADAPTIVE AI TRAFFIC SIGNAL CONTROL - Pressure Based Model
# Google Colab - Paste entire code into ONE cell and run
# ============================================================

# ── STEP 1: Run this cell first ──────────────────────────
#!pip install ultralytics fastapi uvicorn pyngrok nest-asyncio cloudinary requests -q


import os, uuid, threading, requests, time
import cv2
import numpy as np
import cloudinary
import cloudinary.uploader
from ultralytics import YOLO
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from pyngrok import ngrok
import nest_asyncio
from collections import defaultdict

nest_asyncio.apply()

# Kill old processes
os.system("kill -9 $(lsof -t -i:8001) 2>/dev/null || true")
os.system("pkill ngrok 2>/dev/null || true")
ngrok.kill()
try:
    tunnels = ngrok.get_tunnels()
    for t in tunnels:
        ngrok.disconnect(t.public_url)
except:
    pass

# ── Cloudinary config ─────────────────────────────────────
cloudinary.config(
    cloud_name="dvrkjsaoa",
    api_key="381579348599678",
    api_secret="HXInza8UeWmoHmGT0oxVOSQEh5E",
)

# ── Load YOLO ─────────────────────────────────────────────
model = YOLO('yolov8n.pt')

# Vehicle classes from COCO dataset
VEHICLE_CLASSES  = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
EMERGENCY_CLASSES = {}  # YOLOv8 doesn't detect ambulance by default
                        # We simulate emergency by checking if bus(5) is alone

# ── Pressure-Based AI Agent ───────────────────────────────
class PressureBasedSignalAgent:
    """
    Realistic Adaptive Traffic Signal Controller using Pressure Model.

    Pressure_i = (0.5 × Occupancy_i) + (0.3 × Queue_i) + (0.2 × WaitingTime_i_normalized)

    With:
    - Fairness bonus if waiting > threshold
    - Emergency vehicle override
    - Minimum green duration (no rapid switching)
    - Starvation prevention
    - Proper GREEN → YELLOW → RED transitions
    """

    TMIN              = 10      # minimum green seconds
    TMAX              = 40      # maximum green seconds (added to Tmin)
    YELLOW_DURATION   = 3       # yellow phase seconds
    FAIRNESS_THRESHOLD = 60     # seconds before fairness bonus kicks in
    FAIRNESS_BONUS    = 0.4     # pressure bonus for starving lanes
    MIN_GREEN_DURATION = 8      # prevent rapid switching (min seconds before can switch)
    EMERGENCY_PRESSURE = 999    # override pressure for emergency vehicles

    # Pressure weights
    W_OCCUPANCY = 0.5
    W_QUEUE     = 0.3
    W_WAITING   = 0.2

    def __init__(self, lanes):
        self.lanes            = lanes           # ["North","South","East","West"]
        self.current_green    = lanes[0]
        self.phase            = "GREEN"         # GREEN / YELLOW / RED_TRANSITION
        self.phase_start_time = 0.0             # elapsed seconds when phase started
        self.green_duration   = self.TMIN       # current green duration
        self.waiting_times    = {l: 0.0 for l in lanes}  # seconds each lane waited
        self.last_green_time  = {l: 0.0 for l in lanes}  # last time each lane was green
        self.pressures        = {l: 0.0 for l in lanes}
        self.decisions        = {}
        self.emergency_lane   = None
        self.cycle_count      = 0

    def compute_occupancy(self, vehicle_boxes, lane_box, frame_shape):
        """
        Occupancy = total vehicle pixel area in lane / lane pixel area (0 to 1)
        """
        lx1, ly1, lx2, ly2 = lane_box
        lane_area = max(1, (lx2 - lx1) * (ly2 - ly1))
        vehicle_area = 0
        for box in vehicle_boxes:
            bx1, by1, bx2, by2 = box
            # Intersection of vehicle box with lane box
            ix1 = max(lx1, bx1)
            iy1 = max(ly1, by1)
            ix2 = min(lx2, bx2)
            iy2 = min(ly2, by2)
            if ix2 > ix1 and iy2 > iy1:
                vehicle_area += (ix2 - ix1) * (iy2 - iy1)
        return min(1.0, vehicle_area / lane_area)

    def compute_queue_length(self, vehicle_centers, lane_box):
        """
        Queue = normalized distance of farthest vehicle from stop line (0 to 1)
        Stop line assumed at center of frame (intersection point)
        Farthest vehicle = one most away from center = highest queue
        """
        lx1, ly1, lx2, ly2 = lane_box
        lane_h = max(1, ly2 - ly1)
        lane_w = max(1, lx2 - lx1)
        max_dist = 0.0
        for cx, cy in vehicle_centers:
            if lx1 <= cx <= lx2 and ly1 <= cy <= ly2:
                # Normalize position within lane (0=stop line, 1=far end)
                dist_x = abs(cx - (lx1 + lane_w / 2)) / (lane_w / 2)
                dist_y = abs(cy - (ly1 + lane_h / 2)) / (lane_h / 2)
                dist = min(1.0, (dist_x + dist_y) / 2)
                max_dist = max(max_dist, dist)
        return max_dist

    def compute_pressure(self, occupancy, queue, waiting_time, elapsed_sec):
        """
        Core pressure formula:
        Pressure = (0.5 × Occupancy) + (0.3 × Queue) + (0.2 × Waiting_normalized)
        + Fairness bonus if waiting > threshold
        """
        # Normalize waiting time (cap at 120s)
        waiting_norm = min(1.0, waiting_time / 120.0)

        pressure = (
            self.W_OCCUPANCY * occupancy +
            self.W_QUEUE     * queue +
            self.W_WAITING   * waiting_norm
        )

        # Fairness bonus — prevents starvation
        if waiting_time >= self.FAIRNESS_THRESHOLD:
            bonus = self.FAIRNESS_BONUS * (waiting_time / self.FAIRNESS_THRESHOLD)
            pressure += bonus
            pressure = min(2.0, pressure)  # cap at 2.0

        return round(pressure, 4)

    def detect_emergency(self, vehicle_data):
        """
        Emergency detection:
        Simulate: if a lane has a single large vehicle (bus/truck) with
        high confidence and nothing else around = potential emergency
        In real deployment: use fine-tuned model with ambulance class
        """
        for lane, data in vehicle_data.items():
            for cls_id, conf in data.get("classes", []):
                if cls_id in (5, 7) and conf > 0.85 and data["count"] == 1:
                    return lane  # single high-confidence bus/truck = emergency sim
        return None

    def update(self, lane_metrics, elapsed_sec):
        """
        Main update called every processed frame.
        lane_metrics = {
          "North": {"occupancy": 0.3, "queue": 0.5, "vehicle_centers": [...], "vehicle_boxes": [...], "count": 4, "classes": [...]},
          ...
        }
        Returns decisions dict for all lanes.
        """
        # Update waiting times
        for lane in self.lanes:
            if lane != self.current_green:
                self.waiting_times[lane] += (elapsed_sec - self.last_green_time.get(lane + "_last_update", elapsed_sec - 0.2))
            else:
                self.waiting_times[lane] = 0.0
            self.last_green_time[lane + "_last_update"] = elapsed_sec

        # Compute pressures
        for lane in self.lanes:
            m = lane_metrics.get(lane, {})
            occ     = m.get("occupancy", 0.0)
            queue   = m.get("queue", 0.0)
            waiting = self.waiting_times[lane]
            self.pressures[lane] = self.compute_pressure(occ, queue, waiting, elapsed_sec)

        # Emergency detection
        self.emergency_lane = self.detect_emergency(lane_metrics)
        if self.emergency_lane:
            self.pressures[self.emergency_lane] = self.EMERGENCY_PRESSURE

        # Phase state machine
        phase_elapsed = elapsed_sec - self.phase_start_time

        if self.phase == "GREEN":
            time_left = max(0, int(self.green_duration - phase_elapsed))

            # Can we switch? Only if min green elapsed
            if phase_elapsed >= max(self.MIN_GREEN_DURATION, self.green_duration):
                # Check if another lane has significantly higher pressure
                best_lane    = max(self.pressures, key=self.pressures.get)
                current_p    = self.pressures[self.current_green]
                best_p       = self.pressures[best_lane]

                # Switch if best lane pressure > current by margin OR emergency
                if best_lane != self.current_green and (best_p > current_p + 0.1 or self.emergency_lane):
                    self.phase            = "YELLOW"
                    self.phase_start_time = elapsed_sec
                    self._next_green_lane = best_lane
                    time_left = 0

        elif self.phase == "YELLOW":
            time_left = max(0, int(self.YELLOW_DURATION - phase_elapsed))
            if phase_elapsed >= self.YELLOW_DURATION:
                # Switch to new green lane
                self.current_green    = self._next_green_lane
                self.phase            = "GREEN"
                self.phase_start_time = elapsed_sec
                self.waiting_times[self.current_green] = 0.0
                self.last_green_time[self.current_green] = elapsed_sec
                self.cycle_count     += 1

                # Calculate new green duration based on pressure
                p = min(1.0, self.pressures[self.current_green])
                self.green_duration = int(self.TMIN + p * self.TMAX)
                self.green_duration = max(self.TMIN, min(self.TMIN + self.TMAX, self.green_duration))
                time_left = self.green_duration

        # Build decisions
        self.decisions = {}
        for lane in self.lanes:
            if lane == self.current_green:
                if self.phase == "GREEN":
                    phase_elapsed_now = elapsed_sec - self.phase_start_time
                    tl    = max(0, int(self.green_duration - phase_elapsed_now))
                    sig   = "GREEN"
                    ck    = "GREEN"
                elif self.phase == "YELLOW":
                    phase_elapsed_now = elapsed_sec - self.phase_start_time
                    tl  = max(0, int(self.YELLOW_DURATION - phase_elapsed_now))
                    sig = "YELLOW"
                    ck  = "YELLOW"
                else:
                    tl, sig, ck = 0, "RED", "RED"
            else:
                sig = "RED"
                ck  = "RED"
                # Estimate wait time
                tl = max(0, int(self.green_duration - (elapsed_sec - self.phase_start_time)))
                tl += self.YELLOW_DURATION
                idx_curr = self.lanes.index(self.current_green)
                idx_lane = self.lanes.index(lane)
                steps    = (idx_lane - idx_curr) % len(self.lanes)
                total    = self.pressures
                for s in range(1, steps):
                    ahead = self.lanes[(idx_curr + s) % len(self.lanes)]
                    p     = min(1.0, total.get(ahead, 0))
                    tl   += int(self.TMIN + p * self.TMAX) + self.YELLOW_DURATION

            p = self.pressures.get(lane, 0)
            self.decisions[lane] = {
                "signal":        sig,
                "color_key":     ck,
                "time_left":     tl,
                "green_duration": self.green_duration,
                "vehicle_count": lane_metrics.get(lane, {}).get("count", 0),
                "occupancy":     round(lane_metrics.get(lane, {}).get("occupancy", 0), 3),
                "queue":         round(lane_metrics.get(lane, {}).get("queue", 0), 3),
                "waiting_time":  round(self.waiting_times.get(lane, 0), 1),
                "pressure":      round(p, 3),
                "priority":      "EMERGENCY" if lane == self.emergency_lane
                                 else "HIGH"    if p > 0.6
                                 else "NORMAL"  if p > 0.3
                                 else "LOW",
                "fairness_bonus": self.waiting_times.get(lane, 0) >= self.FAIRNESS_THRESHOLD,
            }

        return self.decisions


# ── Lane geometry ─────────────────────────────────────────
def get_lanes(frame):
    h, w = frame.shape[:2]
    return {
        "North": (0,    0,    w//2, h//2),
        "South": (w//2, 0,    w,    h//2),
        "East":  (0,    h//2, w//2, h),
        "West":  (w//2, h//2, w,    h),
    }


# ── Draw overlay ──────────────────────────────────────────
def draw_overlay(frame, lanes, decisions):
    COLORS = {
        "GREEN":  (0,   220, 0),
        "YELLOW": (0,   220, 220),
        "RED":    (30,  30,  220),
    }
    BG = {
        "GREEN":  (0,  45, 0),
        "YELLOW": (0,  45, 45),
        "RED":    (45, 0,  0),
    }

    h, w = frame.shape[:2]
    cv2.line(frame, (w//2, 0),   (w//2, h),   (200,200,0), 2)
    cv2.line(frame, (0, h//2),   (w, h//2),   (200,200,0), 2)

    origins = {
        "North": (0,    0),
        "South": (w//2, 0),
        "East":  (0,    h//2),
        "West":  (w//2, h//2),
    }

    for lane, d in decisions.items():
        ck     = d["color_key"]
        color  = COLORS[ck]
        bg     = BG[ck]
        ox, oy = origins[lane]
        qw, qh = w//2, h//2

        # Lane border
        bthick = 5 if ck == "GREEN" else 2
        cv2.rectangle(frame, (ox+2, oy+2), (ox+qw-2, oy+qh-2), color, bthick)

        # Top info bar
        cv2.rectangle(frame, (ox, oy), (ox+qw, oy+44), bg, -1)

        # Lane name + signal + count
        cv2.putText(frame,
            f"{lane}  [{d['signal']}]  {d['vehicle_count']} veh",
            (ox+6, oy+18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Pressure bar text
        pbar = f"P:{d['pressure']:.2f}  Occ:{d['occupancy']:.2f}  Q:{d['queue']:.2f}"
        cv2.putText(frame, pbar,
            (ox+6, oy+36), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (180,180,180), 1)

        # Pressure bar (visual)
        bar_w    = int((qw - 12) * min(1.0, d['pressure']))
        bar_color = (0,200,0) if d['pressure'] < 0.5 else (0,200,200) if d['pressure'] < 0.8 else (0,0,220)
        cv2.rectangle(frame, (ox+6, oy+46), (ox+6+bar_w, oy+52), bar_color, -1)
        cv2.rectangle(frame, (ox+6, oy+46), (ox+qw-6,    oy+52), (80,80,80), 1)

        # BIG countdown timer
        ttext = f"{d['time_left']}s"
        fs, th = 2.6, 5
        (tw, txh), _ = cv2.getTextSize(ttext, cv2.FONT_HERSHEY_DUPLEX, fs, th)
        tx = ox + (qw - tw) // 2
        ty = oy + (qh + txh) // 2 + 10
        cv2.putText(frame, ttext, (tx+3, ty+3), cv2.FONT_HERSHEY_DUPLEX, fs, (0,0,0), th+3)
        cv2.putText(frame, ttext, (tx, ty),     cv2.FONT_HERSHEY_DUPLEX, fs, color,   th)

        # Signal circle (traffic light style)
        cx_c = ox + qw - 22
        cy_c = oy + qh - 22
        cv2.circle(frame, (cx_c, cy_c), 16, color, -1)
        cv2.circle(frame, (cx_c, cy_c), 16, (255,255,255), 2)

        # Fairness badge
        if d.get("fairness_bonus"):
            cv2.rectangle(frame, (ox+6, oy+qh-30), (ox+100, oy+qh-10), (0,100,200), -1)
            cv2.putText(frame, "FAIRNESS!", (ox+8, oy+qh-15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255,255,255), 1)

        # Priority badge
        if d["priority"] in ("EMERGENCY", "HIGH"):
            bc = (0,0,200) if d["priority"] == "EMERGENCY" else (0,120,200)
            cv2.rectangle(frame, (ox+qw-95, oy+58), (ox+qw-5, oy+80), bc, -1)
            cv2.putText(frame, d["priority"], (ox+qw-91, oy+74),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255,255,255), 1)

        # Waiting time bottom left
        cv2.putText(frame, f"wait: {d['waiting_time']}s",
            (ox+6, oy+qh-6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160,160,160), 1)

    return frame


# ── Main Video Processing ─────────────────────────────────
def process_traffic_video(video_url):
    temp_input      = f"/tmp/input_{uuid.uuid4()}.mp4"
    temp_output     = f"/tmp/output_{uuid.uuid4()}.mp4"
    temp_output_web = f"/tmp/web_{uuid.uuid4()}.mp4"

    # Download video
    r = requests.get(video_url, stream=True)
    with open(temp_input, 'wb') as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    cap = cv2.VideoCapture(temp_input)
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
    W   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Video: {W}x{H} @ {fps}fps")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out    = cv2.VideoWriter(temp_output, fourcc, fps, (W, H))

    # Agent + tracking state
    lanes_list = ["North", "South", "East", "West"]
    agent      = PressureBasedSignalAgent(lanes_list)

    counted_ids       = set()
    total_lane_counts = {l: 0 for l in lanes_list}
    last_boxes        = {}   # track_id → (x1,y1,x2,y2,cls_id,conf)
    frame_data        = []
    frame_count       = 0
    process_every     = max(1, fps // 5)

    current_decisions = {l: {
        "signal": "RED", "color_key": "RED", "time_left": 30,
        "green_duration": 30, "vehicle_count": 0, "occupancy": 0,
        "queue": 0, "waiting_time": 0, "pressure": 0,
        "priority": "LOW", "fairness_bonus": False,
    } for l in lanes_list}
    current_decisions["North"]["signal"] = "GREEN"
    current_decisions["North"]["color_key"] = "GREEN"

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count  += 1
        elapsed_sec   = frame_count / fps

        if frame_count % process_every == 0:
            lane_boxes = get_lanes(frame)
            results    = model.track(frame, persist=True, verbose=False)[0]

            # Per-lane metrics for pressure model
            lane_metrics = {l: {
                "count": 0, "occupancy": 0.0, "queue": 0.0,
                "vehicle_boxes": [], "vehicle_centers": [], "classes": []
            } for l in lanes_list}

            if results.boxes and len(results.boxes) > 0:
                detections = results.boxes.data.cpu().numpy()
                track_ids  = (results.boxes.id.cpu().numpy().astype(int)
                              if results.boxes.id is not None
                              else np.arange(len(detections)) + frame_count * 1000)

                for i, det in enumerate(detections):
                    cls_id = int(det[5])
                    if cls_id not in VEHICLE_CLASSES:
                        continue

                    track_id = track_ids[i]
                    x1,y1,x2,y2 = int(det[0]),int(det[1]),int(det[2]),int(det[3])
                    conf = float(det[4])
                    cx, cy = (x1+x2)//2, (y1+y2)//2

                    # Update smooth box store
                    last_boxes[track_id] = (x1,y1,x2,y2,cls_id,conf)

                    # Find which lane
                    for lane_name, (lx1,ly1,lx2,ly2) in lane_boxes.items():
                        if lx1 <= cx <= lx2 and ly1 <= cy <= ly2:
                            lane_metrics[lane_name]["count"]            += 1
                            lane_metrics[lane_name]["vehicle_boxes"].append((x1,y1,x2,y2))
                            lane_metrics[lane_name]["vehicle_centers"].append((cx,cy))
                            lane_metrics[lane_name]["classes"].append((cls_id, conf))
                            if track_id not in counted_ids:
                                counted_ids.add(track_id)
                                total_lane_counts[lane_name] += 1
                            break

                # Remove stale tracks
                active = set(track_ids)
                for tid in list(last_boxes.keys()):
                    if tid not in active:
                        del last_boxes[tid]

            # Compute occupancy and queue for each lane
            for lane_name, (lx1,ly1,lx2,ly2) in lane_boxes.items():
                m = lane_metrics[lane_name]
                m["occupancy"] = agent.compute_occupancy(
                    m["vehicle_boxes"], (lx1,ly1,lx2,ly2), frame.shape)
                m["queue"] = agent.compute_queue_length(
                    m["vehicle_centers"], (lx1,ly1,lx2,ly2))

            # Update AI agent
            current_decisions = agent.update(lane_metrics, elapsed_sec)

            frame_data.append({
                "frame":    frame_count,
                "time_sec": round(elapsed_sec, 1),
                "North":    lane_metrics["North"]["count"],
                "South":    lane_metrics["South"]["count"],
                "East":     lane_metrics["East"]["count"],
                "West":     lane_metrics["West"]["count"],
                "total":    sum(m["count"] for m in lane_metrics.values()),
                "pressure_North": lane_metrics["North"].get("occupancy",0),
                "pressure_South": lane_metrics["South"].get("occupancy",0),
            })

        # Draw smooth bounding boxes on EVERY frame
        for track_id, (x1,y1,x2,y2,cls_id,conf) in last_boxes.items():
            label = f"{VEHICLE_CLASSES.get(cls_id,'v')} #{track_id}"
            cv2.rectangle(frame, (x1,y1), (x2,y2), (0,230,230), 2)
            (lw,lh),_ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
            cv2.rectangle(frame, (x1, y1-16), (x1+lw+4, y1), (0,0,0), -1)
            cv2.putText(frame, label, (x1+2, y1-4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0,230,230), 1)

        # Draw pressure-based signal overlay on EVERY frame
        frame = draw_overlay(frame, get_lanes(frame), current_decisions)

        out.write(frame)

    cap.release()
    out.release()

    # Convert to H.264
    print("Converting to H.264...")
    os.system(f"ffmpeg -i {temp_output} -vcodec libx264 -acodec aac -crf 28 -preset fast {temp_output_web} -y -loglevel quiet")
    upload_file = temp_output_web if os.path.exists(temp_output_web) else temp_output

    # Upload to Cloudinary
    print("Uploading to Cloudinary...")
    result = cloudinary.uploader.upload(upload_file, resource_type="video", folder="traffic-ai/processed")
    processed_url = result["secure_url"]

    for f in [temp_input, temp_output, temp_output_web]:
        if os.path.exists(f): os.remove(f)

    final = agent.update({l: {"count": total_lane_counts[l], "occupancy":0,
                               "queue":0, "vehicle_boxes":[], "vehicle_centers":[],
                               "classes":[]} for l in lanes_list}, 0)

    return {
        "lane_counts":           total_lane_counts,
        "signal_decisions":      final,
        "frame_data":            frame_data[::3],
        "processed_video_url":   processed_url,
        "total_vehicles":        sum(total_lane_counts.values()),
        "unique_vehicles":       len(counted_ids),
        "total_frames":          frame_count,
        "pressure_summary":      {l: round(agent.pressures.get(l,0),3) for l in lanes_list},
        "cycles_completed":      agent.cycle_count,
    }


# ── FastAPI ───────────────────────────────────────────────
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

class VideoRequest(BaseModel):
    video_url: str

@app.get("/")
def root():
    return {"status": "Pressure-Based AI Traffic Signal running"}

@app.post("/process-video")
def process_video(req: VideoRequest):
    return process_traffic_video(req.video_url)

# ── Start ─────────────────────────────────────────────────
def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8001)

thread = threading.Thread(target=run_server, daemon=True)
thread.start()

ngrok.set_auth_token("3AUAixp36V7I1pIRBokoYJ0LUYC_5XKqgh1tTniCW5J4kgbvH")
public_url = ngrok.connect(8001)
print("=" * 50)
print("Pressure-Based AI Traffic Signal Server LIVE!")
print(f"ngrok URL: {public_url}")
print("Copy this URL to backend .env as COLAB_API_URL")
print("=" * 50)