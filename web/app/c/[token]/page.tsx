import React, { Suspense } from "react";
import { normalizeMode } from "../../../lib/api";
import { ChatSessionPageClient } from "./chat-session-page-client";

type ChatSessionPageProps = {
  params: Promise<{
    token: string;
  }>;
  searchParams: Promise<{
    mode?: string | string[];
  }>;
};

export default async function ChatSessionPage(props: ChatSessionPageProps) {
  const [{ token }, query] = await Promise.all([props.params, props.searchParams]);
  const requestedMode = normalizeMode(query.mode);

  return (
    <Suspense fallback={<main className="min-h-screen" />}>
      <ChatSessionPageClient requestedMode={requestedMode} token={token} />
    </Suspense>
  );
}
