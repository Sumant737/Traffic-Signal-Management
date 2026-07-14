import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

export const uploadVideo = (file, onProgress) => {
  const formData = new FormData();
  formData.append("file", file);
  return API.post("/upload-video", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (onProgress) onProgress(Math.round((e.loaded * 100) / e.total));
    },
    timeout: 600000, // 10 min timeout for video processing
  });
};

export const getHistory = () => API.get("/history");
export const getRecord = (id) => API.get(`/history/${id}`);
