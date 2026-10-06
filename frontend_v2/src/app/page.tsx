'use client';

import { useState, useEffect, useMemo, UIEvent } from 'react';
import { getHealth, getHouseholds, getForecast, getMetrics, getHistory } from '../lib/api';
import { HealthResponse, HouseholdsResponse, ForecastResponse, MetricsResponse, HistoryResponse } from '../types';
import { ResponsiveContainer, ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from 'recharts';
import { BarChart2, RefreshCw, User, Calendar, Clock, Target, BarChart, TrendingUp, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Calculator } from 'lucide-react';

interface ChartPoint {
  dateStr: string;
  timestamp: number;
  fullDate: string;
  actual_kwh: number | null;
  expected_kwh: number | null;
  predicted_range?: [number, number] | null;
  predicted_upper_kwh?: number | null;
  predicted_lower_kwh?: number | null;
  isConnectionPoint: boolean;
  isPartialDay: boolean;
}

const CustomForecastDot = (props: any) => {
  const { cx, cy, payload, value } = props;
  if (value === null || value === undefined) return null;
  if (payload.isConnectionPoint) return null;
  return <circle cx={cx} cy={cy} r={4} strokeWidth={2} fill="#fff" stroke="#10b981" />;
};

const BoundaryLabel = (props: any) => {
  const { viewBox } = props;
  if (!viewBox) return null;
  return (
    <g>
      <text x={viewBox.x - 8} y={viewBox.y - 12} textAnchor="end" fontSize={10} fontWeight="bold" fill="#475569">Feb 27, 2014</text>
      <text x={viewBox.x - 8} y={viewBox.y - 2} textAnchor="end" fontSize={9} fill="#64748b">Last actual</text>
      <text x={viewBox.x + 8} y={viewBox.y - 12} textAnchor="start" fontSize={10} fontWeight="bold" fill="#10b981">Feb 28, 2014</text>
      <text x={viewBox.x + 8} y={viewBox.y - 2} textAnchor="start" fontSize={9} fill="#10b981">First predicted</text>
    </g>
  );
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white dark:bg-slate-900 p-3 border border-slate-200 dark:border-slate-700 shadow-lg rounded-lg text-sm z-50">
        <p className="font-semibold text-slate-800 dark:text-slate-100 mb-2">
          {new Date(data.fullDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
        </p>
        <div className="space-y-1">
          {data.isPartialDay && (
            <div className="text-amber-600 dark:text-amber-400 font-medium text-xs mb-2">
              <p>Feb 28 — Partial-day data</p>
              <p className="opacity-80">Only 30 minutes of source readings available.</p>
            </div>
          )}
          {data.actual_kwh !== null && (
            <div className="flex justify-between items-center gap-4 text-slate-700 dark:text-slate-300">
              <span className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
                Actual
              </span>
              <span className="font-bold">{data.actual_kwh.toFixed(2)} kWh</span>
            </div>
          )}
          {data.expected_kwh !== null && !data.isConnectionPoint && (
            <div className="flex justify-between items-center gap-4 text-slate-700 dark:text-slate-300">
              <span className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                Forecast
              </span>
              <span className="font-bold">{data.expected_kwh.toFixed(2)} kWh</span>
            </div>
          )}
          {data.predicted_upper_kwh !== null && data.predicted_upper_kwh !== undefined && !data.isConnectionPoint && (
            <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-1">
              Range: {data.predicted_lower_kwh?.toFixed(2)} - {data.predicted_upper_kwh?.toFixed(2)} kWh
            </div>
          )}
        </div>
      </div>
    );
  }
  return null;
};

export default function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [householdsData, setHouseholdsData] = useState<HouseholdsResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  
  const [selectedHousehold, setSelectedHousehold] = useState<string>('');
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [historyDays, setHistoryDays] = useState<number>(30); // Default to 30 based on UI active state
  
  const [isLoadingHouseholds, setIsLoadingHouseholds] = useState(true);
  const [isLoadingForecast, setIsLoadingForecast] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const [startIndex, setStartIndex] = useState(0);
  const [assumedRate, setAssumedRate] = useState<number>(0.15);

  // Initial Load
  useEffect(() => {
    async function init() {
      try {
        const [healthData, hData, mData] = await Promise.all([
          getHealth().catch(() => null),
          getHouseholds(),
          getMetrics()
        ]);
        if (healthData) setHealth(healthData);
        setHouseholdsData(hData);
        setMetrics(mData);
        
        // Auto-select first household if none selected
        if (hData && hData.households.length > 0) {
          setSelectedHousehold(hData.households[0]);
        }
      } catch (err: any) {
        setError("Unable to connect to the forecasting service.");
      } finally {
        setIsLoadingHouseholds(false);
      }
    }
    init();
  }, []);

  // Fetch Forecast
  useEffect(() => {
    if (!selectedHousehold) {
      setForecast(null);
      setError(null);
      return;
    }
    
    async function loadForecast() {
      setIsLoadingForecast(true);
      setError(null);
      try {
        const result = await getForecast(selectedHousehold);
        setForecast(result);
      } catch (err: any) {
        setError(err.message || 'Unable to connect to the forecasting service.');
        setForecast(null);
      } finally {
        setIsLoadingForecast(false);
      }
    }
    loadForecast();
  }, [selectedHousehold]);

  // Fetch History
  useEffect(() => {
    if (!selectedHousehold) {
      setHistory(null);
      setHistoryError(null);
      return;
    }
    
    async function loadHistory() {
      try {
        const result = await getHistory(selectedHousehold, historyDays);
        setHistory(result);
        setHistoryError(null);
      } catch (err: any) {
        setHistoryError('Unable to load historical consumption.');
        setHistory(null);
      }
    }
    loadHistory();
  }, [selectedHousehold, historyDays]);

  // Process Chart Data
  const fullChartData = useMemo(() => {
    if (!forecast || !history) return [];
    
    const combined: Record<string, ChartPoint> = {};
    
    history.history.forEach(pt => {
      if (pt.date === '2014-02-28') return; // Completely drop from plotting history
      combined[pt.date] = {
        dateStr: new Date(pt.date).toLocaleDateString('en-US', { month: 'short', day: '2-digit' }),
        timestamp: new Date(pt.date).getTime(),
        fullDate: pt.date,
        actual_kwh: pt.consumption_kwh,
        expected_kwh: null,
        isConnectionPoint: false,
        isPartialDay: false
      };
    });
    
    forecast.forecast.forEach(pt => {
      const isPartial = pt.date === '2014-02-28';
      if (!combined[pt.date]) {
        combined[pt.date] = {
          dateStr: new Date(pt.date).toLocaleDateString('en-US', { month: 'short', day: '2-digit' }),
          timestamp: new Date(pt.date).getTime(),
          fullDate: pt.date,
          actual_kwh: null,
          expected_kwh: pt.predicted_consumption_kwh,
          predicted_range: [(pt as any).predicted_lower_kwh, (pt as any).predicted_upper_kwh],
          predicted_upper_kwh: (pt as any).predicted_upper_kwh,
          predicted_lower_kwh: (pt as any).predicted_lower_kwh,
          isConnectionPoint: false,
          isPartialDay: isPartial
        };
      } else {
        combined[pt.date].expected_kwh = pt.predicted_consumption_kwh;
        combined[pt.date].predicted_range = [(pt as any).predicted_lower_kwh, (pt as any).predicted_upper_kwh];
        combined[pt.date].predicted_upper_kwh = (pt as any).predicted_upper_kwh;
        combined[pt.date].predicted_lower_kwh = (pt as any).predicted_lower_kwh;
        combined[pt.date].isPartialDay = isPartial;
      }
    });
    
    // Connect the lines
    const completeHistory = history.history.filter(pt => pt.date !== '2014-02-28');
    if (completeHistory.length > 0) {
      const lastCompleteDate = completeHistory[completeHistory.length - 1].date;
      if (combined[lastCompleteDate]) {
        combined[lastCompleteDate].expected_kwh = combined[lastCompleteDate].actual_kwh;
        combined[lastCompleteDate].predicted_range = [combined[lastCompleteDate].actual_kwh as number, combined[lastCompleteDate].actual_kwh as number];
        combined[lastCompleteDate].predicted_upper_kwh = combined[lastCompleteDate].actual_kwh;
        combined[lastCompleteDate].predicted_lower_kwh = combined[lastCompleteDate].actual_kwh;
        combined[lastCompleteDate].isConnectionPoint = true;
      }
    }
    
    return Object.values(combined).sort((a, b) => a.timestamp - b.timestamp);
  }, [forecast, history]);

  const VISIBLE_POINTS = 21;
  const maxStartIndex = Math.max(0, fullChartData.length - VISIBLE_POINTS);

  const chartData = useMemo(() => {
    if (fullChartData.length <= VISIBLE_POINTS) return fullChartData;
    return fullChartData.slice(startIndex, startIndex + VISIBLE_POINTS);
  }, [fullChartData, startIndex]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setStartIndex(Number(e.target.value));
  };

  const scrollBy = (amount: number) => {
    setStartIndex(prev => Math.max(0, Math.min(maxStartIndex, prev + amount)));
  };

  const scrollToEdges = (direction: 'left' | 'right') => {
    setStartIndex(direction === 'left' ? 0 : maxStartIndex);
  };

  // Keep view at the rightmost edge when data updates
  useEffect(() => {
    if (fullChartData.length > 0) {
      setStartIndex(Math.max(0, fullChartData.length - VISIBLE_POINTS));
    }
  }, [fullChartData]);

  const completeHistoryForHeader = history?.history.filter(pt => pt.date !== '2014-02-28') || [];
  const lastActualDate = completeHistoryForHeader.length 
    ? new Date(completeHistoryForHeader[completeHistoryForHeader.length - 1].date).toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' })
    : '—';
    
  const forecastBoundaryStr = completeHistoryForHeader.length 
    ? new Date(completeHistoryForHeader[completeHistoryForHeader.length - 1].date).toLocaleDateString('en-US', { month: 'short', day: '2-digit' })
    : undefined;

  const refreshPage = () => {
    window.location.reload();
  };

  return (
    <div className="h-screen w-screen overflow-hidden bg-[#F0F4F8] dark:bg-slate-950 font-sans text-slate-800 dark:text-slate-200 flex flex-col">
      
      {/* 1. HEADER */}
      <header className="bg-[#0f294d] text-white px-6 py-2.5 flex items-center justify-between shadow-md shrink-0">
        <div className="flex items-center gap-4">
          <BarChart2 className="w-6 h-6 text-blue-400" />
          <div className="flex flex-col">
            <h1 className="text-lg font-semibold tracking-wide leading-tight">Smart Meter Consumption Forecasting</h1>
            <span className="text-xs text-blue-200">Household Consumption Insights & 7-Day Forecast</span>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-blue-100">
          <span>Data Through: 27 Feb 2014</span>
          <button onClick={refreshPage} className="hover:text-white transition-colors" aria-label="Refresh">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* ERROR BANNER */}
      {error && (
        <div className="max-w-[1400px] mx-auto px-4 w-full mt-3 shrink-0">
          <div className="bg-[#5c1328] text-rose-100 p-3 rounded-lg flex items-center gap-3 shadow-sm border border-[#7a1b37]">
            <Target className="w-4 h-4 text-rose-400" />
            <p className="font-medium text-sm">{error}</p>
          </div>
        </div>
      )}

      <main className="max-w-[1400px] w-full mx-auto px-4 sm:px-6 py-2.5 flex flex-col gap-3 overflow-hidden">
        
        {/* 2. COMPACT FORECAST CONTEXT BAR */}
        <section className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-2.5 flex flex-wrap items-center justify-between gap-3 shrink-0">
          
          <div className="flex items-center gap-3 flex-1 min-w-[200px]">
            <div className="bg-blue-50 dark:bg-slate-800 p-2 rounded-full text-blue-600 dark:text-blue-400">
              <User className="w-4 h-4" />
            </div>
            <div className="flex-1">
              <p className="text-[10px] font-bold text-slate-800 dark:text-slate-400 uppercase">Household ID</p>
              <select
                className="w-full mt-0.5 text-sm font-medium bg-transparent border border-slate-300 dark:border-slate-700 rounded py-0.5 px-2 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
                value={selectedHousehold}
                onChange={(e) => setSelectedHousehold(e.target.value)}
              >
                <option value="">Select Household</option>
                {householdsData?.households.map(hh => (
                  <option key={hh} value={hh}>{hh}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="hidden md:block w-px h-8 bg-slate-200 dark:bg-slate-700"></div>

          <div className="flex items-center gap-3 flex-1 min-w-[180px]">
            <Calendar className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <div>
              <p className="text-[10px] font-bold text-slate-800 dark:text-slate-400 uppercase">Last Actual Date</p>
              <p className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{lastActualDate}</p>
            </div>
          </div>

          <div className="hidden md:block w-px h-8 bg-slate-200 dark:bg-slate-700"></div>

          <div className="flex items-center gap-3 flex-1 min-w-[220px]">
            <Calendar className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <div>
              <p className="text-[10px] font-bold text-slate-800 dark:text-slate-400 uppercase">Forecast Period (7 Days)</p>
              <p className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">
                {forecast ? `${new Date(forecast.forecast_start).toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' })} \u2013 ${new Date(forecast.forecast_end).toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' })}` : '—'}
              </p>
            </div>
          </div>

          <div className="hidden md:block w-px h-8 bg-slate-200 dark:bg-slate-700"></div>

          <div className="flex items-center gap-3 flex-1 min-w-[150px]">
            <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <div>
              <p className="text-[10px] font-bold text-slate-800 dark:text-slate-400 uppercase">Forecast Horizon</p>
              <p className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">7 Days</p>
            </div>
          </div>

        </section>

        {/* 3. MAIN THREE-COLUMN LAYOUT */}
        {forecast && chartData.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-[180px_1fr_260px] gap-3 items-stretch shrink-0">
            
            {/* LEFT COLUMN: History Controls */}
            <div className="flex flex-col gap-4">
              
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-4">
                <div className="flex items-center gap-2 mb-2">
                  <BarChart className="w-4 h-4 text-slate-700 dark:text-slate-300" />
                  <h3 className="font-bold text-sm text-slate-900 dark:text-white">Historical Range</h3>
                </div>
                <div className="flex flex-col gap-2">
                  {[30, 90, 180, 365].map(days => (
                    <button
                      key={days}
                      onClick={() => setHistoryDays(days)}
                      className={`py-1.5 px-3 rounded-md text-xs font-bold border transition-all ${
                        historyDays === days 
                          ? 'bg-[#0f4eb3] text-white border-[#0f4eb3] shadow-inner' 
                          : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700'
                      }`}
                    >
                      {days} Days
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-3">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-4 h-4 text-slate-700 dark:text-slate-300" />
                  <h3 className="font-bold text-sm text-slate-900 dark:text-white">Explore History</h3>
                </div>
                <div className="flex items-center gap-1 mb-1">
                  <button onClick={() => scrollToEdges('left')} className="p-1 flex-shrink-0 border border-slate-300 dark:border-slate-600 rounded bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 disabled:opacity-50" disabled={startIndex === 0}>
                    <ChevronsLeft className="w-3 h-3" />
                  </button>
                  <button onClick={() => scrollBy(-7)} className="p-1 flex-shrink-0 border border-slate-300 dark:border-slate-600 rounded bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 disabled:opacity-50" disabled={startIndex === 0}>
                    <ChevronLeft className="w-3 h-3" />
                  </button>
                  
                  <input 
                    type="range" 
                    min="0" 
                    max={maxStartIndex} 
                    value={startIndex} 
                    onChange={handleSliderChange}
                    disabled={maxStartIndex === 0}
                    className="flex-1 min-w-[30px] h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-[#0f4eb3] disabled:opacity-50"
                  />
                  
                  <button onClick={() => scrollBy(7)} className="p-1 flex-shrink-0 border border-slate-300 dark:border-slate-600 rounded bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 disabled:opacity-50" disabled={startIndex === maxStartIndex}>
                    <ChevronRight className="w-3 h-3" />
                  </button>
                  <button onClick={() => scrollToEdges('right')} className="p-1 flex-shrink-0 border border-slate-300 dark:border-slate-600 rounded bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 disabled:opacity-50" disabled={startIndex === maxStartIndex}>
                    <ChevronsRight className="w-3 h-3" />
                  </button>
                </div>
                <div className="flex justify-between text-[10px] font-bold text-slate-600 dark:text-slate-400 mt-1">
                  <span>Older</span>
                  <span>Recent</span>
                </div>
                <p className="text-[9px] text-slate-400 mt-1">Drag or use arrows to navigate.</p>
              </div>
            </div>

            {/* CENTER COLUMN: Main Chart */}
            <div className="flex flex-col bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm relative min-w-0">
              <div className="p-3 border-b border-slate-100 dark:border-slate-800 flex items-center">
                <BarChart className="w-4 h-4 text-blue-600 mr-2" />
                <h2 className="text-sm font-bold text-[#0f294d] dark:text-white">Actual vs Forecast Consumption (kWh)</h2>
              </div>
              
              <div className="flex-1 p-3 relative flex flex-col">
                {/* Custom Legend to match screenshot */}
                <div className="flex gap-6 mb-4 ml-8 shrink-0 flex-wrap">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center">
                      <div className="w-5 h-0.5 bg-blue-500"></div>
                      <div className="w-2.5 h-2.5 rounded-full border-2 border-blue-500 bg-white -ml-3.5 z-10"></div>
                    </div>
                    <span className="text-xs font-bold text-slate-800">Actual (Historical)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center">
                      <div className="w-5 h-0.5 bg-emerald-500"></div>
                      <div className="w-2.5 h-2.5 rounded-full border-2 border-emerald-500 bg-white -ml-3.5 z-10"></div>
                    </div>
                    <span className="text-xs font-bold text-slate-800">Forecast (7 Days)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-3 bg-emerald-500 opacity-20"></div>
                    <span className="text-xs font-bold text-slate-800">Forecast Range</span>
                  </div>
                </div>

                <div className="w-full min-h-[220px] flex-1 relative">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 10, bottom: 25 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                        <XAxis 
                          dataKey="dateStr" 
                          tick={{ fontSize: 10, fill: '#475569', fontWeight: 600 }} 
                          tickLine={false} 
                          axisLine={{ stroke: '#cbd5e1' }}
                          tickMargin={10}
                          minTickGap={15}
                        />
                        <YAxis 
                          tick={{ fontSize: 10, fill: '#475569', fontWeight: 600 }} 
                          tickLine={false} 
                          axisLine={false}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#94a3b8', strokeWidth: 1, strokeDasharray: '4 4' }} />
                        
                        {/* Boundary line */}
                        {forecastBoundaryStr && (
                          <ReferenceLine 
                            x={forecastBoundaryStr} 
                            stroke="#64748b" 
                            strokeDasharray="4 4" 
                            strokeWidth={1.5}
                            label={<BoundaryLabel />}
                          />
                        )}

                        <Line 
                          type="linear" 
                          dataKey="actual_kwh" 
                          stroke="#3b82f6" 
                          strokeWidth={2.5} 
                          dot={{ r: 4, strokeWidth: 2, fill: '#fff', stroke: '#3b82f6' }}
                          activeDot={{ r: 6, strokeWidth: 0, fill: '#3b82f6' }}
                          isAnimationActive={false}
                        />
                        <Area 
                          type="monotone" 
                          dataKey="predicted_range" 
                          stroke="none" 
                          fill="#10b981" 
                          fillOpacity={0.15} 
                          isAnimationActive={false}
                        />
                        <Line 
                          type="linear" 
                          dataKey="expected_kwh" 
                          stroke="#10b981" 
                          strokeWidth={2.5} 
                          dot={CustomForecastDot}
                          activeDot={{ r: 6, strokeWidth: 0, fill: '#10b981' }}
                          isAnimationActive={false}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                </div>

                {/* Footer contextual bar */}
                <div className="mt-3 flex rounded-md overflow-hidden text-[10px] font-bold text-center border border-slate-200">
                  <div className="flex-1 bg-blue-100 text-blue-800 py-1.5 border-r border-blue-200">Actual (Historical)</div>
                  <div className="flex-1 bg-emerald-100 text-emerald-800 py-1.5">Forecast (7 Days)</div>
                </div>
              </div>
            </div>

            {/* RIGHT COLUMN: Table */}
            <div className="flex flex-col bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm h-full overflow-hidden">
              <div className="p-3 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-[#0f294d] dark:text-blue-400" />
                <h2 className="text-sm font-bold text-[#0f294d] dark:text-white">7-Day Forecast</h2>
              </div>
              
              <div className="flex-1 flex flex-col">
                <div className="flex bg-[#42618a] text-white sticky top-0 z-10">
                  <div className="py-1.5 px-2 w-[25%] font-semibold text-[10px] border-r border-[#5174a1]">Day</div>
                  <div className="py-1.5 px-2 w-[38%] whitespace-nowrap font-semibold text-[10px] border-r border-[#5174a1]">Date</div>
                  <div className="py-1.5 px-2 w-[37%] font-semibold text-[10px] text-center">Expected (kWh)</div>
                </div>
                <div className="flex-1 flex flex-col divide-y divide-slate-100 dark:divide-slate-800">
                  {forecast.forecast.map(pt => (
                    <div key={pt.date} className="flex-1 flex items-center hover:bg-slate-50 dark:hover:bg-slate-800">
                      <div className="py-1.5 px-2 w-[25%] font-medium text-slate-800 text-[11px] whitespace-nowrap">Day {pt.forecast_day}</div>
                      <div className="py-1.5 px-2 w-[38%] text-slate-600 text-[11px] whitespace-nowrap">{pt.date}</div>
                      <div className="py-1.5 px-2 w-[37%] font-bold text-slate-800 text-center text-[11px]">{pt.predicted_consumption_kwh.toFixed(2)}</div>
                    </div>
                  ))}
                </div>
              </div>


            </div>

          </div>
        )}

        {/* 3.5 INSIGHTS AND EXPLANATION */}
        {forecast && (
          <div className="flex flex-col lg:flex-row gap-3 items-stretch shrink-0">
            <div className="flex-[1.5] bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm pt-3 px-3 pb-2 flex flex-col">
              <h3 className="font-bold text-[#0f294d] dark:text-white text-sm mb-1.5 shrink-0">Consumption Insights</h3>
              <div className="flex flex-col">
                <div className="grid grid-cols-2 sm:grid-cols-6 gap-3 w-full">
                <div>
                  <p className="text-[10px] font-bold text-slate-500 uppercase">Expected 7-Day Total</p>
                  <p className="font-black text-lg text-slate-900 dark:text-white">{forecast.insights.total_7d_consumption.toFixed(2)} <span className="text-[10px] font-semibold text-slate-500">kWh</span></p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-slate-500 uppercase">Expected Avg / Day</p>
                  <p className="font-black text-lg text-slate-900 dark:text-white">{forecast.insights.average_daily_consumption.toFixed(2)} <span className="text-[10px] font-semibold text-slate-500">kWh</span></p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-slate-500 uppercase">Peak Expected</p>
                  <p className="font-black text-lg text-slate-900 dark:text-white">{forecast.insights.peak_consumption_kwh.toFixed(2)} <span className="text-[10px] font-semibold text-slate-500">kWh</span></p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-slate-500 uppercase">Lowest Expected</p>
                  <p className="font-black text-lg text-slate-900 dark:text-white">{forecast.insights.lowest_consumption_kwh.toFixed(2)} <span className="text-[10px] font-semibold text-slate-500">kWh</span></p>
                </div>
                <div className="col-span-2">
                  <p className="text-[10px] font-bold text-slate-500 uppercase">Trend</p>
                  <div className="flex flex-col mt-0.5">
                    <span className="font-black text-lg text-slate-900 dark:text-white capitalize leading-tight">
                      {forecast.insights.trend}
                    </span>
                    <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400 leading-tight">
                      {forecast.insights.vs_prior_7d_pct > 0 ? '+' : ''}{forecast.insights.vs_prior_7d_pct.toFixed(1)}% vs. prior 7 days
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

            {/* Estimated Cost */}
            <div className="flex-1 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm pt-3 px-3 pb-2 flex flex-col">
              <div className="flex items-center gap-2 mb-1.5 text-emerald-600 dark:text-emerald-400">
                <Calculator className="w-4 h-4" />
                <h3 className="font-bold text-sm">Estimated 7-Day Energy Cost</h3>
              </div>
              <div className="grid grid-cols-3 gap-3 w-full items-end mb-1">
                <div>
                  <p className="font-black text-2xl text-slate-900 dark:text-white leading-none">${(forecast.insights.total_7d_consumption * assumedRate).toFixed(2)}</p>
                  <p className="text-[10px] font-bold text-slate-500 uppercase mt-1">7-Day Cost</p>
                </div>
                <div>
                  <p className="font-bold text-sm text-slate-700 dark:text-slate-300 leading-none">${(forecast.insights.total_7d_consumption * assumedRate / 7).toFixed(2)}<span className="text-[10px] font-semibold text-slate-500">/day</span></p>
                  <p className="text-[10px] font-bold text-slate-500 uppercase mt-1.5">Avg Daily Cost</p>
                </div>
                <div>
                  <p className="font-bold text-sm text-slate-700 dark:text-slate-300 leading-none">${(forecast.insights.peak_consumption_kwh * assumedRate).toFixed(2)}<span className="text-[10px] font-semibold text-slate-500">/day</span></p>
                  <p className="text-[10px] font-bold text-slate-500 uppercase mt-1.5">Highest Daily Cost</p>
                </div>
              </div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400 flex flex-col gap-0.5 mt-auto">
                <div className="flex items-center gap-1.5">
                  Based on assumed rate: $
                  <input 
                    type="number" 
                    value={assumedRate} 
                    onChange={(e) => setAssumedRate(Number(e.target.value))} 
                    className="w-14 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded px-1.5 py-0.5 text-slate-800 dark:text-slate-200 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                    step="0.01"
                    min="0"
                  />
                  / kWh
                </div>
                <div className="italic text-[9px] text-slate-400">Demo estimate; actual utility rates vary.</div>
              </div>
            </div>
          </div>
        )}

        {/* 4. BOTTOM ROW: Model Performance */}
        {metrics && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-wrap md:flex-row items-center justify-between p-3 px-5 gap-4 shrink-0">
            
            <div className="flex items-center gap-3">
              <div className="bg-blue-600 text-white p-1.5 rounded-md">
                <Target className="w-4 h-4" />
              </div>
              <h3 className="font-bold text-[#0f294d] dark:text-white text-sm">Model Performance</h3>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-6 flex-1 px-4">
              <div className="flex-1 text-center">
                <p className="text-[10px] font-bold text-slate-500 uppercase">MAE</p>
                <p className="font-black text-lg text-slate-900 dark:text-white leading-tight">
                  {metrics.v2_mae_7d.toFixed(2)} <span className="text-[10px] font-semibold text-slate-500">kWh/day</span>
                </p>
              </div>
              
              <div className="hidden sm:block w-px h-8 bg-slate-200 dark:bg-slate-700"></div>
              
              <div className="flex-1 text-center">
                <p className="text-[10px] font-bold text-slate-500 uppercase">Seasonal-naive baseline</p>
                <p className="font-black text-lg text-slate-900 dark:text-white leading-tight">
                  {metrics.baseline_mae_7d.toFixed(2)} <span className="text-[10px] font-semibold text-slate-500">kWh/day</span>
                </p>
              </div>

              <div className="hidden sm:block w-px h-8 bg-slate-200 dark:bg-slate-700"></div>

              <div className="flex-1 flex flex-col items-center text-center text-emerald-600">
                <p className="text-[10px] font-bold text-emerald-700/70 uppercase">Improvement</p>
                <p className="font-black text-lg leading-tight">
                  {metrics.improvement_pct.toFixed(2)}% <span className="text-[10px] font-medium text-emerald-700/70">Reduction</span>
                </p>
              </div>
            </div>

            <div className="text-[9px] font-medium text-slate-400 italic bg-slate-50 dark:bg-slate-800 px-3 py-1.5 rounded border border-slate-100 dark:border-slate-700 hidden lg:block">
              Historical backtest performance. Actual future error may vary.
            </div>
            
          </div>
        )}
        
      </main>
    </div>
  );
}
