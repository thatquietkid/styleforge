"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import {
  ArrowLeft,
  Upload,
  Sparkles,
  Loader2,
  CheckCircle,
  XCircle,
  Coins,
  History,
  AlertTriangle,
  Cpu,
} from "lucide-react";
import ImageLightbox from "../components/ImageLightbox";

const API_URL = process.env.NEXT_PUBLIC_AUTH_API_URL || "http://localhost:8000";

const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = (error) => reject(error);
  });
};

// Custom parser to translate Ollama/Qwen markdown into styled luxury panels
function renderPremiumCritique(markdownText) {
  if (!markdownText) return null;

  // Split response into sections using the '###' markdown headers
  const sections = markdownText.split(/###\s+/);
  const elements = [];

  sections.forEach((section, idx) => {
    if (!section.trim()) return;

    const lines = section.split("\n");
    const title = lines[0].trim();
    const contentLines = lines.slice(1).filter(l => l.trim());

    // Custom icons for each section to look premium
    let sectionIcon = <Sparkles size={20} className="text-[#f6d7b0]" />;
    if (title.toLowerCase().includes("core issue")) {
      sectionIcon = <AlertTriangle size={20} className="text-amber-400" />;
    } else if (title.toLowerCase().includes("aesthetic")) {
      sectionIcon = <Sparkles size={20} className="text-purple-400" />;
    } else if (title.toLowerCase().includes("execution")) {
      sectionIcon = <CheckCircle size={20} className="text-green-400" />;
    }

    elements.push(
      <div
        key={idx}
        className="p-6 rounded-[25px] bg-black/40 border border-white/10 backdrop-blur-md space-y-4 hover:border-white/20 transition duration-300"
      >
        <div className="flex items-center gap-3 border-b border-white/5 pb-3">
          {sectionIcon}
          <h3 className="text-xl font-bold tracking-wide text-[#f6d7b0] uppercase">
            {title}
          </h3>
        </div>
        <ul className="space-y-3">
          {contentLines.map((line, lIdx) => {
            const cleanLine = line.replace(/^-\s*\*\*/, "").replace(/^-\s*/, "");
            const parts = cleanLine.split(":**");
            if (parts.length > 1) {
              // Styled bullet with bold prefix
              return (
                <li key={lIdx} className="flex gap-3 text-sm text-[#d8c7b5] leading-relaxed">
                  <span className="text-[#f6d7b0] mt-1.5">•</span>
                  <span>
                    <strong className="text-white font-semibold">{parts[0]}:</strong>
                    {parts.slice(1).join(":")}
                  </span>
                </li>
              );
            }
            return (
              <li key={lIdx} className="flex gap-3 text-sm text-[#d8c7b5] leading-relaxed">
                <span className="text-[#f6d7b0] mt-1.5">•</span>
                <span>{cleanLine}</span>
              </li>
            );
          })}
        </ul>
      </div>
    );
  });

  return <div className="space-y-6">{elements}</div>;
}

export default function StyleCritiquePage() {
  const { token, hydrated, authFetch } = useAuth();
  const router = useRouter();

  // Handle auto-trigger of pending critique on redirect back after login
  useEffect(() => {
    if (!token || !hydrated) return;

    const pendingTrigger = sessionStorage.getItem("pending_critique_trigger");
    if (pendingTrigger === "true") {
      sessionStorage.removeItem("pending_critique_trigger");
      const base64Img = sessionStorage.getItem("pending_critique_image");
      sessionStorage.removeItem("pending_critique_image");

      if (base64Img) {
        try {
          const arr = base64Img.split(',');
          const mime = arr[0].match(/:(.*?);/)[1];
          const bstr = atob(arr[1]);
          let n = bstr.length;
          const u8arr = new Uint8Array(n);
          while (n--) {
            u8arr[n] = bstr.charCodeAt(n);
          }
          const file = new File([u8arr], "pending-critique-image.png", { type: mime });

          setImageFile(file);
          setImagePreview(base64Img);

          // Auto-trigger analysis
          handleCritique(file);
        } catch (e) {
          console.error("Failed to restore pending critique image", e);
        }
      }
    }
  }, [token, hydrated]);

  // State management
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [credits, setCredits] = useState(null);
  const [history, setHistory] = useState([]);
  
  // API states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [critique, setCritique] = useState(null);
  const [preflightStatus, setPreflightStatus] = useState("checking"); // checking | online | offline

  // Lightbox & Dynamic Loading Phrases State
  const [lightboxSrc, setLightboxSrc] = useState(null);
  const [loadingPhrase, setLoadingPhrase] = useState("");

  const CRITIQUE_PHRASES = [
    "Analyzing portrait composition...",
    "Scanning collar, sleeves, and pants seams...",
    "Measuring fit cuts & tailoring drape specs...",
    "Evaluating outfit color palette cohesion...",
    "Cross-referencing global style trends ledger...",
    "Consulting fashion director criteria...",
    "Compiling sartorial aesthetic diagnostics...",
    "Drafting final critique execution report..."
  ];

  useEffect(() => {
    let timer;
    if (loading) {
      let index = 0;
      setLoadingPhrase(CRITIQUE_PHRASES[0]);
      timer = setInterval(() => {
        index = (index + 1) % CRITIQUE_PHRASES.length;
        setLoadingPhrase(CRITIQUE_PHRASES[index]);
      }, 2500);
    }
    return () => clearInterval(timer);
  }, [loading]);

  const fileInputRef = useRef(null);

  // Fetch credits and past history
  const fetchData = useCallback(async () => {
    if (!token) return;
    const headers = {};

    // Fetch credits
    try {
      const credRes = await authFetch(`${API_URL}/api/v1/genai/credits`, { headers });
      if (credRes.ok) {
        const data = await credRes.json();
        setCredits(data.credits);
      }
    } catch (_) {}

    // Fetch past critiques
    try {
      const histRes = await authFetch(
        `${API_URL}/api/v1/genai/analyze/style-critique/me?limit=3`,
        { headers }
      );
      if (histRes.ok) {
        const data = await histRes.json();
        setHistory(data);
      }
    } catch (_) {}
  }, [token, authFetch]);

  // Preflight check for local Ollama / Qwen model availability
  const checkPreflight = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/genai/health`);
      if (res.ok) {
        setPreflightStatus("online");
      } else {
        setPreflightStatus("offline");
      }
    } catch (_) {
      setPreflightStatus("offline");
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchData();
      checkPreflight();
    }
  }, [token, fetchData, checkPreflight]);

  const handleFileChange = useCallback((e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    setCritique(null);
    setError(null);
  }, []);

  const handleCritique = useCallback(async (overrideFile = null) => {
    const fileToUse = (overrideFile && overrideFile instanceof Blob) ? overrideFile : imageFile;
    if (!token) {
      if (fileToUse) {
        try {
          const base64 = await fileToBase64(fileToUse);
          sessionStorage.setItem("pending_critique_image", base64);
          sessionStorage.setItem("pending_critique_trigger", "true");
        } catch (e) {
          console.error("Failed to temporarily save critique image", e);
        }
      }
      router.push("/login?redirect=/style-critique");
      return;
    }
    if (!fileToUse) {
      setError("Please select or drop an image file first.");
      return;
    }

    setLoading(true);
    setError(null);
    setCritique(null);

    try {
      const formData = new FormData();
      formData.append("image", fileToUse);

      const headers = {};

      const res = await authFetch(`${API_URL}/api/v1/genai/analyze/style-critique`, {
        method: "POST",
        headers,
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        let msg = "Failed to run critique. Please try again.";
        if (data.detail) {
          msg = typeof data.detail === "string" ? data.detail : data.detail.detail || msg;
        }
        throw new Error(msg);
      }

      setCritique(data);
      // Refresh user credits and list
      fetchData();
    } catch (err) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  }, [imageFile, token, fetchData]);

  const handleSelectHistory = useCallback((histItem) => {
    setCritique({
      critique_id: histItem.critique_id,
      markdown: histItem.markdown,
      image_url: histItem.image_url,
      created_at: histItem.created_at,
    });
    setImagePreview(histItem.image_url.startsWith("/uploads/") ? `${API_URL}${histItem.image_url}` : histItem.image_url);
    setImageFile(null);
    setError(null);
  }, []);

  return (
    <main className="relative min-h-screen text-white overflow-hidden">
      {/* BACKGROUND */}
      <div className="absolute inset-0">
        <Image
          src="/IMG_5120.JPG"
          alt="Background"
          fill
          priority
          className="object-cover"
        />
        <div className="absolute inset-0 bg-black/80"></div>
      </div>

      {/* BLURRY ACCENT ORBS */}
      <div className="absolute top-20 right-20 w-[400px] h-[400px] bg-purple-500/10 blur-3xl rounded-full"></div>
      <div className="absolute bottom-20 left-20 w-[400px] h-[400px] bg-amber-500/10 blur-3xl rounded-full"></div>

      {/* CONTENT */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-10 py-16">
        {/* TOP BAR */}
        <div className="flex flex-wrap items-center justify-between gap-6 mb-12">
          <Link href="/">
            <button className="flex items-center gap-3 px-6 py-3 rounded-full bg-white/10 border border-white/10 backdrop-blur-xl hover:bg-white/20 transition duration-300">
              <ArrowLeft size={18} />
              Back Home
            </button>
          </Link>

          {/* CREDITS BADGE */}
          <div className="flex items-center gap-3 px-5 py-3 rounded-full bg-white/10 border border-white/10 backdrop-blur-xl">
            <Coins size={18} className="text-[#f6d7b0]" />
            <span className="text-sm font-semibold tracking-wide text-[#d8c7b5]">
              AI Balance:
            </span>
            <span className="text-[#f6d7b0] font-bold text-lg">
              {credits !== null ? `${credits} credits` : "---"}
            </span>
          </div>
        </div>

        {/* TITLE */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[#f6d7b0]/20 bg-[#f6d7b0]/10 mb-6">
            <Sparkles size={16} className="text-[#f6d7b0]" />
            <span className="text-xs tracking-[0.3em] uppercase text-[#f6d7b0]">
              Style Critique AI
            </span>
          </div>
          <h1 className="text-4xl md:text-6xl font-black leading-tight mb-4 tracking-tight">
            EDITORIAL FASHION CRITIQUE
          </h1>
          <p className="text-[#d8c7b5] text-base md:text-lg max-w-3xl mx-auto">
            Upload an outfit photograph to receive immediate, professional styling reviews powered by our local fashion intelligence engine.
          </p>
        </div>

        {/* MODEL PREFLIGHT BANNER */}
        {preflightStatus === "offline" && (
          <div className="flex items-center gap-4 p-5 rounded-3xl bg-amber-500/10 border border-amber-500/25 mb-10 text-amber-200">
            <Cpu size={24} className="flex-shrink-0 animate-pulse text-[#f6d7b0]" />
            <div>
              <h4 className="font-bold text-[#f6d7b0]">Local LLM Service Notice</h4>
              <p className="text-xs text-[#d8c7b5]">
                The Ollama fashion intelligence daemon is currently offline. Please ensure <strong>ollama serve</strong> is running and model <strong>qwen3.5:9b</strong> is pulled locally.
              </p>
            </div>
          </div>
        )}

        {/* MAIN BODY GRID */}
        <div className="grid lg:grid-cols-12 gap-10">
          {/* LEFT SIDE: UPLOAD & ACTIONS (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* FILE UPLOAD CARD */}
            <div className="rounded-[35px] bg-white/10 border border-white/10 backdrop-blur-2xl p-6">
              <label className="block text-xs uppercase tracking-[0.3em] text-[#f6d7b0] mb-4">
                Select Outfit Portrait
              </label>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
                className="hidden"
              />

              <div
                onClick={() => fileInputRef.current?.click()}
                className={`group border-2 border-dashed rounded-[25px] p-8 text-center cursor-pointer transition duration-300 ${
                  imagePreview
                    ? "border-green-500/40 bg-green-500/5"
                    : "border-white/15 hover:border-[#f6d7b0]/40 bg-black/25"
                }`}
              >
                <div className="flex flex-col items-center justify-center gap-4">
                  {imagePreview ? (
                    <div className="space-y-4 w-full">
                      <div className="relative w-full h-[220px] rounded-2xl overflow-hidden bg-black/40 cursor-zoom-in">
                        <img
                          src={imagePreview}
                          alt="Outfit Preview"
                          className="w-full h-full object-contain"
                          onClick={(e) => {
                            e.stopPropagation();
                            setLightboxSrc(imagePreview);
                          }}
                        />
                      </div>
                      <div className="flex items-center justify-center gap-2 text-green-400 font-semibold text-sm">
                        <CheckCircle size={16} />
                        Image loaded successfully (Click to Zoom)
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="p-4 rounded-full bg-white/5 group-hover:bg-[#f6d7b0]/15 transition duration-300">
                        <Upload size={32} className="text-[#f6d7b0]" />
                      </div>
                      <div>
                        <p className="font-semibold text-base mb-1">Click to Upload</p>
                        <p className="text-[#d8c7b5] text-xs">
                          Accepts JPEG, PNG or WebP up to 5 MB
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* ERROR CARD */}
            {error && (
              <div className="flex gap-3 p-5 rounded-[25px] bg-red-500/10 border border-red-500/30 text-red-200 text-sm">
                <XCircle size={20} className="flex-shrink-0 mt-0.5 text-red-400" />
                <div className="space-y-1">
                  <h5 className="font-bold">Critique Analysis Failed</h5>
                  <p className="text-xs text-[#d8c7b5] leading-relaxed">{error}</p>
                </div>
              </div>
            )}

            {/* ACTION BUTTON */}
            <button
              onClick={handleCritique}
              disabled={loading || preflightStatus === "offline"}
              className="w-full py-5 rounded-full bg-[#f6d7b0] text-black font-bold text-lg hover:scale-105 transition duration-300 disabled:opacity-50 disabled:hover:scale-100 flex items-center justify-center gap-3 shadow-lg shadow-amber-500/5"
            >
              {loading ? (
                <>
                  <Loader2 size={22} className="animate-spin" />
                  Stylist is analyzing…
                </>
              ) : (
                <>
                  <Sparkles size={20} />
                  Critique Outfit (Costs 5 Credits)
                </>
              )}
            </button>

            {/* HISTORY CARDS */}
            {history.length > 0 && (
              <div className="rounded-[35px] bg-white/10 border border-white/10 backdrop-blur-2xl p-6 space-y-4">
                <h3 className="text-xs uppercase tracking-[0.3em] text-[#f6d7b0] flex items-center gap-2">
                  <History size={14} />
                  Your Past Critiques
                </h3>

                <div className="space-y-3">
                  {history.map((item, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleSelectHistory(item)}
                      className="p-3 rounded-2xl bg-black/40 border border-white/5 flex items-center gap-4 cursor-pointer hover:bg-white/5 hover:border-white/10 transition duration-300"
                    >
                      <div className="relative w-12 h-12 rounded-xl overflow-hidden bg-black flex-shrink-0">
                        <img
                          src={item.image_url.startsWith("/uploads/") ? `${API_URL}${item.image_url}` : item.image_url}
                          alt="Past Outfit"
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-semibold text-white truncate">
                          Outfit Analysis #{item.critique_id}
                        </h4>
                        <p className="text-xs text-[#d8c7b5] truncate mt-0.5">
                          {new Date(item.created_at).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* RIGHT SIDE: CRITIQUE BOARD (7 cols) */}
          <div className="lg:col-span-7">
            <div className="min-h-[600px] h-full rounded-[40px] overflow-hidden border border-white/10 bg-white/10 backdrop-blur-2xl p-8 flex flex-col">
              <AnimatePresence mode="wait">
                {critique ? (
                  <motion.div
                    key="critique-content"
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -15 }}
                    className="space-y-8 flex-1"
                  >
                    <div className="flex items-center justify-between border-b border-white/10 pb-5">
                      <div>
                        <h2 className="text-3xl font-extrabold tracking-tight">Style Report</h2>
                        <p className="text-xs text-[#d8c7b5] mt-1 uppercase tracking-wider">
                          Critique ID: #{critique.critique_id} • Analyzed on {new Date().toLocaleDateString()}
                        </p>
                      </div>
                      <Sparkles size={28} className="text-[#f6d7b0] animate-pulse" />
                    </div>

                    <div className="flex-1">
                      {renderPremiumCritique(critique.markdown)}
                    </div>
                  </motion.div>
                ) : loading ? (
                  <motion.div
                    key="critique-loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex flex-col items-center justify-center flex-1 text-center py-20"
                  >
                    <div className="relative mb-8">
                      <div className="w-16 h-16 rounded-full border-4 border-t-[#f6d7b0] border-r-white/5 border-b-white/5 border-l-white/5 animate-spin"></div>
                      <Sparkles size={24} className="absolute inset-0 m-auto text-[#f6d7b0] animate-pulse" />
                    </div>
                    <h2 className="text-2xl font-bold mb-3 text-[#f6d7b0] animate-pulse h-[40px] flex items-center justify-center text-center">
                      {loadingPhrase}
                    </h2>
                    <p className="text-[#c8b8a7] max-w-sm text-sm">
                      Our Fashion Intelligence Model is dissecting garment weights, fits, tailoring cuts, and aesthetic coordinates.
                    </p>
                  </motion.div>
                ) : (
                  <motion.div
                    key="critique-empty"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex flex-col items-center justify-center flex-1 text-center py-20"
                  >
                    <Sparkles size={64} className="text-[#f6d7b0] mb-8 animate-bounce" />
                    <h2 className="text-3xl font-black mb-3">Critique Board</h2>
                    <p className="text-[#c8b8a7] max-w-xs text-sm">
                      Please load a fashion image on the left panel and submit to view your custom editorial style breakdown.
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
      {lightboxSrc && (
        <ImageLightbox
          src={lightboxSrc}
          downloadUrl={lightboxSrc}
          onClose={() => setLightboxSrc(null)}
        />
      )}
    </main>
  );
}
