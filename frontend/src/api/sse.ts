// Native `EventSource` only supports GET requests; the backend's step
// pipeline is a POST (it has a JSON body). This parses the same
// "event: X\ndata: Y\n\n" SSE format directly from a streamed fetch
// response body instead — a standard, well-known pattern for SSE-over-POST.
// Must stay in sync with backend/src/studyhelp/api/routes/sessions.py's
// `_sse_format()`.

export interface SseEvent {
  event: string;
  data: unknown;
}

export async function* parseSseStream(response: Response): AsyncGenerator<SseEvent> {
  if (!response.body) {
    throw new Error("Response has no readable body");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const parsed = parseSseBlock(block);
        if (parsed) yield parsed;
        boundary = buffer.indexOf("\n\n");
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseSseBlock(block: string): SseEvent | null {
  let eventName: string | null = null;
  let dataLine: string | null = null;
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) eventName = line.slice("event: ".length);
    if (line.startsWith("data: ")) dataLine = line.slice("data: ".length);
  }
  if (eventName === null || dataLine === null) return null;
  return { event: eventName, data: JSON.parse(dataLine) as unknown };
}
