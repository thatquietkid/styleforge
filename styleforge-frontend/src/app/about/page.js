"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";

export default function AboutPage() {
  return (
    <main className="relative min-h-screen text-white overflow-hidden">

      {/* BACKGROUND */}
      <div className="absolute inset-0">

        <Image
          src="/IMG_5111.JPG"
          alt="Background"
          fill
          priority
          className="object-cover"
        />

        <div className="absolute inset-0 bg-black/50"></div>

      </div>

      {/* GLOW */}
      <div className="absolute top-20 left-20 w-[400px] h-[400px] bg-amber-300/20 blur-3xl rounded-full"></div>

      {/* CONTENT */}
      <div className="relative z-10 px-8 py-20 max-w-7xl mx-auto">

        {/* BACK BUTTON */}
        <Link href="/">

          <motion.button
            whileHover={{ scale: 1.05 }}
            className="flex items-center gap-3 px-6 py-3 rounded-full bg-white/10 backdrop-blur-xl border border-white/10 mb-20"
          >

            <ArrowLeft size={20} />

            Back Home

          </motion.button>

        </Link>

        <div className="grid md:grid-cols-2 gap-20 items-center">

          {/* LEFT */}
          <motion.div
            initial={{ opacity: 0, x: -80 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1 }}
          >

            <p className="uppercase tracking-[0.4em] text-[#d6a676] mb-6">
              About Styleforge
            </p>

            <h1 className="text-6xl md:text-7xl font-black mb-8 leading-tight">
              AI Meets Luxury Fashion
            </h1>

            <p className="text-[#e6d5c3] text-lg leading-relaxed mb-6">
              STYLEFORGE combines futuristic AI technology
              with cinematic luxury fashion experiences.
            </p>

            <p className="text-[#d8c7b5] leading-relaxed">
              Our platform lets users visualize intelligent outfits,
              premium fabrics, and immersive styling powered by AI.
            </p>

          </motion.div>

          {/* RIGHT */}
          <motion.div
            whileHover={{ scale: 1.03 }}
            className="backdrop-blur-xl bg-white/5 rounded-[40px] overflow-hidden border border-white/10"
          >

           
          </motion.div>

        </div>

      </div>

    </main>
  );
}