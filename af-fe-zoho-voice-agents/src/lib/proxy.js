import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/config";

const BODYLESS_METHODS = new Set(["GET", "HEAD"]);

export async function proxyRequest(request, targetPath) {
  if (!BACKEND_URL) {
    return NextResponse.json(
      { error: "BACKEND_URL is not configured." },
      { status: 500 }
    );
  }

  const backend = BACKEND_URL.replace(/\/$/, "");
  const url = `${backend}${targetPath}${request.nextUrl.search}`;
  const headers = new Headers(request.headers);

  headers.set("host", new URL(backend).host);
  headers.delete("content-length");

  // ---- WebSocket Upgrade handling ----
  const upgradeHeader = request.headers.get("upgrade");
  if (upgradeHeader && upgradeHeader.toLowerCase() === "websocket") {
    // For a WebSocket handshake we cannot use fetch – we simply rewrite the request
    // to the backend URL so that the underlying server (Next.js edge runtime) will
    // forward the Upgrade request directly. This works because NextResponse.rewrite
    // supports external URLs and preserves the original headers.
    return NextResponse.rewrite(url);
  }

  let response;
  try {
    response = await fetch(url, {
      method: request.method,
      headers,
      body: BODYLESS_METHODS.has(request.method)
        ? undefined
        : await request.arrayBuffer(),
      redirect: "manual",
      signal: AbortSignal.timeout(120_000),
    });
  } catch (err) {
    const msg = err?.name === "TimeoutError" ? "Request timed out." : "Backend unreachable.";
    return NextResponse.json({ error: msg }, { status: 504 });
  }

  return new NextResponse(response.body, {
    status: response.status,
    headers: response.headers,
  });
}
