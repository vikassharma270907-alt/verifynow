/** Mirrors the backend default upload limit (MAX_UPLOAD_SIZE_MB, sized for Vercel). */
export const MAX_UPLOAD_MB = 4;
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;
/** Images are not advertised: the backend answers 501 for them. */
export const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".md"] as const;

export function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === "AbortError";
}
