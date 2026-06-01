"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import {
  Sparkles,
  Menu,
  X,
  User,
  LogOut,
  UserPlus,
  LogIn,
} from "lucide-react";
import { useAuth } from "./context/AuthContext";

export default function Home() {
  const router = useRouter();
  const { token, user, logout, hydrated } = useAuth();
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  const isLoggedIn = hydrated && !!token;
  const displayName = user?.email?.split("@")[0] || "Account";

  return (
    <main className="relative bg-[#0f0d0b] text-white overflow-hidden min-h-screen">

      {/* CURSOR GLOW */}
      <motion.div
        className="fixed top-0 left-0 w-125 h-125 rounded-full bg-amber-200/20 blur-3xl pointer-events-none z-0"
        animate={{
          x: mousePosition.x - 250,
          y: mousePosition.y - 250,
        }}
        transition={{
          type: "spring",
          stiffness: 60,
          damping: 20,
        }}
      />

      {/* NAVBAR */}
      <nav className="fixed top-0 left-0 w-full z-50 backdrop-blur-xl bg-black/20 border-b border-white/10">

        <div className="max-w-7xl mx-auto px-8 py-5 flex items-center justify-between">

          {/* LOGO */}
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="flex items-center gap-3"
          >
            <Sparkles className="text-[#f6d7b0]" />

            <h2 className="text-2xl md:text-3xl font-black tracking-[0.2em] text-[#f6d7b0]">
              STYLEFORGE
            </h2>
          </motion.div>

          {/* NAV LINKS */}
          <div className="hidden md:flex items-center gap-10 text-sm uppercase tracking-[0.2em] text-[#d8c7b5]">

            <a href="/" className="hover:text-[#f6d7b0] transition">
              Home
            </a>

            <a href="/about" className="hover:text-[#f6d7b0] transition">
              About
            </a>

            <a href="/features" className="hover:text-[#f6d7b0] transition">
              Features
            </a>

            {isLoggedIn && (
              <Link href="/profile" className="hover:text-[#f6d7b0] transition">
                Profile
              </Link>
            )}

            <a href="/contact" className="hover:text-[#f6d7b0] transition">
              Contact
            </a>

          </div>

          {/* RIGHT BUTTONS */}
          <div className="flex items-center gap-4">

            {hydrated && (
              isLoggedIn ? (
                /* ── LOGGED IN ── */
                <div className="hidden md:flex items-center gap-3">
                  <Link href="/profile">
                    <button className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-white/10 border border-[#f6d7b0]/30 hover:border-[#f6d7b0]/70 hover:bg-white/15 transition duration-300 backdrop-blur-sm cursor-pointer">
                      <div className="w-7 h-7 rounded-full bg-[#f6d7b0]/20 flex items-center justify-center">
                        <User size={14} className="text-[#f6d7b0]" />
                      </div>
                      <span className="text-sm text-[#f6d7b0] font-medium tracking-wide">{displayName}</span>
                    </button>
                  </Link>
                  <button
                    onClick={logout}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-white/20 text-white/70 hover:text-white hover:border-white/40 transition duration-300 text-sm"
                  >
                    <LogOut size={15} />
                    Logout
                  </button>
                </div>
              ) : (
                /* ── LOGGED OUT ── */
                <div className="hidden md:flex items-center gap-3">
                  <Link href="/login">
                    <button className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-[#f6d7b0]/40 text-[#f6d7b0] hover:bg-[#f6d7b0]/10 transition duration-300 text-sm font-medium">
                      <LogIn size={15} />
                      Login
                    </button>
                  </Link>
                  <Link href="/register">
                    <button className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#f6d7b0] text-black font-semibold hover:scale-105 transition duration-300 text-sm shadow-lg shadow-amber-300/20">
                      <UserPlus size={15} />
                      Register
                    </button>
                  </Link>
                </div>
              )
            )}

            {/* MOBILE HAMBURGER */}
            <button
              className="md:hidden text-white/80 hover:text-white transition cursor-pointer p-2 relative z-50"
              onClick={() => setMobileOpen(v => !v)}
              aria-label="Toggle menu"
            >
              {mobileOpen ? <X size={22} /> : <Menu size={22} />}
            </button>

          </div>
        </div>

        {/* MOBILE MENU */}
        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              key="mobile-menu"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden border-t border-white/10 overflow-hidden bg-[#0f0d0b]/95 backdrop-blur-3xl shadow-2xl"
            >
              <div className="px-8 py-6 flex flex-col gap-4 text-sm uppercase tracking-[0.2em] text-[#d8c7b5]">
                <a href="/" className="hover:text-[#f6d7b0] transition" onClick={() => setMobileOpen(false)}>Home</a>
                <a href="/about" className="hover:text-[#f6d7b0] transition" onClick={() => setMobileOpen(false)}>About</a>
                <a href="/features" className="hover:text-[#f6d7b0] transition" onClick={() => setMobileOpen(false)}>Features</a>
                <a href="/contact" className="hover:text-[#f6d7b0] transition" onClick={() => setMobileOpen(false)}>Contact</a>
                <div className="pt-2 border-t border-white/10 flex flex-col gap-3">
                  {isLoggedIn ? (
                    <>
                      <Link
                        href="/profile"
                        onClick={() => setMobileOpen(false)}
                        className="flex items-center gap-2 text-[#f6d7b0] normal-case hover:underline"
                      >
                        <User size={14} /> Profile: {displayName}
                      </Link>
                      <button
                        onClick={() => { logout(); setMobileOpen(false); }}
                        className="flex items-center gap-2 text-white/60 hover:text-white transition normal-case text-left cursor-pointer"
                      >
                        <LogOut size={14} /> Logout
                      </button>
                    </>
                  ) : (
                    <>
                      <Link href="/login" onClick={() => setMobileOpen(false)} className="hover:text-[#f6d7b0] transition">Login</Link>
                      <Link href="/register" onClick={() => setMobileOpen(false)} className="text-[#f6d7b0] hover:underline">Register</Link>
                    </>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

      </nav>

      {/* HERO SECTION */}
      <section
        id="home"
        className="relative min-h-screen flex items-center justify-center overflow-hidden"
      >

        {/* BACKGROUND IMAGE */}
        <div className="absolute inset-0 z-0">

          <Image
            src="/IMG_5120.JPG"
            alt="Background"
            fill
            priority
            className="object-cover"
          />

          <div className="absolute inset-0 bg-black/35"></div>

        </div>

        {/* AMBER GLOW */}
        <div className="absolute top-20 left-20 w-[400px] h-[400px] bg-amber-300/20 blur-3xl rounded-full"></div>

        <div className="absolute bottom-10 right-10 w-[350px] h-[350px] bg-orange-300/10 blur-3xl rounded-full"></div>

        {/* SPARKLES */}
        <div className="absolute inset-0 overflow-hidden">

          <div className="absolute top-20 left-1/4 w-2 h-2 bg-white rounded-full animate-ping"></div>

          <div className="absolute top-1/3 right-1/4 w-1 h-1 bg-amber-200 rounded-full animate-pulse"></div>

          <div className="absolute bottom-1/4 left-1/3 w-2 h-2 bg-[#f6d7b0] rounded-full animate-ping"></div>

        </div>

        {/* HERO CONTENT */}
        <div className="relative z-10 max-w-6xl mx-auto px-8 text-center">

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1 }}
            className="uppercase tracking-[0.5em] text-[#e0b27f] mb-6"
          >
            Luxury AI Fashion Platform
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 80 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1 }}
            className="text-6xl md:text-8xl lg:text-[10rem] font-black leading-none tracking-tight"
          >
            STYLEFORGE
          </motion.h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-8 max-w-3xl mx-auto text-lg md:text-xl text-[#e6d5c3]"
          >
            Experience futuristic AI-powered fashion visualization,
            cinematic fabric rendering, and immersive virtual styling.
          </motion.p>

          {/* BUTTONS */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1 }}
            className="flex flex-col md:flex-row gap-6 justify-center mt-12"
          >

            <button
              onClick={() => router.push(isLoggedIn ? "/studio" : "/login")}
              className="px-10 py-5 rounded-full bg-[#f6d7b0] text-black font-bold hover:scale-105 transition duration-300 shadow-2xl"
            >
              {isLoggedIn ? "Open AI Stylist" : "Start Experience"}
            </button>

            <button
              onClick={() => router.push("/features")}
              className="px-10 py-5 rounded-full border border-[#f6d7b0]/30 text-[#f6d7b0] hover:bg-white/10 transition duration-300"
            >
              Explore Collection
            </button>

          </motion.div>

        </div>

      </section>

      {/* ABOUT SECTION */}
      <section
        id="about"
        className="relative py-32 px-8 bg-[#100d0b]"
      >

        <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-20 items-center">

          {/* LEFT */}
          <motion.div
            initial={{ opacity: 0, x: -80 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 1 }}
          >

            <p className="uppercase tracking-[0.4em] text-[#d6a676] mb-6">
              About Styleforge
            </p>

            <h2 className="text-5xl md:text-6xl font-black mb-8 leading-tight">
              AI Meets Luxury Fashion
            </h2>

            <p className="text-[#d8c7b5] text-lg leading-relaxed mb-6">
              STYLEFORGE is a futuristic AI-powered fashion platform
              where technology blends with luxury design.
            </p>

            <p className="text-[#c8b8a7] leading-relaxed">
              From virtual try-ons to intelligent fabric simulation,
              STYLEFORGE transforms how people experience fashion online.
            </p>

          </motion.div>

          {/* RIGHT IMAGE */}
          <motion.div
            initial={{ opacity: 0, x: 80 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 1 }}
            className="relative"
          >

            <div className="absolute inset-0 bg-amber-300/10 blur-3xl rounded-full"></div>

            <Image
              src="/IMG_5118.JPG"
              alt="Fashion"
              width={700}
              height={700}
              className="relative z-10 rounded-[40px] object-cover"
            />

          </motion.div>

        </div>

      </section>

      {/* FEATURES SECTION */}
      <section
        id="features"
        className="py-28 px-8 bg-[#12100e]"
      >

        <div className="max-w-7xl mx-auto">

          <div className="text-center mb-20">

            <p className="uppercase tracking-[0.3em] text-[#d6a676] mb-4">
              Features
            </p>

            <h2 className="text-5xl md:text-6xl font-black">
              AI FASHION EXPERIENCE
            </h2>

          </div>

          <div className="grid md:grid-cols-3 gap-8">

            {/* CARD 1 */}
            <Link href="/outfit-ai" className="block w-full h-full">

              <motion.div
                whileHover={{
                  y: -15,
                  scale: 1.03,
                }}
                className="bg-[#1a1714] rounded-[30px] overflow-hidden border border-white/10 cursor-pointer h-full"
              >

                <Image
                  src="/IMG_5117.JPG"
                  alt="AI Outfit"
                  width={500}
                  height={300}
                  className="w-full h-[250px] object-cover hover:scale-110 transition duration-700"
                />

                <div className="p-8">

                  <h3 className="text-2xl font-bold text-[#f6d7b0] mb-4">
                    AI Outfit Creation
                  </h3>

                  <p className="text-[#c8b8a7]">
                    Generate futuristic outfit concepts with AI-powered styling.
                  </p>

                </div>

              </motion.div>

            </Link>

            {/* CARD 2 */}
            <Link href="/fabric-ai" className="block w-full h-full">

              <motion.div
                whileHover={{
                  y: -15,
                  scale: 1.03,
                }}
                className="bg-[#1a1714]/80 backdrop-blur-xl rounded-[30px] overflow-hidden border border-white/10 cursor-pointer h-full"
              >

                <Image
                  src="/IMG_5118.JPG"
                  alt="Fabric"
                  width={500}
                  height={300}
                  className="w-full h-[250px] object-cover hover:scale-110 transition duration-700"
                />

                <div className="p-8">

                  <h3 className="text-2xl font-bold text-[#f6d7b0] mb-4">
                    Fabric Simulation
                  </h3>

                  <p className="text-[#c8b8a7]">
                    Visualize luxury textures, realistic folds, and materials.
                  </p>

                </div>

              </motion.div>

            </Link>

            {/* CARD 3 */}
            <Link href="/style-critique" className="block w-full h-full">

              <motion.div
                whileHover={{
                  y: -15,
                  scale: 1.03,
                }}
                className="bg-[#1a1714]/80 backdrop-blur-xl rounded-[30px] overflow-hidden border border-white/10 cursor-pointer h-full"
              >

                <Image
                  src="/IMG_5111.JPG"
                  alt="Style Critique"
                  width={500}
                  height={300}
                  className="w-full h-[250px] object-cover hover:scale-110 transition duration-700"
                />

                <div className="p-8">

                  <h3 className="text-2xl font-bold text-[#f6d7b0] mb-4">
                    Style Critique AI
                  </h3>

                  <p className="text-[#c8b8a7]">
                    Analyze your outfit image and receive professional styling reviews instantly.
                  </p>

                </div>

              </motion.div>

            </Link>

          </div>

        </div>

      </section>
      {/* STYLEFORGE EXPERIENCE */}
      <section className="relative py-40 overflow-hidden bg-[#0d0b09]">

        {/* GLOW EFFECTS */}
        <div className="absolute top-20 left-20 w-[400px] h-[400px] bg-amber-300/10 blur-3xl rounded-full"></div>

        <div className="absolute bottom-10 right-10 w-[300px] h-[300px] bg-orange-300/10 blur-3xl rounded-full"></div>

        {/* TITLE */}
        <div className="text-center mb-24 relative z-10">

          <p className="uppercase tracking-[0.4em] text-[#d6a676] mb-6">
            From Imagination To Reality
          </p>

          <h2 className="text-5xl md:text-7xl font-black mb-8">
            THE STYLEFORGE EXPERIENCE
          </h2>

          <p className="max-w-3xl mx-auto text-[#d8c7b5] text-lg">
            A futuristic fashion journey powered by AI,
            luxury visualization, and real-world craftsmanship.
          </p>

        </div>

        {/* SCROLL CONTAINER */}
        <div className="relative overflow-hidden">

          {/* FADE LEFT */}
          <div className="absolute left-0 top-0 z-20 w-40 h-full bg-gradient-to-r from-[#0d0b09] to-transparent"></div>

          {/* FADE RIGHT */}
          <div className="absolute right-0 top-0 z-20 w-40 h-full bg-gradient-to-l from-[#0d0b09] to-transparent"></div>

          {/* MOVING TRACK */}
          <div className="flex animate-scroll gap-8 w-max px-10">

            {/* DUPLICATE SET FOR INFINITE LOOP */}

            {[1, 2].map((set) => (

              <div key={set} className="flex gap-8">

                {/* CARD 1 */}
                <Link href="/imagination">

                  <div className="group min-w-[340px] bg-white/10 backdrop-blur-2xl border border-white/10 rounded-[35px] overflow-hidden hover:scale-105 transition duration-500 cursor-pointer">

                    <Image
                      src="/IMG_5140.JPG"
                      alt="Dream Fashion"
                      width={400}
                      height={500}
                      className="w-full h-[380px] object-cover group-hover:scale-110 transition duration-700"
                    />

                    <div className="p-6">

                      <p className="uppercase tracking-[0.3em] text-[#d6a676] mb-3 text-sm">
                        Step 01
                      </p>

                      <h3 className="text-3xl font-black mb-4">
                        Imagine Fashion
                      </h3>

                      <p className="text-[#c8b8a7] leading-relaxed">
                        Describe your dream luxury outfit and let AI understand your imagination.
                      </p>

                    </div>

                  </div>

                </Link>

                {/* CARD 2 */}
                <Link href="/ai-designs">

                  <div className="group min-w-[340px] bg-white/10 backdrop-blur-2xl border border-white/10 rounded-[35px] overflow-hidden hover:scale-105 transition duration-500 cursor-pointer">

                    <Image
                      src="/IMG_5119.JPG"
                      alt="AI Fashion"
                      width={400}
                      height={500}
                      className="w-full h-[380px] object-cover group-hover:scale-110 transition duration-700"
                    />

                    <div className="p-6">

                      <p className="uppercase tracking-[0.3em] text-[#d6a676] mb-3 text-sm">
                        Step 02
                      </p>

                      <h3 className="text-3xl font-black mb-4">
                        AI Visualization
                      </h3>

                      <p className="text-[#c8b8a7] leading-relaxed">
                        AI creates cinematic couture renders with ultra realistic luxury detailing.
                      </p>

                    </div>

                  </div>

                </Link>

                {/* CARD 3 VIDEO */}
                <Link href="/fabric-simulation">

                  <div className="group min-w-[340px] bg-white/10 backdrop-blur-2xl border border-white/10 rounded-[35px] overflow-hidden hover:scale-105 transition duration-500 cursor-pointer">

                    <video
                      src="/vid.mp4"
                      autoPlay
                      loop
                      muted
                      playsInline
                      className="w-full h-[380px] object-cover group-hover:scale-110 transition duration-700"
                    />

                    <div className="p-6">

                      <p className="uppercase tracking-[0.3em] text-[#d6a676] mb-3 text-sm">
                        Step 03
                      </p>

                      <h3 className="text-3xl font-black mb-4">
                        Fabric Simulation
                      </h3>

                      <p className="text-[#c8b8a7] leading-relaxed">
                        Experience folds, silk reflections and digital luxury fabrics in motion.
                      </p>

                    </div>

                  </div>

                </Link>

                {/* CARD 4 */}
                <Link href="/style-critique">

                  <div className="group min-w-[340px] bg-white/10 backdrop-blur-2xl border border-white/10 rounded-[35px] overflow-hidden hover:scale-105 transition duration-500 cursor-pointer">

                    <Image
                      src="/IMG_5139.JPG"
                      alt="Style Critique"
                      width={400}
                      height={500}
                      className="w-full h-[380px] object-cover group-hover:scale-110 transition duration-700"
                    />

                    <div className="p-6">

                      <p className="uppercase tracking-[0.3em] text-[#d6a676] mb-3 text-sm">
                        Step 04
                      </p>

                      <h3 className="text-3xl font-black mb-4">
                        Style Critique AI
                      </h3>

                      <p className="text-[#c8b8a7] leading-relaxed">
                        Upload your photograph to receive professional fashion audits and refinement plans.
                      </p>

                    </div>

                  </div>

                </Link>

                {/* CARD 5 */}
                <Link href="/tailor-network">

                  <div className="group min-w-[340px] bg-white/10 backdrop-blur-2xl border border-white/10 rounded-[35px] overflow-hidden hover:scale-105 transition duration-500 cursor-pointer">

                    <Image
                      src="/IMG_5111.JPG"
                      alt="Tailor"
                      width={400}
                      height={500}
                      className="w-full h-[380px] object-cover group-hover:scale-110 transition duration-700"
                    />

                    <div className="p-6">

                      <p className="uppercase tracking-[0.3em] text-[#d6a676] mb-3 text-sm">
                        Step 05
                      </p>

                      <h3 className="text-3xl font-black mb-4">
                        Tailor Network
                      </h3>

                      <p className="text-[#c8b8a7] leading-relaxed">
                        Connect with verified luxury tailors who bring AI designs into reality.
                      </p>

                    </div>

                  </div>

                </Link>

                {/* FINAL CARD */}
                <Link href="/start">

                  <div className="group min-w-[340px] bg-[#f6d7b0] text-black rounded-[35px] overflow-hidden hover:scale-105 transition duration-500 shadow-2xl cursor-pointer">

                    <Image
                      src="/IMG_5116 (1).JPG"
                      alt="Final Fashion"
                      width={400}
                      height={500}
                      className="w-full h-[380px] object-cover group-hover:scale-110 transition duration-700"
                    />

                    <div className="p-6">

                      <p className="uppercase tracking-[0.3em] mb-3 text-sm">
                        Final Step
                      </p>

                      <h3 className="text-3xl font-black mb-4">
                        Bring It To Life
                      </h3>

                      <p className="leading-relaxed mb-6">
                        STYLEFORGE transforms imagination into real couture craftsmanship.
                      </p>

                      <button className="px-6 py-3 rounded-full bg-black text-white font-bold hover:scale-105 transition">
                        START EXPERIENCE
                      </button>

                    </div>

                  </div>

                </Link>

              </div>

            ))}

          </div>

        </div>

      </section>

      {/* ELEGANT LUXURY FOOTER */}
      <footer className="relative border-t border-white/10 bg-black/60 backdrop-blur-3xl py-20 z-10 overflow-hidden">
        {/* Ambient Glow in Footer */}
        <div className="absolute -bottom-20 -left-20 w-[300px] h-[300px] bg-[#f6d7b0]/5 blur-3xl rounded-full pointer-events-none"></div>

        <div className="max-w-7xl mx-auto px-8 grid grid-cols-1 md:grid-cols-4 gap-12">
          {/* Column 1: Branding */}
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <Sparkles className="text-[#f6d7b0]" size={20} />
              <h3 className="text-xl font-bold tracking-[0.2em] text-[#f6d7b0]">STYLEFORGE</h3>
            </div>
            <p className="text-[#d8c7b5]/60 text-sm leading-relaxed">
              Experience the vanguard of digital fashion. Merging predictive artificial intelligence with timeless luxury tailoring craftsmanship.
            </p>
            <div className="text-xs text-[#d8c7b5]/40">
              © {new Date().getFullYear()} STYLEFORGE. All rights reserved.
            </div>
          </div>

          {/* Column 2: Suite */}
          <div className="space-y-4">
            <h4 className="text-xs uppercase tracking-[0.3em] text-[#f6d7b0] font-bold">Fashion Suite</h4>
            <ul className="space-y-2.5 text-sm text-[#d8c7b5]/70">
              <li>
                <Link href="/style-critique" className="hover:text-[#f6d7b0] transition duration-300">Style Critique AI</Link>
              </li>
              <li>
                <Link href="/outfit-ai" className="hover:text-[#f6d7b0] transition duration-300">AI Outfit Creator</Link>
              </li>
              <li>
                <Link href="/fabric-ai" className="hover:text-[#f6d7b0] transition duration-300">Fabric Simulation</Link>
              </li>
              <li>
                <Link href="/studio" className="hover:text-[#f6d7b0] transition duration-300">Interactive Studio</Link>
              </li>
            </ul>
          </div>

          {/* Column 3: Platform */}
          <div className="space-y-4">
            <h4 className="text-xs uppercase tracking-[0.3em] text-[#f6d7b0] font-bold">Platform</h4>
            <ul className="space-y-2.5 text-sm text-[#d8c7b5]/70">
              <li>
                <a href="#about" className="hover:text-[#f6d7b0] transition duration-300">About Studio</a>
              </li>
              <li>
                <a href="#features" className="hover:text-[#f6d7b0] transition duration-300">Features</a>
              </li>
              <li>
                <a href="#experience" className="hover:text-[#f6d7b0] transition duration-300">Experience</a>
              </li>
              <li>
                <Link href="/tailors" className="hover:text-[#f6d7b0] transition duration-300">Tailor Network</Link>
              </li>
            </ul>
          </div>

          {/* Column 4: Newsletter / Connect */}
          <div className="space-y-4">
            <h4 className="text-xs uppercase tracking-[0.3em] text-[#f6d7b0] font-bold">Studio Dispatch</h4>
            <p className="text-xs text-[#d8c7b5]/60 leading-relaxed">
              Subscribe to receive private collection releases and AI-couture design dispatches.
            </p>
            <div className="flex gap-2">
              <input
                type="email"
                placeholder="Email Address"
                className="flex-1 px-4 py-2.5 rounded-full bg-black/40 border border-white/10 text-xs text-white placeholder:text-white/20 outline-none focus:border-[#f6d7b0]/40 transition"
              />
              <button className="px-5 py-2.5 rounded-full bg-[#f6d7b0] text-black font-bold text-xs hover:scale-105 active:scale-95 transition cursor-pointer">
                Subscribe
              </button>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}