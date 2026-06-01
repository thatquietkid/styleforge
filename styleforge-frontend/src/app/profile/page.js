"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "../context/AuthContext";
import { parseApiError } from "../utils/error";
import {
  ArrowLeft,
  Upload,
  User,
  Sparkles,
  Trash2,
  Download,
  CheckCircle,
  XCircle,
  Loader2,
  ShieldCheck,
  Mail,
  Layers,
  Calendar,
  Key,
  Info,
  Maximize2,
  Coins
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_AUTH_API_URL || "http://localhost:8000";

export default function ProfilePage() {
  const router = useRouter();
  const { token, user, hydrated, updateUser, logout } = useAuth();

  // Redirect to login if not logged in after hydration
  useEffect(() => {
    if (hydrated && !token) {
      router.push("/login");
    }
  }, [hydrated, token, router]);

  // Profile Form State
  const [emailInput, setEmailInput] = useState("");
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState(false);
  const [profileError, setProfileError] = useState(null);
  const [profileValidationFields, setProfileValidationFields] = useState([]);

  // Initialize email once user details are loaded
  useEffect(() => {
    if (user?.email) {
      setEmailInput(user.email);
    }
  }, [user]);

  // Quota State
  const [quota, setQuota] = useState(null);
  const [quotaLoading, setQuotaLoading] = useState(true);

  // Credits State
  const [credits, setCredits] = useState(null);
  const [creditsLoading, setCreditsLoading] = useState(true);

  // Gallery State
  const [images, setImages] = useState([]);
  const [imagesLoading, setImagesLoading] = useState(true);
  const [galleryFilter, setGalleryFilter] = useState(""); // empty means all, 'upload', 'generated'
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const LIMIT = 12;

  // Upload State
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  // Lightbox Modal State
  const [activeImage, setActiveImage] = useState(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [deletingLoading, setDeletingLoading] = useState(false);

  // ── Fetch Quota ───────────────────────────────────────────────────────────
  const fetchQuota = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/catalog/images/quota`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Could not load quota status.");
      const data = await res.json();
      setQuota(data);
    } catch (_) {
      // Fallback fallback if quota endpoint is down
      setQuota({ used: 0, limit: 20, remaining: 20 });
    } finally {
      setQuotaLoading(false);
    }
  }, [token]);

  // ── Fetch Credits ──────────────────────────────────────────────────────────
  const fetchCredits = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/genai/credits`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Could not load credits balance.");
      const data = await res.json();
      setCredits(data.credits);
    } catch (_) {
      setCredits(0);
    } finally {
      setCreditsLoading(false);
    }
  }, [token]);

  // ── Fetch Images ──────────────────────────────────────────────────────────
  const fetchImages = useCallback(
    async (reset = false) => {
      if (!token) return;
      if (reset) {
        setImagesLoading(true);
      }
      const currentSkip = reset ? 0 : skip;
      try {
        const queryParams = new URLSearchParams({
          skip: currentSkip.toString(),
          limit: LIMIT.toString(),
        });
        if (galleryFilter) {
          queryParams.append("image_type", galleryFilter);
        }

        const res = await fetch(
          `${API_URL}/api/v1/catalog/images/me?${queryParams.toString()}`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        if (!res.ok) throw new Error("Could not load image collection.");
        const data = await res.json();

        if (reset) {
          setImages(data);
          setSkip(LIMIT);
        } else {
          setImages((prev) => [...prev, ...data]);
          setSkip((prev) => prev + LIMIT);
        }

        // If returned records is less than limit, no more pages
        if (data.length < LIMIT) {
          setHasMore(false);
        } else {
          setHasMore(true);
        }
      } catch (err) {
        console.error("Gallery Fetch Error:", err);
      } finally {
        setImagesLoading(false);
      }
    },
    [token, galleryFilter, skip]
  );

  // Reload gallery on filter changes
  useEffect(() => {
    if (token) {
      fetchQuota();
      fetchCredits();
      fetchImages(true);
    }
  }, [token, galleryFilter]);

  // ── Update Profile Handlers ──────────────────────────────────────────────
  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    if (!emailInput.trim()) return;

    setProfileLoading(true);
    setProfileSuccess(false);
    setProfileError(null);
    setProfileValidationFields([]);

    try {
      const res = await fetch(`${API_URL}/api/v1/auth/me`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ email: emailInput.trim() }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        const parsed = parseApiError(errorData, "Failed to update profile info.");

        // Map conflict error code custom response
        if (res.status === 409 || parsed.code === "email_taken") {
          throw new Error("This email address is already registered to another account.");
        }

        if (parsed.code === "validation_error" && parsed.fields) {
          setProfileValidationFields(parsed.fields);
        }
        throw new Error(parsed.message);
      }

      const updatedUser = await res.json();
      updateUser(updatedUser);
      setProfileSuccess(true);

      // Auto-hide success state after 4 seconds
      setTimeout(() => setProfileSuccess(false), 4000);
    } catch (err) {
      setProfileError(err.message);
    } finally {
      setProfileLoading(false);
    }
  };

  // ── Upload Handlers ───────────────────────────────────────────────────────
  const uploadFile = async (file) => {
    if (!file) return;

    // Client-side limit validation: 5 MB
    const MAX_SIZE = 5 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      setUploadError("File size exceeds 5 MB limit. Please optimize your sketch.");
      return;
    }

    // Format validation
    const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      setUploadError("Unsupported file format. Please upload a JPEG, PNG, or WebP sketch.");
      return;
    }

    setUploadLoading(true);
    setUploadError(null);
    setUploadSuccess(false);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_URL}/api/v1/catalog/images/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        const parsed = parseApiError(errorData, "Image upload failed.");

        if (res.status === 413 || parsed.code === "file_too_large") {
          throw new Error("File size exceeds 5 MB limit.");
        }
        if (res.status === 422 || parsed.code === "invalid_file_type") {
          throw new Error("Unsupported file format. Upload JPEG, PNG, or WebP.");
        }
        if (res.status === 429 || parsed.code === "quota_exceeded") {
          throw new Error("Daily upload quota of 20 images reached. Try again tomorrow.");
        }
        throw new Error(parsed.message);
      }

      setUploadSuccess(true);
      fetchQuota();
      fetchImages(true); // reload list

      // Reset file input
      if (fileInputRef.current) fileInputRef.current.value = "";
      setTimeout(() => setUploadSuccess(false), 4000);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploadLoading(false);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    uploadFile(file);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const file = e.dataTransfer.files?.[0];
    uploadFile(file);
  };

  // ── Image Deletion Handler ────────────────────────────────────────────────
  const handleDeleteImage = async (imageId) => {
    if (!imageId) return;
    setDeletingLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/v1/catalog/images/${imageId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const errorData = await res.json();
        const parsed = parseApiError(errorData, "Failed to delete image.");
        throw new Error(parsed.message);
      }

      // Successful deletion — close modal & refresh components
      setImages((prev) => prev.filter((img) => img.id !== imageId));
      setActiveImage(null);
      setDeleteConfirmId(null);
      fetchQuota();
    } catch (err) {
      alert(`Delete error: ${err.message}`);
    } finally {
      setDeletingLoading(false);
    }
  };

  // Prevent page flicker before hydration is completed
  if (!hydrated) {
    return (
      <main className="relative min-h-screen bg-[#0f0d0b] text-white flex items-center justify-center">
        <Loader2 className="animate-spin text-[#f6d7b0]" size={40} />
      </main>
    );
  }

  if (!token) return null; // let useEffect redirect do its work

  const displayName = user?.email?.split("@")[0] || "Account";

  return (
    <main className="relative min-h-screen bg-[#0f0d0b] text-white overflow-x-hidden pb-20">
      {/* GLOBAL BACKGROUND COUTURE IMAGE */}
      <div className="absolute inset-0 z-0 opacity-20 pointer-events-none">
        <Image
          src="/IMG_5120.JPG"
          alt="Studio Background"
          fill
          priority
          className="object-cover object-top"
        />
        <div className="absolute inset-0 bg-[#0f0d0b] bg-gradient-to-b from-[#0f0d0b]/80 via-[#0f0d0b]/95 to-[#0f0d0b]"></div>
      </div>

      {/* DYNAMIC AMBER GLOW EFFECTS */}
      <div className="fixed top-[-100px] left-[-100px] w-[500px] h-[500px] bg-amber-300/5 blur-3xl rounded-full pointer-events-none z-0"></div>
      <div className="fixed bottom-0 right-[-100px] w-[500px] h-[500px] bg-orange-300/5 blur-3xl rounded-full pointer-events-none z-0"></div>

      {/* CONTAINER */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-10 py-16">
        
        {/* BACK TO DASHBOARD HEADER */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
          <Link href="/">
            <button className="flex items-center gap-3 px-6 py-3 rounded-full bg-white/5 border border-white/10 hover:border-white/20 hover:bg-white/10 backdrop-blur-xl transition">
              <ArrowLeft size={18} />
              <span>Back Home</span>
            </button>
          </Link>

          <div className="flex items-center gap-3">
            <div className="px-5 py-2.5 rounded-full bg-[#f6d7b0]/5 border border-[#f6d7b0]/20 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-sm font-semibold tracking-wider text-[#f6d7b0] uppercase">
                Active Session
              </span>
            </div>
            <button
              onClick={logout}
              className="px-5 py-2.5 rounded-full border border-white/10 text-white/60 hover:text-white hover:border-white/30 transition text-sm font-medium"
            >
              Sign Out
            </button>
          </div>
        </div>

        {/* HERO TITLE SECTION */}
        <div className="mb-14">
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-[#f6d7b0]/20 bg-[#f6d7b0]/5 mb-6">
            <Sparkles size={16} className="text-[#f6d7b0]" />
            <span className="text-xs font-semibold tracking-[0.3em] uppercase text-[#f6d7b0]">
              User Fashion Studio
            </span>
          </div>

          <h1 className="text-4xl md:text-6xl font-black leading-none tracking-tight">
            MY DASHBOARD
          </h1>
          <p className="text-[#d8c7b5]/80 text-lg mt-4 max-w-xl">
            Refine your digital profile, oversee your daily storage parameters, and explore your generated couture concepts.
          </p>
        </div>

        {/* PROFILE INFO & IMAGE QUOTA MATRIX ROW */}
        <div className="grid lg:grid-cols-3 gap-8 mb-16">
          
          {/* PROFILE SETTINGS CARD */}
          <div className="lg:col-span-1 rounded-[30px] border border-white/10 bg-[#161311]/60 backdrop-blur-2xl p-8 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-3 border-b border-white/10 pb-4 mb-6">
                <div className="w-10 h-10 rounded-full bg-[#f6d7b0]/15 flex items-center justify-center">
                  <User size={18} className="text-[#f6d7b0]" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-[#f6d7b0]">Profile Information</h3>
                  <p className="text-xs text-[#d8c7b5]/60">Secure credentials and email management</p>
                </div>
              </div>

              <form onSubmit={handleUpdateProfile} className="space-y-6">
                <div>
                  <label className="block text-xs uppercase tracking-widest text-[#d8c7b5] mb-2 font-semibold">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" size={18} />
                    <input
                      type="email"
                      value={emailInput}
                      onChange={(e) => {
                        setEmailInput(e.target.value);
                        if (profileError) setProfileError(null);
                        if (profileValidationFields.length > 0) setProfileValidationFields([]);
                      }}
                      required
                      className="w-full pl-12 pr-6 py-4 rounded-2xl bg-black/45 border border-white/10 outline-none focus:border-[#f6d7b0]/50 transition text-white placeholder:text-white/20 font-medium"
                      placeholder="e.g. fashionista@couture.com"
                    />
                  </div>
                  
                  {/* Validation and Standard Errors */}
                  {profileValidationFields.length > 0 && (
                    <div className="mt-3 space-y-1 text-xs text-red-400">
                      {profileValidationFields.map((f, i) => (
                        <p key={i} className="flex items-center gap-1.5 font-medium">
                          <XCircle size={12} /> {f.field}: {f.message}
                        </p>
                      ))}
                    </div>
                  )}

                  {profileError && (
                    <div className="mt-3 flex items-center gap-2 p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-200 text-xs font-semibold">
                      <XCircle size={14} className="flex-shrink-0" />
                      <span>{profileError}</span>
                    </div>
                  )}

                  {profileSuccess && (
                    <div className="mt-3 flex items-center gap-2 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
                      <CheckCircle size={14} className="flex-shrink-0" />
                      <span>Profile info successfully updated.</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between gap-4 pt-2">
                  <div className="flex items-center gap-2 text-xs text-[#d8c7b5]/50">
                    <ShieldCheck size={14} className="text-[#f6d7b0]" />
                    <span>Double check email syntax before committing changes.</span>
                  </div>
                  <button
                    type="submit"
                    disabled={profileLoading || emailInput === user?.email}
                    className="px-6 py-3 rounded-full bg-[#f6d7b0] text-black font-bold text-sm hover:scale-[1.03] transition duration-300 disabled:opacity-40 disabled:hover:scale-100 flex items-center gap-2"
                  >
                    {profileLoading && <Loader2 size={14} className="animate-spin" />}
                    <span>Update Email</span>
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* QUOTA BAR CARD */}
          <div className="rounded-[30px] border border-white/10 bg-[#161311]/60 backdrop-blur-2xl p-8 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-3 border-b border-white/10 pb-4 mb-6">
                <div className="w-10 h-10 rounded-full bg-[#f6d7b0]/15 flex items-center justify-center">
                  <Layers size={18} className="text-[#f6d7b0]" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-[#f6d7b0]">Storage Quota Status</h3>
                  <p className="text-xs text-[#d8c7b5]/60">Daily image upload tracking</p>
                </div>
              </div>

              {quotaLoading ? (
                <div className="flex flex-col items-center justify-center py-6">
                  <Loader2 className="animate-spin text-[#f6d7b0]" size={30} />
                </div>
              ) : quota ? (
                <div className="space-y-6">
                  <div>
                    <div className="flex justify-between text-sm mb-2 font-medium">
                      <span className="text-[#d8c7b5]">Daily Limit Used</span>
                      <span className="text-[#f6d7b0] font-bold">
                        {quota.used} / {quota.limit} Images
                      </span>
                    </div>

                    {/* Progress slider bar */}
                    <div className="w-full h-3 rounded-full bg-white/5 overflow-hidden border border-white/5 p-[1px]">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(quota.used / quota.limit) * 100}%` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                        className="h-full rounded-full bg-gradient-to-r from-orange-400 via-amber-300 to-[#f6d7b0]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 pt-2">
                    <div className="bg-black/25 rounded-2xl p-4 border border-white/5">
                      <p className="text-xs text-[#d8c7b5]/50 uppercase tracking-wider font-semibold">Remaining</p>
                      <p className="text-2xl font-black text-[#f6d7b0] mt-1">{quota.remaining}</p>
                    </div>
                    <div className="bg-black/25 rounded-2xl p-4 border border-white/5">
                      <p className="text-xs text-[#d8c7b5]/50 uppercase tracking-wider font-semibold">Limit Limit</p>
                      <p className="text-2xl font-black text-[#f6d7b0] mt-1">{quota.limit}</p>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-red-200">Could not retrieve active quota status.</p>
              )}
            </div>
            
            <div className="mt-6 flex items-start gap-2.5 p-3 rounded-xl bg-[#f6d7b0]/5 border border-[#f6d7b0]/10 text-xs text-[#d8c7b5]/70 leading-normal">
              <Info size={14} className="text-[#f6d7b0] mt-0.5 flex-shrink-0" />
              <span>Upload limits reset daily. High resolution fashion sketches consume standard generation metrics.</span>
            </div>
          </div>

          {/* CREDITS SYSTEM CARD */}
          <div className="rounded-[30px] border border-white/10 bg-[#161311]/60 backdrop-blur-2xl p-8 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-3 border-b border-white/10 pb-4 mb-6">
                <div className="w-10 h-10 rounded-full bg-[#f6d7b0]/15 flex items-center justify-center">
                  <Coins size={18} className="text-[#f6d7b0]" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-[#f6d7b0]">AI Credits</h3>
                  <p className="text-xs text-[#d8c7b5]/60">Tokens for AI operations</p>
                </div>
              </div>

              {creditsLoading ? (
                <div className="flex flex-col items-center justify-center py-6">
                  <Loader2 className="animate-spin text-[#f6d7b0]" size={30} />
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="text-center bg-black/35 rounded-2xl py-6 border border-white/5">
                    <p className="text-xs uppercase tracking-widest text-[#d8c7b5] font-semibold">Available Balance</p>
                    <p className="text-4xl font-black text-[#f6d7b0] mt-2 tracking-tight">
                      {credits !== null ? `${credits}` : "---"} <span className="text-xs font-bold text-[#d8c7b5]/60">Credits</span>
                    </p>
                  </div>

                  <div className="space-y-2 text-xs text-[#d8c7b5]/80">
                    <div className="flex justify-between items-center py-1.5 border-b border-white/5">
                      <span>Style Critique AI</span>
                      <span className="font-bold text-[#f6d7b0] bg-[#f6d7b0]/10 px-2 py-0.5 rounded border border-[#f6d7b0]/20">5 credits</span>
                    </div>
                    <div className="flex justify-between items-center py-1.5">
                      <span>AI Outfit Creator</span>
                      <span className="font-bold text-[#f6d7b0] bg-[#f6d7b0]/10 px-2 py-0.5 rounded border border-[#f6d7b0]/20">10 credits</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            <div className="mt-6 flex items-start gap-2.5 p-3 rounded-xl bg-[#f6d7b0]/5 border border-[#f6d7b0]/10 text-xs text-[#d8c7b5]/70 leading-normal">
              <Info size={14} className="text-[#f6d7b0] mt-0.5 flex-shrink-0" />
              <span>Starting balance is 100 credits. Please contact support for top-ups.</span>
            </div>
          </div>

        </div>

        {/* DOCK UPLOADER AND FILTERABLE GALLERY SECTION */}
        <div className="grid lg:grid-cols-3 gap-8 items-start">
          
          {/* UPLOAD DRAG AND DROP BOX */}
          <div className="rounded-[30px] border border-white/10 bg-[#161311]/60 backdrop-blur-2xl p-8 lg:sticky lg:top-8">
            <h3 className="text-xl font-bold text-[#f6d7b0] pb-4 border-b border-white/10 mb-6 uppercase tracking-wider">
              Upload New Sketch
            </h3>

            {/* DRAG BOX AREA */}
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`
                group
                relative
                border-2
                border-dashed
                rounded-3xl
                p-10
                text-center
                cursor-pointer
                transition-all
                duration-300
                flex
                flex-col
                items-center
                justify-center
                gap-4
                ${dragActive 
                  ? "border-[#f6d7b0] bg-[#f6d7b0]/5 scale-[0.99]" 
                  : "border-white/10 hover:border-[#f6d7b0]/40 hover:bg-white/5"}
              `}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
                className="hidden"
                id="catalog-upload-input"
              />

              {uploadLoading ? (
                <>
                  <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
                    <Loader2 size={28} className="animate-spin text-[#f6d7b0]" />
                  </div>
                  <div>
                    <p className="font-bold text-[#f6d7b0] text-sm">Uploading sketch...</p>
                    <p className="text-xs text-[#d8c7b5]/50 mt-1">Please wait for server geometry mapping</p>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-16 h-16 rounded-full bg-[#f6d7b0]/5 border border-[#f6d7b0]/20 flex items-center justify-center transition group-hover:scale-115">
                    <Upload size={28} className="text-[#f6d7b0]" />
                  </div>

                  <div>
                    <h4 className="font-bold text-[#e6d5c3] group-hover:text-[#f6d7b0] transition">
                      Drag sketch here
                    </h4>
                    <p className="text-xs text-[#d8c7b5]/60 mt-1">
                      or click to explore files
                    </p>
                  </div>

                  <span className="text-[10px] uppercase font-semibold text-[#d8c7b5]/40 tracking-wider">
                    JPEG, PNG, WebP · Max 5MB
                  </span>
                </>
              )}
            </div>

            {/* Error messaging for Upload */}
            {uploadError && (
              <div className="mt-6 flex items-start gap-2.5 p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-200 text-xs font-semibold leading-relaxed">
                <XCircle size={16} className="text-red-400 mt-0.5 flex-shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            {uploadSuccess && (
              <div className="mt-6 flex items-center gap-2.5 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
                <CheckCircle size={16} className="text-emerald-400 flex-shrink-0" />
                <span>Sketch successfully mapped to catalog!</span>
              </div>
            )}

            {/* PRE-RENDER PROTIP */}
            <div className="mt-6 p-4 rounded-2xl bg-white/5 border border-white/5 flex items-start gap-2.5 text-xs text-[#d8c7b5]/60 leading-normal">
              <Info size={14} className="text-[#f6d7b0] mt-0.5 flex-shrink-0" />
              <span>Sketches uploaded here become instantly selectable inside the AI Outfit Creator workbench.</span>
            </div>
          </div>

          {/* MAIN GALLERY CATALOG GRID (2 columns) */}
          <div className="lg:col-span-2 rounded-[30px] border border-white/10 bg-[#161311]/60 backdrop-blur-2xl p-8 min-h-[550px] flex flex-col">
            
            {/* GALLERY HEADER FILTERS */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-white/10 pb-6 mb-8 gap-4">
              <div>
                <h3 className="text-xl font-bold text-[#f6d7b0] tracking-wide uppercase">
                  My Media Catalog
                </h3>
                <p className="text-xs text-[#d8c7b5]/60 mt-1">Uploaded sketches and generated renders</p>
              </div>

              {/* TOGGLE TABS */}
              <div className="flex bg-black/40 rounded-full border border-white/10 p-[4px] self-stretch sm:self-auto">
                <button
                  onClick={() => setGalleryFilter("")}
                  className={`
                    px-4 py-2 text-xs rounded-full uppercase tracking-wider font-bold transition duration-300 flex-1 sm:flex-none
                    ${galleryFilter === "" 
                      ? "bg-[#f6d7b0] text-black" 
                      : "text-white/60 hover:text-white"}
                  `}
                >
                  All
                </button>
                <button
                  onClick={() => setGalleryFilter("upload")}
                  className={`
                    px-4 py-2 text-xs rounded-full uppercase tracking-wider font-bold transition duration-300 flex-1 sm:flex-none
                    ${galleryFilter === "upload" 
                      ? "bg-[#f6d7b0] text-black" 
                      : "text-white/60 hover:text-white"}
                  `}
                >
                  Uploads
                </button>
                <button
                  onClick={() => setGalleryFilter("generated")}
                  className={`
                    px-4 py-2 text-xs rounded-full uppercase tracking-wider font-bold transition duration-300 flex-1 sm:flex-none
                    ${galleryFilter === "generated" 
                      ? "bg-[#f6d7b0] text-black" 
                      : "text-white/60 hover:text-white"}
                  `}
                >
                  Generations
                </button>
              </div>
            </div>

            {/* GALLERY IMAGES INNER */}
            {imagesLoading && images.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center py-20 text-center">
                <Loader2 className="animate-spin text-[#f6d7b0] mb-4" size={40} />
                <p className="text-sm text-[#d8c7b5]/70">Retrieving fashion catalog...</p>
              </div>
            ) : images.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center py-20 text-center">
                <div className="w-16 h-16 rounded-full border border-dashed border-[#f6d7b0]/20 flex items-center justify-center text-white/20 mb-6">
                  <Layers size={24} />
                </div>
                <h4 className="text-xl font-bold text-white mb-2">No Images in Catalog</h4>
                <p className="text-[#d8c7b5]/60 text-sm max-w-xs mx-auto">
                  {galleryFilter === "upload"
                    ? "You haven't uploaded any fashion sketches yet. Drag one onto the drop box to start."
                    : galleryFilter === "generated"
                    ? "You haven't generated any AI outfit renders yet. Try out the AI Outfit Creator!"
                    : "Your studio gallery is empty. Upload sketches or generate outfit layouts to fill it."}
                </p>
                
                {galleryFilter !== "" && (
                  <button
                    onClick={() => setGalleryFilter("")}
                    className="mt-6 px-5 py-2.5 rounded-full border border-[#f6d7b0]/40 text-[#f6d7b0] hover:bg-[#f6d7b0]/5 transition text-xs font-bold uppercase tracking-wider"
                  >
                    Reset Active Filters
                  </button>
                )}
              </div>
            ) : (
              <div className="flex-1 flex flex-col justify-between">
                
                {/* GALLERY GRID */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-6">
                  <AnimatePresence mode="popLayout">
                    {images.map((img) => (
                      <motion.div
                        key={img.id}
                        layout
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        whileHover={{ y: -6 }}
                        className="group relative h-[220px] rounded-2xl overflow-hidden border border-white/10 bg-black/40 cursor-pointer"
                        onClick={() => setActiveImage(img)}
                      >
                        <img
                          src={img.url.startsWith("/") ? `${API_URL}${img.url}` : img.url}
                          alt={img.prompt || "Fashion Sketch"}
                          className="w-full h-full object-cover transition duration-700 group-hover:scale-108"
                        />

                        {/* HOVER OVERLAY */}
                        <div className="absolute inset-0 bg-black/65 opacity-0 group-hover:opacity-100 transition duration-300 flex flex-col justify-between p-4 z-10">
                          <span className={`
                            self-start px-2.5 py-1 rounded-full text-[9px] font-bold uppercase tracking-wider
                            ${img.image_type === "upload" 
                              ? "bg-amber-400/20 text-amber-300 border border-amber-400/20" 
                              : "bg-[#f6d7b0]/20 text-[#f6d7b0] border border-[#f6d7b0]/20"}
                          `}>
                            {img.image_type}
                          </span>

                          <div className="flex items-center justify-between gap-2">
                            <span className="text-[10px] text-[#d8c7b5]/60 truncate max-w-[80px]">
                              ID: #{img.id}
                            </span>
                            <div className="w-8 h-8 rounded-full bg-white/10 hover:bg-[#f6d7b0] hover:text-black flex items-center justify-center transition">
                              <Maximize2 size={13} />
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>

                {/* LOAD MORE BUTTON */}
                {hasMore && (
                  <div className="mt-12 flex justify-center border-t border-white/5 pt-8">
                    <button
                      onClick={() => fetchImages(false)}
                      disabled={imagesLoading}
                      className="px-8 py-3.5 rounded-full border border-white/10 hover:border-white/20 hover:bg-white/5 text-xs uppercase font-bold tracking-wider transition disabled:opacity-40 disabled:hover:scale-100"
                    >
                      {imagesLoading ? "Loading images..." : "Load More"}
                    </button>
                  </div>
                )}

              </div>
            )}

          </div>

        </div>

      </div>

      {/* ── LIGHTBOX/DETAIL DIALOG MODAL ─────────────────────────────────────── */}
      <AnimatePresence>
        {activeImage && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/85 backdrop-blur-md"
            onClick={() => {
              if (!deletingLoading) {
                setActiveImage(null);
                setDeleteConfirmId(null);
              }
            }}
          >
            <motion.div
              initial={{ scale: 0.95, y: 15 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 15 }}
              className="relative w-full max-w-4xl rounded-[35px] border border-white/10 bg-[#141210]/95 backdrop-blur-2xl p-6 sm:p-10 flex flex-col md:flex-row gap-8 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              {/* IMAGE PORTION (LEFT) */}
              <div className="flex-1 relative h-[300px] sm:h-[450px] rounded-2xl overflow-hidden border border-white/5 bg-black/45 flex items-center justify-center">
                <img
                  src={activeImage.url.startsWith("/") ? `${API_URL}${activeImage.url}` : activeImage.url}
                  alt={activeImage.prompt || "Fashion Sketch Detail"}
                  className="w-full h-full object-contain"
                />
              </div>

              {/* DETAILED SPECS (RIGHT) */}
              <div className="flex-1 flex flex-col justify-between">
                <div>
                  
                  {/* TAGS */}
                  <div className="flex items-center justify-between border-b border-white/10 pb-5 mb-6">
                    <span className={`
                      px-3.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider
                      ${activeImage.image_type === "upload" 
                        ? "bg-amber-400/20 text-amber-300 border border-amber-400/20" 
                        : "bg-[#f6d7b0]/20 text-[#f6d7b0] border border-[#f6d7b0]/20"}
                    `}>
                      {activeImage.image_type} Image
                    </span>

                    <button
                      onClick={() => {
                        setActiveImage(null);
                        setDeleteConfirmId(null);
                      }}
                      className="w-8 h-8 rounded-full border border-white/10 hover:border-white/30 text-white/50 hover:text-white flex items-center justify-center transition"
                    >
                      <XCircle size={18} />
                    </button>
                  </div>

                  <h3 className="text-2xl font-black text-[#f6d7b0] mb-6">
                    IMAGING SPECIFICATIONS
                  </h3>

                  <div className="space-y-4 text-sm">
                    <div className="bg-white/5 rounded-2xl p-4 border border-white/5 space-y-1.5">
                      <p className="text-xs uppercase tracking-wider text-[#d8c7b5]/50 font-semibold">Image Identity</p>
                      <p className="font-mono text-white/90">ID: #{activeImage.id}</p>
                    </div>

                    <div className="bg-white/5 rounded-2xl p-4 border border-white/5 space-y-1.5">
                      <p className="text-xs uppercase tracking-wider text-[#d8c7b5]/50 font-semibold">Prompt String</p>
                      <p className="text-white/90 leading-relaxed font-medium">
                        {activeImage.prompt || "N/A — Manually Uploaded Layout Sketch"}
                      </p>
                    </div>

                    <div className="bg-white/5 rounded-2xl p-4 border border-white/5 flex items-center gap-3">
                      <Calendar size={16} className="text-[#f6d7b0] flex-shrink-0" />
                      <div className="space-y-0.5">
                        <p className="text-[10px] uppercase tracking-wider text-[#d8c7b5]/50 font-semibold">Created On</p>
                        <p className="text-xs text-white/90 font-medium">
                          {new Date(activeImage.created_at).toLocaleString("en-US", {
                            dateStyle: "medium",
                            timeStyle: "short",
                          })}
                        </p>
                      </div>
                    </div>
                  </div>

                </div>

                {/* BOTTOM BUTTON MATRIX */}
                <div className="mt-8 border-t border-white/10 pt-6 flex flex-col gap-4">
                  
                  {/* Download */}
                  <a
                    href={activeImage.url.startsWith("/") ? `${API_URL}${activeImage.url}` : activeImage.url}
                    download={`styleforge-${activeImage.image_type}-${activeImage.id}.png`}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full"
                  >
                    <button className="w-full py-4 rounded-full bg-[#f6d7b0] text-black font-bold hover:scale-[1.02] transition duration-300 flex items-center justify-center gap-2">
                      <Download size={16} />
                      <span>Download HD Image</span>
                    </button>
                  </a>

                  {/* Deletion with warning trigger */}
                  {deleteConfirmId === activeImage.id ? (
                    <div className="flex flex-col gap-3 p-4 rounded-2xl border border-red-500/25 bg-red-500/5">
                      <div className="text-xs text-red-200 font-semibold leading-relaxed">
                        Are you sure you want to delete this image? This cleans the file off server storage and cannot be undone.
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <button
                          onClick={() => setDeleteConfirmId(null)}
                          disabled={deletingLoading}
                          className="py-2.5 rounded-xl border border-white/10 hover:bg-white/5 text-xs font-bold tracking-wider"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleDeleteImage(activeImage.id)}
                          disabled={deletingLoading}
                          className="py-2.5 rounded-xl bg-red-500 hover:bg-red-600 text-white text-xs font-bold tracking-wider flex items-center justify-center gap-1.5"
                        >
                          {deletingLoading && <Loader2 size={12} className="animate-spin" />}
                          Confirm Delete
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDeleteConfirmId(activeImage.id)}
                      className="w-full py-4 rounded-full border border-red-500/20 text-red-400 hover:bg-red-500/10 hover:border-red-500/40 transition font-bold flex items-center justify-center gap-2"
                    >
                      <Trash2 size={16} />
                      <span>Delete from Catalog</span>
                    </button>
                  )}

                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </main>
  );
}
