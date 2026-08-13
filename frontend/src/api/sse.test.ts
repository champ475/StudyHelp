import { describe, expect, it } from "vitest";
import { parseSseStream } from "./sse";

function makeResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(stream);
}

async function collect<T>(iterable: AsyncGenerator<T>): Promise<T[]> {
  const results: T[] = [];
  for await (const item of iterable) results.push(item);
  return results;
}

describe("parseSseStream", () => {
  it("parses a single event", async () => {
    const response = makeResponse(['event: verdict\ndata: {"is_valid":true}\n\n']);
    const events = await collect(parseSseStream(response));
    expect(events).toEqual([{ event: "verdict", data: { is_valid: true } }]);
  });

  it("parses multiple events delivered in one write", async () => {
    const response = makeResponse([
      'event: verdict\ndata: {"is_valid":false}\n\n' +
        'event: message_chunk\ndata: {"text":"hi"}\n\n',
    ]);
    const events = await collect(parseSseStream(response));
    expect(events).toHaveLength(2);
    expect(events[0]).toEqual({ event: "verdict", data: { is_valid: false } });
    expect(events[1]).toEqual({ event: "message_chunk", data: { text: "hi" } });
  });

  it("reassembles an event split across two separate stream writes", async () => {
    const response = makeResponse(['event: verdict\ndata: {"is_valid"', ":true}\n\n"]);
    const events = await collect(parseSseStream(response));
    expect(events).toEqual([{ event: "verdict", data: { is_valid: true } }]);
  });

  it("throws when the response has no readable body", async () => {
    const response = new Response(null);
    await expect(collect(parseSseStream(response))).rejects.toThrow(/no readable body/);
  });
});
