export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-6 py-24">
      <div className="w-full max-w-md text-center">
        <p className="text-[120px] uppercase tracking-[0.16em] text-muted-foreground">
          404
        </p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-foreground">
          Page not found
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          This page does not exist or you do not have permission to view it.
        </p>
      </div>
    </div>
  );
}
