"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function VirtualTryOnRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/style-critique");
  }, [router]);

  return null;
}