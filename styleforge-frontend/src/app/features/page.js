"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";

export default function FeaturesPage() {
  return (
    <main className="relative min-h-screen text-white overflow-hidden">

      {/* BACKGROUND */}
      <div className="absolute inset-0">

        <Image
          src="/IMG_5117.JPG"
          alt="Background"
          fill
          priority
          className="object-cover"
        />

        <div className="absolute inset-0 bg-black/55"></div>

      </div>

      {/* GLOW */}
      <div className="absolute top-20 right-20 w-[400px] h-[400px] bg-amber-300/20 blur-3xl rounded-full"></div>

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

        <motion.div
          initial={{ opacity: 0, y: 80 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1 }}
        >

          <p className="uppercase tracking-[0.4em] text-[#d6a676] mb-6">
            Features
          </p>

          <h1 className="text-6xl md:text-7xl font-black mb-14">
            AI FASHION EXPERIENCE
          </h1>

        </motion.div>

        {/* FEATURE CARDS */}
        <div className="grid md:grid-cols-3 gap-8">

          {/* CARD */}
          <motion.div
            whileHover={{ scale: 1.03, y: -10 }}
            className="bg-white/10 backdrop-blur-xl rounded-[35px] overflow-hidden border border-white/10"
          >

            <Image
              src="/IMG_5111.JPG"
              alt="AI Fashion"
              width={500}
              height={400}
              className="w-full h-[250px] object-cover hover:scale-110 transition duration-700"
            />

            <div className="p-8">

              <h2 className="text-3xl font-bold text-[#f6d7b0] mb-4">
                AI Outfit Creation
              </h2>

              <p className="text-[#d8c7b5]">
                Generate futuristic fashion concepts powered by intelligent styling AI.
              </p>

            </div>

          </motion.div>

          {/* CARD */}
          <motion.div
            whileHover={{ scale: 1.03, y: -10 }}
            className="bg-white/10 backdrop-blur-xl rounded-[35px] overflow-hidden border border-white/10"
          >

            <Image
              src="/IMG_5118.JPG"
              alt="Fabric"
              width={500}
              height={400}
              className="w-full h-[250px] object-cover hover:scale-110 transition duration-700"
            />

            <div className="p-8">

              <h2 className="text-3xl font-bold text-[#f6d7b0] mb-4">
                Fabric Simulation
              </h2>

              <p className="text-[#d8c7b5]">
                Visualize premium textures and realistic material rendering.
              </p>

            </div>

          </motion.div>

          {/* CARD */}
          <motion.div
            whileHover={{ scale: 1.03, y: -10 }}
            className="bg-white/10 backdrop-blur-xl rounded-[35px] overflow-hidden border border-white/10"
          >

            <Image
              src="/IMG_5120.JPG"
              alt="Virtual Try On"
              width={500}
              height={400}
              className="w-full h-[250px] object-cover hover:scale-110 transition duration-700"
            />

            <div className="p-8">

              <h2 className="text-3xl font-bold text-[#f6d7b0] mb-4">
                Virtual Try-On
              </h2>

              <p className="text-[#d8c7b5]">
                Upload your image and experience immersive AI fashion styling.
              </p>

            </div>

          </motion.div>

        </div>

      </div>

    </main>
  );
}