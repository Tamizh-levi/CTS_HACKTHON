import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Radio, 
  ShieldCheck, 
  Zap, 
  Activity, 
  Lock, 
  User, 
  ArrowRight, 
  CheckCircle2, 
  AlertTriangle,
  Server,
  Cpu
} from 'lucide-react';
import API_BASE_URL from '../services/api';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('ganesh@gmail.com');
  const [password, setPassword] = useState('ganesh123');
  const [selectedRole, setSelectedRole] = useState<'operator' | 'admin' | 'field'>('operator');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [serverOnline, setServerOnline] = useState<boolean | null>(null);

  // Check backend server status on mount
  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((res) => {
        if (res.ok) setServerOnline(true);
        else setServerOnline(false);
      })
      .catch(() => setServerOnline(false));
  }, []);

  const handleLogin = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsLoading(true);
    setErrorMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role: selectedRole }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        const token = data.token || `token_telecom_${Date.now()}`;
        const userData = data.user || {
          username: username || 'operator',
          name: username === 'admin' ? 'System Administrator' : 'Senior NOC Controller',
          role: selectedRole,
          department: selectedRole === 'admin' ? 'Central Core Ops' : 'Tier-2 NOC Console',
        };

        localStorage.setItem('authToken', token);
        localStorage.setItem('user', JSON.stringify(userData));

        // Intelligently route Admin users to /admin-dashboard and Operators to /noc-dashboard
        const isAdminUser =
          userData.role === 'admin' ||
          selectedRole === 'admin' ||
          username.toLowerCase().includes('admin') ||
          username.toLowerCase() === 'sakthi@gmail.com' ||
          username.toLowerCase() === 'tamilzh@gmail.com';

        if (isAdminUser) {
          navigate('/admin-dashboard');
        } else {
          navigate('/noc-dashboard');
        }
      } else {
        setErrorMessage(data.message || 'Invalid credentials. Please verify your username and password.');
      }
    } catch (err: any) {
      setErrorMessage(`Cannot connect to authentication service: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickPersona = (persona: 'operator' | 'admin' | 'field') => {
    setSelectedRole(persona);
    if (persona === 'operator') {
      setUsername('ganesh@gmail.com');
      setPassword('ganesh123');
    } else if (persona === 'admin') {
      setUsername('sakthi@gmail.com');
      setPassword('sakthi123');
    } else {
      setUsername('field_tech');
      setPassword('field123');
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      width: '100%',
      backgroundColor: '#07090e',
      backgroundImage: `
        radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.12), transparent 45%),
        radial-gradient(circle at 100% 100%, rgba(99, 102, 241, 0.08), transparent 40%),
        linear-gradient(to bottom, rgba(7,9,14,0.8), rgba(7,9,14,0.95))
      `,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background Cyber Grid */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundImage: `
          linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
          linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px)
        `,
        backgroundSize: '48px 48px',
        pointerEvents: 'none',
        maskImage: 'radial-gradient(ellipse at center, black 40%, transparent 80%)'
      }} />

      {/* Top Header Bar */}
      <header style={{
        padding: '24px 36px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'relative',
        zIndex: 10,
        borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #0284c7, #6366f1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(56, 189, 248, 0.4)'
          }}>
            <Radio size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ fontSize: '18px', fontWeight: 800, letterSpacing: '-0.02em', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              TELECOM AGENTIC NOC <span style={{ fontSize: '11px', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '2px 8px', borderRadius: '20px', fontWeight: 600 }}>v3.7 AI</span>
            </div>
            <div style={{ fontSize: '12px', color: '#64748b' }}>Autonomous Root Cause Analysis & Field Dispatch</div>
          </div>
        </div>

        {/* Server & DB Status Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            
            background: 'rgba(15, 23, 42, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            padding: '6px 14px',
            borderRadius: '30px',
            fontSize: '12px',
            color: '#94a3b8'
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: serverOnline !== false ? '#10b981' : '#f59e0b',
              boxShadow: serverOnline !== false ? '0 0 10px #10b981' : '0 0 10px #f59e0b'
            }} />
            <span>Backend Engine: {serverOnline === true ? 'Online (8000)' : serverOnline === false ? 'Connecting...' : 'Checking...'}</span>
          </div>
        </div>
      </header>

      {/* Main Login Card Area */}
      <main style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '32px 20px',
        position: 'relative',
        zIndex: 10
      }}>
        <div style={{
          width: '100%',
          maxWidth: '480px',
          background: 'rgba(13, 17, 26, 0.85)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRadius: '18px',
          border: '1px solid rgba(56, 189, 248, 0.2)',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.7), 0 0 35px rgba(56, 189, 248, 0.08)',
          padding: '36px 32px'
        }}>
          {/* Card Header */}
          <div style={{ textAlign: 'center', marginBottom: '28px' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '54px',
              height: '54px',
              borderRadius: '14px',
              background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.15), rgba(99, 102, 241, 0.15))',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              marginBottom: '16px',
              color: '#38bdf8'
            }}>
              <ShieldCheck size={28} />
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc', marginBottom: '6px' }}>
              NOC Security Gateway
            </h1>
            <p style={{ fontSize: '13px', color: '#94a3b8' }}>
              Log in to access live telemetry stream, RAG RCA diagnosis, and autonomous field dispatch.
            </p>
          </div>

          {/* Quick Role Selection Buttons */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '8px' }}>
              Quick Demo Persona (1-Click)
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
              <button
                type="button"
                onClick={() => handleQuickPersona('operator')}
                style={{
                  background: selectedRole === 'operator' ? 'rgba(56, 189, 248, 0.15)' : 'rgba(30, 41, 59, 0.4)',
                  border: `1px solid ${selectedRole === 'operator' ? '#38bdf8' : 'rgba(255, 255, 255, 0.06)'}`,
                  color: selectedRole === 'operator' ? '#38bdf8' : '#94a3b8',
                  padding: '8px 6px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                NOC Operator
              </button>
              <button
                type="button"
                onClick={() => handleQuickPersona('admin')}
                style={{
                  background: selectedRole === 'admin' ? 'rgba(168, 85, 247, 0.15)' : 'rgba(30, 41, 59, 0.4)',
                  border: `1px solid ${selectedRole === 'admin' ? '#a855f7' : 'rgba(255, 255, 255, 0.06)'}`,
                  color: selectedRole === 'admin' ? '#c084fc' : '#94a3b8',
                  padding: '8px 6px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                System Admin
              </button>
              {/* <button
                type="button"
                onClick={() => handleQuickPersona('field')}
                style={{
                  background: selectedRole === 'field' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(30, 41, 59, 0.4)',
                  border: `1px solid ${selectedRole === 'field' ? '#10b981' : 'rgba(255, 255, 255, 0.06)'}`,
                  color: selectedRole === 'field' ? '#34d399' : '#94a3b8',
                  padding: '8px 6px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                Field Ops
              </button> */}
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            {errorMessage && (
              <div style={{
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#f87171',
                padding: '10px 14px',
                borderRadius: '8px',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <AlertTriangle size={16} />
                <span>{errorMessage}</span>
              </div>
            )}

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: '6px' }}>
                Operator ID / Username
              </label>
              <div style={{ position: 'relative' }}>
                <User size={16} color="#64748b" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. noc_operator or admin"
                  required
                  style={{
                    width: '100%',
                    backgroundColor: '#121824',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '8px',
                    padding: '11px 14px 11px 40px',
                    color: '#f8fafc',
                    fontSize: '14px',
                    outline: 'none',
                    transition: 'border-color 0.2s ease',
                  }}
                />
              </div>
            </div>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: '6px' }}>
                Access Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock size={16} color="#64748b" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  style={{
                    width: '100%',
                    backgroundColor: '#121824',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '8px',
                    padding: '11px 14px 11px 40px',
                    color: '#f8fafc',
                    fontSize: '14px',
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary"
              style={{
                width: '100%',
                padding: '13px',
                fontSize: '15px',
                marginTop: '6px',
                opacity: isLoading ? 0.7 : 1
              }}
            >
              {isLoading ? (
                <>
                  <Activity size={18} className="spin-slow" />
                  <span>Authenticating Agent Gateway...</span>
                </>
              ) : (
                <>
                  <span>
                    {selectedRole === 'admin' || username.toLowerCase().includes('admin') || username.toLowerCase() === 'sakthi@gmail.com' || username.toLowerCase() === 'tamilzh@gmail.com'
                      ? 'Enter Admin Console'
                      : 'Enter NOC Command Console'}
                  </span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          {/* Quick Stats Badges */}
          <div style={{
            marginTop: '24px',
            paddingTop: '18px',
            borderTop: '1px solid rgba(255, 255, 255, 0.06)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '11px',
            color: '#64748b'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Cpu size={13} color="#38bdf8" />
              <span>XGBoost Classifier</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Server size={13} color="#a855f7" />
              <span>ChromaDB Vector RAG</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Zap size={13} color="#10b981" />
              <span>Auto Dispatch</span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer Info */}
      <footer style={{
        padding: '16px 36px',
        textAlign: 'center',
        fontSize: '12px',
        color: '#475569',
        borderTop: '1px solid rgba(255, 255, 255, 0.04)',
        position: 'relative',
        zIndex: 10
      }}>
        Telecom Autonomous Incident Resolution & Multi-Agent Network Fault Management
      </footer>
    </div>
  );
}
