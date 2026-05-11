export function Footer() {
  return (
    <footer className="border-t border-border mt-32">
      <div className="mx-auto max-w-7xl px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-muted-foreground font-mono">
        <p>© {new Date().getFullYear()} BOMA — Bill Of Materials Agent</p>
        <p>
          Sourcing from <span className="text-foreground">DigiKey</span>
          <span className="text-muted-foreground"> · Mouser &amp; more soon</span>
        </p>
      </div>
    </footer>
  );
}
