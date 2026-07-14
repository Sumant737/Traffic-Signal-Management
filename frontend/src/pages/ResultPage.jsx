import { useState, useEffect, useRef } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, Cell } from "recharts";

const SIGNAL_COLOR  = { GREEN: "#00ff87", YELLOW: "#ffd32a", RED: "#ff4757" };
const LANE_COLORS   = { North: "#00b4ff", South: "#00ff87", East: "#ffd32a", West: "#ff6b81" };
const PRIORITY_COLOR = { EMERGENCY: "#ff0000", HIGH: "#ff6b35", NORMAL: "#ffd32a", LOW: "#00ff87" };

export default function ResultPage({ result, setPage }) {
  if (!result) return (
    <div style={{ textAlign:"center", padding:60, color:"#4a7090" }}>
      No results yet.{" "}
      <button onClick={() => setPage("upload")} style={linkBtn}>Upload a video</button>
    </div>
  );

  const { lane_counts, signal_decisions, frame_data, processed_video_url,
          total_vehicles, unique_vehicles, pressure_summary, cycles_completed } = result;

  return (
    <div style={{ maxWidth:1200, margin:"0 auto", padding:"40px 20px" }}>

      {/* Header */}
      <div style={{ marginBottom:32 }}>
        <button onClick={() => setPage("upload")} style={linkBtn}>← Upload New Video</button>
        <h1 style={{ color:"#e0f0ff", fontSize:30, fontWeight:900, margin:"12px 0 4px" }}>
          Analysis Complete
        </h1>
        <div style={{ display:"flex", gap:24, flexWrap:"wrap", marginTop:8 }}>
          <Chip label="Unique Vehicles" value={unique_vehicles || total_vehicles} color="#00ff87" />
          <Chip label="Total Detections" value={total_vehicles} color="#00b4ff" />
          <Chip label="Signal Cycles" value={cycles_completed || "—"} color="#ffd32a" />
        </div>
      </div>

      {/* Live Signal Display */}
      <SectionTitle>🚦 Pressure-Based Signal Decisions</SectionTitle>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(240px,1fr))", gap:16, marginBottom:48 }}>
        {Object.entries(signal_decisions).map(([lane, data]) => (
          <SignalCard key={lane} lane={lane} data={data} />
        ))}
      </div>

      {/* Pressure Summary */}
      {pressure_summary && (
        <>
          <SectionTitle>📊 Traffic Pressure per Lane</SectionTitle>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(200px,1fr))", gap:12, marginBottom:48 }}>
            {Object.entries(pressure_summary).map(([lane, pressure]) => (
              <PressureCard key={lane} lane={lane} pressure={pressure} color={LANE_COLORS[lane]} />
            ))}
          </div>
        </>
      )}

      {/* Stats */}
      <SectionTitle>🚗 Unique Vehicle Count Per Lane</SectionTitle>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(130px,1fr))", gap:12, marginBottom:48 }}>
        {Object.entries(lane_counts).map(([lane, count]) => (
          <StatCard key={lane} label={lane} value={count} color={LANE_COLORS[lane]} unit="vehicles" />
        ))}
        <StatCard label="Total" value={unique_vehicles || total_vehicles} color="#e0f0ff" unit="unique" />
      </div>

      {/* Line Chart */}
      <SectionTitle>📈 Traffic Density Over Time</SectionTitle>
      <ChartBox>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={frame_data} margin={{ top:5, right:20, left:0, bottom:5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d4a" />
            <XAxis dataKey="time_sec" stroke="#4a7090" tick={{ fontSize:11 }}
              label={{ value:"Time (s)", position:"insideBottom", offset:-2, fill:"#4a7090" }} />
            <YAxis stroke="#4a7090" tick={{ fontSize:11 }} />
            <Tooltip contentStyle={{ background:"#0d1929", border:"1px solid #1e3a5a", borderRadius:8 }}
              labelStyle={{ color:"#7090b0" }} />
            <Legend />
            {["North","South","East","West"].map(lane => (
              <Line key={lane} type="monotone" dataKey={lane}
                stroke={LANE_COLORS[lane]} dot={false} strokeWidth={2} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartBox>

      {/* Bar Chart */}
      <SectionTitle style={{ marginTop:40 }}>📊 Vehicles Per Lane</SectionTitle>
      <ChartBox>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={Object.entries(lane_counts).map(([lane,count]) => ({ lane, count }))}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d4a" />
            <XAxis dataKey="lane" stroke="#4a7090" tick={{ fontSize:12 }} />
            <YAxis stroke="#4a7090" tick={{ fontSize:11 }} />
            <Tooltip contentStyle={{ background:"#0d1929", border:"1px solid #1e3a5a", borderRadius:8 }} />
            <Bar dataKey="count" radius={[4,4,0,0]}>
              {Object.keys(lane_counts).map(lane => (
                <Cell key={lane} fill={LANE_COLORS[lane]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartBox>

      {/* Processed Video */}
      {processed_video_url && (
        <>
          <SectionTitle style={{ marginTop:48 }}>🎬 Processed Video — Pressure Based Signal with Countdown</SectionTitle>
          <div style={{ borderRadius:12, overflow:"hidden", border:"1px solid #1e3a5a", marginBottom:48 }}>
            <video key={processed_video_url} src={processed_video_url}
              controls style={{ width:"100%", maxHeight:480, background:"#000", display:"block" }}>
              <source src={processed_video_url} type="video/mp4" />
            </video>
            <div style={{ padding:"10px 16px", background:"#0d1929" }}>
              <a href={processed_video_url} target="_blank" rel="noreferrer"
                style={{ color:"#00b4ff", fontSize:13 }}>
                🔗 Open video in new tab
              </a>
            </div>
          </div>
        </>
      )}

      {/* How Pressure Works */}
      <SectionTitle>🧠 How Pressure Model Works</SectionTitle>
      <div style={{
        background:"rgba(255,255,255,0.02)", border:"1px solid #1e2d4a",
        borderRadius:12, padding:"24px", marginBottom:48, color:"#7090b0", fontSize:13, lineHeight:1.8
      }}>
        <div style={{ color:"#e0f0ff", fontWeight:700, marginBottom:12 }}>Formula:</div>
        <code style={{ color:"#00ff87", fontSize:14 }}>
          Pressure = (0.5 × Occupancy) + (0.3 × Queue) + (0.2 × WaitingTime)
        </code>
        <div style={{ marginTop:16, display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(200px,1fr))", gap:12 }}>
          {[
            ["Occupancy (50%)", "Vehicle pixel area / lane area"],
            ["Queue (30%)",     "Farthest vehicle from stop line"],
            ["Waiting (20%)",   "How long lane has been waiting"],
            ["Fairness Bonus",  "Extra pressure if waiting > 60s"],
            ["Emergency",       "Single bus/truck = immediate green"],
            ["Min Green",       "8s minimum before switching"],
          ].map(([k,v]) => (
            <div key={k} style={{ background:"rgba(255,255,255,0.03)", borderRadius:8, padding:"10px 12px" }}>
              <div style={{ color:"#00b4ff", fontWeight:700, fontSize:12 }}>{k}</div>
              <div style={{ marginTop:4 }}>{v}</div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

// ── Interactive Signal Card with live countdown ───────────
function SignalCard({ lane, data }) {
  const [timeLeft, setTimeLeft] = useState(data.time_left || 0);
  const intervalRef = useRef(null);

  useEffect(() => {
    setTimeLeft(data.time_left || 0);
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => {
      setTimeLeft(t => Math.max(0, t - 1));
    }, 1000);
    return () => clearInterval(intervalRef.current);
  }, [data.time_left, data.signal]);

  const isGreen  = data.signal === "GREEN";
  const isYellow = data.signal === "YELLOW";
  const color    = SIGNAL_COLOR[data.signal] || SIGNAL_COLOR.RED;
  const pressure = data.pressure || 0;

  return (
    <div style={{
      background:"rgba(255,255,255,0.03)",
      border:`1px solid ${color}33`,
      borderRadius:12, padding:"20px 16px", textAlign:"center",
    }}>
      {/* Lane name */}
      <div style={{ fontSize:11, color:"#4a7090", letterSpacing:2, marginBottom:8 }}>
        {lane.toUpperCase()} LANE
      </div>

      {/* Traffic light */}
      <div style={{
        width:52, height:52, borderRadius:"50%", margin:"0 auto 10px",
        background:color, boxShadow:`0 0 24px ${color}88`,
        display:"flex", alignItems:"center", justifyContent:"center", fontSize:24,
      }}>
        {isGreen ? "🟢" : isYellow ? "🟡" : "🔴"}
      </div>

      {/* Signal */}
      <div style={{ color, fontWeight:900, fontSize:20 }}>{data.signal}</div>

      {/* Live countdown */}
      <div style={{
        fontSize:36, fontWeight:900, color, margin:"8px 0",
        fontVariantNumeric:"tabular-nums",
        textShadow:`0 0 20px ${color}66`,
      }}>
        {timeLeft}s
      </div>

      {/* Stats */}
      <div style={{ color:"#7090b0", fontSize:12, marginTop:4 }}>
        Vehicles: <span style={{ color:"#e0f0ff", fontWeight:700 }}>{data.vehicle_count}</span>
      </div>
      <div style={{ color:"#7090b0", fontSize:12 }}>
        Wait: <span style={{ color:"#e0f0ff", fontWeight:700 }}>{data.waiting_time}s</span>
      </div>

      {/* Pressure bar */}
      <div style={{ marginTop:10 }}>
        <div style={{ fontSize:10, color:"#4a7090", marginBottom:4 }}>
          PRESSURE: {pressure.toFixed(2)}
        </div>
        <div style={{ height:4, background:"#1e2d4a", borderRadius:2, overflow:"hidden" }}>
          <div style={{
            height:"100%",
            width:`${Math.min(100, pressure * 100)}%`,
            background:pressure > 0.6 ? "#ff4757" : pressure > 0.3 ? "#ffd32a" : "#00ff87",
            borderRadius:2, transition:"width 0.5s",
          }} />
        </div>
      </div>

      {/* Priority badge */}
      <div style={{
        marginTop:10, fontSize:10, fontWeight:800, letterSpacing:1,
        color: PRIORITY_COLOR[data.priority],
        background:`${PRIORITY_COLOR[data.priority]}18`,
        borderRadius:4, padding:"3px 8px", display:"inline-block",
        border:`1px solid ${PRIORITY_COLOR[data.priority]}44`,
      }}>
        {data.priority} PRIORITY
        {data.fairness_bonus && " ⚡"}
      </div>
    </div>
  );
}

function PressureCard({ lane, pressure, color }) {
  const pct = Math.min(100, pressure * 100);
  return (
    <div style={{
      background:"rgba(255,255,255,0.02)", border:"1px solid #1e2d4a",
      borderRadius:10, padding:"16px",
    }}>
      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:8 }}>
        <span style={{ color:"#7090b0", fontSize:12, fontWeight:700 }}>{lane}</span>
        <span style={{ color, fontSize:14, fontWeight:900 }}>{pressure.toFixed(3)}</span>
      </div>
      <div style={{ height:8, background:"#1e2d4a", borderRadius:4, overflow:"hidden" }}>
        <div style={{
          height:"100%", width:`${pct}%`,
          background:pressure > 0.6 ? "#ff4757" : pressure > 0.3 ? "#ffd32a" : color,
          borderRadius:4, transition:"width 0.8s",
        }} />
      </div>
      <div style={{ fontSize:10, color:"#3a5070", marginTop:6 }}>
        {pressure > 0.6 ? "HIGH PRESSURE" : pressure > 0.3 ? "MEDIUM" : "LOW PRESSURE"}
      </div>
    </div>
  );
}

function Chip({ label, value, color }) {
  return (
    <div style={{
      background:"rgba(255,255,255,0.03)", border:`1px solid ${color}33`,
      borderRadius:8, padding:"8px 16px", display:"flex", gap:8, alignItems:"center",
    }}>
      <span style={{ color, fontSize:18, fontWeight:900 }}>{value}</span>
      <span style={{ color:"#4a7090", fontSize:12 }}>{label}</span>
    </div>
  );
}

function StatCard({ label, value, color, unit }) {
  return (
    <div style={{
      background:"rgba(255,255,255,0.02)", border:"1px solid #1e2d4a",
      borderRadius:10, padding:"16px 12px", textAlign:"center",
    }}>
      <div style={{ color, fontSize:26, fontWeight:900 }}>{value}</div>
      <div style={{ color:"#7090b0", fontSize:11, marginTop:2 }}>{unit}</div>
      <div style={{ color:"#4a7090", fontSize:11, letterSpacing:1, marginTop:4 }}>
        {label.toUpperCase()}
      </div>
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <h2 style={{ color:"#7090b0", fontSize:13, fontWeight:700, letterSpacing:2,
      marginBottom:16, textTransform:"uppercase" }}>
      {children}
    </h2>
  );
}

function ChartBox({ children }) {
  return (
    <div style={{ background:"rgba(255,255,255,0.02)", border:"1px solid #1e2d4a",
      borderRadius:12, padding:"20px 8px", marginBottom:16 }}>
      {children}
    </div>
  );
}

const linkBtn = {
  background:"none", border:"none", color:"#00b4ff",
  cursor:"pointer", fontSize:13, padding:0, textDecoration:"underline",
};
