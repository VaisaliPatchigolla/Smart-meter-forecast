'use client';

import { useState, useEffect, useMemo, UIEvent } from 'react';
import { getHealth, getHouseholds, getForecast, getMetrics, getHistory } from '../lib/api';
import { HealthResponse, HouseholdsResponse, ForecastResponse, MetricsResponse, HistoryResponse } from '../types';
import { ResponsiveContainer, ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from 'recharts';
import { BarChart2, RefreshCw, User, Calendar, Clock, Target, BarChart, TrendingUp, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

interface ChartPoint {
  dateStr: string;
  timestamp: number;
  fullDate: string;
  actual_kwh: number | null;
  expected_kwh: number | null;
  isConnectionPoint: boolean;
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
      <text x={viewBox.x - 8} y={viewBox.y + 15} textAnchor="end" fontSize={10} fontWeight="bold" fill="#475569">Feb 28, 2014</text>
      <text x={viewBox.x - 8} y={viewBox.y + 27} textAnchor="end" fontSize={9} fill="#64748b">Last actual</text>
      <text x={viewBox.x + 8} y={viewBox.y + 15} textAnchor="start" fontSize={10} fontWeight="bold" fill="#10b981">Mar 01, 2014</text>
      <text x={viewBox.x + 8} y={viewBox.y + 27} textAnchor="start" fontSize={9} fill="#10b981">First predicted</text>
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
      combined[pt.date] = {
        dateStr: new Date(pt.date).toLocaleDateString('en-US', { month: 'short', day: '2-digit' }),
        timestamp: new Date(pt.date).getTime(),
        fullDate: pt.date,
        actual_kwh: pt.consumption_kwh,
        expected_kwh: null,
        isConnectionPoint: false
      };
    });
    
    forecast.forecast.forEach(pt => {
      if (!combined[pt.date]) {
        combined[pt.date] = {
          dateStr: new Date(pt.date).toLocaleDateString('en-US', { month: 'short', day: '2-digit' }),
          timestamp: new Date(pt.date).getTime(),
          fullDate: pt.date,
          actual_kwh: null,
          expected_kwh: pt.predicted_consumption_kwh,
          isConnectionPoint: false
        };
      } else {
        combined[pt.date].expected_kwh = pt.predicted_consumption_kwh;
      }
    });
    
    // Connect the lines
    if (history.history.length > 0) {
      const lastHistDate = history.history[history.history.length - 1].date;
      if (combined[lastHistDate]) {
        combined[lastHistDate].expected_kwh = combined[lastHistDate].actual_kwh;
        combined[lastHistDate].isConnectionPoint = true;
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

  const lastActualDate = history?.history.length 
    ? new Date(history.history[history.history.length - 1].date).toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' })
    : '—';
    
  const forecastBoundaryStr = history?.history.length 
    ? new Date(history.history[history.history.length - 1].date).toLocaleDateString('en-US', { month: 'short', day: '2-digit' })
    : undefined;

  const refreshPage = () => {
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-[#F0F4F8] dark:bg-slate-950 font-sans text-slate-800 dark:text-slate-200 flex flex-col">
      
      {/* 1. HEADER */}
      <header className="bg-[#0f294d] text-white px-6 py-2.5 flex items-center justify-between shadow-md shrink-0">
        <div className="flex items-center gap-4">
          <BarChart2 className="w-6 h-6 text-blue-400" />
          <h1 className="text-lg font-semibold tracking-wide">Smart Meter Consumption Forecasting V2</h1>
          <span className="bg-white/20 text-white text-[10px] px-2 py-0.5 rounded font-medium tracking-wide">MVP Dashboard</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-blue-100">
          <span>Last Updated: 28 Feb 2014 11:30 AM</span>
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

      <main className="max-w-[1400px] w-full mx-auto px-4 sm:px-6 py-4 space-y-4 flex-1 flex flex-col">
        
        {/* 2. COMPACT FORECAST CONTEXT BAR */}
        <section className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-3 flex flex-wrap items-center justify-between gap-6 shrink-0">
          
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
          <div className="flex flex-col lg:flex-row gap-4 items-stretch flex-1 min-h-0">
            
            {/* LEFT COLUMN: History Controls */}
            <div className="w-full lg:w-[180px] flex flex-col gap-4 flex-shrink-0">
              
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
                  <h3 className="font-bold text-sm text-slate-900 dark:text-white">Historical Navigation</h3>
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
            <div className="flex-1 min-w-0 flex flex-col bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm relative">
              <div className="p-3 border-b border-slate-100 dark:border-slate-800 flex items-center">
                <BarChart className="w-4 h-4 text-blue-600 mr-2" />
                <h2 className="text-sm font-bold text-[#0f294d] dark:text-white">Actual vs Forecast Consumption (kWh)</h2>
              </div>
              
              <div className="flex-1 p-3 relative flex flex-col">
                {/* Custom Legend to match screenshot */}
                <div className="flex gap-6 mb-4 ml-8 shrink-0">
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
                </div>

                <div className="w-full flex-1 min-h-0 relative">
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
            <div className="w-full lg:w-[260px] flex flex-col bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex-shrink-0 self-start">
              <div className="p-3 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-[#0f294d] dark:text-blue-400" />
                <h2 className="text-sm font-bold text-[#0f294d] dark:text-white">7-Day Forecast</h2>
              </div>
              
              <div className="flex-1 overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="bg-[#42618a] text-white">
                    <tr>
                      <th className="py-2 px-3 w-[25%] font-semibold text-[10px] border-r border-[#5174a1]">Day</th>
                      <th className="py-2 px-3 w-[38%] whitespace-nowrap font-semibold text-[10px] border-r border-[#5174a1]">Date</th>
                      <th className="py-2 px-3 w-[37%] font-semibold text-[10px] text-center">Expected (kWh)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {forecast.forecast.map(pt => (
                      <tr key={pt.date} className="hover:bg-slate-50 dark:hover:bg-slate-800">
                        <td className="py-2 px-3 font-medium text-slate-800 text-[11px] whitespace-nowrap">Day {pt.forecast_day}</td>
                        <td className="py-2 px-3 text-slate-600 text-[11px] whitespace-nowrap">{pt.date}</td>
                        <td className="py-2 px-3 font-bold text-slate-800 text-center text-[11px]">{pt.predicted_consumption_kwh.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 grid grid-cols-3 divide-x divide-slate-200 dark:divide-slate-700">
                <div className="p-2 flex flex-col items-center text-center justify-center">
                  <span className="text-[9px] font-bold text-slate-500 uppercase flex items-center gap-1">
                    <span className="text-sm">Σ</span> Total
                  </span>
                  <div className="font-black text-slate-900 mt-1 text-sm">
                    {forecast.insights.total_7d_consumption.toFixed(2)} <span className="text-[8px] font-medium text-slate-500">kWh</span>
                  </div>
                </div>
                <div className="p-2 flex flex-col items-center text-center justify-center">
                  <span className="text-[9px] font-bold text-slate-500 uppercase flex items-center gap-1">
                    <BarChart className="w-3 h-3" /> Avg / Day
                  </span>
                  <div className="font-black text-slate-900 mt-1 text-sm">
                    {forecast.insights.average_daily_consumption.toFixed(2)} <span className="text-[8px] font-medium text-slate-500">kWh</span>
                  </div>
                </div>
                <div className="p-2 flex flex-col items-center text-center justify-center">
                  <span className="text-[9px] font-bold text-slate-500 uppercase flex items-center gap-1">
                    <TrendingUp className="w-3 h-3 text-blue-500" /> Peak <span className="text-[7px] opacity-70">(D{(new Date(forecast.insights.peak_consumption_day).getTime() - new Date(forecast.forecast_start).getTime()) / (1000 * 3600 * 24) + 1})</span>
                  </span>
                  <div className="font-black text-slate-900 mt-1 text-sm">
                    {forecast.insights.peak_consumption_kwh.toFixed(2)} <span className="text-[8px] font-medium text-slate-500">kWh</span>
                  </div>
                </div>
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
                <p className="text-[10px] font-bold text-slate-500 uppercase">V2 MAE</p>
                <p className="font-black text-lg text-slate-900 dark:text-white leading-tight">
                  {metrics.v2_mae_7d.toFixed(2)} <span className="text-[10px] font-semibold text-slate-500">kWh/day</span>
                </p>
              </div>
              
              <div className="hidden sm:block w-px h-8 bg-slate-200 dark:bg-slate-700"></div>
              
              <div className="flex-1 text-center">
                <p className="text-[10px] font-bold text-slate-500 uppercase">Baseline MAE</p>
                <p className="font-black text-lg text-slate-900 dark:text-white leading-tight">
                  {(metrics.v2_mae_7d / (1 - metrics.improvement_pct/100)).toFixed(2)} <span className="text-[10px] font-semibold text-slate-500">kWh/day</span>
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
