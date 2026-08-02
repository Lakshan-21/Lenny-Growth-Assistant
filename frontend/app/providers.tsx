"use client";

import { useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";

import { createQueryClient } from "@/lib/query-client";

export function Providers({ children }: { children: React.ReactNode }) {
  // One QueryClient per browser session, created lazily on the client
  // (not module-level) so server-rendered requests never share cache
  // state across users — the standard TanStack Query + App Router pattern.
  const [queryClient] = useState(createQueryClient);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
