"use client";

import dynamic from "next/dynamic";

const ScrollDemo = dynamic(() => import("./ScrollDemo").then((m) => ({ default: m.ScrollDemo })), {
  ssr: false,
  loading: () => <ScrollDemoSkeleton />,
});

function ScrollDemoSkeleton() {
  return (
    <section className="relative h-[420vh]" aria-busy aria-label="Loading interactive demo">
      <div className="sticky top-0 min-h-screen overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-40" />
        <div className="relative mx-auto flex min-h-screen max-w-7xl flex-col items-center justify-center px-6 py-20">
          <div className="h-10 w-64 max-w-full animate-pulse rounded-md bg-muted" />
          <div className="mt-6 h-64 w-full max-w-4xl animate-pulse rounded-2xl border border-border bg-card/50" />
        </div>
      </div>
    </section>
  );
}

export function HomeScrollDemo() {
  return <ScrollDemo />;
}
