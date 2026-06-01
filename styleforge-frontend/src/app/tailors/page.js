"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Sparkles, MapPin, Star, PhoneCall, Shield } from "lucide-react";

const PREMIUM_TAILORS = [
  {
    id: 1,
    name: "Royal Stitch Studio",
    location: "Delhi, India",
    rating: 4.9,
    reviews: 142,
    specialty: "Luxury Gowns & Traditional Bridal Couture",
    experience: "15+ Years",
    image: "/IMG_5138.JPG"
  },
  {
    id: 2,
    name: "Urban Couture Tailors",
    location: "Mumbai, India",
    rating: 4.8,
    reviews: 98,
    specialty: "Futuristic Streetwear & Modern Drape Suits",
    experience: "8 Years",
    image: "/IMG_5137.JPG"
  },
  {
    id: 3,
    name: "Heritage Fabrics & Tailors",
    location: "Kolkata, India",
    rating: 4.7,
    reviews: 76,
    specialty: "Premium Silks & Handcrafted Sherwanis",
    experience: "25+ Years",
    image: "/IMG_5111.JPG"
  },
  {
    id: 4,
    name: "Apex Bespoke Designers",
    location: "Bangalore, India",
    rating: 4.9,
    reviews: 110,
    specialty: "Precise Pattern Engineering & Velvet Blazers",
    experience: "12 Years",
    image: "/IMG_5118.JPG"
  }
];

export default function TailorsPage() {
  return (
    <main className="relative min-h-screen text-white overflow-hidden pb-20">
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

      {/* GLOW */}
      <div className="absolute top-20 left-20 w-[500px] h-[500px] bg-amber-300/10 blur-3xl rounded-full"></div>

      {/* CONTENT */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-10 py-20">
        {/* BACK BUTTON */}
        <Link href="/">
          <button className="flex items-center gap-3 mb-16 px-6 py-3 rounded-full bg-white/10 border border-white/10 backdrop-blur-xl hover:bg-white/20 transition">
            <ArrowLeft size={20} />
            <span>Back Home</span>
          </button>
        </Link>

        {/* TITLE */}
        <div className="text-center mb-20">
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[#f6d7b0]/20 bg-[#f6d7b0]/10 mb-6">
            <Sparkles size={18} className="text-[#f6d7b0]" />
            <span className="text-sm tracking-[0.3em] uppercase text-[#f6d7b0]">
              Verified Couture Craftsmanship
            </span>
          </div>

          <h1 className="text-5xl md:text-7xl font-black leading-tight mb-6 uppercase tracking-tight">
            Tailor Network
          </h1>

          <p className="text-[#d8c7b5] text-lg max-w-3xl mx-auto">
            Connect with certified master craftsmen who specialize in turning your AI-generated designs into physical haute couture.
          </p>
        </div>

        {/* LISTING GRID */}
        <div className="grid md:grid-cols-2 gap-8">
          {PREMIUM_TAILORS.map((tailor) => (
            <motion.div
              key={tailor.id}
              whileHover={{ y: -8 }}
              className="p-6 rounded-[35px] bg-[#1a1714]/85 backdrop-blur-xl border border-white/10 flex flex-col sm:flex-row gap-6 items-center"
            >
              {/* IMAGE */}
              <div className="relative w-full sm:w-36 h-36 rounded-2xl overflow-hidden border border-white/10 flex-shrink-0">
                <img
                  src={tailor.image}
                  alt={tailor.name}
                  className="w-full h-full object-cover"
                />
              </div>

              {/* DETAILS */}
              <div className="flex-1 flex flex-col justify-between h-full text-center sm:text-left">
                <div>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                    <h3 className="text-xl font-bold text-white">{tailor.name}</h3>
                    <div className="flex items-center justify-center gap-1 text-[#f6d7b0] text-sm">
                      <Star size={14} className="fill-current" />
                      <span className="font-bold">{tailor.rating}</span>
                      <span className="text-white/40">({tailor.reviews})</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-center sm:justify-start gap-1.5 text-xs text-[#d8c7b5]/70 mb-4">
                    <MapPin size={13} className="text-[#f6d7b0]" />
                    <span>{tailor.location}</span>
                    <span className="text-white/20">•</span>
                    <span>{tailor.experience} Exp</span>
                  </div>

                  <p className="text-sm text-[#c8b8a7] leading-relaxed mb-4">
                    {tailor.specialty}
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row gap-3 pt-2 border-t border-white/5">
                  <div className="flex items-center justify-center gap-1.5 text-xs text-[#f6d7b0]/80">
                    <Shield size={13} />
                    <span>Verified Partner</span>
                  </div>
                  <button className="sm:ml-auto px-5 py-2.5 rounded-full bg-[#f6d7b0] text-black font-bold text-xs hover:scale-105 active:scale-95 transition flex items-center justify-center gap-1.5">
                    <PhoneCall size={12} />
                    <span>Contact Tailor</span>
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* FOOTER ADVISORY */}
        <div className="mt-16 text-center text-[#d8c7b5]/40 text-xs flex items-center justify-center gap-2 max-w-xl mx-auto p-4 rounded-2xl bg-white/5 border border-white/5">
          <Shield size={14} className="text-[#f6d7b0]" />
          <span>All member tailors follow standard fabric guidelines and are vetted for extreme sizing precision.</span>
        </div>
      </div>
    </main>
  );
}
