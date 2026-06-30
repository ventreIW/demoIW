"use client"

import { useRouter } from "next/navigation"
import CsvUpload from "@/components/scenarios/CsvUpload"

export default function CsvUploadWrapper() {
  const router = useRouter()
  return <CsvUpload onUploadComplete={() => router.refresh()} />
}