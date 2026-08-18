import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Calendar,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  Clock,
  BarChart3,
  ShieldAlert,
  Download,
  RefreshCw,
  LogOut,
  UserCheck,
  Zap,
  Search
} from 'lucide-react';
import API_BASE_URL from '../services/api';

interface DailyRecord {
  date: string;
  date_iso: string;
  day_of_week: string;
  high: number;
  medium: number;
  low: number;
  total: number;
  daily_priority: string;
}

interface SlaPredictionResult {
  success: boolean;
  date_range: {
    start_date: string;
    end_date: string;
    total_days: number;
  };
  summary: {
    total_faults: number;
    severity_counts: {
      HIGH: number;
      MEDIUM: number;
      LOW: number;
    };
    overall_priority: string;
  };
  sla_targets: {
    HIGH: string;
    MEDIUM: string;
    LOW: string;
  };
  workload_priority: {
    urgent_workload: number;
    normal_workload: number;
    low_priority_workload: number;
  };
  daily_breakdown: DailyRecord[];
}

export default function AdminPredict() {
  const navigate = useNavigate();

  // Date selection state (Defaults to June demo window 01-06-2025 -> 15-06-2025)
  const [startDate, setStartDate] = useState('2025-06-01');
  const [endDate, setEndDate] = useState('2025-06-15');

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult] = useState<SlaPredictionResult | null>(null);

  // Table filtering and search state
  const [tableSearch, setTableSearch] = useState('');
  const [selectedDayFilter, setSelectedDayFilter] = useState<'ALL' | 'WEEKDAYS' | 'WEEKENDS'>('ALL');
  const [sortField, setSortField] = useState<'date' | 'total' | 'high'>('date');
  const [sortAsc, setSortAsc] = useState(true);

  const [currentUser, setCurrentUser] = useState<any>(null);

  useEffect(() => {
    const rawUser = localStorage.getItem('user');
    if (rawUser) {
      try {
        setCurrentUser(JSON.parse(rawUser));
      } catch {
        setCurrentUser({ name: 'System Administrator', role: 'admin' });
      }
    }

    // Auto run prediction on mount for the initial range
    executePrediction('01-06-2025', '15-06-2025');
  }, []);

  const formatDateToDDMMYYYY = (isoDate: string) => {
    if (!isoDate) return '';
    const parts = isoDate.split('-');
    if (parts.length === 3) {
      return `${parts[2]}-${parts[1]}-${parts[0]}`;
    }
    return isoDate;
  };

  const executePrediction = async (startFormatted?: string, endFormatted?: string) => {
    const sDate = startFormatted || formatDateToDDMMYYYY(startDate);
    const eDate = endFormatted || formatDateToDDMMYYYY(endDate);

    setLoading(true);
    setErrorMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/sla/predict-date`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: sDate,
          end_date: eDate
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setResult(data);
      } else {
        setErrorMessage(data.error || 'Failed to generate SLA prediction. Please verify date format.');
      }
    } catch (err: any) {
      setErrorMessage(`Cannot connect to SLA prediction engine: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyPreset = (type: 'june_demo' | 'next_7' | 'next_14' | 'next_30') => {
    let s = '2025-06-01';
    let e = '2025-06-15';

    if (type === 'june_demo') {
      s = '2025-06-01';
      e = '2025-06-15';
    } else if (type === 'next_7') {
      const d1 = new Date();
      const d2 = new Date();
      d2.setDate(d2.getDate() + 7);
      s = d1.toISOString().split('T')[0];
      e = d2.toISOString().split('T')[0];
    } else if (type === 'next_14') {
      const d1 = new Date();
      const d2 = new Date();
      d2.setDate(d2.getDate() + 14);
      s = d1.toISOString().split('T')[0];
      e = d2.toISOString().split('T')[0];
    } else if (type === 'next_30') {
      const d1 = new Date();
      const d2 = new Date();
      d2.setDate(d2.getDate() + 30);
      s = d1.toISOString().split('T')[0];
      e = d2.toISOString().split('T')[0];
    }

    setStartDate(s);
    setEndDate(e);
    executePrediction(formatDateToDDMMYYYY(s), formatDateToDDMMYYYY(e));
  };

  const handleExportCsv = () => {
    if (!result || !result.daily_breakdown) return;

    const headers = ['Date', 'Day of Week', 'HIGH Severity', 'MEDIUM Severity', 'LOW Severity', 'Total Faults', 'Daily Priority'];
    const rows = result.daily_breakdown.map(r => [
      r.date,
      r.day_of_week,
      r.high,
      r.medium,
      r.low,
      r.total,
      r.daily_priority
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `SLA_Fault_Forecast_${result.date_range.start_date}_to_${result.date_range.end_date}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    navigate('/login');
  };

  // Filtered & Sorted Daily Breakdown
  const filteredDailyRecords = (result?.daily_breakdown || []).filter(item => {
    const matchesSearch =
      item.date.includes(tableSearch) ||
      item.day_of_week.toLowerCase().includes(tableSearch.toLowerCase()) ||
      item.daily_priority.toLowerCase().includes(tableSearch.toLowerCase());

    const isWeekend = item.day_of_week === 'Saturday' || item.day_of_week === 'Sunday';
    const matchesDay =
      selectedDayFilter === 'ALL' ||
      (selectedDayFilter === 'WEEKDAYS' && !isWeekend) ||
      (selectedDayFilter === 'WEEKENDS' && isWeekend);

    return matchesSearch && matchesDay;
  }).sort((a, b) => {
    if (sortField === 'total') {
      return sortAsc ? a.total - b.total : b.total - a.total;
    }
    if (sortField === 'high') {
      return sortAsc ? a.high - b.high : b.high - a.high;
    }
    return sortAsc ? a.date_iso.localeCompare(b.date_iso) : b.date_iso.localeCompare(a.date_iso);
  });

  const highPct = result?.summary.total_faults ? ((result.summary.severity_counts.HIGH / result.summary.total_faults) * 100).toFixed(1) : '0';
  const medPct = result?.summary.total_faults ? ((result.summary.severity_counts.MEDIUM / result.summary.total_faults) * 100).toFixed(1) : '0';
  const lowPct = result?.summary.total_faults ? ((result.summary.severity_counts.LOW / result.summary.total_faults) * 100).toFixed(1) : '0';

  return (
    <div style={{
      minHeight: '100vh',
      width: '100%',
      backgroundColor: '#07090e',
      color: '#f8fafc',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Top Navbar */}
      <header style={{
        backgroundColor: '#0d111a',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        padding: '14px 28px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 40
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #0284c7, #7c3aed)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(56, 189, 248, 0.4)'
          }}>
            <Sparkles size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ fontSize: '17px', fontWeight: 800, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '8px' }}>
              TELECOM SLA WORKLOAD & FAULT FORECASTER <span style={{ fontSize: '11px', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '2px 8px', borderRadius: '12px' }}>AI MODEL PREDICTION</span>
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>Predictive Date Range Fault Severity • SLA Compliance Target • Capacity Planning</div>
          </div>
        </div>

        {/* Header Right Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={() => navigate('/admin-dashboard')}
            className="btn-secondary"
            style={{ padding: '7px 14px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <ShieldAlert size={14} color="#a855f7" />
            <span>Admin Console</span>
          </button>


          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(30, 41, 59, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            padding: '6px 12px',
            borderRadius: '20px',
            fontSize: '12px',
            color: '#c084fc'
          }}>
            <UserCheck size={14} />
            <span>{currentUser?.name || 'Administrator'}</span>
            <span style={{ fontSize: '10px', background: '#3b0764', padding: '1px 6px', borderRadius: '8px', textTransform: 'uppercase', color: '#d8b4fe' }}>ADMIN</span>
          </div>

          <button
            onClick={handleLogout}
            style={{
              background: 'transparent',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#f87171',
              padding: '6px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12px',
              fontWeight: 600
            }}
          >
            <LogOut size={14} />
            <span>Exit</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <div style={{ flex: 1, padding: '24px 28px', maxWidth: '1600px', width: '100%', margin: '0 auto', boxSizing: 'border-box' }}>

        {/* TOP CONTROL PANEL: DATE RANGE SELECTOR & PRESETS */}
        <div className="glass-panel" style={{ padding: '22px 24px', marginBottom: '24px', borderLeft: '4px solid #0284c7' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
            
            <div>
              <div style={{ fontSize: '16px', fontWeight: 800, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Calendar size={18} color="#38bdf8" />
                <span>Forecast Date Window Configuration</span>
              </div>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                Select a start and end date to forecast expected fault volumes across HIGH (5h SLA), MEDIUM (10h SLA), and LOW (24h SLA) severities.
              </div>
            </div>

            {/* Quick Demo Presets */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Quick Presets:</span>
              <button
                type="button"
                onClick={() => handleApplyPreset('june_demo')}
                className="btn-secondary"
                style={{ padding: '5px 10px', fontSize: '11px', borderColor: 'rgba(56, 189, 248, 0.4)', color: '#38bdf8' }}
              >
                June 1-15 Demo (319 Faults)
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset('next_7')}
                className="btn-secondary"
                style={{ padding: '5px 10px', fontSize: '11px' }}
              >
                Next 7 Days
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset('next_14')}
                className="btn-secondary"
                style={{ padding: '5px 10px', fontSize: '11px' }}
              >
                Next 14 Days
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset('next_30')}
                className="btn-secondary"
                style={{ padding: '5px 10px', fontSize: '11px' }}
              >
                Next 30 Days
              </button>
            </div>

          </div>

          {/* Date Picker Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              executePrediction();
            }}
            style={{
              marginTop: '18px',
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr)) 200px',
              gap: '14px',
              alignItems: 'flex-end'
            }}
          >
            <div>
              <label style={{ fontSize: '11px', fontWeight: 700, color: '#94a3b8', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>
                Start Date
              </label>
              <input
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                style={{
                  width: '100%',
                  backgroundColor: '#0d111a',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  color: '#f8fafc',
                  fontSize: '13px',
                  outline: 'none'
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '11px', fontWeight: 700, color: '#94a3b8', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>
                End Date
              </label>
              <input
                type="date"
                required
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                style={{
                  width: '100%',
                  backgroundColor: '#0d111a',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  color: '#f8fafc',
                  fontSize: '13px',
                  outline: 'none'
                }}
              />
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="btn-primary"
                style={{
                  width: '100%',
                  padding: '11px 16px',
                  fontSize: '13px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  background: 'linear-gradient(135deg, #0284c7, #6366f1)',
                  opacity: loading ? 0.7 : 1
                }}
              >
                {loading ? (
                  <>
                    <RefreshCw size={16} className="spin-slow" />
                    <span>Predicting Workload...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={16} />
                    <span>Run AI Forecast</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {errorMessage && (
            <div style={{
              marginTop: '14px',
              padding: '10px 14px',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              color: '#f87171',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <AlertTriangle size={16} />
              <span>{errorMessage}</span>
            </div>
          )}
        </div>

        {/* PREDICTION RESULTS */}
        {result && result.summary && (
          <>
            {/* EXECUTIVE SUMMARY KPI CARDS */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
              
              {/* Card 1: Overall Workload Priority */}
              <div className="glass-panel" style={{
                padding: '20px',
                borderLeft: `4px solid ${result.summary.overall_priority === 'URGENT' ? '#ef4444' : result.summary.overall_priority === 'NORMAL' ? '#f59e0b' : '#10b981'}`
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>Overall Priority</span>
                  <Zap size={18} color={result.summary.overall_priority === 'URGENT' ? '#ef4444' : '#34d399'} />
                </div>
                <div style={{
                  fontSize: '26px',
                  fontWeight: 900,
                  letterSpacing: '-0.02em',
                  color: result.summary.overall_priority === 'URGENT' ? '#f87171' : result.summary.overall_priority === 'NORMAL' ? '#fbbf24' : '#34d399'
                }}>
                  {result.summary.overall_priority}
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '6px' }}>
                  Date Span: <strong>{result.date_range.total_days} Days</strong> ({result.date_range.start_date} → {result.date_range.end_date})
                </div>
              </div>

              {/* Card 2: Total Predicted Faults */}
              <div className="glass-panel" style={{ padding: '20px', borderLeft: '4px solid #38bdf8' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase' }}>Total Expected Faults</span>
                  <TrendingUp size={18} color="#38bdf8" />
                </div>
                <div style={{ fontSize: '28px', fontWeight: 900, color: '#f8fafc', letterSpacing: '-0.02em' }}>
                  {result.summary.total_faults} <span style={{ fontSize: '14px', color: '#94a3b8', fontWeight: 500 }}>Faults</span>
                </div>
                <div style={{ fontSize: '11px', color: '#38bdf8', opacity: 0.9, marginTop: '6px' }}>
                  Avg {(result.summary.total_faults / (result.date_range.total_days || 1)).toFixed(1)} faults / day
                </div>
              </div>

              {/* Card 3: Urgent Workload (HIGH Severity - 5h SLA) */}
              <div className="glass-panel" style={{ padding: '20px', borderLeft: '4px solid #ef4444' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: '#f87171', textTransform: 'uppercase' }}>Urgent Workload (HIGH)</span>
                  <Clock size={16} color="#ef4444" />
                </div>
                <div style={{ fontSize: '28px', fontWeight: 900, color: '#f87171', letterSpacing: '-0.02em' }}>
                  {result.summary.severity_counts.HIGH} <span style={{ fontSize: '13px', color: '#fca5a5', fontWeight: 600 }}>({highPct}%)</span>
                </div>
                <div style={{ fontSize: '11px', color: '#f87171', marginTop: '6px' }}>
                  SLA Target: <strong>{result.sla_targets.HIGH}</strong>
                </div>
              </div>

              {/* Card 4: Normal Workload (MEDIUM Severity - 10h SLA) */}
              <div className="glass-panel" style={{ padding: '20px', borderLeft: '4px solid #f59e0b' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: '#fbbf24', textTransform: 'uppercase' }}>Normal Workload (MED)</span>
                  <Clock size={16} color="#f59e0b" />
                </div>
                <div style={{ fontSize: '28px', fontWeight: 900, color: '#fbbf24', letterSpacing: '-0.02em' }}>
                  {result.summary.severity_counts.MEDIUM} <span style={{ fontSize: '13px', color: '#fde68a', fontWeight: 600 }}>({medPct}%)</span>
                </div>
                <div style={{ fontSize: '11px', color: '#fbbf24', marginTop: '6px' }}>
                  SLA Target: <strong>{result.sla_targets.MEDIUM}</strong>
                </div>
              </div>

              {/* Card 5: Low-Priority Workload (LOW Severity - 24h SLA) */}
              <div className="glass-panel" style={{ padding: '20px', borderLeft: '4px solid #10b981' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: '#34d399', textTransform: 'uppercase' }}>Low-Priority (LOW)</span>
                  <Clock size={16} color="#10b981" />
                </div>
                <div style={{ fontSize: '28px', fontWeight: 900, color: '#34d399', letterSpacing: '-0.02em' }}>
                  {result.summary.severity_counts.LOW} <span style={{ fontSize: '13px', color: '#a7f3d0', fontWeight: 600 }}>({lowPct}%)</span>
                </div>
                <div style={{ fontSize: '11px', color: '#34d399', marginTop: '6px' }}>
                  SLA Target: <strong>{result.sla_targets.LOW}</strong>
                </div>
              </div>

            </div>

            {/* SEVERITY BREAKDOWN RATIO BAR */}
            <div className="glass-panel" style={{ padding: '18px 22px', marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>
                  Severity Distribution & Resource Allocation Ratio
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', display: 'flex', gap: '16px' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '3px', background: '#ef4444' }} />
                    HIGH: <strong>{highPct}%</strong>
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '3px', background: '#f59e0b' }} />
                    MEDIUM: <strong>{medPct}%</strong>
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '3px', background: '#10b981' }} />
                    LOW: <strong>{lowPct}%</strong>
                  </span>
                </div>
              </div>

              {/* Progress Track */}
              <div style={{ width: '100%', height: '12px', borderRadius: '6px', background: '#121824', overflow: 'hidden', display: 'flex' }}>
                <div style={{ width: `${highPct}%`, background: 'linear-gradient(90deg, #dc2626, #ef4444)', transition: 'width 0.4s ease' }} title={`HIGH: ${result.summary.severity_counts.HIGH}`} />
                <div style={{ width: `${medPct}%`, background: 'linear-gradient(90deg, #d97706, #f59e0b)', transition: 'width 0.4s ease' }} title={`MEDIUM: ${result.summary.severity_counts.MEDIUM}`} />
                <div style={{ width: `${lowPct}%`, background: 'linear-gradient(90deg, #059669, #10b981)', transition: 'width 0.4s ease' }} title={`LOW: ${result.summary.severity_counts.LOW}`} />
              </div>
            </div>

            {/* DAILY BREAKDOWN FORECAST TABLE */}
            <div className="glass-panel" style={{ overflow: 'hidden' }}>
              
              {/* Header Bar */}
              <div style={{
                padding: '16px 22px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '12px'
              }}>
                <div>
                  <div style={{ fontSize: '15px', fontWeight: 800, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <BarChart3 size={18} color="#38bdf8" />
                    <span>Daily SLA Workload Breakdown & Forecast Roster</span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                    Granular breakdown of predicted faults per calendar date.
                  </div>
                </div>

                {/* Filter Controls & CSV Export */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  
                  {/* Search inside table */}
                  <div style={{ position: 'relative', minWidth: '180px' }}>
                    <Search size={13} color="#64748b" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
                    <input
                      type="text"
                      placeholder="Search date or day..."
                      value={tableSearch}
                      onChange={(e) => setTableSearch(e.target.value)}
                      style={{
                        width: '100%',
                        background: '#0d111a',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '6px',
                        padding: '6px 10px 6px 30px',
                        fontSize: '12px',
                        color: '#f8fafc',
                        outline: 'none'
                      }}
                    />
                  </div>

                  {/* Day Filter */}
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {(['ALL', 'WEEKDAYS', 'WEEKENDS'] as const).map((df) => (
                      <button
                        key={df}
                        onClick={() => setSelectedDayFilter(df)}
                        style={{
                          background: selectedDayFilter === df ? '#0284c7' : '#1e293b',
                          color: selectedDayFilter === df ? '#ffffff' : '#94a3b8',
                          border: 'none',
                          padding: '5px 10px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: 700,
                          cursor: 'pointer'
                        }}
                      >
                        {df}
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={handleExportCsv}
                    className="btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    <Download size={13} />
                    <span>Export CSV</span>
                  </button>
                </div>
              </div>

              {/* Table */}
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ background: '#0d111a', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: '#64748b', fontSize: '11px', textTransform: 'uppercase' }}>
                      <th
                        onClick={() => { setSortField('date'); setSortAsc(!sortAsc); }}
                        style={{ padding: '12px 20px', cursor: 'pointer' }}
                      >
                        Date (DD-MM-YYYY) {sortField === 'date' ? (sortAsc ? '↑' : '↓') : ''}
                      </th>
                      <th style={{ padding: '12px 20px' }}>Day of Week</th>
                      <th
                        onClick={() => { setSortField('high'); setSortAsc(!sortAsc); }}
                        style={{ padding: '12px 20px', color: '#f87171', cursor: 'pointer' }}
                      >
                        HIGH (5h SLA) {sortField === 'high' ? (sortAsc ? '↑' : '↓') : ''}
                      </th>
                      <th style={{ padding: '12px 20px', color: '#fbbf24' }}>MEDIUM (10h SLA)</th>
                      <th style={{ padding: '12px 20px', color: '#34d399' }}>LOW (24h SLA)</th>
                      <th
                        onClick={() => { setSortField('total'); setSortAsc(!sortAsc); }}
                        style={{ padding: '12px 20px', color: '#38bdf8', cursor: 'pointer' }}
                      >
                        Daily Total {sortField === 'total' ? (sortAsc ? '↑' : '↓') : ''}
                      </th>
                      <th style={{ padding: '12px 20px', textAlign: 'right' }}>Daily Priority</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDailyRecords.map((row, idx) => (
                      <tr
                        key={idx}
                        style={{
                          borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                          background: row.day_of_week === 'Sunday' || row.day_of_week === 'Saturday' ? 'rgba(30, 41, 59, 0.2)' : 'transparent'
                        }}
                      >
                        <td style={{ padding: '14px 20px', fontWeight: 700, color: '#f8fafc' }}>
                          <span className="mono-tag" style={{ color: '#38bdf8' }}>{row.date}</span>
                        </td>
                        <td style={{ padding: '14px 20px', color: row.day_of_week === 'Sunday' || row.day_of_week === 'Saturday' ? '#c084fc' : '#cbd5e1' }}>
                          {row.day_of_week}
                        </td>
                        <td style={{ padding: '14px 20px', color: '#f87171', fontWeight: 800 }}>
                          {row.high}
                        </td>
                        <td style={{ padding: '14px 20px', color: '#fbbf24', fontWeight: 700 }}>
                          {row.medium}
                        </td>
                        <td style={{ padding: '14px 20px', color: '#34d399', fontWeight: 700 }}>
                          {row.low}
                        </td>
                        <td style={{ padding: '14px 20px', fontWeight: 900, color: '#f8fafc' }}>
                          {row.total}
                        </td>
                        <td style={{ padding: '14px 20px', textAlign: 'right' }}>
                          <span style={{
                            fontSize: '10px',
                            fontWeight: 800,
                            padding: '3px 8px',
                            borderRadius: '10px',
                            background: row.daily_priority === 'URGENT' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                            color: row.daily_priority === 'URGENT' ? '#f87171' : '#fbbf24',
                            border: `1px solid ${row.daily_priority === 'URGENT' ? 'rgba(239, 68, 68, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`
                          }}>
                            {row.daily_priority}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

            </div>
          </>
        )}

      </div>
    </div>
  );
}
