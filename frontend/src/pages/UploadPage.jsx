import { useState, useRef } from "react";
import { uploadVideo } from "../api/traffic";

const S = {
  page: {
    minHeight: "calc(100vh - 70px)",
    display: "flex", flexDirection: "column",
    alignItems: "center", justifyContent: "center",
    padding: "40px 20px",
    background: "radial-gradient(ellipse at 50% 0%, #0d2040 0%, #0a0f1e 70%)",
  },
  title: {
    fontSize: "clamp(28px, 5vw, 52px)", fontWeight: 900,
    color: "#e0f0ff", textAlign: "center", marginBottom: 8,
    letterSpacing: -1,
  },
  sub: { color: "#4a7090", fontSize: 15, textAlign: "center", marginBottom: 48 },
  dropzone: (drag) => ({
    width: "100%", maxWidth: 560,
    border: `2px dashed ${drag ? "#00ff87" : "#1e3a5a"}`,
    borderRadius: 16, padding: "60px 40px",
    textAlign: "center", cursor: "pointer",
    background: drag ? "rgba(0,255,135,0.04)" : "rgba(255,255,255,0.02)",
    transition: "all 0.25s",
  }),
  btn: (loading) => ({
    marginTop: 24, padding: "14px 48px",
    background: loading
      ? "linear-gradient(135deg, #1e3a5a, #1e3a5a)"
      : "linear-gradient(135deg, #00ff87, #00b4ff)",
    border: "none", borderRadius: 10, cursor: loading ? "not-allowed" : "pointer",
    color: loading ? "#4a7090" : "#0a0f1e",
    fontWeight: 800, fontSize: 15, letterSpacing: 1,
    width: "100%", maxWidth: 560, transition: "all 0.2s",
  }),
  progress: {
    width: "100%", maxWidth: 560, marginTop: 16,
    height: 4, background: "#1e2d4a", borderRadius: 2, overflow: "hidden",
  },
  bar: (pct) => ({
    height: "100%", width: `${pct}%`,
    background: "linear-gradient(90deg, #00ff87, #00b4ff)",
    transition: "width 0.3s", borderRadius: 2,
  }),
  error: {
    marginTop: 16, color: "#ff6b6b", fontSize: 13,
    background: "rgba(255,107,107,0.08)", padding: "10px 20px",
    borderRadius: 8, maxWidth: 560, textAlign: "center",
  },
  steps: {
    display: "flex", gap: 32, marginTop: 64,
    flexWrap: "wrap", justifyContent: "center",
  },
  step: {
    textAlign: "center", color: "#4a7090", fontSize: 13, maxWidth: 130,
  },
};

export default function UploadPage({ setResult, setPage }) {
  const [drag, setDrag] = useState(false);
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef();

  const handleFile = (f) => {
    if (!f) return;
    if (!f.type.startsWith("video/")) { setError("Please upload a video file"); return; }
    if (f.size > 200 * 1024 * 1024) { setError("File too large (max 200MB)"); return; }
    setFile(f); setError("");
  };

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true); setError(""); setProgress(0);

    try {
      setStatus("Uploading video...");
      const res = await uploadVideo(file, (pct) => {
        setProgress(pct);
        if (pct === 100) setStatus("AI processing video (may take 1–3 mins)...");
      });
      setResult(res.data);
      setPage("result");
    } catch (e) {
      setError(e.response?.data?.detail || "Something went wrong. Is Colab running?");
    } finally {
      setLoading(false); setStatus("");
    }
  };

  return (
    <div style={S.page}>
      <h1 style={S.title}>Traffic Signal AI</h1>
      <p style={S.sub}>Upload a traffic video → AI detects vehicles → Smart signal decisions</p>

      <div
        style={S.dropzone(drag)}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handleFile(e.dataTransfer.files[0]); }}
        onClick={() => inputRef.current.click()}
      >
        <input ref={inputRef} type="file" accept="video/*" style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files[0])} />
        <div style={{ fontSize: 48, marginBottom: 16 }}>🎬</div>
        {file ? (
          <>
            <div style={{ color: "#00ff87", fontWeight: 700, fontSize: 16 }}>{file.name}</div>
            <div style={{ color: "#4a7090", fontSize: 13, marginTop: 4 }}>
              {(file.size / (1024 * 1024)).toFixed(1)} MB
            </div>
          </>
        ) : (
          <>
            <div style={{ color: "#7090b0", fontSize: 16, fontWeight: 600 }}>
              Drop your traffic video here
            </div>
            <div style={{ color: "#3a5070", fontSize: 13, marginTop: 6 }}>
              MP4, AVI, MOV — up to 200MB
            </div>
          </>
        )}
      </div>

      {loading && (
        <div style={S.progress}>
          <div style={S.bar(progress)} />
        </div>
      )}
      {status && <div style={{ color: "#00b4ff", fontSize: 13, marginTop: 8 }}>{status}</div>}
      {error && <div style={S.error}>⚠️ {error}</div>}

      <button style={S.btn(loading || !file)} onClick={handleSubmit}
        disabled={loading || !file}>
        {loading ? "Processing..." : "Analyze Traffic →"}
      </button>

      <div style={S.steps}>
        {[
          ["📤", "Upload Video", "Any traffic footage"],
          ["🤖", "AI Detection", "YOLOv8 counts vehicles"],
          ["🚦", "Signal Logic", "4-way adaptive timing"],
          ["📊", "Results", "Stats + annotated video"],
        ].map(([icon, title, desc]) => (
          <div key={title} style={S.step}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>{icon}</div>
            <div style={{ color: "#7090b0", fontWeight: 700, fontSize: 13 }}>{title}</div>
            <div style={{ marginTop: 4 }}>{desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
