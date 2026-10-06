import { HealthResponse, HouseholdsResponse, ForecastResponse, MetricsResponse, HistoryResponse } from '../types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001';

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, { next: { revalidate: 0 } });
  if (!res.ok) throw new Error(`Health fetch failed: ${res.status}`);
  return res.json();
}

export async function getHouseholds(): Promise<HouseholdsResponse> {
  const res = await fetch(`${API_BASE}/households`, { next: { revalidate: 3600 } });
  if (!res.ok) throw new Error(`Households fetch failed: ${res.status}`);
  return res.json();
}

export async function getForecast(householdId: string): Promise<ForecastResponse> {
  const res = await fetch(`${API_BASE}/forecast/${householdId}`, { next: { revalidate: 0 } });
  
  if (!res.ok) {
    if (res.status === 404) throw new Error('404: Household not found.');
    if (res.status === 422) throw new Error('422: This household does not have sufficient historical data for forecasting.');
    if (res.status === 503) throw new Error('503: Forecast service is currently unavailable.');
    throw new Error('500: We couldn\'t generate the forecast right now. Please try again.');
  }
  
  return res.json();
}

export async function getMetrics(): Promise<MetricsResponse> {
  const res = await fetch(`${API_BASE}/metrics`, { next: { revalidate: 3600 } });
  if (!res.ok) throw new Error(`Metrics fetch failed: ${res.status}`);
  return res.json();
}

export async function getHistory(householdId: string, days: number = 365): Promise<HistoryResponse> {
  const res = await fetch(`${API_BASE}/history/${householdId}?days=${days}`, { next: { revalidate: 0 } });
  
  if (!res.ok) {
    if (res.status === 404) throw new Error('404: Household not found.');
    throw new Error('500: Unable to load historical consumption.');
  }
  
  return res.json();
}

