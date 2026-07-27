export class HttpError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "HttpError";
  }
}

export function isNotFoundError(error: unknown): boolean {
  return error instanceof HttpError && error.status === 404;
}
