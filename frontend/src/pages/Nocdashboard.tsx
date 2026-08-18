import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Radio,
  Activity,
  Search,
  User,
  LogOut,
  Database,
  Layers,
  PhoneForwarded,
  CheckCheck,
  LayoutGrid,
  List,
  ArrowRight,
  FileText,
  Eye,
} from 'lucide-react';
import API_BASE_URL from '../services/api';

interface Incident {
  id: string;
  ticket_id: number | string;
  title?: string;
  location: string;
  region?: string;
  severity_type: string;
  resource_type: string;
  event_types?: string[];
  log_features?: string[];
  total_log_volume?: number;
  status: string;
  severity: string;
  fault_severity: number;
  confidence: number;
  created_at: string;
  assigned_to: string;
  finished_at?: string;
  confirmed_root_cause?: string;
}

interface OperatorDecision {
  ticket_id: string | number;
  decision_type: string;
  confirmed?: boolean;
  selected_rank?: number;
  root_cause?: string;
  resolution?: string;
  notes?: string;
  operator: string;
  commit_id?: string;
  reason?: string;
  assigned_group?: string;
  status: string;
  timestamp: string;
}

type MainCategory = 'COMMON' | 'PENDING' | 'FINISH' | 'ESCALATION';

export default function NocDashboard() {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [decisions, setDecisions] = useState<OperatorDecision[]>([]);

  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'HIGH' | 'MED' | 'LOW'>('ALL');

  // Dashboard Primary View Mode: INCIDENTS vs DECISIONS LOG
  const [activeConsoleView, setActiveConsoleView] = useState<'INCIDENTS' | 'DECISIONS'>('INCIDENTS');

  // The primary 4 categories: COMMON, PENDING, FINISH, ESCALATION
  const [selectedCategory, setSelectedCategory] = useState<MainCategory>('COMMON');
  const [viewMode, setViewMode] = useState<'table' | 'kanban'>('table');

  const [currentUser, setCurrentUser] = useState<any>(null);

  // Load user session & poll live telemetry and decisions from MongoDB
  useEffect(() => {
    const rawUser = localStorage.getItem('user');
    if (rawUser) {
      try {
        setCurrentUser(JSON.parse(rawUser));
      } catch {
        setCurrentUser({ name: 'Lead NOC Engineer', role: 'operator' });
      }
    } else {
      setCurrentUser({ name: 'Lead NOC Engineer', role: 'operator' });
    }

    fetchAllData();

    // Auto poll every 3 seconds to catch live dispatches from sender.py & MongoDB updates
    const interval = setInterval(() => {
      fetchAllDataSilent();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    try {
      const [incRes, decRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/incidents`),
        fetch(`${API_BASE_URL}/api/decisions`)
      ]);

      if (incRes.ok) {
        const incData = await incRes.json();
        setIncidents(incData.incidents || []);
      }

      if (decRes.ok) {
        const decData = await decRes.json();
        setDecisions(decData.decisions || []);
      }
    } catch {
      // Retain existing
    }
  };

  const fetchAllDataSilent = async () => {
    try {
      const [incRes, decRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/incidents`),
        fetch(`${API_BASE_URL}/api/decisions`)
      ]);

      if (incRes.ok) {
        const incData = await incRes.json();
        if (incData.incidents) setIncidents(incData.incidents);
      }

      if (decRes.ok) {
        const decData = await decRes.json();
        if (decData.decisions) setDecisions(decData.decisions);
      }
    } catch {
      // Keep existing list on transient poll error
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    navigate('/login');
  };

  // Helper to look up all decisions for a ticket from the decisions table
  const getTicketDecisions = (ticketId: number | string): OperatorDecision[] => {
    const cleanId = String(ticketId).replace('INC-', '').trim();
    return decisions.filter(d => String(d.ticket_id).replace('INC-', '').trim() === cleanId);
  };

  const getIncidentEffectiveStatus = (inc: Incident): string => {
    const ticketDecisions = getTicketDecisions(inc.ticket_id || inc.id);
    if (ticketDecisions.length > 0) {
      // 1. Check if there is any COMMIT_RESOLUTION in decisions table
      const hasCommit = ticketDecisions.some(
        d => d.decision_type === 'COMMIT_RESOLUTION' || d.confirmed === true || String(d.status || '').toUpperCase().includes('RESOLV')
      );
      if (hasCommit) {
        return 'FINISHED (RESOLVED)';
      }

      // 2. Check if there is an ESCALATION_TO_TIER_3 or if all 3 ranks (1, 2, 3) were rejected in decisions table
      const hasEscalation = ticketDecisions.some(
        d => d.decision_type === 'ESCALATION_TO_TIER_3' || String(d.status || '').toUpperCase().includes('ESCALAT')
      );
      const rejectedRanks = new Set(
        ticketDecisions
          .filter(d => d.decision_type === 'REJECT_CANDIDATE' || d.confirmed === false)
          .map(d => Number(d.selected_rank || 0))
          .filter(Boolean)
      );

      if (hasEscalation || (rejectedRanks.has(1) && rejectedRanks.has(2) && rejectedRanks.has(3))) {
        return 'FINISHED (ESCALATED)';
      }

      return 'PENDING REVIEW';
    }

    return 'PENDING REVIEW';
  };

  // Helper check for status categories using decisions table
  const isIncidentResolved = (inc: Incident) => {
    return getIncidentEffectiveStatus(inc) === 'FINISHED (RESOLVED)';
  };

  const isIncidentEscalated = (inc: Incident) => {
    return getIncidentEffectiveStatus(inc) === 'FINISHED (ESCALATED)';
  };

  const isIncidentPending = (inc: Incident) => {
    return getIncidentEffectiveStatus(inc) === 'PENDING REVIEW';
  };

  // 4 Category Partitioned Lists
  const commonList = incidents;
  const pendingList = incidents.filter(inc => isIncidentPending(inc));
  const finishList = incidents.filter(inc => isIncidentResolved(inc));
  const escalationList = incidents.filter(inc => isIncidentEscalated(inc));

  // Filtered incidents based on active Category, search, and severity
  const filteredIncidents = incidents.filter(inc => {
    const matchesSearch =
      String(inc.id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(inc.ticket_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(inc.location || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(inc.resource_type || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(inc.title || '').toLowerCase().includes(searchTerm.toLowerCase());

    const matchesSeverity =
      severityFilter === 'ALL' ||
      (severityFilter === 'HIGH' && inc.fault_severity === 2) ||
      (severityFilter === 'MED' && inc.fault_severity === 1) ||
      (severityFilter === 'LOW' && inc.fault_severity === 0);

    const matchesCategory =
      selectedCategory === 'COMMON' ||
      (selectedCategory === 'PENDING' && isIncidentPending(inc)) ||
      (selectedCategory === 'FINISH' && isIncidentResolved(inc)) ||
      (selectedCategory === 'ESCALATION' && isIncidentEscalated(inc));

    return matchesSearch && matchesSeverity && matchesCategory;
  });

  // Filtered decisions based on search
  const filteredDecisions = decisions.filter(dec => {
    const matchesSearch =
      String(dec.ticket_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(dec.operator || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(dec.root_cause || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(dec.resolution || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(dec.decision_type || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(dec.commit_id || '').toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

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
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #0284c7, #6366f1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(56, 189, 248, 0.4)'
          }}>
            <Radio size={20} color="#ffffff" />
          </div>
          <div>
            <div style={{ fontSize: '16px', fontWeight: 800, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '8px' }}>
              TELECOM NOC COMMAND <span style={{ fontSize: '11px', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '1px 7px', borderRadius: '12px' }}>MONGODB PERSISTED</span>
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>Common Feed • Pending Review • Finish & Resolved • Escalation Tier-3 • Decision Logs</div>
          </div>
        </div>

        {/* Live Status Indicators */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* MongoDB Connection Status */}


          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(30, 41, 59, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            padding: '5px 12px',
            borderRadius: '20px',
            fontSize: '12px',
            color: '#94a3b8'
          }}>
            <User size={14} color="#38bdf8" />
            <span>{currentUser?.name || 'NOC Operator'}</span>
            <span style={{ fontSize: '10px', background: '#1e293b', padding: '1px 6px', borderRadius: '8px', textTransform: 'uppercase' }}>{currentUser?.role || 'NOC'}</span>
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
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div style={{ flex: 1, padding: '24px 28px', maxWidth: '1600px', width: '100%', margin: '0 auto', boxSizing: 'border-box' }}>

        {/* 4 Category Summary KPI Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '24px' }}>

          {/* Category 1: COMMON (Total Ingested from MongoDB) */}
          <div
            onClick={() => {
              setActiveConsoleView('INCIDENTS');
              setSelectedCategory('COMMON');
            }}
            className="glass-panel"
            style={{
              padding: '18px 20px',
              cursor: 'pointer',
              border: activeConsoleView === 'INCIDENTS' && selectedCategory === 'COMMON' ? '2px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
              background: activeConsoleView === 'INCIDENTS' && selectedCategory === 'COMMON' ? 'rgba(56, 189, 248, 0.08)' : undefined,
              transition: 'all 0.18s ease'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#38bdf8', fontSize: '12px', fontWeight: 700, marginBottom: '8px' }}>
              <span>1. COMMON (ALL PERSISTED)</span>
              <Layers size={18} color="#38bdf8" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em' }}>
              {commonList.length}
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
              Total Streamed & Stored in Database
            </div>
          </div>

          {/* Category 2: PENDING (Awaiting 3-Option Review) */}
          <div
            onClick={() => {
              setActiveConsoleView('INCIDENTS');
              setSelectedCategory('PENDING');
            }}
            className="glass-panel"
            style={{
              padding: '18px 20px',
              borderLeft: '4px solid #f59e0b',
              cursor: 'pointer',
              border: activeConsoleView === 'INCIDENTS' && selectedCategory === 'PENDING' ? '2px solid #f59e0b' : undefined,
              background: activeConsoleView === 'INCIDENTS' && selectedCategory === 'PENDING' ? 'rgba(245, 158, 11, 0.08)' : undefined,
              transition: 'all 0.18s ease'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#fbbf24', fontSize: '12px', fontWeight: 700, marginBottom: '8px' }}>
              <span>2. PENDING REVIEW</span>
              <Activity size={18} color="#f59e0b" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: '#fbbf24', letterSpacing: '-0.02em' }}>
              {pendingList.length}
            </div>
            <div style={{ fontSize: '11px', color: '#fbbf24', opacity: 0.85, marginTop: '4px' }}>
              Awaiting Operator 3-Option Diagnosis
            </div>
          </div>

          {/* Category 3: FINISH (Resolved by YES) */}
          <div
            onClick={() => {
              setActiveConsoleView('INCIDENTS');
              setSelectedCategory('FINISH');
            }}
            className="glass-panel"
            style={{
              padding: '18px 20px',
              borderLeft: '4px solid #10b981',
              cursor: 'pointer',
              border: activeConsoleView === 'INCIDENTS' && selectedCategory === 'FINISH' ? '2px solid #10b981' : undefined,
              background: activeConsoleView === 'INCIDENTS' && selectedCategory === 'FINISH' ? 'rgba(16, 185, 129, 0.08)' : undefined,
              transition: 'all 0.18s ease'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#34d399', fontSize: '12px', fontWeight: 700, marginBottom: '8px' }}>
              <span>3. FINISH (RESOLVED)</span>
              <CheckCheck size={18} color="#10b981" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: '#34d399', letterSpacing: '-0.02em' }}>
              {finishList.length}
            </div>
            <div style={{ fontSize: '11px', color: '#34d399', opacity: 0.85, marginTop: '4px' }}>
              Work Done (Committed via YES & Dispatched)
            </div>
          </div>

          {/* Category 4: ESCALATION (Tier-3 by 3x NO) */}
          <div
            onClick={() => {
              setActiveConsoleView('INCIDENTS');
              setSelectedCategory('ESCALATION');
            }}
            className="glass-panel"
            style={{
              padding: '18px 20px',
              borderLeft: '4px solid #ef4444',
              cursor: 'pointer',
              border: activeConsoleView === 'INCIDENTS' && selectedCategory === 'ESCALATION' ? '2px solid #ef4444' : undefined,
              background: activeConsoleView === 'INCIDENTS' && selectedCategory === 'ESCALATION' ? 'rgba(239, 68, 68, 0.08)' : undefined,
              transition: 'all 0.18s ease'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#f87171', fontSize: '12px', fontWeight: 700, marginBottom: '8px' }}>
              <span>4. ESCALATION (TIER-3)</span>
              <PhoneForwarded size={18} color="#ef4444" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: '#ef4444', letterSpacing: '-0.02em' }}>
              {escalationList.length}
            </div>
            <div style={{ fontSize: '11px', color: '#f87171', opacity: 0.85, marginTop: '4px' }}>
              Work Done (Escalated via 3x NO)
            </div>
          </div>

        </div>

        {/* Console View Switcher: Telemetry Incidents Feed vs MongoDB Decision Log */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          paddingBottom: '12px',
          marginBottom: '18px',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => setActiveConsoleView('INCIDENTS')}
              style={{
                background: activeConsoleView === 'INCIDENTS' ? '#1e293b' : 'transparent',
                border: `1px solid ${activeConsoleView === 'INCIDENTS' ? '#38bdf8' : 'rgba(255, 255, 255, 0.06)'}`,
                color: activeConsoleView === 'INCIDENTS' ? '#38bdf8' : '#94a3b8',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <Activity size={16} />
              <span>1. Telemetry Incidents Queue ({incidents.length})</span>
            </button>

            <button
              onClick={() => setActiveConsoleView('DECISIONS')}
              style={{
                background: activeConsoleView === 'DECISIONS' ? '#1e293b' : 'transparent',
                border: `1px solid ${activeConsoleView === 'DECISIONS' ? '#a855f7' : 'rgba(255, 255, 255, 0.06)'}`,
                color: activeConsoleView === 'DECISIONS' ? '#c084fc' : '#94a3b8',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <Database size={16} />
              <span>2. MongoDB Decision & Commit History ({decisions.length})</span>
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* View Mode Switcher (For Incidents) */}
            {activeConsoleView === 'INCIDENTS' && (
              <div style={{ display: 'flex', background: '#1e293b', padding: '2px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <button
                  onClick={() => setViewMode('table')}
                  style={{
                    background: viewMode === 'table' ? '#0284c7' : 'transparent',
                    color: viewMode === 'table' ? '#ffffff' : '#94a3b8',
                    border: 'none',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11px',
                    fontWeight: 600
                  }}
                >
                  <List size={13} />
                  <span>Table</span>
                </button>
                <button
                  onClick={() => setViewMode('kanban')}
                  style={{
                    background: viewMode === 'kanban' ? '#0284c7' : 'transparent',
                    color: viewMode === 'kanban' ? '#ffffff' : '#94a3b8',
                    border: 'none',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11px',
                    fontWeight: 600
                  }}
                >
                  <LayoutGrid size={13} />
                  <span>Kanban</span>
                </button>
              </div>
            )}

            {/* <button
              onClick={fetchAllData}
              className="btn-secondary"
              style={{ padding: '6px 12px', fontSize: '11px' }}
            >
              <RefreshCw size={12} className={loading ? 'spin-slow' : ''} />
              <span>Sync from MongoDB</span>
            </button> */}
          </div>
        </div>

        {/* ============================================================
            VIEW 1: TELEMETRY INCIDENTS QUEUE (WITH 4 CATEGORIES)
        ============================================================ */}
        {activeConsoleView === 'INCIDENTS' && (
          <>
            {/* PRIMARY CATEGORY SELECTOR TABS */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              paddingBottom: '12px',
              marginBottom: '18px',
              overflowX: 'auto'
            }}>
              {/* Tab 1: COMMON */}
              <button
                onClick={() => setSelectedCategory('COMMON')}
                style={{
                  background: selectedCategory === 'COMMON' ? '#0284c7' : 'transparent',
                  color: selectedCategory === 'COMMON' ? '#ffffff' : '#94a3b8',
                  border: `1px solid ${selectedCategory === 'COMMON' ? '#38bdf8' : 'rgba(255, 255, 255, 0.08)'}`,
                  padding: '7px 14px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Layers size={14} />
                <span>COMMON ({commonList.length})</span>
              </button>

              {/* Tab 2: PENDING */}
              <button
                onClick={() => setSelectedCategory('PENDING')}
                style={{
                  background: selectedCategory === 'PENDING' ? '#d97706' : 'transparent',
                  color: selectedCategory === 'PENDING' ? '#ffffff' : '#fbbf24',
                  border: `1px solid ${selectedCategory === 'PENDING' ? '#f59e0b' : 'rgba(245, 158, 11, 0.3)'}`,
                  padding: '7px 14px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Activity size={14} />
                <span>PENDING ({pendingList.length})</span>
              </button>

              {/* Tab 3: FINISH */}
              <button
                onClick={() => setSelectedCategory('FINISH')}
                style={{
                  background: selectedCategory === 'FINISH' ? '#059669' : 'transparent',
                  color: selectedCategory === 'FINISH' ? '#ffffff' : '#34d399',
                  border: `1px solid ${selectedCategory === 'FINISH' ? '#10b981' : 'rgba(16, 185, 129, 0.3)'}`,
                  padding: '7px 14px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <CheckCheck size={14} />
                <span>FINISH ({finishList.length})</span>
              </button>

              {/* Tab 4: ESCALATION */}
              <button
                onClick={() => setSelectedCategory('ESCALATION')}
                style={{
                  background: selectedCategory === 'ESCALATION' ? '#dc2626' : 'transparent',
                  color: selectedCategory === 'ESCALATION' ? '#ffffff' : '#f87171',
                  border: `1px solid ${selectedCategory === 'ESCALATION' ? '#ef4444' : 'rgba(239, 68, 68, 0.3)'}`,
                  padding: '7px 14px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <PhoneForwarded size={14} />
                <span>ESCALATION ({escalationList.length})</span>
              </button>
            </div>

            {/* Filter and Search Bar */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '16px',
              gap: '12px',
              flexWrap: 'wrap'
            }}>
              <div style={{ position: 'relative', flex: 1, minWidth: '280px', maxWidth: '420px' }}>
                <Search size={16} color="#64748b" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="text"
                  placeholder="Search incident ID, node location, resource..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#0d111a',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '8px',
                    padding: '8px 12px 8px 36px',
                    color: '#f8fafc',
                    fontSize: '13px',
                    outline: 'none'
                  }}
                />
              </div>

              {/* Severity Pills */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', marginRight: '4px' }}>Filter Severity:</span>
                {(['ALL', 'HIGH', 'MED', 'LOW'] as const).map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setSeverityFilter(sev)}
                    style={{
                      background: severityFilter === sev ? '#0284c7' : '#1e293b',
                      color: severityFilter === sev ? '#ffffff' : '#94a3b8',
                      border: 'none',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    {sev}
                  </button>
                ))}
              </div>
            </div>

            {/* Content View: Table or Kanban Board */}
            {viewMode === 'table' ? (
              <div className="glass-panel" style={{ overflow: 'hidden' }}>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ background: '#0d111a', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: '#64748b', fontSize: '11px', textTransform: 'uppercase' }}>
                        <th style={{ padding: '12px 18px' }}>Ticket ID</th>
                        <th style={{ padding: '12px 18px' }}>Location & Node</th>
                        <th style={{ padding: '12px 18px' }}>ML Severity</th>
                        <th style={{ padding: '12px 18px' }}>Confidence</th>
                        <th style={{ padding: '12px 18px' }}>Status</th>
                        <th style={{ padding: '12px 18px' }}>Dispatcher / Assigned</th>
                        <th style={{ padding: '12px 18px', textAlign: 'right' }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredIncidents.length === 0 ? (
                        <tr>
                          <td colSpan={7} style={{ padding: '48px', textAlign: 'center', color: '#64748b' }}>
                            <div style={{ fontSize: '14px', fontWeight: 600, color: '#94a3b8' }}>
                              No incidents found in database for category: <strong>{selectedCategory}</strong>
                            </div>
                            <div style={{ fontSize: '12px', marginTop: '6px' }}>
                              Execute <code>python backend/rag/sender.py</code> to dispatch live incidents.
                            </div>
                          </td>
                        </tr>
                      ) : (
                        filteredIncidents.map((inc) => {
                          const isResolved = isIncidentResolved(inc);
                          const isEscalated = isIncidentEscalated(inc);

                          return (
                            <tr
                              key={inc.id}
                              style={{
                                borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                                cursor: 'pointer',
                                transition: 'background-color 0.15s ease'
                              }}
                              onClick={() => navigate(`/incident/${String(inc.ticket_id || inc.id).replace('INC-', '')}`)}
                              onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)'; }}
                              onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
                            >
                              <td style={{ padding: '14px 18px' }}>
                                <span className="mono-tag" style={{ color: '#38bdf8', fontWeight: 700 }}>
                                  {inc.id}
                                </span>
                              </td>
                              <td style={{ padding: '14px 18px' }}>
                                <div style={{ fontWeight: 600, color: '#f8fafc' }}>
                                  {inc.title || `Alert at ${inc.location}`}
                                </div>
                                <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                                  {inc.location} • {inc.resource_type}
                                </div>
                              </td>
                              <td style={{ padding: '14px 18px' }}>
                                <span className={`badge-severity badge-sev-${inc.fault_severity}`}>
                                  {inc.severity}
                                </span>
                              </td>
                              <td style={{ padding: '14px 18px', color: '#38bdf8', fontWeight: 600 }}>
                                {(inc.confidence * 100).toFixed(1)}%
                              </td>
                              <td style={{ padding: '14px 18px' }}>
                                <span style={{
                                  fontSize: '11px',
                                  fontWeight: 700,
                                  padding: '3px 8px',
                                  borderRadius: '10px',
                                  background: isResolved ? 'rgba(16, 185, 129, 0.18)' : isEscalated ? 'rgba(239, 68, 68, 0.18)' : 'rgba(245, 158, 11, 0.18)',
                                  color: isResolved ? '#34d399' : isEscalated ? '#f87171' : '#fbbf24',
                                  border: `1px solid ${isResolved ? 'rgba(16, 185, 129, 0.4)' : isEscalated ? 'rgba(239, 68, 68, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`
                                }}>
                                  {isResolved ? 'FINISH (RESOLVED)' : isEscalated ? 'FINISH (ESCALATED)' : 'PENDING REVIEW'}
                                </span>
                              </td>
                              <td style={{ padding: '14px 18px', color: '#cbd5e1', fontSize: '12px' }}>
                                {inc.assigned_to || 'Autonomous Dispatch'}
                              </td>
                              <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                                <button
                                  className="btn-primary"
                                  style={{
                                    padding: '6px 12px',
                                    fontSize: '11px',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                    background: isResolved ? 'linear-gradient(135deg, #059669, #10b981)' : isEscalated ? 'linear-gradient(135deg, #dc2626, #ef4444)' : undefined
                                  }}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    navigate(`/incident/${String(inc.ticket_id || inc.id).replace('INC-', '')}`);
                                  }}
                                >
                                  <span>{isResolved ? 'View Resolution' : isEscalated ? 'View Escalation' : 'Review 3 RCA Options'}</span>
                                  <ArrowRight size={12} />
                                </button>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              /* KANBAN BOARD VIEW */
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                {/* Column 1: PENDING REVIEW */}
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '12px', padding: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', borderBottom: '1px solid rgba(245, 158, 11, 0.2)', paddingBottom: '8px' }}>
                    <div style={{ fontSize: '13px', fontWeight: 800, color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Activity size={15} />
                      <span>PENDING REVIEW</span>
                    </div>
                    <span style={{ fontSize: '11px', background: '#d97706', color: '#ffffff', padding: '2px 8px', borderRadius: '10px', fontWeight: 700 }}>
                      {pendingList.length}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {pendingList.map(inc => (
                      <div
                        key={inc.id}
                        onClick={() => navigate(`/incident/${String(inc.ticket_id || inc.id).replace('INC-', '')}`)}
                        style={{
                          background: '#0d111a',
                          border: '1px solid rgba(255, 255, 255, 0.08)',
                          borderRadius: '8px',
                          padding: '12px',
                          cursor: 'pointer'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span className="mono-tag" style={{ color: '#38bdf8', fontWeight: 700 }}>{inc.id}</span>
                          <span className={`badge-severity badge-sev-${inc.fault_severity}`}>{inc.severity}</span>
                        </div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc', marginTop: '6px' }}>{inc.title || `Alert at ${inc.location}`}</div>
                        <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Node: {inc.location} • Conf: {(inc.confidence * 100).toFixed(0)}%</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Column 2: FINISH & RESOLVED */}
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '12px', padding: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', borderBottom: '1px solid rgba(16, 185, 129, 0.2)', paddingBottom: '8px' }}>
                    <div style={{ fontSize: '13px', fontWeight: 800, color: '#34d399', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCheck size={15} />
                      <span>FINISH (RESOLVED)</span>
                    </div>
                    <span style={{ fontSize: '11px', background: '#059669', color: '#ffffff', padding: '2px 8px', borderRadius: '10px', fontWeight: 700 }}>
                      {finishList.length}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {finishList.map(inc => (
                      <div
                        key={inc.id}
                        onClick={() => navigate(`/incident/${String(inc.ticket_id || inc.id).replace('INC-', '')}`)}
                        style={{
                          background: '#0d111a',
                          border: '1px solid rgba(16, 185, 129, 0.3)',
                          borderRadius: '8px',
                          padding: '12px',
                          cursor: 'pointer'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span className="mono-tag" style={{ color: '#34d399', fontWeight: 700 }}>{inc.id}</span>
                          <span style={{ fontSize: '10px', color: '#34d399', fontWeight: 700, background: 'rgba(16, 185, 129, 0.2)', padding: '2px 6px', borderRadius: '4px' }}>COMMITTED (YES)</span>
                        </div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc', marginTop: '6px' }}>{inc.confirmed_root_cause || inc.title}</div>
                        <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>Assigned: {inc.assigned_to}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Column 3: ESCALATION TIER-3 */}
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '12px', padding: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', borderBottom: '1px solid rgba(239, 68, 68, 0.2)', paddingBottom: '8px' }}>
                    <div style={{ fontSize: '13px', fontWeight: 800, color: '#f87171', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <PhoneForwarded size={15} />
                      <span>ESCALATION (TIER-3)</span>
                    </div>
                    <span style={{ fontSize: '11px', background: '#dc2626', color: '#ffffff', padding: '2px 8px', borderRadius: '10px', fontWeight: 700 }}>
                      {escalationList.length}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {escalationList.map(inc => (
                      <div
                        key={inc.id}
                        onClick={() => navigate(`/incident/${String(inc.ticket_id || inc.id).replace('INC-', '')}`)}
                        style={{
                          background: '#0d111a',
                          border: '1px solid rgba(239, 68, 68, 0.3)',
                          borderRadius: '8px',
                          padding: '12px',
                          cursor: 'pointer'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span className="mono-tag" style={{ color: '#f87171', fontWeight: 700 }}>{inc.id}</span>
                          <span style={{ fontSize: '10px', color: '#f87171', fontWeight: 700, background: 'rgba(239, 68, 68, 0.2)', padding: '2px 6px', borderRadius: '4px' }}>3x NO ESCALATED</span>
                        </div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc', marginTop: '6px' }}>{inc.title || `Escalation Alarm at ${inc.location}`}</div>
                        <div style={{ fontSize: '11px', color: '#fca5a5', marginTop: '4px' }}>Assigned: NOC_ENGINEERING_TEAM (Tier-3)</div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            )}
          </>
        )}

        {/* ============================================================
            VIEW 2: MONGODB OPERATOR DECISIONS & COMMIT AUDIT LOG
        ============================================================ */}
        {activeConsoleView === 'DECISIONS' && (
          <div className="glass-panel" style={{ overflow: 'hidden' }}>
            <div style={{
              padding: '18px 20px',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: 'rgba(168, 85, 247, 0.06)'
            }}>
              <div>
                <div style={{ fontSize: '16px', fontWeight: 800, color: '#c084fc', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Database size={18} />
                  <span>Historical Decisions & Operator Audit Trail (Stored in MongoDB)</span>
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                  Live records retrieved directly from <code>cts_incident_management.decisions</code> collection in MongoDB.
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '12px', background: 'rgba(168, 85, 247, 0.2)', color: '#c084fc', padding: '4px 10px', borderRadius: '12px', fontWeight: 700 }}>
                  {filteredDecisions.length} Total Decisions Logged
                </span>
              </div>
            </div>

            {/* Search within Decisions */}
            <div style={{ padding: '12px 20px', borderBottom: '1px solid rgba(255, 255, 255, 0.04)', background: '#0d111a' }}>
              <div style={{ position: 'relative', maxWidth: '380px' }}>
                <Search size={14} color="#64748b" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="text"
                  placeholder="Search decisions by ticket ID, operator, root cause..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{
                    width: '100%',
                    background: '#121824',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '6px',
                    padding: '6px 10px 6px 30px',
                    fontSize: '12px',
                    color: '#f8fafc',
                    outline: 'none'
                  }}
                />
              </div>
            </div>

            {/* Decisions List */}
            {filteredDecisions.length === 0 ? (
              <div style={{ padding: '60px', textAlign: 'center', color: '#64748b' }}>
                <FileText size={36} style={{ margin: '0 auto 10px', opacity: 0.4 }} />
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc' }}>No Decisions Logged in MongoDB Yet</div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                  Click <strong>YES</strong> to commit or <strong>NO</strong> to reject root causes in the NOC Details console to record operator decisions in MongoDB.
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {filteredDecisions.map((dec, idx) => {
                  const isCommit = dec.decision_type === 'COMMIT_RESOLUTION' || dec.confirmed === true;
                  const isEsc = dec.decision_type.includes('ESCALAT');

                  return (
                    <div
                      key={idx}
                      style={{
                        padding: '16px 20px',
                        borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                        display: 'grid',
                        gridTemplateColumns: '120px 180px 1.5fr 160px 180px 120px',
                        alignItems: 'center',
                        gap: '16px'
                      }}
                    >
                      <div>
                        <span className="mono-tag" style={{ color: '#38bdf8', fontWeight: 700 }}>
                          INC-{dec.ticket_id}
                        </span>
                      </div>

                      <div>
                        <span style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '3px 8px',
                          borderRadius: '10px',
                          background: isCommit ? 'rgba(16, 185, 129, 0.2)' : isEsc ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                          color: isCommit ? '#34d399' : isEsc ? '#f87171' : '#fbbf24'
                        }}>
                          {isCommit ? 'COMMIT (YES)' : isEsc ? 'ESCALATION (3x NO)' : 'REJECT (NO)'}
                        </span>
                      </div>

                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc' }}>
                          {dec.root_cause || dec.reason || 'Operator Decision'}
                        </div>
                        {dec.resolution && (
                          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                            Action: {dec.resolution}
                          </div>
                        )}
                        {dec.commit_id && (
                          <div style={{ fontSize: '10px', color: '#64748b', marginTop: '2px' }}>
                            Commit ID: <code>{dec.commit_id}</code>
                          </div>
                        )}
                      </div>

                      <div>
                        <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase' }}>Operator</div>
                        <div style={{ fontSize: '12px', color: '#e2e8f0', fontWeight: 600 }}>{dec.operator || 'NOC Operator'}</div>
                      </div>

                      <div>
                        <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase' }}>Timestamp (UTC)</div>
                        <div style={{ fontSize: '11px', color: '#94a3b8' }}>{dec.timestamp}</div>
                      </div>

                      <div style={{ textAlign: 'right' }}>
                        <button
                          className="btn-secondary"
                          style={{ padding: '5px 10px', fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                          onClick={() => navigate(`/incident/${String(dec.ticket_id).replace('INC-', '')}`)}
                        >
                          <Eye size={12} />
                          <span>Inspect</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
