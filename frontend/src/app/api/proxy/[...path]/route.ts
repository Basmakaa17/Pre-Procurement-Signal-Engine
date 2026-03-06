import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_URL ||
  "http://localhost:8000";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const pathStr = path.length ? path.join("/") : "";
  const url = new URL(request.url);
  const query = url.searchParams.toString();
  const backendPath = query ? `${pathStr}?${query}` : pathStr;
  const target = `${BACKEND_URL.replace(/\/$/, "")}/${backendPath}`;

  try {
    const res = await fetch(target, {
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error("[proxy] GET", target, err);
    return NextResponse.json(
      { error: "Backend unreachable", details: String(err) },
      { status: 502 }
    );
  }
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const pathStr = path.length ? path.join("/") : "";
  const target = `${BACKEND_URL.replace(/\/$/, "")}/${pathStr}`;
  let body: string | undefined;
  try {
    body = await request.text();
  } catch {
    body = undefined;
  }

  try {
    const res = await fetch(target, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: body || undefined,
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    console.error("[proxy] POST", target, err);
    return NextResponse.json(
      { error: "Backend unreachable", details: String(err) },
      { status: 502 }
    );
  }
}
