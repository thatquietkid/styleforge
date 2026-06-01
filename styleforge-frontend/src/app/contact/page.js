"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";

export default function ContactPage() {
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

        <div className="absolute inset-0 bg-black/60"></div>

      </div>

      {/* GLOW */}
      <div className="absolute bottom-10 left-20 w-[400px] h-[400px] bg-orange-300/20 blur-3xl rounded-full"></div>

      {/* CONTENT */}
      <div className="relative z-10 px-8 py-20 max-w-5xl mx-auto">

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

        <div className="text-center">

          <motion.h1
            initial={{ opacity: 0, y: 80 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-6xl md:text-8xl font-black mb-8"
          >
            CONTACT
          </motion.h1>

          <p className="text-[#d8c7b5] text-xl mb-12">
            Let’s build the future of AI fashion together.
          </p>

          <div className="bg-white/10 backdrop-blur-xl border border-white/10 rounded-[40px] p-12">

            <p className="text-2xl text-[#f6d7b0] mb-6">
              styleforge@fashion.ai
            </p>

            <button className="px-10 py-5 rounded-full bg-[#f6d7b0] text-black font-bold hover:scale-105 transition duration-300">

              Send Message

            </button>

          </div>

        </div>

      </div>

    </main>
  );
}