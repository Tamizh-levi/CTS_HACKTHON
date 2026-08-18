import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  Users,
  CheckCircle2,
  PhoneForwarded,
  Activity,
  UserCheck,
  Search,
  LogOut,
  Eye,
  X,
  Database,
  FileText,
  AlertTriangle,
  CheckCheck,
  BarChart3,
  UserPlus,
  Sparkles
} from 'lucide-react';
import API_BASE_URL from '../services/api';
import AdminChatBot from '../components/AdminChatBot';

interface MongoUser {
  id: string;
  username: string;
  name: string;
  role: string;
  department: string;
  email: string;
  last_login_at: string;
  created_at: string;
}

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
  agent_result?: any;
  dispatch_result?: any;
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

export default function AdminDashboard() {
  const navigate = useNavigate();

  const [users, setUsers] = useState<MongoUser[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [decisions, setDecisions] = useState<OperatorDecision[]>([]);

  const [activeTab, setActiveTab] = useState<'overview' | 'operators' | 'decisions' | 'escalations'>('overview');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRoleFilter, setSelectedRoleFilter] = useState<'ALL' | 'operator' | 'admin' | 'field'>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'SOLVED' | 'PENDING' | 'ESCALATED'>('ALL');
  const [decisionFilter, setDecisionFilter] = useState<'ALL' | 'COMMIT' | 'REJECT' | 'ESCALATION'>('ALL');

  // Selected Escalation Incident for Pop-up Modal
  const [selectedEscalation, setSelectedEscalation] = useState<{
    incident: Incident | null;
    decision: OperatorDecision | null;
  } | null>(null);

  // New Operator Modal
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [newUserData, setNewUserData] = useState({
    username: '',
    password: '',
    name: '',
    role: 'operator',
    department: 'Tier-2 NOC Console',
    email: ''
  });
  const [addUserLoading, setAddUserLoading] = useState(false);
  const [addUserMsg, setAddUserMsg] = useState('');

  const [currentUser, setCurrentUser] = useState<any>(null);

  useEffect(() => {
    const rawUser = localStorage.getItem('user');
    if (rawUser) {
      try {
        setCurrentUser(JSON.parse(rawUser));
      } catch {
        setCurrentUser({ name: 'System Administrator', role: 'admin' });
      }
    } else {
      setCurrentUser({ name: 'System Administrator', role: 'admin' });
    }

    fetchAdminData();

    // Auto poll every 3 seconds to keep admin stats live
    const interval = setInterval(() => {
      fetchAdminDataSilent();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const fetchAdminData = async () => {
    try {
      // 1. Fetch users from MongoDB
      const userRes = await fetch(`${API_BASE_URL}/api/auth/users`);
      if (userRes.ok) {
        const userData = await userRes.json();
        setUsers(userData.users || []);
      }

      // 2. Fetch incidents
      const incRes = await fetch(`${API_BASE_URL}/api/incidents`);
      if (incRes.ok) {
        const incData = await incRes.json();
        setIncidents(incData.incidents || []);
      }

      // 3. Fetch decisions from MongoDB
      const decRes = await fetch(`${API_BASE_URL}/api/decisions`);
      if (decRes.ok) {
        const decData = await decRes.json();
        setDecisions(decData.decisions || []);
      }
    } catch (err) {
      console.warn('Admin fetch notice:', err);
    }
  };

  const fetchAdminDataSilent = async () => {
    try {
      const [userRes, incRes, decRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/auth/users`),
        fetch(`${API_BASE_URL}/api/incidents`),
        fetch(`${API_BASE_URL}/api/decisions`)
      ]);

      if (userRes.ok) {
        const userData = await userRes.json();
        if (Array.isArray(userData.users)) setUsers(userData.users);
      }
      if (incRes.ok) {
        const incData = await incRes.json();
        if (Array.isArray(incData.incidents)) setIncidents(incData.incidents);
      }
      if (decRes.ok) {
        const decData = await decRes.json();
        if (Array.isArray(decData.decisions)) setDecisions(decData.decisions);
      }
    } catch {
      // Retain existing state
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddUserLoading(true);
    setAddUserMsg('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newUserData)
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setAddUserMsg('Operator successfully created in MongoDB with PBKDF2 encrypted password!');
        fetchAdminDataSilent();
        setTimeout(() => {
          setShowAddUserModal(false);
          setAddUserMsg('');
          setNewUserData({
            username: '',
            password: '',
            name: '',
            role: 'operator',
            department: 'Tier-2 NOC Console',
            email: ''
          });
        }, 1200);
      } else {
        setAddUserMsg(`Failed: ${data.message || 'Error creating user'}`);
      }
    } catch (err: any) {
      setAddUserMsg(`Error: ${err.message}`);
    } finally {
      setAddUserLoading(false);
    }
  };

  // Helper to look up all decisions for a ticket from the decisions table
  const getTicketDecisions = (ticketId: number | string): OperatorDecision[] => {
    const cleanId = String(ticketId || '').replace(/^INC-/i, '').trim();
    if (!cleanId) return [];
    return decisions.filter((d) => {
      const decCleanId = String(d.ticket_id || '').replace(/^INC-/i, '').trim();
      return decCleanId === cleanId;
    });
  };

  const getIncidentEffectiveStatus = (inc: Incident): string => {
    const ticketDecisions = getTicketDecisions(inc.ticket_id || inc.id);
    if (ticketDecisions.length > 0) {
      // 1. Check if there is any COMMIT_RESOLUTION in decisions table
      const hasCommit = ticketDecisions.some(
        (d) =>
          d.decision_type === 'COMMIT_RESOLUTION' ||
          d.confirmed === true ||
          String(d.decision_type || '').toUpperCase().includes('COMMIT') ||
          String(d.status || '').toUpperCase().includes('RESOLV') ||
          String(d.status || '').toUpperCase().includes('COMMITT')
      );
      if (hasCommit) {
        return 'FINISHED (RESOLVED)';
      }

      // 2. Check if there is an ESCALATION_TO_TIER_3 or if all 3 ranks (1, 2, 3) were rejected in decisions table
      const hasEscalation = ticketDecisions.some(
        (d) =>
          d.decision_type === 'ESCALATION_TO_TIER_3' ||
          String(d.decision_type || '').toUpperCase().includes('ESCALAT') ||
          String(d.status || '').toUpperCase().includes('ESCALAT')
      );
      const rejectedRanks = new Set(
        ticketDecisions
          .filter((d) => d.decision_type === 'REJECT_CANDIDATE' || d.confirmed === false)
          .map((d) => Number(d.selected_rank || 0))
          .filter(Boolean)
      );

      if (hasEscalation || (rejectedRanks.has(1) && rejectedRanks.has(2) && rejectedRanks.has(3))) {
        return 'FINISHED (ESCALATED)';
      }

      return 'PENDING REVIEW';
    }

    // Direct fallback from MongoDB incident document
    const rawStatus = String(inc.status || '').toUpperCase();
    if (rawStatus.includes('RESOLV') || rawStatus.includes('COMMITT') || rawStatus.includes('CLOSED')) {
      return 'FINISHED (RESOLVED)';
    }
    if (rawStatus.includes('ESCALAT')) {
      return 'FINISHED (ESCALATED)';
    }

    return 'PENDING REVIEW';
  };

  const isIncidentResolved = (inc: Incident) =>
    getIncidentEffectiveStatus(inc) === 'FINISHED (RESOLVED)';

  const isIncidentEscalated = (inc: Incident) =>
    getIncidentEffectiveStatus(inc) === 'FINISHED (ESCALATED)';

  const isIncidentPending = (inc: Incident) =>
    getIncidentEffectiveStatus(inc) === 'PENDING REVIEW';

  // Helper calculations
  const totalOperatorsCount = users.length;
  const operatorRoleCount = users.filter((u) => u.role === 'operator').length;
  const adminRoleCount = users.filter((u) => u.role === 'admin').length;
  const fieldRoleCount = users.filter((u) => u.role === 'field').length;

  const totalCommittedCount = decisions.filter(
    (d) =>
      d.decision_type === 'COMMIT_RESOLUTION' ||
      d.confirmed === true ||
      String(d.decision_type || '').toUpperCase().includes('COMMIT')
  ).length;

  const totalRejectionsCount = decisions.filter(
    (d) =>
      (d.decision_type === 'REJECT_CANDIDATE' || d.confirmed === false) &&
      d.decision_type !== 'ESCALATION_TO_TIER_3'
  ).length;

  const totalEscalatedDecisionsCount = decisions.filter(
    (d) =>
      d.decision_type === 'ESCALATION_TO_TIER_3' ||
      String(d.decision_type || '').toUpperCase().includes('ESCALAT')
  ).length;

  const totalSolvedCount = incidents.filter(isIncidentResolved).length;
  const totalPendingCount = incidents.filter(isIncidentPending).length;
  const totalEscalatedCount = incidents.filter(isIncidentEscalated).length;
  const escalatedIncidents = incidents.filter(isIncidentEscalated);

  // Filtered Decisions (Audit Trail)
  const filteredDecisions = decisions.filter((dec) => {
    const isCommit =
      dec.decision_type === 'COMMIT_RESOLUTION' ||
      dec.confirmed === true ||
      String(dec.decision_type || '').toUpperCase().includes('COMMIT');
    const isEsc =
      dec.decision_type === 'ESCALATION_TO_TIER_3' ||
      String(dec.decision_type || '').toUpperCase().includes('ESCALAT');
    const isReject =
      dec.decision_type === 'REJECT_CANDIDATE' || dec.confirmed === false;

    if (decisionFilter === 'COMMIT') return isCommit;
    if (decisionFilter === 'REJECT') return isReject && !isEsc;
    if (decisionFilter === 'ESCALATION') return isEsc;
    return true;
  });

  // Filtered Users
  const filteredUsers = users.filter((u) => {
    const matchesRole = selectedRoleFilter === 'ALL' || u.role === selectedRoleFilter;
    const matchesSearch =
      (u.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (u.username || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (u.email || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (u.department || '').toLowerCase().includes(searchTerm.toLowerCase());
    return matchesRole && matchesSearch;
  });

  // Filtered Incidents
  const filteredIncidents = incidents.filter((inc) => {
    const matchesSearch =
      String(inc.id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(inc.ticket_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(inc.location || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(inc.resource_type || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(inc.title || '').toLowerCase().includes(searchTerm.toLowerCase());

    const isResolved = isIncidentResolved(inc);
    const isEscalated = isIncidentEscalated(inc);
    const isPending = isIncidentPending(inc);

    const matchesStatus =
      statusFilter === 'ALL' ||
      (statusFilter === 'SOLVED' && isResolved) ||
      (statusFilter === 'PENDING' && isPending) ||
      (statusFilter === 'ESCALATED' && isEscalated);

    return matchesSearch && matchesStatus;
  });

  // Open Pop-up Modal for Escalation Item
  const handleOpenEscalationModal = (inc: Incident) => {
    const cleanId = String(inc.ticket_id || inc.id).replace('INC-', '').trim();
    const relatedDec = decisions.find(
      (d) =>
        String(d.ticket_id).replace('INC-', '').trim() === cleanId &&
        (d.decision_type.includes('ESCALAT') || String(d.status || '').includes('ESCALAT'))
    );
    setSelectedEscalation({
      incident: inc,
      decision: relatedDec || null
    });
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100%',
        backgroundColor: '#07090e',
        color: '#f8fafc',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {/* Top Navbar */}
      <header
        style={{
          backgroundColor: '#0d111a',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          padding: '14px 28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 40
        }}
      >
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #7c3aed, #a855f7)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(168, 85, 247, 0.4)'
            }}
          >
            <ShieldAlert size={24} color="#ffffff" />
          </div>
          <div>
            <div
              style={{
                fontSize: '17px',
                fontWeight: 800,
                letterSpacing: '-0.02em',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              NOC EXECUTIVE ADMIN CONSOLE{' '}
              <span
                style={{
                  fontSize: '11px',
                  background: 'rgba(168, 85, 247, 0.2)',
                  color: '#c084fc',
                  border: '1px solid rgba(168, 85, 247, 0.4)',
                  padding: '2px 8px',
                  borderRadius: '12px'
                }}
              >
                /admin-dashboard
              </span>
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
              Total Operators • Total Commits • Solved • Pending • Escalations
            </div>
          </div>
        </div>

        {/* Header Right Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* <button
            onClick={() => navigate('/noc-dashboard')}
            className="btn-secondary"
            style={{
              padding: '7px 14px',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Radio size={14} color="#38bdf8" />
            <span>NOC Operator Console</span>
          </button> */}

          <button
            onClick={() => navigate('/admin-predict')}
            className="btn-secondary"
            style={{
              padding: '7px 14px',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              borderColor: 'rgba(56, 189, 248, 0.4)',
              color: '#38bdf8'
            }}
          >
            <Sparkles size={14} color="#38bdf8" />
            <span>SLA & Workload Forecaster</span>
          </button>

          <button
            onClick={() => setShowAddUserModal(true)}
            className="btn-primary"
            style={{
              padding: '7px 14px',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'linear-gradient(135deg, #7c3aed, #9333ea)'
            }}
          >
            <UserPlus size={14} />
            <span>Add Operator</span>
          </button>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '6px 12px',
              borderRadius: '20px',
              fontSize: '12px',
              color: '#c084fc'
            }}
          >
            <UserCheck size={14} />
            <span>{currentUser?.name || 'Administrator'}</span>
            <span
              style={{
                fontSize: '10px',
                background: '#3b0764',
                padding: '1px 6px',
                borderRadius: '8px',
                textTransform: 'uppercase',
                color: '#d8b4fe'
              }}
            >
              ADMIN
            </span>
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

      {/* Main Container */}
      <div
        style={{
          flex: 1,
          padding: '24px 28px',
          maxWidth: '1600px',
          width: '100%',
          margin: '0 auto',
          boxSizing: 'border-box'
        }}
      >
        {/* ============================================================
            5 TOP KPI CARDS: TOTAL OPERATOR, TOTAL COMMIT, SOLVED, PENDING, ESCALATION
        ============================================================ */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '14px',
            marginBottom: '24px'
          }}
        >
          {/* Card 1: TOTAL OPERATOR */}
          <div
            onClick={() => setActiveTab('operators')}
            className="glass-panel"
            style={{
              padding: '18px',
              borderLeft: '4px solid #a855f7',
              cursor: 'pointer',
              border: activeTab === 'operators' ? '2px solid #a855f7' : undefined
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                color: '#c084fc',
                fontSize: '11px',
                fontWeight: 700,
                marginBottom: '8px'
              }}
            >
              <span>1. TOTAL OPERATOR</span>
              <Users size={18} color="#a855f7" />
            </div>
            <div
              style={{
                fontSize: '28px',
                fontWeight: 800,
                color: '#f8fafc',
                letterSpacing: '-0.02em'
              }}
            >
              {totalOperatorsCount}{' '}
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: 500 }}>
                Users
              </span>
            </div>
            <div
              style={{
                fontSize: '11px',
                color: '#94a3b8',
                marginTop: '6px',
                display: 'flex',
                gap: '8px'
              }}
            >
              <span>Op: <strong>{operatorRoleCount}</strong></span>
              <span>•</span>
              <span>Admin: <strong>{adminRoleCount}</strong></span>
              <span>•</span>
              <span>Field: <strong>{fieldRoleCount}</strong></span>
            </div>
          </div>

          {/* Card 2: TOTAL COMMIT */}
          <div
            onClick={() => {
              setActiveTab('decisions');
              setDecisionFilter('COMMIT');
            }}
            className="glass-panel"
            style={{
              padding: '18px',
              borderLeft: '4px solid #38bdf8',
              cursor: 'pointer',
              border: activeTab === 'decisions' && decisionFilter === 'COMMIT' ? '2px solid #38bdf8' : undefined
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                color: '#38bdf8',
                fontSize: '11px',
                fontWeight: 700,
                marginBottom: '8px'
              }}
            >
              <span>2. TOTAL COMMIT</span>
              <FileText size={18} color="#38bdf8" />
            </div>
            <div
              style={{
                fontSize: '28px',
                fontWeight: 800,
                color: '#38bdf8',
                letterSpacing: '-0.02em'
              }}
            >
              {totalCommittedCount}{' '}
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: 500 }}>
                Commits
              </span>
            </div>
            <div style={{ fontSize: '11px', color: '#38bdf8', opacity: 0.85, marginTop: '6px' }}>
              Recorded in MongoDB Decisions
            </div>
          </div>

          {/* Card 3: SOLVED */}
          <div
            onClick={() => {
              setActiveTab('overview');
              setStatusFilter('SOLVED');
            }}
            className="glass-panel"
            style={{
              padding: '18px',
              borderLeft: '4px solid #10b981',
              cursor: 'pointer',
              border: statusFilter === 'SOLVED' && activeTab === 'overview' ? '2px solid #10b981' : undefined
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                color: '#34d399',
                fontSize: '11px',
                fontWeight: 700,
                marginBottom: '8px'
              }}
            >
              <span>3. SOLVED & RESOLVED</span>
              <CheckCheck size={18} color="#10b981" />
            </div>
            <div
              style={{
                fontSize: '28px',
                fontWeight: 800,
                color: '#34d399',
                letterSpacing: '-0.02em'
              }}
            >
              {totalSolvedCount}{' '}
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: 500 }}>
                Solved
              </span>
            </div>
            <div style={{ fontSize: '11px', color: '#34d399', opacity: 0.85, marginTop: '6px' }}>
              Confirmed via YES & Dispatched
            </div>
          </div>

          {/* Card 4: PENDING */}
          <div
            onClick={() => {
              setActiveTab('overview');
              setStatusFilter('PENDING');
            }}
            className="glass-panel"
            style={{
              padding: '18px',
              borderLeft: '4px solid #f59e0b',
              cursor: 'pointer',
              border: statusFilter === 'PENDING' && activeTab === 'overview' ? '2px solid #f59e0b' : undefined
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                color: '#fbbf24',
                fontSize: '11px',
                fontWeight: 700,
                marginBottom: '8px'
              }}
            >
              <span>4. PENDING REVIEW</span>
              <Activity size={18} color="#f59e0b" />
            </div>
            <div
              style={{
                fontSize: '28px',
                fontWeight: 800,
                color: '#fbbf24',
                letterSpacing: '-0.02em'
              }}
            >
              {totalPendingCount}{' '}
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: 500 }}>
                Open
              </span>
            </div>
            <div style={{ fontSize: '11px', color: '#fbbf24', opacity: 0.85, marginTop: '6px' }}>
              Awaiting 3-Option Operator Review
            </div>
          </div>

          {/* Card 5: ESCALATION */}
          <div
            onClick={() => setActiveTab('escalations')}
            className="glass-panel"
            style={{
              padding: '18px',
              borderLeft: '4px solid #ef4444',
              cursor: 'pointer',
              border: activeTab === 'escalations' ? '2px solid #ef4444' : undefined,
              background: 'rgba(239, 68, 68, 0.06)'
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                color: '#f87171',
                fontSize: '11px',
                fontWeight: 700,
                marginBottom: '8px'
              }}
            >
              <span>5. ESCALATION (TIER-3)</span>
              <PhoneForwarded size={18} color="#ef4444" />
            </div>
            <div
              style={{
                fontSize: '28px',
                fontWeight: 800,
                color: '#ef4444',
                letterSpacing: '-0.02em'
              }}
            >
              {totalEscalatedCount}{' '}
              <span style={{ fontSize: '13px', color: '#fca5a5', fontWeight: 500 }}>
                Escalated
              </span>
            </div>
            <div style={{ fontSize: '11px', color: '#f87171', marginTop: '6px', fontWeight: 600 }}>
              Click to view Escalation Pop-Up →
            </div>
          </div>
        </div>

        {/* ============================================================
            NAVIGATION TABS
        ============================================================ */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            paddingBottom: '12px',
            marginBottom: '20px',
            flexWrap: 'wrap',
            gap: '12px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <button
              onClick={() => setActiveTab('overview')}
              style={{
                background: activeTab === 'overview' ? '#1e293b' : 'transparent',
                border: `1px solid ${activeTab === 'overview' ? '#38bdf8' : 'rgba(255, 255, 255, 0.06)'}`,
                color: activeTab === 'overview' ? '#38bdf8' : '#94a3b8',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <BarChart3 size={15} />
              <span>Executive Overview ({incidents.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('operators')}
              style={{
                background: activeTab === 'operators' ? '#1e293b' : 'transparent',
                border: `1px solid ${activeTab === 'operators' ? '#a855f7' : 'rgba(255, 255, 255, 0.06)'}`,
                color: activeTab === 'operators' ? '#c084fc' : '#94a3b8',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Users size={15} />
              <span>Total Operators by Role ({users.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('decisions')}
              style={{
                background: activeTab === 'decisions' ? '#1e293b' : 'transparent',
                border: `1px solid ${activeTab === 'decisions' ? '#38bdf8' : 'rgba(255, 255, 255, 0.06)'}`,
                color: activeTab === 'decisions' ? '#38bdf8' : '#94a3b8',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <FileText size={15} />
              <span>Total Commits & Decisions ({decisions.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('escalations')}
              style={{
                background: activeTab === 'escalations' ? 'rgba(239, 68, 68, 0.15)' : 'transparent',
                border: `1px solid ${activeTab === 'escalations' ? '#ef4444' : 'rgba(255, 255, 255, 0.06)'}`,
                color: activeTab === 'escalations' ? '#f87171' : '#94a3b8',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <PhoneForwarded size={15} />
              <span>Escalation Protocol ({escalatedIncidents.length})</span>
            </button>
          </div>

          {/* Search bar */}
          <div style={{ position: 'relative', minWidth: '240px' }}>
            <Search
              size={14}
              color="#64748b"
              style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }}
            />
            <input
              type="text"
              placeholder="Search ID, user, node, root cause..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%',
                background: '#0d111a',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '6px',
                padding: '7px 10px 7px 32px',
                fontSize: '12px',
                color: '#f8fafc',
                outline: 'none'
              }}
            />
          </div>
        </div>

        {/* ============================================================
            TAB 1: EXECUTIVE OVERVIEW
        ============================================================ */}
        {activeTab === 'overview' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1.25fr 1fr', gap: '20px' }}>
            {/* Left: Filterable Incidents Stream */}
            <div className="glass-panel" style={{ padding: '20px' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '14px'
                }}
              >
                <div
                  style={{
                    fontSize: '15px',
                    fontWeight: 700,
                    color: '#f8fafc',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <Activity size={18} color="#38bdf8" />
                  <span>Telemetry Queue & Resolution Status</span>
                </div>

                {/* Status Pills */}
                <div style={{ display: 'flex', gap: '4px' }}>
                  {(['ALL', 'SOLVED', 'PENDING', 'ESCALATED'] as const).map((st) => (
                    <button
                      key={st}
                      onClick={() => setStatusFilter(st)}
                      style={{
                        background: statusFilter === st ? '#38bdf8' : '#1e293b',
                        color: statusFilter === st ? '#07090e' : '#94a3b8',
                        border: 'none',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: 700,
                        cursor: 'pointer'
                      }}
                    >
                      {st}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {filteredIncidents.length === 0 ? (
                  <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                    No matching telemetry records found. Execute <code>python sender.py</code> to stream live network payloads.
                  </div>
                ) : (
                  filteredIncidents.map((inc) => {
                    const isResolved = isIncidentResolved(inc);
                    const isEscalated = isIncidentEscalated(inc);

                    return (
                      <div
                        key={inc.id}
                        style={{
                          background: '#0d111a',
                          border: '1px solid rgba(255, 255, 255, 0.06)',
                          borderRadius: '8px',
                          padding: '14px 16px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span className="mono-tag" style={{ color: '#38bdf8', fontWeight: 700 }}>
                              {inc.id}
                            </span>
                            <span style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc' }}>
                              {inc.title || `Alert at ${inc.location}`}
                            </span>
                          </div>
                          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '3px' }}>
                            Node: <strong>{inc.location}</strong> • Type: {inc.severity_type} • Resource:{' '}
                            {inc.resource_type} • {inc.created_at}
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span
                            style={{
                              fontSize: '11px',
                              fontWeight: 700,
                              padding: '4px 10px',
                              borderRadius: '12px',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              background: isResolved
                                ? 'rgba(16, 185, 129, 0.15)'
                                : isEscalated
                                  ? 'rgba(239, 68, 68, 0.15)'
                                  : 'rgba(245, 158, 11, 0.15)',
                              color: isResolved ? '#34d399' : isEscalated ? '#f87171' : '#fbbf24',
                              border: `1px solid ${isResolved
                                  ? 'rgba(16, 185, 129, 0.35)'
                                  : isEscalated
                                    ? 'rgba(239, 68, 68, 0.35)'
                                    : 'rgba(245, 158, 11, 0.35)'
                                }`
                            }}
                          >
                            {isResolved && <CheckCircle2 size={12} />}
                            {isEscalated && <PhoneForwarded size={12} />}
                            {!isResolved && !isEscalated && <Activity size={12} />}
                            <span>
                              {isResolved
                                ? 'FINISHED (RESOLVED)'
                                : isEscalated
                                  ? 'ESCALATED'
                                  : 'PENDING REVIEW'}
                            </span>
                          </span>

                          {isEscalated && (
                            <button
                              onClick={() => handleOpenEscalationModal(inc)}
                              className="btn-secondary"
                              style={{
                                padding: '4px 10px',
                                fontSize: '11px',
                                color: '#f87171',
                                border: '1px solid rgba(239, 68, 68, 0.4)'
                              }}
                            >
                              <Eye size={12} />
                              <span>Pop-Up</span>
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Right: MongoDB Status & System Breakdown */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div className="glass-panel" style={{ padding: '20px' }}>
                <div
                  style={{
                    fontSize: '15px',
                    fontWeight: 700,
                    color: '#f8fafc',
                    marginBottom: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <Database size={18} color="#a855f7" />
                  <span>MongoDB Security & Persistence</span>
                </div>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '12px',
                    fontSize: '12px'
                  }}
                >

                  {/* <div
                    style={{
                      background: '#0d111a',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid rgba(255, 255, 255, 0.05)'
                    }}
                  >
                    <div style={{ color: '#64748b' }}>ENCRYPTION</div>
                    <div
                      style={{
                        fontSize: '14px',
                        fontWeight: 700,
                        color: '#34d399',
                        marginTop: '2px'
                      }}
                    >
                      PBKDF2:SHA256
                    </div>
                  </div> */}
                  <div
                    style={{
                      background: '#0d111a',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid rgba(255, 255, 255, 0.05)'
                    }}
                  >
                    <div style={{ color: '#64748b' }}>USERS ROSTER</div>
                    <div
                      style={{
                        fontSize: '14px',
                        fontWeight: 700,
                        color: '#c084fc',
                        marginTop: '2px'
                      }}
                    >
                      {users.length} Operators
                    </div>
                  </div>
                  <div
                    style={{
                      background: '#0d111a',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid rgba(255, 255, 255, 0.05)'
                    }}
                  >
                    <div style={{ color: '#64748b' }}>DECISION LOGS</div>
                    <div
                      style={{
                        fontSize: '14px',
                        fontWeight: 700,
                        color: '#38bdf8',
                        marginTop: '2px'
                      }}
                    >
                      {decisions.length} Commits
                    </div>
                  </div>
                </div>
              </div>

              {/* Roles Breakdown */}
              {/* <div className="glass-panel" style={{ padding: '20px' }}>
                <div
                  style={{
                    fontSize: '15px',
                    fontWeight: 700,
                    color: '#f8fafc',
                    marginBottom: '10px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <Users size={18} color="#c084fc" />
                  <span>Operator Breakdown & Dispatchers</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '10px 14px',
                      background: '#0d111a',
                      borderRadius: '6px',
                      fontSize: '12px'
                    }}
                  >
                    <span style={{ color: '#94a3b8' }}>Tier-2 NOC Operators</span>
                    <strong style={{ color: '#38bdf8' }}>{operatorRoleCount} active</strong>
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '10px 14px',
                      background: '#0d111a',
                      borderRadius: '6px',
                      fontSize: '12px'
                    }}
                  >
                    <span style={{ color: '#94a3b8' }}>System Administrators</span>
                    <strong style={{ color: '#c084fc' }}>{adminRoleCount} active</strong>
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '10px 14px',
                      background: '#0d111a',
                      borderRadius: '6px',
                      fontSize: '12px'
                    }}
                  >
                    <span style={{ color: '#94a3b8' }}>Field Technicians</span>
                    <strong style={{ color: '#34d399' }}>{fieldRoleCount} active</strong>
                  </div>
                </div>
              </div> */}
            </div>
          </div>
        )}

        {/* ============================================================
            TAB 2: TOTAL OPERATORS BY ROLE (MongoDB User Directory)
        ============================================================ */}
        {activeTab === 'operators' && (
          <div className="glass-panel" style={{ overflow: 'hidden' }}>
            <div
              style={{
                padding: '16px 20px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '12px'
              }}
            >
              <div>
                <div style={{ fontSize: '15px', fontWeight: 800, color: '#f8fafc' }}>
                  Total Operators & Personnel Directory (Stored in MongoDB)
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                  Total {users.length} active registered users with encrypted authentication records.
                </div>
              </div>

              {/* Role filter buttons */}
              <div style={{ display: 'flex', gap: '6px' }}>
                {(['ALL', 'operator', 'admin', 'field'] as const).map((r) => (
                  <button
                    key={r}
                    onClick={() => setSelectedRoleFilter(r)}
                    style={{
                      background: selectedRoleFilter === r ? '#a855f7' : '#1e293b',
                      color: selectedRoleFilter === r ? '#ffffff' : '#94a3b8',
                      border: 'none',
                      padding: '5px 12px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      textTransform: 'uppercase'
                    }}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  textAlign: 'left',
                  fontSize: '13px'
                }}
              >
                <thead>
                  <tr
                    style={{
                      background: '#0d111a',
                      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                      color: '#64748b',
                      fontSize: '11px',
                      textTransform: 'uppercase'
                    }}
                  >
                    <th style={{ padding: '12px 20px' }}>Full Name</th>
                    <th style={{ padding: '12px 20px' }}>Username / Email</th>
                    <th style={{ padding: '12px 20px' }}>Role</th>
                    <th style={{ padding: '12px 20px' }}>Department</th>
                    <th style={{ padding: '12px 20px' }}>Last Login</th>
                    {/* <th style={{ padding: '12px 20px' }}>Encryption</th> */}
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((u, idx) => (
                    <tr
                      key={u.id || idx}
                      style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}
                    >
                      <td style={{ padding: '14px 20px', fontWeight: 700, color: '#f8fafc' }}>
                        {u.name}
                      </td>
                      <td style={{ padding: '14px 20px', color: '#38bdf8' }}>{u.username}</td>
                      <td style={{ padding: '14px 20px' }}>
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            padding: '3px 8px',
                            borderRadius: '10px',
                            background:
                              u.role === 'admin'
                                ? 'rgba(168, 85, 247, 0.2)'
                                : u.role === 'field'
                                  ? 'rgba(16, 185, 129, 0.2)'
                                  : 'rgba(56, 189, 248, 0.2)',
                            color:
                              u.role === 'admin'
                                ? '#c084fc'
                                : u.role === 'field'
                                  ? '#34d399'
                                  : '#38bdf8',
                            textTransform: 'uppercase'
                          }}
                        >
                          {u.role}
                        </span>
                      </td>
                      <td style={{ padding: '14px 20px', color: '#cbd5e1' }}>{u.department}</td>
                      <td style={{ padding: '14px 20px', color: '#94a3b8', fontSize: '12px' }}>
                        {u.last_login_at || 'Never'}
                      </td>
                      {/* <td
                        style={{
                          padding: '14px 20px',
                          color: '#34d399',
                          fontSize: '11px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        <Lock size={12} />
                        <span>PBKDF2:SHA256 (MongoDB)</span>
                      </td> */}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ============================================================
            TAB 3: OPERATOR DECISIONS AUDIT (MongoDB Decisions Log)
        ============================================================ */}
        {activeTab === 'decisions' && (
          <div className="glass-panel" style={{ overflow: 'hidden', padding: 0 }}>
            {/* Header & Filter Bar */}
            <div
              style={{
                padding: '20px 24px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '16px',
                background: 'linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(0,0,0,0) 100%)'
              }}
            >
              <div>
                <div style={{ fontSize: '17px', fontWeight: 800, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileText size={18} color="#38bdf8" />
                  <span>Total Commits & Decision Audit History</span>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: '#38bdf8',
                      background: 'rgba(56, 189, 248, 0.15)',
                      padding: '2px 8px',
                      borderRadius: '12px'
                    }}
                  >
                    MongoDB Collection: decisions
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                  Live immutable audit record of all YES resolution commits, NO rejections, and Tier-3 escalations.
                </div>
              </div>

              {/* Filter Tabs */}
              <div style={{ display: 'flex', gap: '6px', background: '#0a0d14', padding: '4px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
                {[
                  { key: 'ALL', label: 'ALL', count: decisions.length, color: '#f8fafc' },
                  { key: 'COMMIT', label: 'COMMITS', count: totalCommittedCount, color: '#34d399' },
                  { key: 'REJECT', label: 'REJECTIONS', count: totalRejectionsCount, color: '#fbbf24' },
                  { key: 'ESCALATION', label: 'ESCALATIONS', count: totalEscalatedDecisionsCount, color: '#f87171' }
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setDecisionFilter(tab.key as any)}
                    style={{
                      background: decisionFilter === tab.key ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                      color: decisionFilter === tab.key ? tab.color : '#94a3b8',
                      border: decisionFilter === tab.key ? '1px solid rgba(255,255,255,0.15)' : '1px solid transparent',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <span>{tab.label}</span>
                    <span
                      style={{
                        fontSize: '10px',
                        background: 'rgba(0,0,0,0.3)',
                        padding: '1px 6px',
                        borderRadius: '10px'
                      }}
                    >
                      {tab.count}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Quick Metrics Bar */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: '12px',
                padding: '16px 24px',
                background: 'rgba(0,0,0,0.2)',
                borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#38bdf8' }} />
                <div>
                  <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>Total Actions Logged</div>
                  <div style={{ fontSize: '14px', fontWeight: 800, color: '#f8fafc' }}>{decisions.length} Decisions</div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
                <div>
                  <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>Resolved via Commit</div>
                  <div style={{ fontSize: '14px', fontWeight: 800, color: '#34d399' }}>{totalCommittedCount} Commits</div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b' }} />
                <div>
                  <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>Candidates Rejected</div>
                  <div style={{ fontSize: '14px', fontWeight: 800, color: '#fbbf24' }}>{totalRejectionsCount} Rejections</div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444' }} />
                <div>
                  <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>Tier-3 Escalations</div>
                  <div style={{ fontSize: '14px', fontWeight: 800, color: '#f87171' }}>{totalEscalatedDecisionsCount} Escalated</div>
                </div>
              </div>
            </div>

            {/* Decisions Table */}
            {filteredDecisions.length === 0 ? (
              <div style={{ padding: '60px 20px', textAlign: 'center', color: '#64748b' }}>
                <FileText size={40} style={{ margin: '0 auto 12px', opacity: 0.3 }} />
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#94a3b8' }}>
                  No decisions match filter "{decisionFilter}"
                </div>
                <div style={{ fontSize: '12px', marginTop: '4px' }}>
                  Operator actions on the NOC console will automatically append to this table in real-time.
                </div>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: '#0a0d14', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
                      <th style={{ padding: '14px 20px', fontSize: '11px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Ticket ID</th>
                      <th style={{ padding: '14px 20px', fontSize: '11px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Decision Action</th>
                      <th style={{ padding: '14px 20px', fontSize: '11px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Root Cause & Resolution Summary</th>
                      <th style={{ padding: '14px 20px', fontSize: '11px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Operator</th>
                      <th style={{ padding: '14px 20px', fontSize: '11px', color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDecisions.map((dec, idx) => {
                      const isCommit =
                        dec.decision_type === 'COMMIT_RESOLUTION' ||
                        dec.confirmed === true ||
                        String(dec.decision_type || '').toUpperCase().includes('COMMIT');
                      const isEsc =
                        dec.decision_type === 'ESCALATION_TO_TIER_3' ||
                        String(dec.decision_type || '').toUpperCase().includes('ESCALAT');

                      return (
                        <tr
                          key={idx}
                          style={{
                            borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                            transition: 'background 0.15s ease'
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)')}
                          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                        >
                          {/* 1. Ticket ID */}
                          <td style={{ padding: '16px 20px', verticalAlign: 'middle' }}>
                            <span className="mono-tag" style={{ color: '#38bdf8', fontWeight: 700, fontSize: '12px' }}>
                              INC-{String(dec.ticket_id).replace(/^INC-/i, '')}
                            </span>
                          </td>

                          {/* 2. Decision Badge */}
                          <td style={{ padding: '16px 20px', verticalAlign: 'middle' }}>
                            <span
                              style={{
                                fontSize: '11px',
                                fontWeight: 700,
                                padding: '4px 10px',
                                borderRadius: '12px',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '6px',
                                background: isCommit
                                  ? 'rgba(16, 185, 129, 0.15)'
                                  : isEsc
                                    ? 'rgba(239, 68, 68, 0.15)'
                                    : 'rgba(245, 158, 11, 0.15)',
                                color: isCommit ? '#34d399' : isEsc ? '#f87171' : '#fbbf24',
                                border: `1px solid ${
                                  isCommit
                                    ? 'rgba(16, 185, 129, 0.35)'
                                    : isEsc
                                      ? 'rgba(239, 68, 68, 0.35)'
                                      : 'rgba(245, 158, 11, 0.35)'
                                }`
                              }}
                            >
                              {isCommit && <CheckCircle2 size={12} />}
                              {isEsc && <PhoneForwarded size={12} />}
                              {!isCommit && !isEsc && <Activity size={12} />}
                              <span>
                                {isCommit
                                  ? 'COMMIT (YES)'
                                  : isEsc
                                    ? 'ESCALATION (3x NO)'
                                    : `REJECT (NO - Rank #${dec.selected_rank || 1})`}
                              </span>
                            </span>
                          </td>

                          {/* 3. Root Cause & Resolution */}
                          <td style={{ padding: '16px 20px', verticalAlign: 'middle', maxWidth: '450px' }}>
                            <div style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc', marginBottom: '2px' }}>
                              {dec.root_cause || dec.reason || 'Telemetry Diagnosis'}
                            </div>
                            {dec.resolution && (
                              <div style={{ fontSize: '11px', color: '#94a3b8', lineHeight: 1.4 }}>
                                <strong style={{ color: '#cbd5e1' }}>Resolution:</strong> {dec.resolution}
                              </div>
                            )}
                            {dec.commit_id && (
                              <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px', fontFamily: 'monospace' }}>
                                Commit Ref: {dec.commit_id}
                              </div>
                            )}
                          </td>

                          {/* 4. Operator */}
                          <td style={{ padding: '16px 20px', verticalAlign: 'middle' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <div
                                style={{
                                  width: '24px',
                                  height: '24px',
                                  borderRadius: '50%',
                                  background: 'rgba(56, 189, 248, 0.15)',
                                  color: '#38bdf8',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  fontSize: '11px',
                                  fontWeight: 700
                                }}
                              >
                                {(dec.operator || 'N').charAt(0).toUpperCase()}
                              </div>
                              <span style={{ fontSize: '12px', color: '#e2e8f0', fontWeight: 600 }}>
                                {dec.operator || 'NOC Operator'}
                              </span>
                            </div>
                          </td>

                          {/* 5. Timestamp */}
                          <td style={{ padding: '16px 20px', verticalAlign: 'middle', color: '#94a3b8', fontSize: '11px', whiteSpace: 'nowrap' }}>
                            {dec.timestamp}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ============================================================
            TAB 4: ESCALATION PROTOCOL (Tier-3 Pop-Up Modal)
        ============================================================ */}
        {activeTab === 'escalations' && (
          <div className="glass-panel" style={{ overflow: 'hidden' }}>
            <div
              style={{
                padding: '18px 20px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'rgba(239, 68, 68, 0.06)'
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: '16px',
                    fontWeight: 800,
                    color: '#f87171',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <PhoneForwarded size={18} />
                  <span>5. ESCALATION MANAGEMENT QUEUE (Tier-3 Senior Engineering)</span>
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                  Triggered when an operator rejects all 3 RCA candidates (3x NO). Click any ticket to open detailed pop-up.
                </div>
              </div>

              <span
                style={{
                  fontSize: '12px',
                  background: 'rgba(239, 68, 68, 0.2)',
                  border: '1px solid #ef4444',
                  color: '#fca5a5',
                  padding: '4px 10px',
                  borderRadius: '12px',
                  fontWeight: 700
                }}
              >
                {escalatedIncidents.length} Tickets Escalated
              </span>
            </div>

            {escalatedIncidents.length === 0 ? (
              <div style={{ padding: '60px', textAlign: 'center', color: '#64748b' }}>
                <CheckCircle2
                  size={40}
                  style={{ margin: '0 auto 12px', color: '#10b981', opacity: 0.6 }}
                />
                <div style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>
                  No Escalated Incidents
                </div>
                <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>
                  All network fault candidates were successfully resolved by operators or are currently undergoing active review.
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {escalatedIncidents.map((inc, idx) => (
                  <div
                    key={inc.id || idx}
                    onClick={() => handleOpenEscalationModal(inc)}
                    style={{
                      padding: '18px 20px',
                      borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                      display: 'grid',
                      gridTemplateColumns: '130px 1.4fr 160px 180px 160px',
                      alignItems: 'center',
                      gap: '16px',
                      cursor: 'pointer',
                      transition: 'background-color 0.15s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.08)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    <div>
                      <div className="mono-tag" style={{ color: '#f87171', fontWeight: 700 }}>
                        {inc.id}
                      </div>
                      <span
                        style={{
                          fontSize: '10px',
                          background: 'rgba(239, 68, 68, 0.2)',
                          color: '#fca5a5',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          marginTop: '4px',
                          display: 'inline-block'
                        }}
                      >
                        TIER-3 ESCALATED
                      </span>
                    </div>

                    <div>
                      <div style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc' }}>
                        {inc.title || `Escalation Alarm at ${inc.location}`}
                      </div>
                      <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                        Location: {inc.location} • Type: {inc.severity_type} • Resource:{' '}
                        {inc.resource_type}
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>ASSIGNED GROUP</div>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: '#e2e8f0' }}>
                        NOC_ENGINEERING_TEAM
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>STATUS & TIME</div>
                      <div style={{ fontSize: '12px', color: '#f87171', fontWeight: 600 }}>
                        FINISHED (ESCALATED)
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>{inc.created_at}</div>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <button
                        className="btn-primary"
                        style={{
                          padding: '7px 12px',
                          fontSize: '12px',
                          background: 'linear-gradient(135deg, #dc2626, #ef4444)',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenEscalationModal(inc);
                        }}
                      >
                        <Eye size={14} />
                        <span>Open Pop-Up</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ============================================================
          ADD OPERATOR MODAL (Direct to MongoDB)
      ============================================================ */}
      {showAddUserModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 110,
            padding: '20px'
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '460px',
              backgroundColor: '#0d111a',
              border: '1px solid rgba(168, 85, 247, 0.4)',
              borderRadius: '16px',
              boxShadow: '0 20px 50px rgba(0, 0, 0, 0.9), 0 0 35px rgba(168, 85, 247, 0.2)',
              overflow: 'hidden'
            }}
          >
            <div
              style={{
                padding: '18px 24px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <UserPlus size={20} color="#c084fc" />
                <span style={{ fontSize: '16px', fontWeight: 800, color: '#f8fafc' }}>
                  Register Operator in MongoDB
                </span>
              </div>
              <button
                onClick={() => setShowAddUserModal(false)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateUser} style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {addUserMsg && (
                <div
                  style={{
                    padding: '10px 14px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    background: addUserMsg.includes('success') ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                    color: addUserMsg.includes('success') ? '#34d399' : '#f87171',
                    border: `1px solid ${addUserMsg.includes('success') ? '#10b981' : '#ef4444'}`
                  }}
                >
                  {addUserMsg}
                </div>
              )}

              <div>
                <label style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Ramesh Chandra"
                  value={newUserData.name}
                  onChange={(e) => setNewUserData({ ...newUserData, name: e.target.value })}
                  style={{
                    width: '100%',
                    background: '#121824',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '6px',
                    padding: '9px 12px',
                    color: '#f8fafc',
                    fontSize: '13px'
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
                  Username / Email ID
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. ramesh@telecom-noc.com"
                  value={newUserData.username}
                  onChange={(e) => setNewUserData({ ...newUserData, username: e.target.value, email: e.target.value })}
                  style={{
                    width: '100%',
                    background: '#121824',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '6px',
                    padding: '9px 12px',
                    color: '#f8fafc',
                    fontSize: '13px'
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
                  Access Password (Will be Encrypted in MongoDB)
                </label>
                <input
                  type="password"
                  required
                  placeholder="••••••••••••"
                  value={newUserData.password}
                  onChange={(e) => setNewUserData({ ...newUserData, password: e.target.value })}
                  style={{
                    width: '100%',
                    background: '#121824',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '6px',
                    padding: '9px 12px',
                    color: '#f8fafc',
                    fontSize: '13px'
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
                    Role Assignment
                  </label>
                  <select
                    value={newUserData.role}
                    onChange={(e) => setNewUserData({ ...newUserData, role: e.target.value })}
                    style={{
                      width: '100%',
                      background: '#121824',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      borderRadius: '6px',
                      padding: '9px 12px',
                      color: '#f8fafc',
                      fontSize: '13px'
                    }}
                  >
                    <option value="operator">operator (NOC)</option>
                    <option value="admin">admin (Commander)</option>
                    <option value="field">field (Technician)</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
                    Department
                  </label>
                  <input
                    type="text"
                    value={newUserData.department}
                    onChange={(e) => setNewUserData({ ...newUserData, department: e.target.value })}
                    style={{
                      width: '100%',
                      background: '#121824',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      borderRadius: '6px',
                      padding: '9px 12px',
                      color: '#f8fafc',
                      fontSize: '13px'
                    }}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={addUserLoading}
                className="btn-primary"
                style={{
                  marginTop: '10px',
                  padding: '11px',
                  fontSize: '13px',
                  background: 'linear-gradient(135deg, #7c3aed, #9333ea)',
                  opacity: addUserLoading ? 0.7 : 1
                }}
              >
                {addUserLoading ? 'Encrypting & Saving to MongoDB...' : 'Save Operator to MongoDB'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================
          ESCALATION DETAIL POP-UP MODAL
      ============================================================ */}
      {selectedEscalation && selectedEscalation.incident && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.85)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '20px'
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '680px',
              backgroundColor: '#0d111a',
              border: '2px solid #ef4444',
              borderRadius: '16px',
              boxShadow: '0 25px 60px rgba(0, 0, 0, 0.9), 0 0 40px rgba(239, 68, 68, 0.3)',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                padding: '18px 24px',
                backgroundColor: 'rgba(239, 68, 68, 0.12)',
                borderBottom: '1px solid rgba(239, 68, 68, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '10px',
                    backgroundColor: '#dc2626',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#ffffff'
                  }}
                >
                  <PhoneForwarded size={20} />
                </div>
                <div>
                  <div
                    style={{
                      fontSize: '17px',
                      fontWeight: 800,
                      color: '#f87171',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    <span>
                      ESCALATION PROTOCOL TICKET #
                      {selectedEscalation.incident.ticket_id || selectedEscalation.incident.id}
                    </span>
                  </div>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                    Triggered by 3x NO Rejection on Automated RCA Console
                  </div>
                </div>
              </div>

              <button
                onClick={() => setSelectedEscalation(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer'
                }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div
              style={{
                padding: '24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px',
                maxHeight: '70vh',
                overflowY: 'auto'
              }}
            >
              {/* Alert Summary Box */}
              <div
                style={{
                  background: '#121824',
                  padding: '16px',
                  borderRadius: '10px',
                  border: '1px solid rgba(255, 255, 255, 0.08)'
                }}
              >
                <div
                  style={{
                    fontSize: '11px',
                    color: '#64748b',
                    fontWeight: 700,
                    textTransform: 'uppercase'
                  }}
                >
                  Incident Details
                </div>
                <div
                  style={{
                    fontSize: '15px',
                    fontWeight: 700,
                    color: '#f8fafc',
                    marginTop: '2px'
                  }}
                >
                  {selectedEscalation.incident.title ||
                    `Telecom Alert at ${selectedEscalation.incident.location}`}
                </div>
                <div
                  style={{
                    fontSize: '12px',
                    color: '#94a3b8',
                    marginTop: '4px',
                    display: 'flex',
                    gap: '12px'
                  }}
                >
                  <span>
                    Location: <strong>{selectedEscalation.incident.location}</strong>
                  </span>
                  <span>•</span>
                  <span>
                    Resource: <strong>{selectedEscalation.incident.resource_type}</strong>
                  </span>
                  <span>•</span>
                  <span>
                    ML Confidence:{' '}
                    <strong>{(selectedEscalation.incident.confidence * 100).toFixed(1)}%</strong>
                  </span>
                </div>
              </div>

              {/* Escalation Handoff Details */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div
                  style={{
                    background: '#121824',
                    padding: '14px',
                    borderRadius: '8px',
                    border: '1px solid rgba(239, 68, 68, 0.25)'
                  }}
                >
                  <div
                    style={{
                      fontSize: '11px',
                      color: '#f87171',
                      fontWeight: 700,
                      textTransform: 'uppercase'
                    }}
                  >
                    Assigned Escalation Group
                  </div>
                  <div
                    style={{
                      fontSize: '14px',
                      fontWeight: 800,
                      color: '#f8fafc',
                      marginTop: '3px'
                    }}
                  >
                    {selectedEscalation.decision?.assigned_group ||
                      'NOC_ENGINEERING_TEAM (Tier-3)'}
                  </div>
                </div>

                <div
                  style={{
                    background: '#121824',
                    padding: '14px',
                    borderRadius: '8px',
                    border: '1px solid rgba(239, 68, 68, 0.25)'
                  }}
                >
                  <div
                    style={{
                      fontSize: '11px',
                      color: '#f87171',
                      fontWeight: 700,
                      textTransform: 'uppercase'
                    }}
                  >
                    Escalation Reason
                  </div>
                  <div style={{ fontSize: '13px', color: '#fca5a5', marginTop: '3px' }}>
                    {selectedEscalation.decision?.reason ||
                      'All 3 automated RCA recommendations rejected by operator.'}
                  </div>
                </div>
              </div>

              {/* Evaluated and Rejected RCA Candidates */}
              <div
                style={{
                  background: '#121824',
                  padding: '16px',
                  borderRadius: '10px',
                  border: '1px solid rgba(255, 255, 255, 0.08)'
                }}
              >
                <div
                  style={{
                    fontSize: '11px',
                    color: '#64748b',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    marginBottom: '8px'
                  }}
                >
                  Evaluated & Rejected RCA Hypotheses (3x NO)
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {((selectedEscalation.incident?.agent_result?.ranked_causes && Array.isArray(selectedEscalation.incident.agent_result.ranked_causes))
                    ? selectedEscalation.incident.agent_result.ranked_causes.slice(0, 3)
                    : [
                      { rank: 1, root_cause: 'Radio Interface Hardware Degradation' },
                      { rank: 2, root_cause: 'Optical Link Transceiver Degradation' },
                      { rank: 3, root_cause: 'Backhaul Network Signal Loss' }
                    ]
                  ).map((cause: any, cIdx: number) => (
                    <div
                      key={cIdx}
                      style={{
                        padding: '10px 14px',
                        background: '#0a0e17',
                        borderRadius: '6px',
                        fontSize: '12px',
                        borderLeft: '3px solid #ef4444',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 700, color: '#f87171' }}>Option #{cause.rank || cIdx + 1}:</span>
                        <span style={{ color: '#f8fafc' }}>{cause.root_cause}</span>
                      </div>
                      <span style={{ color: '#f87171', fontWeight: 700, fontSize: '11px', background: 'rgba(239, 68, 68, 0.15)', padding: '2px 8px', borderRadius: '4px' }}>
                        REJECTED (NO)
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Status Note */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '12px',
                  color: '#f87171',
                  background: 'rgba(239, 68, 68, 0.1)',
                  padding: '10px 14px',
                  borderRadius: '8px'
                }}
              >
                <AlertTriangle size={16} />
                <span>
                  Ticket handoff committed to Tier-3 Senior Architects. Automatic pager notification dispatched.
                </span>
              </div>
            </div>

            {/* Modal Footer */}
            <div
              style={{
                padding: '16px 24px',
                backgroundColor: '#0a0e17',
                borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div style={{ fontSize: '11px', color: '#64748b' }}>
                Escalated by:{' '}
                <strong style={{ color: '#f8fafc' }}>
                  {selectedEscalation.decision?.operator || 'NOC Controller'}
                </strong>{' '}
                • {selectedEscalation.incident.created_at}
              </div>

              <button
                onClick={() => setSelectedEscalation(null)}
                className="btn-secondary"
                style={{ padding: '8px 18px', fontSize: '12px' }}
              >
                Close Pop-Up
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating NOC AI Chatbot Popup */}
      <AdminChatBot />
    </div>
  );
}
