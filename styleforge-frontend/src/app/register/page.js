"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuth } from "../context/AuthContext";
import { Sparkles, ArrowLeft, Loader2, XCircle } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const { setToken } = useAuth();

  // Form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const API_URL = process.env.NEXT_PUBLIC_AUTH_API_URL || "http://localhost:8000";

  const handleRegister = async (e) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Registration failed. Please try again.");
      }

      // Registration successful — redirect to login
      router.push("/login");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="relative min-h-screen flex items-center justify-center overflow-hidden text-white">
      {/* BACK HOME BUTTON */}
      <div className="absolute top-8 left-8 z-50">
        <Link href="/">
          <button className="flex items-center gap-3 px-5 py-2.5 rounded-full bg-white/10 border border-white/10 backdrop-blur-xl hover:bg-white/20 transition duration-300 text-sm font-medium cursor-pointer">
            <ArrowLeft size={16} />
            Back Home
          </button>
        </Link>
      </div>

      {/* BACKGROUND */}
      <div className="absolute inset-0 z-0">
        <Image
          src="/IMG_5120.JPG"
          alt="Studio Background"
          fill
          priority
          className="object-cover"
        />
        <div className="absolute inset-0 bg-[#0f0d0b]/80 backdrop-blur-sm"></div>
      </div>

      {/* AMBER GLOW EFFECTS */}
      <div className="absolute w-[500px] h-[500px] bg-amber-400/10 blur-3xl rounded-full z-0 pointer-events-none"></div>

      {/* REGISTER CARD */}
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-[95%] max-w-lg bg-[#161311]/70 border border-white/10 backdrop-blur-2xl rounded-[40px] p-8 md:p-12 shadow-2xl"
      >
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#f6d7b0]/20 bg-[#f6d7b0]/5 mb-4">
            <Sparkles size={14} className="text-[#f6d7b0]" />
            <span className="text-[10px] tracking-[0.2em] uppercase text-[#f6d7b0] font-bold">
              Join the Studio
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight leading-none">
            STYLEFORGE
          </h1>
          <p className="text-[#d8c7b5]/60 text-sm mt-3 font-semibold uppercase tracking-wider">
            Create Studio Account
          </p>
        </div>

        {/* ERROR DISPLAY */}
        {error && (
          <div className="mb-6 flex items-start gap-3 p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-200 text-xs font-semibold leading-relaxed">
            <XCircle size={16} className="text-red-400 mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* FORM */}
        <form onSubmit={handleRegister} className="space-y-6">
          <div className="space-y-2">
            <label className="block text-[10px] uppercase tracking-widest text-[#d8c7b5]/60 font-bold pl-1">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. creative@styleforge.ai"
              required
              className="w-full p-4.5 rounded-2xl bg-black/40 border border-white/10 outline-none focus:border-[#f6d7b0]/50 transition text-white placeholder:text-white/20 text-sm font-semibold"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-[10px] uppercase tracking-widest text-[#d8c7b5]/60 font-bold pl-1">
              Security Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full p-4.5 rounded-2xl bg-black/40 border border-white/10 outline-none focus:border-[#f6d7b0]/50 transition text-white placeholder:text-white/25 text-sm font-semibold"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-[10px] uppercase tracking-widest text-[#d8c7b5]/60 font-bold pl-1">
              Confirm Security Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full p-4.5 rounded-2xl bg-black/40 border border-white/10 outline-none focus:border-[#f6d7b0]/50 transition text-white placeholder:text-white/25 text-sm font-semibold"
            />
          </div>

          {/* ACTION BUTTON */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-4.5 rounded-full bg-[#f6d7b0] text-black font-extrabold text-base hover:scale-105 active:scale-95 transition disabled:opacity-75 disabled:hover:scale-100 flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-amber-300/5"
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span>Creating Account...</span>
              </>
            ) : (
              "Create Account & Join Studio"
            )}
          </button>
        </form>

        <div className="flex flex-col items-center mt-10 space-y-4 text-xs font-semibold tracking-wide">
          <Link href="/login" className="text-[#d8c7b5]/70 hover:text-white transition duration-300 uppercase tracking-widest text-[10px]">
            Already have an account? <span className="underline text-[#f6d7b0]">Sign In</span>
          </Link>
          
          <div className="flex items-center gap-3 text-[#d8c7b5]/40 text-[10px] uppercase">
            <Link href="/" className="hover:text-white hover:underline transition">
              Explore Workbench
            </Link>
          </div>
        </div>
      </motion.div>
    </main>
  );
}