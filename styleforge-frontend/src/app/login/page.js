"use client";

import { useState, useRef, useEffect, Suspense } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "../context/AuthContext";
import { Mail, ArrowLeft, Loader2, Sparkles, XCircle, ShieldCheck, RefreshCw } from "lucide-react";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get("redirect") || "/";
  const { setToken } = useAuth();

  // Form State
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otpDigits, setOtpDigits] = useState(["", "", "", "", "", ""]);

  // UI state
  const [loginMode, setLoginMode] = useState("PASSWORD"); // PASSWORD | OTP
  const [otpSent, setOtpSent] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [countdown, setCountdown] = useState(60);

  const digitRefs = useRef([]);
  const API_URL = process.env.NEXT_PUBLIC_AUTH_API_URL || "http://localhost:8000";

  // Countdown timer for OTP Resend
  useEffect(() => {
    if (!otpSent) return;
    setCountdown(60);
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [otpSent]);

  const handleDigitChange = (index, value) => {
    if (/[^0-9]/.test(value)) return; // Allow numbers only
    const newDigits = [...otpDigits];
    newDigits[index] = value;
    setOtpDigits(newDigits);

    // Auto-focus next box if populated
    if (value && index < 5) {
      digitRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    // Auto-focus previous box on Backspace if current box is empty
    if (e.key === "Backspace" && !otpDigits[index] && index > 0) {
      digitRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasteData = e.clipboardData.getData("text").trim();
    if (pasteData.length === 6 && /^\d+$/.test(pasteData)) {
      const chars = pasteData.split("");
      setOtpDigits(chars);
      digitRefs.current[5]?.focus();
    }
  };

  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const res = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Incorrect email or password.");
      }

      const data = await res.json();
      setToken(data.access_token, data.user || null);
      router.push(redirectTo);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRequestOTP = async (e) => {
    if (e) e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/v1/auth/login/otp/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to deliver OTP. Try again.");
      }

      setOtpSent(true);
      setCountdown(60);
      setOtpDigits(["", "", "", "", "", ""]);
      setTimeout(() => {
        digitRefs.current[0]?.focus();
      }, 100);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    const otpCode = otpDigits.join("");
    if (otpCode.length !== 6) {
      setError("Please fill in all 6 code digits.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/v1/auth/login/otp/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, otp: otpCode }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Invalid or expired OTP.");
      }

      const data = await res.json();
      setToken(data.access_token, data.user || null);
      router.push(redirectTo);
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

      {/* LOGIN CARD */}
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-[95%] max-w-lg bg-[#161311]/70 border border-white/10 backdrop-blur-2xl rounded-[40px] p-8 md:p-12 shadow-2xl"
      >
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#f6d7b0]/20 bg-[#f6d7b0]/5 mb-4">
            <Sparkles size={14} className="text-[#f6d7b0]" />
            <span className="text-[10px] tracking-[0.2em] uppercase text-[#f6d7b0] font-bold">
              Secure Entrance
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight leading-none">
            STYLEFORGE
          </h1>
          <p className="text-[#d8c7b5]/60 text-sm mt-3 font-semibold uppercase tracking-wider">
            AI Fashion Ecosystem
          </p>
        </div>

        {/* STEP INDICATORS FOR OTP MODE */}
        {loginMode === "OTP" && (
          <div className="flex items-center justify-center gap-4 mb-8">
            <div className={`flex items-center gap-2 text-xs font-semibold ${!otpSent ? "text-[#f6d7b0]" : "text-white/40"}`}>
              <span className={`w-5 h-5 rounded-full flex items-center justify-center border ${!otpSent ? "border-[#f6d7b0] bg-[#f6d7b0]/15" : "border-white/20"}`}>1</span>
              <span>Email</span>
            </div>
            <div className="w-8 h-[1px] bg-white/10"></div>
            <div className={`flex items-center gap-2 text-xs font-semibold ${otpSent ? "text-[#f6d7b0]" : "text-white/40"}`}>
              <span className={`w-5 h-5 rounded-full flex items-center justify-center border ${otpSent ? "border-[#f6d7b0] bg-[#f6d7b0]/15" : "border-white/20"}`}>2</span>
              <span>Verification</span>
            </div>
          </div>
        )}

        {/* ERROR DISPLAY */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-6 flex items-start gap-3 p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-200 text-xs font-semibold leading-relaxed"
            >
              <XCircle size={16} className="text-red-400 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* FORMS */}
        <form
          onSubmit={
            loginMode === "PASSWORD"
              ? handlePasswordLogin
              : otpSent
              ? handleVerifyOTP
              : handleRequestOTP
          }
          className="space-y-6"
        >
          {/* EMAIL INPUT */}
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
              disabled={otpSent && loginMode === "OTP"}
              className="w-full p-4.5 rounded-2xl bg-black/40 border border-white/10 outline-none focus:border-[#f6d7b0]/50 transition text-white placeholder:text-white/20 text-sm font-semibold disabled:opacity-50"
            />
          </div>

          {/* PASSWORD IN MODE 'PASSWORD' */}
          {loginMode === "PASSWORD" && (
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
          )}

          {/* OTP DIGIT BOXES IN MODE 'OTP' AND CODESENT */}
          {loginMode === "OTP" && otpSent && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-4 text-center"
            >
              {/* ENVELOPE ICON */}
              <div className="flex justify-center mb-6">
                <div className="relative">
                  <div className="w-16 h-16 rounded-full bg-[#f6d7b0]/10 flex items-center justify-center border border-[#f6d7b0]/25 animate-pulse">
                    <Mail className="text-[#f6d7b0] animate-bounce" size={26} />
                  </div>
                </div>
              </div>

              <label className="block text-xs text-[#d8c7b5] font-semibold">
                Please enter the 6-digit code delivered to your mailbox
              </label>

              {/* 6 DIGIT GRID */}
              <div className="flex gap-2.5 justify-between py-2 max-w-sm mx-auto">
                {otpDigits.map((digit, index) => (
                  <input
                    key={index}
                    ref={(el) => (digitRefs.current[index] = el)}
                    type="text"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleDigitChange(index, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(index, e)}
                    onPaste={handlePaste}
                    className="w-12 h-14 rounded-xl bg-black/50 border border-white/10 outline-none text-center text-2xl font-black text-[#f6d7b0] focus:border-[#f6d7b0] focus:shadow-md focus:shadow-[#f6d7b0]/5 transition duration-200"
                  />
                ))}
              </div>

              {/* RESEND TIMERS */}
              <div className="flex items-center justify-between text-xs text-[#d8c7b5]/60 px-2 mt-4">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck size={13} className="text-[#f6d7b0]" /> Code expires in 10 minutes
                </span>
                <button
                  type="button"
                  disabled={countdown > 0 || isLoading}
                  onClick={handleRequestOTP}
                  className="flex items-center gap-1 text-[#f6d7b0] hover:underline disabled:opacity-50 disabled:no-underline font-semibold"
                >
                  <RefreshCw size={11} className={isLoading ? "animate-spin" : ""} />
                  {countdown > 0 ? `Resend in ${countdown}s` : "Resend Code"}
                </button>
              </div>
            </motion.div>
          )}

          {/* ACTION BUTTON */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-4.5 rounded-full bg-[#f6d7b0] text-black font-extrabold text-base hover:scale-105 active:scale-95 transition disabled:opacity-75 disabled:hover:scale-100 flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-amber-300/5"
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span>Processing...</span>
              </>
            ) : loginMode === "PASSWORD" ? (
              "Sign In to Studio"
            ) : otpSent ? (
              "Complete Authentication"
            ) : (
              "Deliver Security Code"
            )}
          </button>
        </form>

        {/* INTERCHANGE MODES */}
        <div className="flex flex-col items-center mt-10 space-y-4 text-xs font-semibold tracking-wide">
          <button
            type="button"
            onClick={() => {
              setLoginMode(loginMode === "PASSWORD" ? "OTP" : "PASSWORD");
              setError(null);
              setOtpSent(false);
            }}
            className="text-[#d8c7b5]/70 hover:text-white transition duration-300 uppercase tracking-widest text-[10px]"
          >
            {loginMode === "PASSWORD"
              ? "Login with OTP"
              : "Use password authentication instead"}
          </button>
          
          <div className="flex items-center gap-3 text-[#d8c7b5]/40 text-[10px] uppercase">
            <Link href="/register" className="hover:text-white hover:underline transition">
              Create Studio Account
            </Link>
            <span>•</span>
            <Link href="/" className="hover:text-white hover:underline transition">
              Explore Workbench
            </Link>
          </div>
        </div>
      </motion.div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#0f0d0b] text-white flex items-center justify-center">
        <Loader2 className="animate-spin text-[#f6d7b0]" size={36} />
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}