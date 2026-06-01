# Styleforge Product Requirements Document (PRD)

## Project Overview
Styleforge is an innovative, sustainable fashion platform that allows users to recycle fabrics, use AI to design custom clothes, utilize Virtual Try-On (VTON), and connect directly with tailors.

## Brand Aesthetic
- **Style:** High-end fashion, minimalistic, sleek, and modern (e.g., SSENSE, Zara).
- **Interactive Elements:** Subtle 3D elements (React Three Fiber) for a cutting-edge feel.
- **Identity:** Prominent "Make in India" badge/stamp in global footer or navigation.

## Architecture & Portals
The platform consists of four distinct portals accessible via a global routing shell:

### 1. Buyer Portal (Core App)
- **Landing Page:** 3D hero section with "Recycle/Pick a Fabric" and "Start from Scratch" CTAs.
- **Fabric Reuse Flow:** Catalog -> AI Design Configurator (based on measurements/fabric) -> Auth Gate -> AI Generation & VTON -> Checkout/Handoff to Tailor.
- **Start from Scratch Flow:** Studio Workspace (upload sketches/prompts) -> AI Generation & VTON -> Checkout/Handoff.

### 2. Tailor Dashboard
- **Active Orders:** Kanban/List view.
- **Marketplace:** Browse/accept new orders.
- **Order Details:** AI Blueprints, measurements, and status tracking (Cutting, Stitching, etc.).
- **Wallet:** Pending/settled earnings.

### 3. Fabric Seller Dashboard
- **Analytics:** Revenue and inventory charts.
- **Inventory Management:** CRUD operations for fabric listings.

### 4. Admin Portal
- **Overview:** Global metrics and revenue.
- **Financials:** Settlement interface for Tailors and Sellers.
- **User Management:** Directory with moderation actions (Approve, Flag, Ban).

## Technical Requirements
- **Framework:** React/Next.js with Tailwind CSS.
- **3D:** @react-three/fiber for the buyer landing page.
- **State:** React Hooks/Context with robust mock data.
- **Responsiveness:** Mobile-first approach.
- **UX:** Micro-interactions, modal transitions, and multi-step loading for AI steps.