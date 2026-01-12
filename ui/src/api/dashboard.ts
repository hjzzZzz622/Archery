import type { DashboardDataResponse } from "../types/dashboard";

export async function fetchDashboardData(params: {
  startDate: string;
  endDate: string;
}): Promise<DashboardDataResponse> {
  const url = new URL("/dashboard/data/", window.location.origin);
  url.searchParams.set("start_date", params.startDate);
  url.searchParams.set("end_date", params.endDate);

  const res = await fetch(url.toString(), {
    method: "GET",
    credentials: "include", // 同域带 cookie（Django session）
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }
  return (await res.json()) as DashboardDataResponse;
}