import { useState } from "react";
import UploadPage from "./pages/UploadPage";
import ResultPage from "./pages/ResultPage";
import HistoryPage from "./pages/HistoryPage";

export default function App() {
  const [page, setPage] = useState("upload");
  const [result, setResult] = useState(null);

  return (
    <div style={{ minHeight: "100vh", background: "#0a0f1e", fontFamily: "'DM Mono', monospace" }}>
      <Nav page={page} setPage={setPage} />
      {page === "upload" && <UploadPage setResult={setResult} setPage={setPage} />}
      {page === "result" && <ResultPage result={result} setPage={setPage} />}
      {page === "history" && <HistoryPage setResult={setResult} setPage={setPage} />}
    </div>
  );
}

function Nav({ page, setPage }) {
  return (
    <nav style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "18px 40px", borderBottom: "1px solid #1e2d4a",
      background: "rgba(10,15,30,0.95)", position: "sticky", top: 0, zIndex: 100,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: "linear-gradient(135deg, #00ff87, #00b4ff)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 16,
        }}>🚦</div>
        <span style={{ color: "#e0f0ff", fontSize: 15, fontWeight: 700, letterSpacing: 1 }}>
          ADAPTIVE TRAFFIC AI
        </span>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {["upload", "history"].map(p => (
          <button key={p} onClick={() => setPage(p)} style={{
            padding: "8px 20px", borderRadius: 6, border: "none", cursor: "pointer",
            background: page === p ? "linear-gradient(135deg, #00ff87, #00b4ff)" : "transparent",
            color: page === p ? "#0a0f1e" : "#7090b0",
            fontWeight: 700, fontSize: 12, letterSpacing: 1,
            textTransform: "uppercase", transition: "all 0.2s",
          }}>{p}</button>
        ))}
      </div>
    </nav>
  );
}
