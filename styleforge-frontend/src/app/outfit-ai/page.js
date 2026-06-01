"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuth } from "../context/AuthContext";
import {
  ArrowLeft,
  Upload,
  Mic,
  Loader2,
  CheckCircle,
  XCircle,
  Sparkles,
} from "lucide-react";
import ImageLightbox from "../components/ImageLightbox";

// Target-class values accepted by the backend
const OCCASION_TO_TARGET_CLASS = {
  Wedding: "long_sleeve_outwear",
  Party: "short_sleeve_top",
  Casual: "trousers",
  "Luxury Event": "long_sleeve_outwear",
};

const API_URL = process.env.NEXT_PUBLIC_AUTH_API_URL || "http://localhost:8000";

const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = (error) => reject(error);
  });
};

export default function OutfitAIPage() {
  const { token, hydrated, authFetch } = useAuth();
  const router = useRouter();

  // Handle auto-trigger of pending outfit on redirect back after login
  useEffect(() => {
    if (!token || !hydrated) return;

    const pendingTrigger = sessionStorage.getItem("pending_outfit_trigger");
    if (pendingTrigger === "true") {
      sessionStorage.removeItem("pending_outfit_trigger");
      const base64Sketch = sessionStorage.getItem("pending_outfit_sketch");
      sessionStorage.removeItem("pending_outfit_sketch");
      const formString = sessionStorage.getItem("pending_outfit_form");
      sessionStorage.removeItem("pending_outfit_form");

      let formState = null;
      if (formString) {
        try {
          formState = JSON.parse(formString);
          if (formState.prompt) setPrompt(formState.prompt);
          if (formState.occasion) setOccasion(formState.occasion);
          if (formState.gender) setGender(formState.gender);
          if (formState.fabric) setFabric(formState.fabric);
        } catch (e) {
          console.error("Failed to parse pending outfit form", e);
        }
      }

      if (base64Sketch) {
        try {
          const arr = base64Sketch.split(',');
          const mime = arr[0].match(/:(.*?);/)[1];
          const bstr = atob(arr[arr.length - 1]);
          let n = bstr.length;
          const u8arr = new Uint8Array(n);
          while (n--) {
            u8arr[n] = bstr.charCodeAt(n);
          }
          const file = new File([u8arr], "pending-outfit-sketch.png", { type: mime });

          setSketchFile(file);
          setSketchPreview(base64Sketch);

          // Auto-trigger rendering
          handleGenerate(file, formState);
        } catch (e) {
          console.error("Failed to restore pending outfit sketch", e);
        }
      }
    }
  }, [token, hydrated]);

  // ── Form state ──────────────────────────────────────────────────────────
  const [prompt, setPrompt] = useState("");
  const [occasion, setOccasion] = useState("");
  const [gender, setGender] = useState("");
  const [fabric, setFabric] = useState("");
  const [sketchFile, setSketchFile] = useState(null);
  const [sketchPreview, setSketchPreview] = useState(null);

  // ── API state ───────────────────────────────────────────────────────────
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resultImage, setResultImage] = useState(null); // object-URL of returned PNG

  // Lightbox & Dynamic Progress Phases State
  const [lightboxSrc, setLightboxSrc] = useState(null);
  const [loadingPhrase, setLoadingPhrase] = useState("");

  const GENERATION_PHRASES = [
    "Analyzing placement sketch...",
    "Tracing geometric silhouettes...",
    "Formulating generative prompt coordinates...",
    "Weaving base fabric structures...",
    "Stitching premium digital seams...",
    "Polishing raw metallic accents...",
    "Tethering lighting matrices...",
    "Ironing creases and drapes...",
    "Finalizing luxury apparel render..."
  ];

  useEffect(() => {
    let timer;
    if (isLoading) {
      let index = 0;
      setLoadingPhrase(GENERATION_PHRASES[0]);
      timer = setInterval(() => {
        index = (index + 1) % GENERATION_PHRASES.length;
        setLoadingPhrase(GENERATION_PHRASES[index]);
      }, 2300); // 20 seconds total / 9 phases ≈ 2.2 - 2.3 seconds per phase feels very natural
    }
    return () => clearInterval(timer);
  }, [isLoading]);

  const fileInputRef = useRef(null);

  // ── Handlers ────────────────────────────────────────────────────────────
  const handleFileChange = useCallback((e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSketchFile(file);
    setSketchPreview(URL.createObjectURL(file));
    setResultImage(null);
    setError(null);
  }, []);

  const handleGenerate = useCallback(async (overrideFile = null, overrideForm = null) => {
    const fileToUse = (overrideFile && overrideFile instanceof Blob) ? overrideFile : sketchFile;
    const currentPrompt = overrideForm ? overrideForm.prompt : prompt;
    const currentOccasion = overrideForm ? overrideForm.occasion : occasion;
    const currentGender = overrideForm ? overrideForm.gender : gender;
    const currentFabric = overrideForm ? overrideForm.fabric : fabric;

    if (!token) {
      const formState = {
        prompt,
        occasion,
        gender,
        fabric,
      };
      sessionStorage.setItem("pending_outfit_form", JSON.stringify(formState));

      if (fileToUse) {
        try {
          const base64 = await fileToBase64(fileToUse);
          sessionStorage.setItem("pending_outfit_sketch", base64);
        } catch (e) {
          console.error("Failed to temporarily save outfit sketch", e);
        }
      }
      sessionStorage.setItem("pending_outfit_trigger", "true");
      router.push("/login?redirect=/outfit-ai");
      return;
    }

    if (!currentPrompt.trim()) {
      setError("Please describe your fashion idea first.");
      return;
    }
    if (!fileToUse) {
      setError("Please upload a sketch or reference image.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResultImage(null);

    try {
      // Build a rich positive_prompt from all text inputs
      const parts = [currentPrompt.trim()];
      if (currentOccasion) parts.push(`occasion: ${currentOccasion}`);
      if (currentGender) parts.push(`for ${currentGender}`);
      if (currentFabric) parts.push(`fabric: ${currentFabric}`);
      const positivePrompt = parts.join(", ");

      // Resolve target_class from occasion
      const targetClass = OCCASION_TO_TARGET_CLASS[currentOccasion] || "long_sleeve_outwear";

      const formData = new FormData();
      formData.append("positive_prompt", positivePrompt);
      formData.append("target_class", targetClass);
      formData.append("sketch_file", fileToUse, fileToUse.name || "sketch.png");

      const headers = {};

      const res = await authFetch(
        `${API_URL}/api/v1/genai/generate/scratch-or-sketch`,
        {
          method: "POST",
          headers,
          body: formData,
        }
      );

      if (!res.ok) {
        let detail = `Error ${res.status}`;
        try {
          const json = await res.json();
          detail = json.detail || detail;
        } catch (_) {}
        throw new Error(detail);
      }

      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      setResultImage(objectUrl);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [prompt, occasion, gender, fabric, sketchFile, token, router]);

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
        <div className="absolute inset-0 bg-black/75"></div>
      </div>

      {/* AMBER GLOW EFFECTS */}
      <div className="absolute top-20 left-20 w-[500px] h-[500px] bg-amber-400/10 blur-3xl rounded-full z-0 pointer-events-none"></div>

      {/* CONTENT */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-10 py-16">
        {/* BACK */}
        <div className="flex items-center justify-between gap-6 mb-12">
          <Link href="/">
            <button className="flex items-center gap-3 px-6 py-3 rounded-full bg-white/10 border border-white/10 backdrop-blur-xl hover:bg-white/20 transition duration-300">
              <ArrowLeft size={18} />
              Back Home
            </button>
          </Link>
        </div>

        {/* TITLE */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[#f6d7b0]/20 bg-[#f6d7b0]/10 mb-6">
            <Sparkles size={16} className="text-[#f6d7b0]" />
            <span className="text-xs tracking-[0.3em] uppercase text-[#f6d7b0]">
              Creative Suite AI
            </span>
          </div>
          <h1 className="text-4xl md:text-6xl font-black leading-tight mb-4 tracking-tight">
            AI OUTFIT CREATOR
          </h1>
          <p className="text-[#d8c7b5] text-base md:text-lg max-w-3xl mx-auto">
            Provide a physical sketch or reference photo alongside customized styling properties to generate a stunning high-fidelity render.
          </p>
        </div>

        {/* MAIN GRID */}
        <div className="grid lg:grid-cols-2 gap-10">
          {/* LEFT SIDE: DESIGN ENGINE CONTROLS */}
          <div className="space-y-6">
            {/* DESIGN FORM CARD */}
            <div className="rounded-[35px] bg-white/10 border border-white/10 backdrop-blur-2xl p-6 space-y-6">
              <div>
                <label className="block text-xs uppercase tracking-[0.3em] text-[#f6d7b0] mb-3">
                  Describe Your Vision
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="e.g. elegant tailored linen coat with geometric buttons, detailed seams..."
                  className="w-full h-[100px] rounded-[20px] bg-black/30 border border-white/10 p-4.5 outline-none backdrop-blur-xl resize-none placeholder:text-white/20 text-sm"
                />
              </div>

              {/* 3-COLUMN COMPACT SELECTORS */}
              <div className="grid grid-cols-3 gap-3">
                {/* OCCASION */}
                <div className="space-y-1.5">
                  <label className="block text-[9px] uppercase tracking-[0.2em] text-[#d8c7b5]/60 font-bold pl-1">
                    Occasion
                  </label>
                  <select
                    value={occasion}
                    onChange={(e) => setOccasion(e.target.value)}
                    className="w-full p-3.5 rounded-xl bg-black/40 border border-white/10 text-xs text-white outline-none cursor-pointer hover:border-white/20 transition"
                  >
                    <option value="">Occasion</option>
                    <option>Wedding</option>
                    <option>Party</option>
                    <option>Casual</option>
                    <option>Luxury Event</option>
                  </select>
                </div>

                {/* GENDER */}
                <div className="space-y-1.5">
                  <label className="block text-[9px] uppercase tracking-[0.2em] text-[#d8c7b5]/60 font-bold pl-1">
                    Gender
                  </label>
                  <select
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    className="w-full p-3.5 rounded-xl bg-black/40 border border-white/10 text-xs text-white outline-none cursor-pointer hover:border-white/20 transition"
                  >
                    <option value="">Gender</option>
                    <option>Male</option>
                    <option>Female</option>
                    <option>Unisex</option>
                  </select>
                </div>

                {/* FABRIC */}
                <div className="space-y-1.5">
                  <label className="block text-[9px] uppercase tracking-[0.2em] text-[#d8c7b5]/60 font-bold pl-1">
                    Fabric
                  </label>
                  <select
                    value={fabric}
                    onChange={(e) => setFabric(e.target.value)}
                    className="w-full p-3.5 rounded-xl bg-black/40 border border-white/10 text-xs text-white outline-none cursor-pointer hover:border-white/20 transition"
                  >
                    <option value="">Fabric</option>
                    <option>Silk</option>
                    <option>Velvet</option>
                    <option>Leather</option>
                    <option>Cotton</option>
                  </select>
                </div>
              </div>
            </div>

            {/* REFERENCE INPUTS (UPLOAD & VOICE) */}
            <div className="grid grid-cols-2 gap-4">
              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
                className="hidden"
                id="sketch-file-input"
              />

              {/* UPLOAD CARD */}
              <div
                className={`p-6 rounded-[25px] border cursor-pointer backdrop-blur-xl transition duration-300 ${
                  sketchPreview
                    ? "border-green-500/40 bg-green-500/5 hover:bg-green-500/10"
                    : "border-white/10 bg-white/10 hover:bg-white/15"
                }`}
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="flex flex-col items-center text-center gap-2">
                  {sketchPreview ? (
                    <div 
                      className="flex flex-col items-center gap-2"
                      onClick={(e) => {
                        e.stopPropagation(); // prevent clicking key thumbnail to trigger input browse
                        setLightboxSrc(sketchPreview);
                      }}
                    >
                      <div className="relative w-16 h-16 rounded-xl overflow-hidden bg-black/40 border border-white/10 cursor-zoom-in">
                        <img
                          src={sketchPreview}
                          alt="Sketch Preview"
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <p className="text-xs font-bold text-green-300">Sketch Loaded</p>
                      <p className="text-[10px] text-[#d8c7b5] truncate max-w-[130px]">
                        Click Thumbnail to Zoom
                      </p>
                    </div>
                  ) : (
                    <>
                      <Upload size={28} className="text-[#f6d7b0]" />
                      <p className="text-xs font-bold">Reference Sketch</p>
                      <p className="text-[10px] text-[#d8c7b5]/60">
                        Upload image or layout outline
                      </p>
                    </>
                  )}
                </div>
              </div>

              {/* VOICE CARD */}
              <div className="p-6 rounded-[25px] bg-white/10 border border-white/10 backdrop-blur-xl hover:bg-white/15 transition duration-300">
                <div className="flex flex-col items-center text-center gap-2">
                  <Mic size={28} className="text-[#f6d7b0]" />
                  <p className="text-xs font-bold">Voice Prompt</p>
                  <p className="text-[10px] text-[#d8c7b5]/60">
                    Dictate design specs audibly
                  </p>
                </div>
              </div>
            </div>

            {/* ERROR DISPLAY */}
            {error && (
              <div className="flex items-center gap-3 p-4.5 rounded-[20px] bg-red-500/10 border border-red-500/30 text-red-200 text-xs font-semibold leading-relaxed">
                <XCircle size={16} className="text-red-400 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* PROCESS TRIGGER */}
            <button
              onClick={handleGenerate}
              disabled={isLoading}
              className="w-full py-5 rounded-full bg-[#f6d7b0] text-black font-extrabold text-lg hover:scale-105 transition disabled:opacity-50 disabled:hover:scale-100 flex items-center justify-center gap-3 shadow-lg shadow-amber-300/5 cursor-pointer"
            >
              {isLoading ? (
                <>
                  <Loader2 size={22} className="animate-spin" />
                  Generating Rendering…
                </>
              ) : (
                <>
                  <Sparkles size={20} />
                  Generate AI Outfit (10 Credits)
                </>
              )}
            </button>
          </div>

          {/* RIGHT SIDE: INTERACTIVE PORTFOLIO/RESULT PANEL */}
          <div>
            <div className="min-h-[480px] h-full rounded-[40px] overflow-hidden border border-white/10 bg-white/10 backdrop-blur-2xl p-8 flex flex-col items-center justify-center">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center text-center max-w-sm">
                  <div className="relative mb-8">
                    <div className="w-16 h-16 rounded-full border-4 border-t-[#f6d7b0] border-r-white/5 border-b-white/5 border-l-white/5 animate-spin"></div>
                    <Sparkles size={24} className="absolute inset-0 m-auto text-[#f6d7b0] animate-pulse" />
                  </div>
                  <h3 className="text-2xl font-bold mb-2 text-[#f6d7b0] animate-pulse h-[40px] flex items-center justify-center text-center">
                    {loadingPhrase}
                  </h3>
                  <p className="text-sm text-[#d8c7b5]/60 leading-relaxed">
                    Compiling your high-fidelity luxury render on ComfyUI GPU node...
                  </p>
                </div>
              ) : resultImage ? (
                <div className="flex flex-col items-center gap-6 w-full">
                  <div className="rounded-[25px] overflow-hidden border border-white/10 shadow-2xl max-w-sm w-full bg-black/40">
                    <img
                      src={resultImage}
                      alt="AI generated outfit"
                      className="w-full h-auto object-cover cursor-zoom-in"
                      onClick={() => setLightboxSrc(resultImage)}
                    />
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setLightboxSrc(resultImage);
                    }}
                    className="px-8 py-3 rounded-full bg-white/10 border border-white/15 hover:bg-white/20 hover:border-white/30 transition text-sm font-semibold cursor-pointer"
                  >
                    Inspect Fullscreen
                  </button>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center text-center max-w-sm">
                  <Sparkles size={48} className="text-[#f6d7b0] mb-6 animate-bounce" />
                  <h3 className="text-2xl font-black mb-2">Visualizer Screen</h3>
                  <p className="text-sm text-[#d8c7b5]/60 leading-relaxed">
                    Set up your dream design specs and upload a placement sketch on the left. The high-fidelity rendering will generate here.
                  </p>
                </div>
              )}
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