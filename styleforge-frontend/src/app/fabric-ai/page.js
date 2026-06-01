"use client";

import Image from "next/image";
import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import { ArrowLeft, Sliders, Loader2, AlertCircle } from "lucide-react";
import ImageLightbox from "../components/ImageLightbox";

const API_URL = process.env.NEXT_PUBLIC_AUTH_API_URL || "http://localhost:8000";

export default function FabricAIPage() {
  const { token, hydrated, authFetch } = useAuth();
  const router = useRouter();

  // Form State
  const [fabric, setFabric] = useState("Silk");
  const [color, setColor] = useState("#d8c7b5");
  const [weight, setWeight] = useState(50);
  const [stiffness, setStiffness] = useState(30);

  // Simulation State
  const [isSimulating, setIsSimulating] = useState(false);
  const [result, setResult] = useState(null);

  // Lightbox & Dynamic Loading Phrases State
  const [lightboxSrc, setLightboxSrc] = useState(null);
  const [loadingPhrase, setLoadingPhrase] = useState("");

  const SIMULATION_PHRASES = [
    "Initializing cloth physics grids...",
    "Calculating GSM fiber densities...",
    "Applying gravity & wind matrices...",
    "Simulating textile drape stiffness...",
    "Calculating velvet pile light reflections...",
    "Stretching warp and weft fabric yarns...",
    "Bespoke custom dye spectrum infusion...",
    "Compiling real-time draping simulation..."
  ];

  useEffect(() => {
    let timer;
    if (isSimulating) {
      let index = 0;
      setLoadingPhrase(SIMULATION_PHRASES[0]);
      timer = setInterval(() => {
        index = (index + 1) % SIMULATION_PHRASES.length;
        setLoadingPhrase(SIMULATION_PHRASES[index]);
      }, 2500);
    }
    return () => clearInterval(timer);
  }, [isSimulating]);

  // Restore form and trigger simulation if redirected back after login
  useEffect(() => {
    if (!token || !hydrated) return;

    const pendingTrigger = sessionStorage.getItem("pending_fabric_trigger");
    if (pendingTrigger === "true") {
      sessionStorage.removeItem("pending_fabric_trigger");
      const formString = sessionStorage.getItem("pending_fabric_form");
      sessionStorage.removeItem("pending_fabric_form");

      if (formString) {
        try {
          const formState = JSON.parse(formString);
          if (formState.fabric) setFabric(formState.fabric);
          if (formState.color) setColor(formState.color);
          if (formState.weight) setWeight(formState.weight);
          if (formState.stiffness) setStiffness(formState.stiffness);

          // Auto-trigger simulation
          handleSimulate(formState);
        } catch (e) {
          console.error("Failed to restore pending fabric simulation", e);
        }
      }
    }
  }, [token, hydrated]);

const getWeightLabel = (w) => (w < 33 ? "Light" : w < 66 ? "Medium" : "Heavy");
const getStiffnessLabel = (s) => (s < 33 ? "Fluid" : s < 66 ? "Structured" : "Stiff");

  const handleSimulate = async (overrideForm = null) => {
    const hasOverride = overrideForm && typeof overrideForm === "object" && "fabric" in overrideForm;
    const currentFabric = hasOverride ? overrideForm.fabric : fabric;
    const currentColor = hasOverride ? overrideForm.color : color;
    const currentWeight = hasOverride ? overrideForm.weight : weight;
    const currentStiffness = hasOverride ? overrideForm.stiffness : stiffness;

    if (!token) {
      const formState = {
        fabric,
        color,
        weight,
        stiffness,
      };
      sessionStorage.setItem("pending_fabric_form", JSON.stringify(formState));
      sessionStorage.setItem("pending_fabric_trigger", "true");
      router.push("/login?redirect=/fabric-ai");
      return;
    }

    setIsSimulating(true);
    setResult(null);

    try {
      const headers = {
        "Content-Type": "application/json",
      };

      const response = await authFetch(`${API_URL}/api/v1/genai/fabric/simulate`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          fabric: currentFabric,
          color: currentColor,
          weight: currentWeight,
          stiffness: currentStiffness,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        let msg = "Failed to compile fabric physics simulation.";
        if (data.detail) {
          msg = typeof data.detail === "string" ? data.detail : data.detail.detail || msg;
        }
        throw new Error(msg);
      }

      setResult(data);
    } catch (error) {
      console.error("Simulation error:", error);
      setResult({
        status: "error",
        message: error.message || "An unexpected error occurred during drape compilation.",
      });
    } finally {
      setIsSimulating(false);
    }
  };

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
        <div className="absolute inset-0 bg-black/70"></div>
      </div>

      {/* CONTENT */}
      <div className="relative z-10 max-w-6xl mx-auto px-8 py-20">
        {/* BACK */}
        <Link href="/">
          <button className="flex items-center gap-3 mb-14 px-6 py-3 rounded-full bg-white/10 border border-white/10 backdrop-blur-md hover:bg-white/20 transition">
            <ArrowLeft size={20} />
            Back Home
          </button>
        </Link>

        {/* TITLE */}
        <div className="text-center mb-20">
          <h1 className="text-6xl md:text-7xl font-black mb-6">
            FABRIC SIMULATION
          </h1>
          <p className="text-[#d8c7b5] text-lg">
            Visualize raw luxury textiles interacting with realistic light, folds, and draping.
          </p>
        </div>

        {/* FORM */}
        <div className="grid md:grid-cols-2 gap-10">
          {/* LEFT: TEXTILE CONTROLS */}
          <div className="space-y-6">
            <div className="p-6 rounded-[30px] bg-white/10 border border-white/10 backdrop-blur-xl">
              <label className="block text-sm font-bold tracking-wider text-[#f6d7b0] mb-3 uppercase">
                Select Premium Base
              </label>
              <select
                value={fabric}
                onChange={(e) => setFabric(e.target.value)}
                className="w-full p-5 rounded-2xl bg-black/40 border border-white/10 text-white outline-none cursor-pointer"
              >
                {/* Extended Fabric Library */}
                <option value="Silk">Banarasi Silk (Stiff, High Luster)</option>
                <option value="Velvet">Royal Velvet (Heavy, High Pile Reflection)</option>
                <option value="Linen">Pure Linen (Light, Crisp Folds)</option>
                <option value="Satin">Premium Satin (Fluid, Smooth Flow)</option>
                <option value="Cashmere">Plush Cashmere (Soft, Dense Matte)</option>
                <option value="Chiffon">Sheer Chiffon (Ultra-light, Translucent)</option>
                <option value="Organza">Crisp Organza (Stiff, Sheer Structure)</option>
                <option value="Tweed">Heavy Tweed (Textured, Coarse Weave)</option>
                <option value="Leather">Premium Leather (Smooth, High Specular)</option>
                <option value="Brocade">Ornate Brocade (Embossed, Metallic Threads)</option>
                <option value="Denim">Raw Denim (Sturdy, Diagonal Twill)</option>
                <option value="Tulle">Fine Tulle (Netting, Ethereal Volume)</option>
              </select>
            </div>

            {/* DRAPE AND WEIGHT SLIDERS */}
            <div className="p-6 rounded-[30px] bg-white/10 border border-white/10 backdrop-blur-xl space-y-6">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-bold tracking-wider text-[#f6d7b0] uppercase">
                    Fabric Weight (GSM)
                  </span>
                  <span className="text-[#d8c7b5] text-sm">
                    {getWeightLabel(weight)} ({weight})
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="100"
                  value={weight}
                  onChange={(e) => setWeight(Number(e.target.value))}
                  className="w-full accent-[#f6d7b0] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-bold tracking-wider text-[#f6d7b0] uppercase">
                    Drape Stiffness
                  </span>
                  <span className="text-[#d8c7b5] text-sm">
                    {getStiffnessLabel(stiffness)} ({stiffness})
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="100"
                  value={stiffness}
                  onChange={(e) => setStiffness(Number(e.target.value))}
                  className="w-full accent-[#f6d7b0] cursor-pointer"
                />
              </div>
            </div>

            {/* COLOR Spectrum */}
            <div className="p-6 rounded-[30px] bg-white/10 border border-white/10 backdrop-blur-xl">
              <label className="block text-sm font-bold tracking-wider text-[#f6d7b0] mb-3 uppercase">
                Custom Dye Spectrum
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  className="w-16 h-16 rounded-xl border border-white/10 bg-transparent cursor-pointer"
                />
                <div>
                  <p className="font-semibold text-lg">
                    Hex Value: {color.toUpperCase()}
                  </p>
                  <p className="text-sm text-[#d8c7b5]">
                    Adjust dye concentration levels
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT: VIEWPORT CONTAINER */}
          <div className="space-y-6 flex flex-col justify-between">
            <div className="relative h-[380px] rounded-[30px] bg-white/10 border border-white/10 flex flex-col items-center justify-center p-8 text-center overflow-hidden">
              
              {/* Only show the dark gradient overlay if we are NOT showing the rendered image */}
              {(!result || result.status !== "success") && (
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent z-10" />
              )}

              {/* Dynamic Viewport Content based on state */}
              {isSimulating ? (
                <div className="relative z-20 flex flex-col items-center">
                  <Loader2 size={40} className="mb-4 text-[#f6d7b0] animate-spin" />
                  <h2 className="text-2xl font-bold mb-2 text-[#f6d7b0] animate-pulse h-[40px] flex items-center justify-center text-center">
                    {loadingPhrase}
                  </h2>
                  <p className="text-[#d8c7b5] max-w-sm">
                    Sending parameters to GPU backend. Please wait.
                  </p>
                </div>
              ) : result ? (
                result.status === "success" ? (
                  // ELEGANT RENDER VIEW: Image takes up the entire container seamlessly
                  <img
                    src={result.render_base64}
                    alt="Generated Fabric"
                    className="absolute inset-0 w-full h-full object-cover z-20 transition-opacity duration-700 animate-in fade-in cursor-zoom-in"
                    onClick={() => setLightboxSrc(result.render_base64)}
                  />
                ) : (
                  <div className="relative z-20 flex flex-col items-center">
                    <AlertCircle size={40} className="mb-4 text-red-400" />
                    <h2 className="text-3xl font-bold mb-2 text-red-400">Connection Failed</h2>
                    <p className="text-[#d8c7b5] max-w-sm">
                      {result.message}
                    </p>
                  </div>
                )
              ) : (
                <div className="relative z-20 flex flex-col items-center">
                  <Sliders size={40} className="mb-4 text-[#f6d7b0] animate-pulse" />
                  <h2 className="text-3xl font-bold mb-2">Simulation Engine Ready</h2>
                  <p className="text-[#d8c7b5] max-w-sm">
                    Awaiting physics compilation for <span className="text-[#f6d7b0] font-bold">{fabric}</span> weave patterns.
                  </p>
                </div>
              )}
            </div>

            <button 
              onClick={handleSimulate}
              disabled={isSimulating}
              className="w-full py-5 rounded-full bg-[#f6d7b0] text-black font-bold text-lg hover:scale-105 transition shadow-2xl disabled:opacity-50 disabled:hover:scale-100 flex justify-center items-center gap-2"
            >
              {isSimulating ? (
                <>
                  <Loader2 size={24} className="animate-spin" />
                  Processing on GPU...
                </>
              ) : (
                "Simulate Fabric Physics"
              )}
            </button>
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