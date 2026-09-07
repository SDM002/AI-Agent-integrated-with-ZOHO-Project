import { proxyRequest } from "@/lib/proxy";

async function handler(request, { params }) {
  const { path } = await params;
  const normalizedPath = path?.join("/") ?? "";
  return proxyRequest(request, `/api/${normalizedPath}`);
}

export {
  handler as DELETE,
  handler as GET,
  handler as HEAD,
  handler as OPTIONS,
  handler as PATCH,
  handler as POST,
  handler as PUT,
};
