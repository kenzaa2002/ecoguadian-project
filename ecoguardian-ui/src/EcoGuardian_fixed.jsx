import { useState, useEffect, useRef, useCallback } from "react";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts";

// ─── API ──────────────────────────────────────────────────────────────────────
const BASE = "http://localhost:8001/api";
const api = async (path, opts = {}) => {
  const token = localStorage.getItem("eco_token");
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
};

// ─── THEME ────────────────────────────────────────────────────────────────────
const G = {
  bg:       "#0a0f0d",
  bg2:      "#0f1710",
  card:     "#121a13",
  cardHov:  "#161f17",
  border:   "#1e2d20",
  border2:  "#243026",
  accent:   "#3ddc84",
  accent2:  "#2bb36a",
  accentDim:"#1a4a2e",
  warn:     "#f59e0b",
  danger:   "#ef4444",
  dangerDim:"#3d1515",
  warnDim:  "#3d2e0a",
  text:     "#e8f5eb",
  text2:    "#7a9e80",
  text3:    "#4a6b50",
  white:    "#ffffff",
};

const css = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@400;500;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }
  body { background: ${G.bg}; color: ${G.text}; font-family: 'DM Sans', sans-serif; min-height: 100vh; overflow-x: hidden; }
  ::-webkit-scrollbar { width: 4px; } ::-webkit-scrollbar-track { background: ${G.bg2}; } ::-webkit-scrollbar-thumb { background: ${G.border2}; border-radius: 2px; }
  ::selection { background: ${G.accentDim}; color: ${G.accent}; }

  .mono { font-family: 'DM Mono', monospace; }
  .syne { font-family: 'Syne', sans-serif; }

  /* ── Animations ── */
  @keyframes fadeUp   { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
  @keyframes fadeIn   { from { opacity:0; } to { opacity:1; } }
  @keyframes pulse    { 0%,100%{opacity:1} 50%{opacity:.4} }
  @keyframes spin     { to { transform:rotate(360deg); } }
  @keyframes shimmer  { 0%{background-position:-200% 0} 100%{background-position:200% 0} }
  @keyframes glow     { 0%,100%{box-shadow:0 0 8px ${G.accent}40} 50%{box-shadow:0 0 20px ${G.accent}80} }
  @keyframes slideIn  { from{transform:translateX(110%);opacity:0} to{transform:translateX(0);opacity:1} }
  @keyframes dotBlink { 0%,80%,100%{opacity:0} 40%{opacity:1} }

  .fade-up  { animation: fadeUp  .35s ease both; }
  .fade-in  { animation: fadeIn  .25s ease both; }
  .spin     { animation: spin    .8s linear infinite; }
  .pulse-dot{ animation: pulse 2s ease infinite; }

  /* ── Layout ── */
  .app-shell { display:flex; min-height:100vh; }
  .sidebar { width:220px; background:${G.bg2}; border-right:1px solid ${G.border}; display:flex; flex-direction:column; position:fixed; top:0; left:0; height:100vh; z-index:100; transition:transform .2s; }
  .main-content { margin-left:220px; flex:1; min-height:100vh; }

  /* ── Cards ── */
  .card { background:${G.card}; border:1px solid ${G.border}; border-radius:12px; }
  .card-hover { transition:border-color .2s, background .2s; cursor:pointer; }
  .card-hover:hover { border-color:${G.border2}; background:${G.cardHov}; }

  /* ── Buttons ── */
  .btn { display:inline-flex; align-items:center; gap:7px; padding:9px 18px; border-radius:8px; font-size:13px; font-weight:500; cursor:pointer; border:none; transition:all .15s; font-family:'DM Sans',sans-serif; }
  .btn-primary { background:${G.accent}; color:${G.bg}; }
  .btn-primary:hover { background:${G.accent2}; transform:translateY(-1px); box-shadow:0 4px 16px ${G.accent}40; }
  .btn-ghost { background:transparent; color:${G.text2}; border:1px solid ${G.border2}; }
  .btn-ghost:hover { border-color:${G.accent}40; color:${G.accent}; background:${G.accentDim}20; }
  .btn-danger { background:${G.dangerDim}; color:${G.danger}; border:1px solid ${G.danger}30; }
  .btn-danger:hover { background:${G.danger}20; }
  .btn:disabled { opacity:.4; cursor:not-allowed; transform:none; }

  /* ── Inputs ── */
  .input { width:100%; background:${G.bg2}; border:1px solid ${G.border2}; color:${G.text}; border-radius:8px; padding:10px 14px; font-size:13px; font-family:'DM Sans',sans-serif; outline:none; transition:border-color .2s; }
  .input:focus { border-color:${G.accent}60; box-shadow:0 0 0 3px ${G.accent}10; }
  .input::placeholder { color:${G.text3}; }
  .label { font-size:12px; color:${G.text2}; margin-bottom:6px; display:block; letter-spacing:.03em; }
  .input-group { margin-bottom:16px; }

  /* ── Badge ── */
  .badge { display:inline-flex; align-items:center; gap:4px; padding:2px 9px; border-radius:99px; font-size:11px; font-weight:500; font-family:'DM Mono',monospace; }
  .badge-green  { background:${G.accentDim}; color:${G.accent}; }
  .badge-warn   { background:${G.warnDim};   color:${G.warn}; }
  .badge-danger { background:${G.dangerDim}; color:${G.danger}; }
  .badge-muted  { background:${G.border};    color:${G.text3}; }

  /* ── Toast ── */
  .toast-wrap { position:fixed; top:20px; right:20px; z-index:9999; display:flex; flex-direction:column; gap:8px; }
  .toast { background:${G.card}; border:1px solid ${G.border2}; border-radius:10px; padding:12px 16px; min-width:280px; max-width:360px; animation:slideIn .3s ease; display:flex; align-items:flex-start; gap:10px; box-shadow:0 8px 32px #00000060; }
  .toast-success { border-left:3px solid ${G.accent}; }
  .toast-error   { border-left:3px solid ${G.danger}; }
  .toast-warn    { border-left:3px solid ${G.warn}; }

  /* ── Stat card ── */
  .stat-card { padding:20px; }
  .stat-val { font-family:'Syne',sans-serif; font-size:28px; font-weight:700; letter-spacing:-.02em; }
  .stat-label { font-size:11px; color:${G.text2}; margin-top:4px; text-transform:uppercase; letter-spacing:.08em; }
  .stat-delta { font-size:11px; font-family:'DM Mono',monospace; margin-top:8px; }

  /* ── Table ── */
  .tbl { width:100%; border-collapse:collapse; font-size:13px; }
  .tbl th { text-align:left; padding:10px 14px; color:${G.text3}; font-weight:500; font-size:11px; text-transform:uppercase; letter-spacing:.06em; border-bottom:1px solid ${G.border}; }
  .tbl td { padding:12px 14px; border-bottom:1px solid ${G.border}20; vertical-align:middle; }
  .tbl tr:last-child td { border-bottom:none; }
  .tbl tr:hover td { background:${G.bg2}40; }

  /* ── Skeleton ── */
  .skel { background:linear-gradient(90deg,${G.border} 25%,${G.border2} 50%,${G.border} 75%); background-size:200% 100%; animation:shimmer 1.4s infinite; border-radius:6px; }

  /* ── Sidebar nav ── */
  .nav-item { display:flex; align-items:center; gap:10px; padding:10px 16px; border-radius:8px; margin:1px 8px; cursor:pointer; color:${G.text2}; font-size:13px; font-weight:500; transition:all .15s; border:1px solid transparent; text-decoration:none; }
  .nav-item:hover { background:${G.accentDim}20; color:${G.accent}60; }
  .nav-item.active { background:${G.accentDim}; color:${G.accent}; border-color:${G.accent}20; }
  .nav-icon { width:16px; text-align:center; flex-shrink:0; }

  /* ── Scrollbar in chat ── */
  .chat-scroll::-webkit-scrollbar { width:3px; }
  .chat-scroll::-webkit-scrollbar-thumb { background:${G.border2}; }

  /* ── Dot loader ── */
  .dot { width:6px;height:6px;border-radius:50%;background:${G.accent};display:inline-block; }
  .dot:nth-child(1){animation:dotBlink 1.2s .0s infinite}
  .dot:nth-child(2){animation:dotBlink 1.2s .2s infinite}
  .dot:nth-child(3){animation:dotBlink 1.2s .4s infinite}

  /* ── Appliance grid ── */
  .appliance-btn { display:flex;flex-direction:column;align-items:center;gap:6px;padding:14px 8px;border-radius:10px;cursor:pointer;border:1px solid ${G.border2};background:${G.bg2};color:${G.text2};font-size:11px;font-weight:500;transition:all .15s;text-align:center; }
  .appliance-btn:hover { border-color:${G.accent}40;color:${G.accent}; }
  .appliance-btn.selected { border-color:${G.accent};background:${G.accentDim};color:${G.accent}; }

  /* ── Progress bar ── */
  .progress-bar { height:4px;background:${G.border};border-radius:2px;overflow:hidden; }
  .progress-fill { height:100%;background:${G.accent};border-radius:2px;transition:width .4s ease; }

  /* ── Divider ── */
  .divider { border:none;border-top:1px solid ${G.border};margin:16px 0; }

  /* ── Responsive ── */
  @media(max-width:768px){
    .sidebar{transform:translateX(-100%);}
    .sidebar.open{transform:translateX(0);}
    .main-content{margin-left:0;}
  }
`;

// ─── ICONS ────────────────────────────────────────────────────────────────────
const Icon = ({ name, size = 16, color }) => {
  const icons = {
    home:      "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
    zap:       "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
    chart:     "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
    bell:      "M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9",
    house:     "M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z M9 22V12h6v10",
    chat:      "M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z",
    clock:     "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
    alert:     "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
    check:     "M5 13l4 4L19 7",
    x:         "M6 18L18 6M6 6l12 12",
    plus:      "M12 4v16m8-8H4",
    trash:     "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16",
    send:      "M12 19l9 2-9-18-9 18 9-2zm0 0v-8",
    logout:    "M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1",
    eye:       "M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z",
    user:      "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z",
    menu:      "M4 6h16M4 12h16M4 18h16",
    drop:      "M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0016.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 002 8.5c0 2.3 1.5 4.05 3 5.5l7 7 7-7z",
    leaf:      "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z",
    refresh:   "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15",
    download:  "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4",
    arrow:     "M5 12h14M12 5l7 7-7 7",
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color || "currentColor"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {(icons[name] || "").split(" M").map((d, i) => (
        <path key={i} d={i === 0 ? d : "M" + d} />
      ))}
    </svg>
  );
};

// ─── TOAST SYSTEM ─────────────────────────────────────────────────────────────
let _addToast = () => {};
const toast = {
  success: (msg) => _addToast({ type: "success", msg }),
  error:   (msg) => _addToast({ type: "error",   msg }),
  warn:    (msg) => _addToast({ type: "warn",     msg }),
};

function ToastManager() {
  const [toasts, setToasts] = useState([]);
  _addToast = useCallback((t) => {
    const id = Date.now();
    setToasts(p => [...p, { ...t, id }]);
    setTimeout(() => setToasts(p => p.filter(x => x.id !== id)), 4000);
  }, []);
  return (
    <div className="toast-wrap">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          <span style={{ color: t.type === "success" ? G.accent : t.type === "error" ? G.danger : G.warn, marginTop: 1 }}>
            <Icon name={t.type === "success" ? "check" : t.type === "error" ? "x" : "alert"} size={14} />
          </span>
          <span style={{ fontSize: 13, lineHeight: 1.4 }}>{t.msg}</span>
        </div>
      ))}
    </div>
  );
}

// ─── AUTH CONTEXT ─────────────────────────────────────────────────────────────
function useAuth() {
  const [user, setUser]   = useState(() => JSON.parse(localStorage.getItem("eco_user") || "null"));
  const [token, setToken] = useState(() => localStorage.getItem("eco_token") || "");

  const login = (tokenStr, userData) => {
    localStorage.setItem("eco_token", tokenStr);
    localStorage.setItem("eco_user",  JSON.stringify(userData));
    setToken(tokenStr); setUser(userData);
  };
  const logout = () => {
    localStorage.removeItem("eco_token"); localStorage.removeItem("eco_user");
    setToken(""); setUser(null);
  };
  return { user, token, login, logout, isAuth: !!token };
}

// ─── AUTH PAGE ────────────────────────────────────────────────────────────────
function AuthPage({ onLogin }) {
  const [mode, setMode]   = useState("login");
  const [form, setForm]   = useState({ email: "", password: "", username: "", full_name: "" });
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }));

  const submit = async () => {
    setLoading(true);
    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const body = mode === "login"
        ? { email: form.email, password: form.password }
        : { email: form.email, password: form.password, username: form.username, full_name: form.full_name };
      const data = await api(path, { method: "POST", body: JSON.stringify(body) });
      onLogin(data.access_token, data.user);
      toast.success(`Welcome${data.user.full_name ? ", " + data.user.full_name.split(" ")[0] : ""}!`);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: G.bg, position: "relative", overflow: "hidden" }}>
      {/* Background glow */}
      <div style={{ position: "absolute", width: 600, height: 600, borderRadius: "50%", background: `radial-gradient(circle, ${G.accentDim}60 0%, transparent 70%)`, top: "50%", left: "50%", transform: "translate(-50%,-50%)", pointerEvents: "none" }} />

      <div className="card fade-up" style={{ width: 400, padding: 40, position: "relative", zIndex: 1 }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 32 }}>
          <div style={{ width: 36, height: 36, background: G.accentDim, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", animation: "glow 3s ease infinite" }}>
            <Icon name="zap" size={18} color={G.accent} />
          </div>
          <span className="syne" style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-.02em" }}>EcoGuardian</span>
        </div>

        <h1 className="syne" style={{ fontSize: 24, fontWeight: 700, marginBottom: 6 }}>
          {mode === "login" ? "Welcome back" : "Create account"}
        </h1>
        <p style={{ fontSize: 13, color: G.text2, marginBottom: 28 }}>
          {mode === "login" ? "Sign in to your energy dashboard" : "Start monitoring your energy consumption"}
        </p>

        {mode === "register" && (
          <>
            <div className="input-group">
              <label className="label">Full name</label>
              <input className="input" placeholder="Ahmed Ben Ali" value={form.full_name} onChange={set("full_name")} />
            </div>
            <div className="input-group">
              <label className="label">Username</label>
              <input className="input" placeholder="ahmed" value={form.username} onChange={set("username")} />
            </div>
          </>
        )}
        <div className="input-group">
          <label className="label">Email</label>
          <input className="input" type="email" placeholder="you@example.com" value={form.email} onChange={set("email")} onKeyDown={e => e.key === "Enter" && submit()} />
        </div>
        <div className="input-group" style={{ marginBottom: 24 }}>
          <label className="label">Password</label>
          <input className="input" type="password" placeholder="••••••••" value={form.password} onChange={set("password")} onKeyDown={e => e.key === "Enter" && submit()} />
        </div>

        <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center", padding: "12px 0" }} onClick={submit} disabled={loading}>
          {loading ? <><span className="spin" style={{ display: "inline-block", width: 14, height: 14, border: `2px solid ${G.bg}40`, borderTopColor: G.bg, borderRadius: "50%" }} /></> : mode === "login" ? "Sign in" : "Create account"}
        </button>

        <p style={{ textAlign: "center", marginTop: 20, fontSize: 13, color: G.text2 }}>
          {mode === "login" ? "Don't have an account? " : "Already have an account? "}
          <span style={{ color: G.accent, cursor: "pointer" }} onClick={() => setMode(mode === "login" ? "register" : "login")}>
            {mode === "login" ? "Register" : "Sign in"}
          </span>
        </p>
      </div>
    </div>
  );
}

// ─── SIDEBAR ──────────────────────────────────────────────────────────────────
function Sidebar({ page, setPage, user, logout, unread }) {
  const nav = [
    { id: "overview",      icon: "home",    label: "Overview"    },
    { id: "predict",       icon: "zap",     label: "Predict"     },
    { id: "weekly",        icon: "chart",   label: "Weekly"      },
    { id: "history",       icon: "clock",   label: "History"     },
    { id: "houses",        icon: "house",   label: "My Houses"   },
    { id: "notifications", icon: "bell",    label: "Alerts",  badge: unread },
    { id: "chatbot",       icon: "chat",    label: "EcoBot"      },
  ];
  return (
    <div className="sidebar">
      {/* Logo */}
      <div style={{ padding: "20px 16px", borderBottom: `1px solid ${G.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 30, height: 30, background: G.accentDim, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon name="zap" size={14} color={G.accent} />
          </div>
          <span className="syne" style={{ fontSize: 15, fontWeight: 700 }}>EcoGuardian</span>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, paddingTop: 8 }}>
        {nav.map(n => (
          <div key={n.id} className={`nav-item ${page === n.id ? "active" : ""}`} onClick={() => setPage(n.id)}>
            <span className="nav-icon"><Icon name={n.icon} size={15} /></span>
            <span style={{ flex: 1 }}>{n.label}</span>
            {n.badge > 0 && <span style={{ background: G.danger, color: G.white, borderRadius: 99, fontSize: 10, padding: "1px 6px", fontFamily: "DM Mono" }}>{n.badge}</span>}
          </div>
        ))}
      </nav>

      {/* User */}
      <div style={{ padding: "12px 16px", borderTop: `1px solid ${G.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: G.accentDim, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon name="user" size={13} color={G.accent} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user?.username}</div>
            <div style={{ fontSize: 10, color: G.text3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user?.email}</div>
          </div>
        </div>
        <button className="btn btn-ghost" style={{ width: "100%", justifyContent: "center", fontSize: 12, padding: "7px 0" }} onClick={logout}>
          <Icon name="logout" size={13} /> Sign out
        </button>
      </div>
    </div>
  );
}

// ─── STAT CARD ────────────────────────────────────────────────────────────────
function StatCard({ label, value, unit, delta, icon, color, loading }) {
  return (
    <div className="card stat-card fade-up">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <span style={{ fontSize: 11, color: G.text3, textTransform: "uppercase", letterSpacing: ".08em", fontWeight: 500 }}>{label}</span>
        <div style={{ color: color || G.accent, opacity: .7 }}><Icon name={icon} size={15} /></div>
      </div>
      {loading ? <div className="skel" style={{ height: 28, width: "60%", marginBottom: 8 }} /> : (
        <div className="stat-val" style={{ color: color || G.text }}>{value}<span style={{ fontSize: 14, fontWeight: 400, color: G.text2, marginLeft: 4 }}>{unit}</span></div>
      )}
      {delta !== undefined && !loading && (
        <div className="stat-delta" style={{ color: delta >= 0 ? G.danger : G.accent }}>
          {delta >= 0 ? "↑" : "↓"} {Math.abs(delta)}% vs last period
        </div>
      )}
    </div>
  );
}

// ─── OVERVIEW PAGE ────────────────────────────────────────────────────────────
function OverviewPage({ dashboards }) {
  const [stats, setStats]   = useState(null);
  const [history, setHistory] = useState([]);
  const [weekly, setWeekly] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [hist, wk] = await Promise.all([
          api("/history?limit=10"),
          api("/weekly/stats").catch(() => null),
        ]);
        setHistory(hist);
        setWeekly(wk);

        if (hist.length) {
          const avg = hist.reduce((s, h) => s + h.avg_monthly_kwh, 0) / hist.length;
          const totalCost = hist.reduce((s, h) => s + h.month1_cost, 0);
          setStats({ avg: avg.toFixed(1), cost: totalCost.toFixed(2), count: hist.length });
        }
      } catch (e) {
        toast.error("Failed to load overview");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const chartData = history.slice(0, 8).reverse().map((h, i) => ({
    name: `P${i + 1}`, kwh: h.avg_monthly_kwh, cost: h.month1_cost,
    appliance: h.appliance_label,
  }));

  return (
    <div style={{ padding: "28px 32px" }}>
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <h1 className="syne" style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-.02em", marginBottom: 4 }}>Overview</h1>
        <p style={{ color: G.text2, fontSize: 13 }}>{dashboards.length} house{dashboards.length !== 1 ? "s" : ""} monitored · Energy at a glance</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 }}>
        <StatCard label="Avg Monthly"  value={stats?.avg   || "—"} unit="kWh"  icon="zap"   loading={loading} />
        <StatCard label="Total Cost"   value={stats?.cost  || "—"} unit="TND"  icon="drop"  loading={loading} color={G.warn} />
        <StatCard label="Predictions"  value={stats?.count || "—"} unit="runs" icon="chart"  loading={loading} />
        <StatCard label="Anomalies"    value={weekly?.anomaly_count ?? "—"} unit="weeks" icon="alert" loading={loading} color={weekly?.anomaly_count > 0 ? G.danger : G.accent} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 16, marginBottom: 16 }}>
        {/* Consumption chart */}
        <div className="card fade-up" style={{ padding: 20 }}>
          <div style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Prediction History</h3>
            <span className="badge badge-muted">avg kWh/month</span>
          </div>
          {loading ? <div className="skel" style={{ height: 180 }} /> : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="kwh" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={G.accent} stopOpacity={0.15} />
                    <stop offset="95%" stopColor={G.accent} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={G.border} />
                <XAxis dataKey="name" tick={{ fill: G.text3, fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: G.text3, fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: G.card, border: `1px solid ${G.border2}`, borderRadius: 8, fontSize: 12 }} />
                <Area type="monotone" dataKey="kwh" stroke={G.accent} strokeWidth={2} fill="url(#kwh)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : <EmptyState icon="chart" text="No predictions yet" sub="Run your first prediction" />}
        </div>

        {/* Weekly anomaly summary */}
        <div className="card fade-up" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Weekly Summary</h3>
          {loading ? (
            [0,1,2,3].map(i => <div key={i} className="skel" style={{ height: 20, marginBottom: 10 }} />)
          ) : weekly && weekly.total_weeks > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[
                { label: "Total weeks tracked",   val: weekly.total_weeks },
                { label: "Avg weekly consumption", val: `${weekly.avg_weekly_kwh} kWh` },
                { label: "Anomaly rate",           val: `${weekly.anomaly_rate_pct}%`, color: weekly.anomaly_rate_pct > 15 ? G.danger : G.accent },
                { label: "High anomalies",         val: weekly.high_anomalies,  color: G.danger },
                { label: "Low anomalies",          val: weekly.low_anomalies,   color: G.warn },
                { label: "Last week",              val: `${weekly.last_week_kwh} kWh`, color: weekly.last_week_anomaly ? G.danger : G.accent },
              ].map(r => (
                <div key={r.label} style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                  <span style={{ color: G.text2 }}>{r.label}</span>
                  <span className="mono" style={{ color: r.color || G.text, fontWeight: 500 }}>{r.val}</span>
                </div>
              ))}
              <div className="progress-bar" style={{ marginTop: 4 }}>
                <div className="progress-fill" style={{ width: `${Math.min(weekly.anomaly_rate_pct * 3, 100)}%`, background: weekly.anomaly_rate_pct > 15 ? G.danger : G.accent }} />
              </div>
            </div>
          ) : <EmptyState icon="chart" text="No weekly data" sub="Submit your first weekly reading" />}
        </div>
      </div>

      {/* Houses */}
      {dashboards.length > 0 && (
        <div className="card fade-up" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Your Houses</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 10 }}>
            {dashboards.map(d => (
              <div key={d.id} className="card" style={{ padding: 14, borderColor: G.border2 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <div style={{ width: 28, height: 28, background: G.accentDim, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Icon name="house" size={13} color={G.accent} />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.name}</div>
                    <div style={{ fontSize: 11, color: G.text3 }}>{d.household_size} {d.household_size === 1 ? "person" : "people"}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── EMPTY STATE ─────────────────────────────────────────────────────────────
function EmptyState({ icon, text, sub }) {
  return (
    <div style={{ textAlign: "center", padding: "32px 16px" }}>
      <div style={{ color: G.text3, marginBottom: 8 }}><Icon name={icon} size={28} /></div>
      <div style={{ fontSize: 14, fontWeight: 500, color: G.text2 }}>{text}</div>
      {sub && <div style={{ fontSize: 12, color: G.text3, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

// ─── PREDICT PAGE ─────────────────────────────────────────────────────────────
const APPLIANCES = [
  { key: "Appliance_Type_HVAC",                    label: "HVAC",       icon: "❄️" },
  { key: "Appliance_Type_Water_Heater",             label: "Water Htr",  icon: "🚿" },
  { key: "Appliance_Type_Washing_Machine",          label: "Washer",     icon: "🌀" },
  { key: "Appliance_Type_Dryer",                    label: "Dryer",      icon: "♨️" },
  { key: "Appliance_Type_Fridge",                   label: "Fridge",     icon: "🧊" },
  { key: "Appliance_Type_Dishwasher",               label: "Dishwasher", icon: "🍽️" },
  { key: "Appliance_Type_Oven",                     label: "Oven",       icon: "🔥" },
  { key: "Appliance_Type_Microwave",                label: "Microwave",  icon: "📡" },
  { key: "Appliance_Type_TV",                       label: "TV",         icon: "📺" },
  { key: "Appliance_Type_Lighting",                 label: "Lighting",   icon: "💡" },
  { key: "Appliance_Type_Electric_Vehicle_Charger", label: "EV Charger", icon: "⚡" },
];

function PredictPage({ dashboards }) {
  const defaultForm = {
    dashboard_id: null, Household_Size: 4, Weather_Temperature: 25,
    DayOfWeek: 1, Is_Weekend: 0, Is_Cold_Season: 0, Is_Hot_Season: 1,
    Occupancy_Pattern_Evening: 0, Occupancy_Pattern_Mixed: 0,
    ...Object.fromEntries(APPLIANCES.map(a => [a.key, 0])),
  };
  const [form, setForm]       = useState(defaultForm);
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [selAppliance, setSelAppliance] = useState(null);

  const setField = (k, v) => setForm(p => ({ ...p, [k]: v }));
  const selectAppliance = (key) => {
    const reset = Object.fromEntries(APPLIANCES.map(a => [a.key, 0]));
    setForm(p => ({ ...p, ...reset, [key]: 1 }));
    setSelAppliance(key);
    const isHVAC = key === "Appliance_Type_HVAC";
    setField("Is_HVAC", isHVAC ? 1 : 0);
  };

  const submit = async () => {
    if (!selAppliance) return toast.warn("Please select an appliance");
    setLoading(true); setResult(null);
    try {
      const data = await api("/predictions", { method: "POST", body: JSON.stringify(form) });
      setResult(data);
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  };

  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <div style={{ padding: "28px 32px" }}>
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <h1 className="syne" style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-.02em", marginBottom: 4 }}>Energy Prediction</h1>
        <p style={{ color: G.text2, fontSize: 13 }}>Get a 3-month AI-powered forecast for your household</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: result ? "1fr 1fr" : "1fr", gap: 20 }}>
        {/* Form */}
        <div className="card fade-up" style={{ padding: 24 }}>
          {/* House */}
          {dashboards.length > 0 && (
            <div className="input-group">
              <label className="label">House (optional)</label>
              <select className="input" value={form.dashboard_id || ""} onChange={e => setField("dashboard_id", e.target.value ? +e.target.value : null)}>
                <option value="">No specific house</option>
                {dashboards.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div className="input-group">
              <label className="label">Household size</label>
              <input className="input" type="number" min={1} max={20} value={form.Household_Size} onChange={e => setField("Household_Size", +e.target.value)} />
            </div>
            <div className="input-group">
              <label className="label">Temperature (°C)</label>
              <input className="input" type="number" step="0.5" value={form.Weather_Temperature} onChange={e => setField("Weather_Temperature", +e.target.value)} />
            </div>
          </div>

          <div className="input-group">
            <label className="label">Day of week</label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 6 }}>
              {days.map((d, i) => (
                <button key={i} className={`btn ${form.DayOfWeek === i ? "btn-primary" : "btn-ghost"}`} style={{ padding: "7px 4px", fontSize: 11, justifyContent: "center" }}
                  onClick={() => { setField("DayOfWeek", i); setField("Is_Weekend", i >= 5 ? 1 : 0); }}>
                  {d}
                </button>
              ))}
            </div>
          </div>

          <div className="input-group">
            <label className="label">Season</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              {[["🌡️ Hot", 1, 0], ["❄️ Cold", 0, 1], ["🌤️ Neutral", 0, 0]].map(([l, hot, cold]) => (
                <button key={l} className={`btn ${form.Is_Hot_Season === hot && form.Is_Cold_Season === cold ? "btn-primary" : "btn-ghost"}`}
                  style={{ justifyContent: "center", fontSize: 12 }}
                  onClick={() => { setField("Is_Hot_Season", hot); setField("Is_Cold_Season", cold); }}>
                  {l}
                </button>
              ))}
            </div>
          </div>

          <div className="input-group">
            <label className="label">Occupancy pattern</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              {[["🌅 Morning", 0, 0], ["🌆 Evening", 1, 0], ["🔄 Mixed", 0, 1]].map(([l, ev, mx]) => (
                <button key={l} className={`btn ${form.Occupancy_Pattern_Evening === ev && form.Occupancy_Pattern_Mixed === mx ? "btn-primary" : "btn-ghost"}`}
                  style={{ justifyContent: "center", fontSize: 12 }}
                  onClick={() => { setField("Occupancy_Pattern_Evening", ev); setField("Occupancy_Pattern_Mixed", mx); }}>
                  {l}
                </button>
              ))}
            </div>
          </div>

          <div className="input-group" style={{ marginBottom: 0 }}>
            <label className="label">Primary appliance</label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
              {APPLIANCES.map(a => (
                <button key={a.key} className={`appliance-btn ${selAppliance === a.key ? "selected" : ""}`} onClick={() => selectAppliance(a.key)}>
                  <span style={{ fontSize: 20 }}>{a.icon}</span>
                  <span>{a.label}</span>
                </button>
              ))}
            </div>
          </div>

          <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center", marginTop: 20, padding: "13px 0", fontSize: 14 }} onClick={submit} disabled={loading}>
            {loading ? <><span className="spin" style={{ display: "inline-block", width: 14, height: 14, border: `2px solid ${G.bg}40`, borderTopColor: G.bg, borderRadius: "50%" }} /> Predicting…</> : <><Icon name="zap" size={14} /> Generate Forecast</>}
          </button>
        </div>

        {/* Results */}
        {result && (
          <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Forecast bars */}
            <div className="card" style={{ padding: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600 }}>3-Month Forecast</h3>
                <span className="badge badge-green">{result.appliance_label}</span>
              </div>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={result.forecasts}>
                  <CartesianGrid strokeDasharray="3 3" stroke={G.border} />
                  <XAxis dataKey="label" tick={{ fill: G.text3, fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: G.text3, fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: G.card, border: `1px solid ${G.border2}`, borderRadius: 8, fontSize: 12 }} formatter={(v) => [`${v.toFixed(1)} kWh`]} />
                  <Bar dataKey="kwh" fill={G.accent} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, marginTop: 12 }}>
                {result.forecasts.map(f => (
                  <div key={f.month} style={{ background: G.bg2, borderRadius: 8, padding: 10, textAlign: "center" }}>
                    <div className="mono" style={{ fontSize: 11, color: G.text3, marginBottom: 3 }}>{f.label}</div>
                    <div className="syne" style={{ fontSize: 18, fontWeight: 700, color: G.accent }}>{f.kwh.toFixed(0)}</div>
                    <div style={{ fontSize: 10, color: G.text3 }}>kWh</div>
                    <div className="mono" style={{ fontSize: 11, color: G.warn, marginTop: 3 }}>{f.cost_tnd.toFixed(2)} TND</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Summary */}
            <div className="card" style={{ padding: 16, display: "flex", gap: 12 }}>
              {[
                { l: "Avg/month", v: `${result.avg_monthly_kwh.toFixed(1)} kWh` },
                { l: "Peak",      v: `${result.peak_kwh.toFixed(1)} kWh` },
                { l: "Total cost", v: `${result.total_cost_tnd.toFixed(2)} TND`, c: G.warn },
              ].map(s => (
                <div key={s.l} style={{ flex: 1, textAlign: "center", padding: "8px 0" }}>
                  <div style={{ fontSize: 11, color: G.text3, marginBottom: 4 }}>{s.l}</div>
                  <div className="mono" style={{ fontSize: 15, fontWeight: 500, color: s.c || G.text }}>{s.v}</div>
                </div>
              ))}
            </div>

            {/* Recommendations */}
            <div className="card" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Recommendations</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {result.recommendations.map((r, i) => (
                  <div key={i} style={{ background: G.bg2, borderRadius: 8, padding: "10px 12px", fontSize: 12, color: G.text2, lineHeight: 1.5, borderLeft: `2px solid ${G.accent}40` }}>
                    {r}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── WEEKLY PAGE ──────────────────────────────────────────────────────────────
function WeeklyPage({ dashboards }) {
  const [records, setRecords] = useState([]);
  const [stats, setStats]     = useState(null);
  const [form, setForm]       = useState({ weekly_kwh: "", household_size: 4, avg_temperature: "", is_hot_season: 0, is_cold_season: 0, is_hvac_week: 0, dashboard_id: null });
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [recs, st] = await Promise.all([api("/weekly?limit=20"), api("/weekly/stats").catch(() => null)]);
      setRecords(recs.items || []);
      setStats(st);
    } catch (e) { toast.error("Failed to load weekly data"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    if (!form.weekly_kwh || +form.weekly_kwh <= 0) return toast.warn("Enter a valid kWh value");
    setSubmitting(true);
    try {
      await api("/weekly", { method: "POST", body: JSON.stringify({ ...form, weekly_kwh: +form.weekly_kwh, avg_temperature: form.avg_temperature ? +form.avg_temperature : null }) });
      toast.success("Weekly reading submitted!");
      setForm(p => ({ ...p, weekly_kwh: "", avg_temperature: "" }));
      load();
    } catch (e) { toast.error(e.message); }
    finally { setSubmitting(false); }
  };

  const del = async (id) => {
    try { await api(`/weekly/${id}`, { method: "DELETE" }); load(); toast.success("Deleted"); }
    catch (e) { toast.error(e.message); }
  };

  const chartData = [...records].reverse().map(r => ({
    week: `W${r.week_number}`, kwh: r.weekly_kwh, mean: r.rolling_mean, anomaly: r.is_anomaly,
  }));

  return (
    <div style={{ padding: "28px 32px" }}>
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <h1 className="syne" style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-.02em", marginBottom: 4 }}>Weekly Consumption</h1>
        <p style={{ color: G.text2, fontSize: 13 }}>Submit your weekly readings — anomalies are detected automatically</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 20, alignItems: "start" }}>
        {/* Submit form */}
        <div className="card fade-up" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Submit This Week</h3>

          {dashboards.length > 0 && (
            <div className="input-group">
              <label className="label">House</label>
              <select className="input" value={form.dashboard_id || ""} onChange={e => setForm(p => ({ ...p, dashboard_id: e.target.value ? +e.target.value : null }))}>
                <option value="">No specific house</option>
                {dashboards.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
          )}
          <div className="input-group">
            <label className="label">Weekly consumption (kWh) *</label>
            <input className="input" type="number" step="0.1" placeholder="e.g. 280.5" value={form.weekly_kwh} onChange={e => setForm(p => ({ ...p, weekly_kwh: e.target.value }))} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div className="input-group">
              <label className="label">Household size</label>
              <input className="input" type="number" min={1} max={50} value={form.household_size} onChange={e => setForm(p => ({ ...p, household_size: +e.target.value }))} />
            </div>
            <div className="input-group">
              <label className="label">Avg temp °C</label>
              <input className="input" type="number" step="0.5" placeholder="optional" value={form.avg_temperature} onChange={e => setForm(p => ({ ...p, avg_temperature: e.target.value }))} />
            </div>
          </div>
          <div className="input-group">
            <label className="label">Season</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6 }}>
              {[["🌡️ Hot", 1, 0], ["❄️ Cold", 0, 1], ["🌤️ Neutral", 0, 0]].map(([l, hot, cold]) => (
                <button key={l} className={`btn ${form.is_hot_season === hot && form.is_cold_season === cold ? "btn-primary" : "btn-ghost"}`}
                  style={{ justifyContent: "center", fontSize: 11 }}
                  onClick={() => setForm(p => ({ ...p, is_hot_season: hot, is_cold_season: cold }))}>
                  {l}
                </button>
              ))}
            </div>
          </div>
          <div className="input-group" style={{ marginBottom: 20 }}>
            <label className="label">HVAC in use this week?</label>
            <div style={{ display: "flex", gap: 8 }}>
              {[["Yes", 1], ["No", 0]].map(([l, v]) => (
                <button key={l} className={`btn ${form.is_hvac_week === v ? "btn-primary" : "btn-ghost"}`} style={{ flex: 1, justifyContent: "center" }}
                  onClick={() => setForm(p => ({ ...p, is_hvac_week: v }))}>
                  {l}
                </button>
              ))}
            </div>
          </div>
          <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center", padding: "12px 0" }} onClick={submit} disabled={submitting}>
            {submitting ? "Submitting…" : <><Icon name="plus" size={14} /> Submit Reading</>}
          </button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Stats row */}
          {stats && stats.total_weeks > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
              {[
                { l: "Weeks",        v: stats.total_weeks,         u: "weeks" },
                { l: "Avg weekly",   v: stats.avg_weekly_kwh,      u: "kWh" },
                { l: "Anomaly rate", v: stats.anomaly_rate_pct,    u: "%", c: stats.anomaly_rate_pct > 15 ? G.danger : G.accent },
                { l: "Last week",    v: stats.last_week_kwh,       u: "kWh", c: stats.last_week_anomaly ? G.danger : G.accent },
              ].map(s => (
                <div key={s.l} className="card stat-card fade-up">
                  <div style={{ fontSize: 11, color: G.text3, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 8 }}>{s.l}</div>
                  <div className="syne" style={{ fontSize: 22, fontWeight: 700, color: s.c || G.text }}>{s.v}<span style={{ fontSize: 12, color: G.text2, marginLeft: 3 }}>{s.u}</span></div>
                </div>
              ))}
            </div>
          )}

          {/* Chart */}
          {chartData.length > 1 && (
            <div className="card fade-up" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Consumption vs Rolling Mean</h3>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={G.border} />
                  <XAxis dataKey="week" tick={{ fill: G.text3, fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: G.text3, fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: G.card, border: `1px solid ${G.border2}`, borderRadius: 8, fontSize: 12 }} />
                  <Line type="monotone" dataKey="kwh"  stroke={G.accent} strokeWidth={2} dot={(p) => p.payload.anomaly ? <circle key={p.key} cx={p.cx} cy={p.cy} r={5} fill={G.danger} stroke={G.danger} /> : <circle key={p.key} cx={p.cx} cy={p.cy} r={3} fill={G.accent} />} />
                  <Line type="monotone" dataKey="mean" stroke={G.text3} strokeWidth={1} strokeDasharray="4 4" dot={false} />
                </LineChart>
              </ResponsiveContainer>
              <div style={{ display: "flex", gap: 16, marginTop: 10, fontSize: 11 }}>
                <span style={{ color: G.accent }}>— Actual kWh</span>
                <span style={{ color: G.text3 }}>--- Rolling mean</span>
                <span style={{ color: G.danger }}>● Anomaly</span>
              </div>
            </div>
          )}

          {/* Table */}
          <div className="card fade-up">
            <div style={{ padding: "16px 20px", borderBottom: `1px solid ${G.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: 14, fontWeight: 600 }}>History</h3>
              <span className="badge badge-muted">{records.length} weeks</span>
            </div>
            {loading ? (
              <div style={{ padding: 20 }}>{[0,1,2,3].map(i => <div key={i} className="skel" style={{ height: 36, marginBottom: 8 }} />)}</div>
            ) : records.length === 0 ? <EmptyState icon="chart" text="No weekly data yet" sub="Submit your first reading above" /> : (
              <div style={{ overflowX: "auto" }}>
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Week</th><th>kWh</th><th>Status</th><th>Z-score</th><th>Rolling mean</th><th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map(r => (
                      <tr key={r.id}>
                        <td><span className="mono" style={{ fontSize: 12 }}>W{r.week_number}/{r.year}</span></td>
                        <td><span className="mono" style={{ color: G.accent }}>{r.weekly_kwh.toFixed(1)}</span></td>
                        <td>
                          {r.is_anomaly ? (
                            <span className={`badge ${r.anomaly_type === "high" ? "badge-danger" : "badge-warn"}`}>
                              {r.anomaly_type === "high" ? "⚡ High" : "📉 Low"}
                            </span>
                          ) : <span className="badge badge-green">✓ Normal</span>}
                        </td>
                        <td><span className="mono" style={{ fontSize: 12, color: Math.abs(r.z_score) > 2 ? G.danger : G.text2 }}>{r.z_score?.toFixed(2)}</span></td>
                        <td><span className="mono" style={{ fontSize: 12, color: G.text2 }}>{r.rolling_mean?.toFixed(1) || "—"}</span></td>
                        <td>
                          <button className="btn btn-danger" style={{ padding: "4px 8px", fontSize: 11 }} onClick={() => del(r.id)}>
                            <Icon name="trash" size={11} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── HISTORY PAGE ─────────────────────────────────────────────────────────────
function HistoryPage({ dashboards }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter]   = useState("");

  useEffect(() => {
    (async () => {
      setLoading(true);
      try { setRecords(await api("/history?limit=50")); }
      catch (e) { toast.error(e.message); }
      finally { setLoading(false); }
    })();
  }, []);

  const filtered = records.filter(r =>
    !filter || r.appliance_label?.toLowerCase().includes(filter.toLowerCase()) ||
    (r.dashboard_name || "").toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div style={{ padding: "28px 32px" }}>
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <h1 className="syne" style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-.02em", marginBottom: 4 }}>Prediction History</h1>
        <p style={{ color: G.text2, fontSize: 13 }}>All your past 3-month energy forecasts</p>
      </div>

      <div className="card fade-up">
        <div style={{ padding: "16px 20px", borderBottom: `1px solid ${G.border}`, display: "flex", gap: 12, alignItems: "center" }}>
          <input className="input" style={{ maxWidth: 240 }} placeholder="Filter by appliance or house…" value={filter} onChange={e => setFilter(e.target.value)} />
          <span className="badge badge-muted">{filtered.length} records</span>
        </div>
        {loading ? (
          <div style={{ padding: 20 }}>{[0,1,2,3,4].map(i => <div key={i} className="skel" style={{ height: 40, marginBottom: 8 }} />)}</div>
        ) : filtered.length === 0 ? <EmptyState icon="clock" text="No predictions yet" sub="Run a prediction from the Predict tab" /> : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl">
              <thead>
                <tr><th>Date</th><th>Appliance</th><th>House</th><th>Avg kWh/mo</th><th>Peak kWh</th><th>Month 1 cost</th></tr>
              </thead>
              <tbody>
                {filtered.map(r => (
                  <tr key={r.id}>
                    <td><span className="mono" style={{ fontSize: 11, color: G.text2 }}>{new Date(r.created_at).toLocaleDateString()}</span></td>
                    <td><span className="badge badge-green">{r.appliance_label}</span></td>
                    <td><span style={{ fontSize: 12, color: G.text2 }}>{r.dashboard_name || "—"}</span></td>
                    <td><span className="mono" style={{ color: G.accent }}>{r.avg_monthly_kwh?.toFixed(1)}</span></td>
                    <td><span className="mono" style={{ color: G.text2 }}>{r.peak_kwh?.toFixed(1)}</span></td>
                    <td><span className="mono" style={{ color: G.warn }}>{r.month1_cost?.toFixed(2)} TND</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── HOUSES PAGE ─────────────────────────────────────────────────────────────
function HousesPage({ dashboards, reload }) {
  const [form, setForm]       = useState({ name: "", address: "", household_size: 2 });
  const [adding, setAdding]   = useState(false);
  const [loading, setLoading] = useState(false);

  const create = async () => {
    if (!form.name.trim()) return toast.warn("Please enter a house name");
    setLoading(true);
    try {
      await api("/dashboards", { method: "POST", body: JSON.stringify(form) });
      toast.success("House created!");
      setForm({ name: "", address: "", household_size: 2 });
      setAdding(false);
      reload();
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  };

  const del = async (id) => {
    try { await api(`/dashboards/${id}`, { method: "DELETE" }); reload(); toast.success("House deleted"); }
    catch (e) { toast.error(e.message); }
  };

  return (
    <div style={{ padding: "28px 32px" }}>
      <div className="fade-up" style={{ marginBottom: 28, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 className="syne" style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-.02em", marginBottom: 4 }}>My Houses</h1>
          <p style={{ color: G.text2, fontSize: 13 }}>Each house is a separate dashboard with its own predictions</p>
        </div>
        <button className="btn btn-primary" onClick={() => setAdding(p => !p)}>
          <Icon name="plus" size={14} /> Add House
        </button>
      </div>

      {adding && (
        <div className="card fade-up" style={{ padding: 20, marginBottom: 20, maxWidth: 480 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>New House</h3>
          <div className="input-group"><label className="label">Name *</label><input className="input" placeholder="e.g. Maison Tunis" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} /></div>
          <div className="input-group"><label className="label">Address</label><input className="input" placeholder="optional" value={form.address} onChange={e => setForm(p => ({ ...p, address: e.target.value }))} /></div>
          <div className="input-group"><label className="label">Household size</label><input className="input" type="number" min={1} max={50} value={form.household_size} onChange={e => setForm(p => ({ ...p, household_size: +e.target.value }))} /></div>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn btn-primary" onClick={create} disabled={loading}>{loading ? "Creating…" : "Create"}</button>
            <button className="btn btn-ghost" onClick={() => setAdding(false)}>Cancel</button>
          </div>
        </div>
      )}

      {dashboards.length === 0 ? (
        <EmptyState icon="house" text="No houses yet" sub="Add your first house to get started" />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
          {dashboards.map((d, i) => (
            <div key={d.id} className="card card-hover fade-up" style={{ padding: 20, animationDelay: `${i * 60}ms` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                <div style={{ width: 40, height: 40, background: G.accentDim, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Icon name="house" size={18} color={G.accent} />
                </div>
                <button className="btn btn-danger" style={{ padding: "5px 8px", fontSize: 11 }} onClick={() => del(d.id)}>
                  <Icon name="trash" size={12} />
                </button>
              </div>
              <h3 className="syne" style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{d.name}</h3>
              {d.address && <p style={{ fontSize: 12, color: G.text3, marginBottom: 8 }}>{d.address}</p>}
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <span className="badge badge-green">{d.household_size} {d.household_size === 1 ? "person" : "people"}</span>
                <span className="badge badge-muted">Since {new Date(d.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── NOTIFICATIONS PAGE ───────────────────────────────────────────────────────
function NotificationsPage({ onRead }) {
  const [data, setData]       = useState({ items: [], total: 0, unread: 0 });
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await api("/notifications?limit=40")); }
    catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const markRead = async (id) => {
    try { await api(`/notifications/${id}/read`, { method: "PATCH" }); load(); onRead(); }
    catch (e) { toast.error(e.message); }
  };

  const markAll = async () => {
    try { await api("/notifications/read-all", { method: "PATCH" }); load(); onRead(); toast.success("All marked as read"); }
    catch (e) { toast.error(e.message); }
  };

  const del = async (id) => {
    try { await api(`/notifications/${id}`, { method: "DELETE" }); load(); }
    catch (e) { toast.error(e.message); }
  };

  const levelColor = (l) => l === "critical" ? G.danger : l === "warning" ? G.warn : G.accent;
  const levelBadge = (l) => l === "critical" ? "badge-danger" : l === "warning" ? "badge-warn" : "badge-green";

  return (
    <div style={{ padding: "28px 32px" }}>
      <div className="fade-up" style={{ marginBottom: 28, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 className="syne" style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-.02em", marginBottom: 4 }}>Alerts</h1>
          <p style={{ color: G.text2, fontSize: 13 }}>Anomaly notifications and system alerts</p>
        </div>
        {data.unread > 0 && (
          <button className="btn btn-ghost" onClick={markAll}><Icon name="check" size={13} /> Mark all read</button>
        )}
      </div>

      {data.unread > 0 && (
        <div className="card fade-up" style={{ padding: 14, marginBottom: 16, borderColor: G.danger + "40", background: G.dangerDim + "30", display: "flex", gap: 10, alignItems: "center" }}>
          <Icon name="bell" size={15} color={G.danger} />
          <span style={{ fontSize: 13, color: G.text }}><strong style={{ color: G.danger }}>{data.unread} unread</strong> alert{data.unread !== 1 ? "s" : ""}</span>
        </div>
      )}

      <div className="card fade-up">
        {loading ? (
          <div style={{ padding: 20 }}>{[0,1,2,3].map(i => <div key={i} className="skel" style={{ height: 60, marginBottom: 10 }} />)}</div>
        ) : data.items.length === 0 ? <EmptyState icon="bell" text="No alerts" sub="Anomaly alerts will appear here when detected" /> : (
          <div>
            {data.items.map((n, i) => (
              <div key={n.id} style={{ padding: "16px 20px", borderBottom: i < data.items.length - 1 ? `1px solid ${G.border}20` : "none", display: "flex", gap: 14, alignItems: "flex-start", opacity: n.is_read ? .6 : 1, transition: "opacity .2s" }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: levelColor(n.level) + "20", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 2 }}>
                  <Icon name={n.level === "critical" ? "zap" : "alert"} size={14} color={levelColor(n.level)} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>{n.title}</span>
                    <span className={`badge ${levelBadge(n.level)}`}>{n.level}</span>
                    {!n.is_read && <span style={{ width: 6, height: 6, borderRadius: "50%", background: G.danger, display: "inline-block" }} />}
                  </div>
                  <p style={{ fontSize: 12, color: G.text2, lineHeight: 1.5 }}>{n.message}</p>
                  <span className="mono" style={{ fontSize: 10, color: G.text3 }}>{new Date(n.created_at).toLocaleString()}</span>
                </div>
                <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                  {!n.is_read && (
                    <button className="btn btn-ghost" style={{ padding: "4px 8px", fontSize: 11 }} onClick={() => markRead(n.id)}>
                      <Icon name="eye" size={11} />
                    </button>
                  )}
                  <button className="btn btn-danger" style={{ padding: "4px 8px", fontSize: 11 }} onClick={() => del(n.id)}>
                    <Icon name="trash" size={11} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── CHATBOT PAGE ─────────────────────────────────────────────────────────────
function ChatbotPage({ dashboards }) {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi! I'm EcoBot 🌿 — your energy efficiency assistant. Ask me anything about reducing consumption, understanding your bills, solar energy, or appliance efficiency." }
  ]);
  const [input, setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const [dashId, setDashId]  = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    const userMsg = { role: "user", content: text };
    setMessages(p => [...p, userMsg]);
    setInput(""); setLoading(true);
    try {
      const history = [...messages.slice(-8), userMsg].filter(m => m.role !== "assistant" || messages.indexOf(m) > 0);
      const data = await api("/chatbot", { method: "POST", body: JSON.stringify({ messages: history, dashboard_id: dashId }) });
      setMessages(p => [...p, { role: "assistant", content: data.reply }]);
    } catch (e) {
      setMessages(p => [...p, { role: "assistant", content: "Sorry, I couldn't connect right now. Please try again." }]);
    } finally { setLoading(false); }
  };

  const SUGGESTIONS = [
    "How can I reduce my HVAC bill?",
    "Is solar worth it in Tunisia?",
    "What uses the most electricity at home?",
    "How do I read my electricity meter?",
  ];

  return (
    <div style={{ padding: "28px 32px", height: "calc(100vh - 0px)", display: "flex", flexDirection: "column" }}>
      <div className="fade-up" style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 className="syne" style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-.02em", marginBottom: 4 }}>EcoBot</h1>
          <p style={{ color: G.text2, fontSize: 13 }}>AI energy efficiency assistant</p>
        </div>
        {dashboards.length > 0 && (
          <select className="input" style={{ maxWidth: 180 }} value={dashId || ""} onChange={e => setDashId(e.target.value ? +e.target.value : null)}>
            <option value="">No house context</option>
            {dashboards.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        )}
      </div>

      <div className="card fade-up" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, overflow: "hidden" }}>
        {/* Messages */}
        <div ref={scrollRef} className="chat-scroll" style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
          {messages.map((m, i) => (
            <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start", gap: 10, animation: "fadeUp .2s ease" }}>
              {m.role === "assistant" && (
                <div style={{ width: 28, height: 28, borderRadius: 8, background: G.accentDim, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 2 }}>
                  <Icon name="zap" size={12} color={G.accent} />
                </div>
              )}
              <div style={{
                maxWidth: "72%", padding: "10px 14px", borderRadius: m.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                background: m.role === "user" ? G.accent : G.bg2,
                color: m.role === "user" ? G.bg : G.text,
                fontSize: 13, lineHeight: 1.6,
                border: m.role === "assistant" ? `1px solid ${G.border2}` : "none",
              }}>
                {m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <div style={{ width: 28, height: 28, borderRadius: 8, background: G.accentDim, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <Icon name="zap" size={12} color={G.accent} />
              </div>
              <div style={{ background: G.bg2, border: `1px solid ${G.border2}`, padding: "12px 16px", borderRadius: "12px 12px 12px 2px", display: "flex", gap: 4, alignItems: "center" }}>
                <span className="dot" /><span className="dot" /><span className="dot" />
              </div>
            </div>
          )}
        </div>

        {/* Suggestions */}
        {messages.length === 1 && (
          <div style={{ padding: "0 20px 12px", display: "flex", flexWrap: "wrap", gap: 6 }}>
            {SUGGESTIONS.map(s => (
              <button key={s} className="btn btn-ghost" style={{ fontSize: 11, padding: "5px 10px" }} onClick={() => { setInput(s); }}>
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div style={{ padding: "12px 16px", borderTop: `1px solid ${G.border}`, display: "flex", gap: 10 }}>
          <input className="input" placeholder="Ask about energy saving…" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()} style={{ flex: 1 }} />
          <button className="btn btn-primary" onClick={send} disabled={loading || !input.trim()} style={{ padding: "10px 14px" }}>
            <Icon name="send" size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── TOP BAR ──────────────────────────────────────────────────────────────────
function TopBar({ page, unread, setPage }) {
  const titles = { overview: "Overview", predict: "Predict", weekly: "Weekly", history: "History", houses: "Houses", notifications: "Alerts", chatbot: "EcoBot" };
  return (
    <div style={{ height: 56, background: G.bg2, borderBottom: `1px solid ${G.border}`, display: "flex", alignItems: "center", padding: "0 32px", justifyContent: "space-between", position: "sticky", top: 0, zIndex: 50 }}>
      <h2 className="syne" style={{ fontSize: 15, fontWeight: 600 }}>{titles[page] || page}</h2>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <button className="btn btn-ghost" style={{ padding: "6px 10px", position: "relative" }} onClick={() => setPage("notifications")}>
          <Icon name="bell" size={15} />
          {unread > 0 && <span style={{ position: "absolute", top: 4, right: 4, width: 8, height: 8, background: G.danger, borderRadius: "50%", animation: "pulse 2s infinite" }} />}
        </button>
      </div>
    </div>
  );
}

// ─── APP SHELL ────────────────────────────────────────────────────────────────
function App() {
  const { user, token, login, logout, isAuth } = useAuth();
  const [page, setPage]           = useState("overview");
  const [dashboards, setDashboards] = useState([]);
  const [unread, setUnread]       = useState(0);

  const loadDashboards = useCallback(async () => {
    try { setDashboards(await api("/dashboards")); }
    catch {}
  }, []);

  const loadUnread = useCallback(async () => {
    try { const d = await api("/notifications/unread"); setUnread(d.unread || 0); }
    catch {}
  }, []);

  useEffect(() => {
    if (isAuth) {
      loadDashboards();
      loadUnread();
      const t = setInterval(loadUnread, 30000);
      return () => clearInterval(t);
    }
  }, [isAuth, loadDashboards, loadUnread]);

  if (!isAuth) return <><style>{css}</style><ToastManager /><AuthPage onLogin={login} /></>;

  const pages = {
    overview:      <OverviewPage dashboards={dashboards} />,
    predict:       <PredictPage  dashboards={dashboards} />,
    weekly:        <WeeklyPage   dashboards={dashboards} />,
    history:       <HistoryPage  dashboards={dashboards} />,
    houses:        <HousesPage   dashboards={dashboards} reload={loadDashboards} />,
    notifications: <NotificationsPage onRead={loadUnread} />,
    chatbot:       <ChatbotPage  dashboards={dashboards} />,
  };

  return (
    <>
      <style>{css}</style>
      <ToastManager />
      <div className="app-shell">
        <Sidebar page={page} setPage={setPage} user={user} logout={logout} unread={unread} />
        <div className="main-content">
          <TopBar page={page} unread={unread} setPage={setPage} />
          {pages[page] || null}
        </div>
      </div>
    </>
  );
}

export default App;
