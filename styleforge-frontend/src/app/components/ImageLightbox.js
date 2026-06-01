"use client";

import { useState, useRef, useEffect } from "react";
import { X, ZoomIn, ZoomOut, Maximize, Download } from "lucide-react";

export default function ImageLightbox({ src, downloadUrl, onClose }) {
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const imgRef = useRef(null);

  // Reset zoom and panning coordinates when the image source changes
  useEffect(() => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  }, [src]);

  const handleZoomIn = () => setScale((prev) => Math.min(prev + 0.25, 4));
  const handleZoomOut = () =>
    setScale((prev) => {
      const newScale = Math.max(prev - 0.25, 0.5);
      if (newScale <= 1) setPosition({ x: 0, y: 0 }); // reset position if zoomed back to fit
      return newScale;
    });

  const handleReset = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  // Mouse wheel scroll to zoom
  const handleWheel = (e) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      setScale((prev) => Math.min(prev + 0.1, 4));
    } else {
      setScale((prev) => {
        const newScale = Math.max(prev - 0.1, 0.5);
        if (newScale <= 1) setPosition({ x: 0, y: 0 });
        return newScale;
      });
    }
  };

  // Double-click to toggle between zoom-fit and 2x zoom
  const handleDoubleClick = (e) => {
    e.stopPropagation();
    if (scale > 1) {
      handleReset();
    } else {
      setScale(2);
      // Center the zoom on mouse pointer location relative to container
      const container = e.currentTarget.getBoundingClientRect();
      const clickX = e.clientX - container.left - container.width / 2;
      const clickY = e.clientY - container.top - container.height / 2;
      setPosition({ x: -clickX, y: -clickY });
    }
  };

  // Drag to pan logic
  const handleMouseDown = (e) => {
    if (scale <= 1) return; // Only allow panning when zoomed in
    e.preventDefault();
    setIsDragging(true);
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUpOrLeave = () => {
    setIsDragging(false);
  };

  // Download handler
  const handleDownload = async (e) => {
    e.stopPropagation();
    try {
      const targetUrl = downloadUrl || src;
      // If it's a blob URL, we can directly download it
      if (targetUrl.startsWith("blob:") || targetUrl.startsWith("data:")) {
        const link = document.createElement("a");
        link.href = targetUrl;
        link.download = `styleforge-inspect-${Date.now()}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        return;
      }

      // Fetch file as blob to prevent standard browser image opening
      const response = await fetch(targetUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `styleforge-inspect-${Date.now()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Failed to download image", error);
      // Fallback redirect method
      const link = document.createElement("a");
      link.href = downloadUrl || src;
      link.download = "styleforge-inspect.png";
      link.target = "_blank";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/90 backdrop-blur-md animate-in fade-in duration-300 select-none"
      onClick={onClose}
    >
      {/* Top Glassmorphic Navigation Panel */}
      <div
        className="absolute top-6 left-6 right-6 z-51 flex items-center justify-between p-4 rounded-3xl bg-white/5 border border-white/10 backdrop-blur-xl shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex flex-col pl-2">
          <span className="text-sm font-bold tracking-wider text-[#f6d7b0] uppercase">
            Sartorial Inspection
          </span>
          <span className="text-[10px] text-[#d8c7b5]/60 mt-0.5">
            whatsapp-style pan and zoom visualizer
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Zoom controls */}
          <button
            onClick={handleZoomIn}
            className="p-3.5 rounded-2xl bg-white/5 border border-white/10 text-white hover:bg-white/10 active:scale-95 transition"
            title="Zoom In (+)"
          >
            <ZoomIn size={16} />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-3.5 rounded-2xl bg-white/5 border border-white/10 text-white hover:bg-white/10 active:scale-95 transition"
            title="Zoom Out (-)"
          >
            <ZoomOut size={16} />
          </button>
          <button
            onClick={handleReset}
            className="p-3.5 rounded-2xl bg-white/5 border border-white/10 text-white hover:bg-white/10 active:scale-95 transition"
            title="Reset (1:1)"
          >
            <Maximize size={16} />
          </button>
          <button
            onClick={handleDownload}
            className="p-3.5 rounded-2xl bg-[#f6d7b0] text-black hover:scale-105 active:scale-95 transition shadow-lg shadow-amber-500/10 font-bold"
            title="Download Design"
          >
            <Download size={16} />
          </button>
          <div className="w-[1px] h-6 bg-white/15 mx-2" />
          <button
            onClick={onClose}
            className="p-3.5 rounded-2xl bg-red-500/10 border border-red-500/25 text-red-400 hover:bg-red-500/20 active:scale-95 transition"
            title="Close Viewer (Esc)"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Main Interactive Zoom Workspace */}
      <div
        className="w-full h-full flex items-center justify-center overflow-hidden"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUpOrLeave}
        onMouseLeave={handleMouseUpOrLeave}
        onDoubleClick={handleDoubleClick}
        style={{ cursor: scale > 1 ? (isDragging ? "grabbing" : "grab") : "default" }}
      >
        <img
          ref={imgRef}
          src={src}
          alt="Visual Inspection"
          style={{
            transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
            transition: isDragging ? "none" : "transform 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
            maxHeight: "80vh",
            maxWidth: "90vw",
            objectFit: "contain",
          }}
          className="pointer-events-none select-none rounded-2xl border border-white/5 shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        />
      </div>

      {/* Bottom Subtle Usage Instructions */}
      <div className="absolute bottom-6 text-[10px] text-[#d8c7b5]/40 tracking-widest uppercase pointer-events-none text-center">
        Scroll Wheel to Zoom • Double Click to Toggle • Drag when Zoomed to Pan
      </div>
    </div>
  );
}
