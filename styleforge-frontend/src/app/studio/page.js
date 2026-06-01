"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Upload } from "lucide-react";

export default function StudioPage() {
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

        <div className="absolute inset-0 bg-black/60"></div>

      </div>

      {/* CONTENT */}
      <div className="relative z-10 px-8 py-20 max-w-6xl mx-auto">

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
            AI STUDIO
          </motion.h1>

          <p className="text-[#d8c7b5] text-lg mb-16 max-w-2xl mx-auto">
            Upload your fashion image and let AI generate futuristic styling experiences.
          </p>

          {/* UPLOAD BOX */}
          <motion.div
            whileHover={{ scale: 1.02 }}
            className="max-w-3xl mx-auto p-20 rounded-[40px] bg-white/10 backdrop-blur-xl border border-white/10"
          >

            <div className="flex flex-col items-center">

              <div className="w-24 h-24 rounded-full bg-[#f6d7b0]/10 flex items-center justify-center mb-8">

                <Upload size={40} className="text-[#f6d7b0]" />

              </div>

              <h2 className="text-3xl font-bold text-[#f6d7b0] mb-4">
                Upload Fashion Image
              </h2>

              <p className="text-[#d8c7b5] mb-8">
                Drag & drop your image or click below
              </p>

              <button className="px-8 py-4 rounded-full bg-[#f6d7b0] text-black font-bold hover:scale-105 transition duration-300">

                Choose File

              </button>

            </div>

          </motion.div>

        </div>

      </div>

    </main>
  );
}