import { useState, useEffect, createContext, useContext } from "react";
import { createClient } from "@supabase/supabase-js";

// ── Config ────────────────────────────────────────────────────────────────────
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// ── Auth Context ──────────────────────────────────────────────────────────────
const AuthContext = createContext(null);

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setUser(session.user);
        setToken(session.access_token);
        fetchProfile(session.access_token);
      }
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        setUser(session.user);
        setToken(session.access_token);
        fetchProfile(session.access_token);
      } else {
        setUser(null);
        setProfile(null);
        setToken(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchProfile = async (accessToken) => {
    try {
      const res = await fetch(`${API_URL}/api/auth/me`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setProfile(data.user);
      }
    } catch (e) { console.error("Profile fetch error:", e); }
  };

  const signUp = async (email, password, fullName) => {
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
    if (data.session) {
      await fetch(`${API_URL}/api/auth/register-profile`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${data.session.access_token}`
        },
        body: JSON.stringify({ email, full_name: fullName })
      });
    }
    return data;
  };

  const signIn = async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    return data;
  };

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  const apiCall = async (endpoint, options = {}) => {
    const res = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...options.headers
      }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(err.detail || "Request failed");
    }
    return res.json();
  };

  return (
    <AuthContext.Provider value={{ user, profile, loading, token, signUp, signIn, signOut, apiCall, fetchProfile: () => fetchProfile(token) }}>
      {children}
    </AuthContext.Provider>
  );
}

const useAuth = () => useContext(AuthContext);

// ── Design System ─────────────────────────────────────────────────────────────
const colors = {
  bg: "#0A0C10",
  surface: "#111318",
  card: "#161B22",
  border: "#21262D",
  borderHover: "#30363D",
  accent: "#00D4FF",
  accentDim: "#00D4FF22",
  gold: "#FFB800",
  goldDim: "#FFB80022",
  green: "#00E676",
  greenDim: "#00E67622",
  red: "#FF3D71",
  redDim: "#FF3D7122",
  orange: "#FF9500",
  text: "#E6EDF3",
  textMuted: "#8B949E",
  textDim: "#484F58"
};

const styles = {
  btn: {
    primary: {
      background: `linear-gradient(135deg, ${colors.accent}, #0099BB)`,
      color: "#000",
      border: "none",
      borderRadius: "8px",
      padding: "12px 24px",
      fontWeight: "700",
      cursor: "pointer",
      fontSize: "14px",
      letterSpacing: "0.5px",
      fontFamily: "'Space Mono', monospace"
    },
    ghost: {
      background: "transparent",
      color: colors.accent,
      border: `1px solid ${colors.accent}`,
      borderRadius: "8px",
      padding: "11px 23px",
      fontWeight: "600",
      cursor: "pointer",
      fontSize: "14px",
      fontFamily: "'Space Mono', monospace"
    },
    danger: {
      background: colors.redDim,
      color: colors.red,
      border: `1px solid ${colors.red}44`,
      borderRadius: "8px",
      padding: "8px 16px",
      fontWeight: "600",
      cursor: "pointer",
      fontSize: "13px",
      fontFamily: "'Space Mono', monospace"
    }
  },
  card: {
    background: colors.card,
    border: `1px solid ${colors.border}`,
    borderRadius: "12px",
    padding: "20px"
  },
  input: {
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderRadius: "8px",
    padding: "12px 16px",
    color: colors.text,
    fontSize: "14px",
    width: "100%",
    outline: "none",
    fontFamily: "'Space Mono', monospace",
    boxSizing: "border-box"
  }
};

// ── Bias Badge ────────────────────────────────────────────────────────────────
function BiasBadge({ bias }) {
  const config = {
    BULLISH: { color: colors.green, bg: colors.greenDim, label: "▲ BULLISH" },
    BEARISH: { color: colors.red, bg: colors.redDim, label: "▼ BEARISH" },
    RANGING: { color: colors.orange, bg: "#FF950022", label: "◆ RANGING" },
    UNAVAILABLE: { color: colors.textMuted, bg: colors.border, label: "— N/A" },
    UNDECIDED: { color: colors.gold, bg: colors.goldDim, label: "⚡ UNDECIDED" }
  };
  const c = config[bias] || config.UNAVAILABLE;
  return (
    <span style={{
      background: c.bg, color: c.color,
      padding: "3px 10px", borderRadius: "20px",
      fontSize: "11px", fontWeight: "700",
      fontFamily: "'Space Mono', monospace",
      border: `1px solid ${c.color}33`
    }}>
      {c.label}
    </span>
  );
}

// ── Landing Page ──────────────────────────────────────────────────────────────
function Landing({ onNav }) {
  return (
    <div style={{ minHeight: "100vh", background: colors.bg, color: colors.text, fontFamily: "'Space Mono', monospace" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: ${colors.bg}; }
        .hero-glow { position: absolute; top: -200px; left: 50%; transform: translateX(-50%); width: 600px; height: 600px; background: radial-gradient(circle, ${colors.accent}15 0%, transparent 70%); pointer-events: none; }
      `}</style>

      {/* Nav */}
      <nav style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "20px 48px", borderBottom: `1px solid ${colors.border}` }}>
        <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "800", fontSize: "22px", color: colors.accent }}>
          SMC<span style={{ color: colors.text }}> LENS</span>
        </div>
        <div style={{ display: "flex", gap: "12px" }}>
          <button style={styles.btn.ghost} onClick={() => onNav("login")}>LOGIN</button>
          <button style={styles.btn.primary} onClick={() => onNav("signup")}>START FREE</button>
        </div>
      </nav>

      {/* Hero */}
      <div style={{ position: "relative", textAlign: "center", padding: "100px 24px 80px", overflow: "hidden" }}>
        <div className="hero-glow" />
        <div style={{ fontSize: "12px", color: colors.accent, letterSpacing: "4px", marginBottom: "24px", fontWeight: "700" }}>
          SMC / ICT METHODOLOGY
        </div>
        <h1 style={{ fontFamily: "'Syne', sans-serif", fontSize: "clamp(40px, 8vw, 80px)", fontWeight: "800", lineHeight: "1.1", marginBottom: "24px" }}>
          See The Market<br />
          <span style={{ color: colors.accent }}>Through Smart Money.</span>
        </h1>
        <p style={{ fontSize: "16px", color: colors.textMuted, maxWidth: "560px", margin: "0 auto 40px", lineHeight: "1.7" }}>
          Real-time Order Block and FVG detection, top-down multi-timeframe analysis, and AI-powered trade narratives. Built on actual price data — zero guesswork.
        </p>
        <button style={{ ...styles.btn.primary, fontSize: "16px", padding: "16px 40px" }} onClick={() => onNav("signup")}>
          START 30-DAY FREE TRIAL
        </button>
        <div style={{ marginTop: "16px", color: colors.textMuted, fontSize: "12px" }}>
          No credit card required · $10/month after trial
        </div>
      </div>

      {/* Features */}
      <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "60px 24px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px" }}>
          {[
            { icon: "📊", title: "Top-Down Analysis", desc: "Monthly → Weekly → Daily → 4H → Entry. HTF bias determines every trade.", badge: "PRO" },
            { icon: "🎯", title: "Order Block Detection", desc: "Mathematically identified, unmitigated OBs with 50% entry levels.", badge: null },
            { icon: "⚡", title: "Fair Value Gaps", desc: "FVG detection across all timeframes. Only unmitigated gaps shown.", badge: null },
            { icon: "🧠", title: "AI Narrative", desc: "Groq AI writes the trade summary from real data. Never guesses.", badge: null },
            { icon: "🛡️", title: "Confluence Scoring", desc: "Score out of 13. Minimum 8 to show a signal. No low-quality setups.", badge: null },
            { icon: "📐", title: "Auto Entry/SL/TP", desc: "Entry at zone 50%. SL below OB with pip distance enforcement. Minimum 1:2 RR.", badge: null }
          ].map((f, i) => (
            <div key={i} style={{ ...styles.card, position: "relative" }}>
              {f.badge && (
                <span style={{ position: "absolute", top: "16px", right: "16px", background: colors.goldDim, color: colors.gold, padding: "2px 8px", borderRadius: "4px", fontSize: "10px", fontWeight: "700", border: `1px solid ${colors.gold}44` }}>
                  {f.badge}
                </span>
              )}
              <div style={{ fontSize: "28px", marginBottom: "12px" }}>{f.icon}</div>
              <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "700", fontSize: "16px", marginBottom: "8px" }}>{f.title}</div>
              <div style={{ color: colors.textMuted, fontSize: "13px", lineHeight: "1.6" }}>{f.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Pricing */}
      <div style={{ maxWidth: "500px", margin: "0 auto 80px", padding: "0 24px", textAlign: "center" }}>
        <div style={{ ...styles.card, border: `1px solid ${colors.accent}44` }}>
          <div style={{ color: colors.accent, fontSize: "12px", letterSpacing: "3px", marginBottom: "16px", fontWeight: "700" }}>PRICING</div>
          <div style={{ fontFamily: "'Syne', sans-serif", fontSize: "48px", fontWeight: "800", color: colors.accent }}>$10<span style={{ fontSize: "18px", color: colors.textMuted }}>/month</span></div>
          <div style={{ color: colors.textMuted, marginBottom: "24px" }}>after 30-day free trial</div>
          {["Full top-down analysis", "Unlimited signal history", "OB + FVG detection all pairs", "AI 5-sentence narratives", "Auto Entry / SL / TP", "EcoCash payment accepted"].map((f, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: "10px", padding: "8px 0", textAlign: "left", borderBottom: `1px solid ${colors.border}`, fontSize: "13px" }}>
              <span style={{ color: colors.green }}>✓</span> {f}
            </div>
          ))}
          <button style={{ ...styles.btn.primary, width: "100%", marginTop: "24px" }} onClick={() => onNav("signup")}>
            GET STARTED FREE
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Auth Pages ─────────────────────────────────────────────────────────────────
function AuthPage({ mode, onNav }) {
  const { signIn, signUp } = useAuth();
  const [form, setForm] = useState({ email: "", password: "", fullName: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async () => {
    setError(""); setSuccess("");
    if (!form.email || !form.password) { setError("All fields required"); return; }
    if (mode === "signup" && !form.fullName) { setError("Full name required"); return; }
    setLoading(true);
    try {
      if (mode === "login") {
        await signIn(form.email, form.password);
      } else {
        await signUp(form.email, form.password, form.fullName);
        setSuccess("Account created! Check your email to verify, then login.");
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: colors.bg, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Space Mono', monospace" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');`}</style>
      <div style={{ width: "100%", maxWidth: "420px", padding: "24px" }}>
        <div style={{ textAlign: "center", marginBottom: "40px" }}>
          <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "800", fontSize: "28px", color: colors.accent, marginBottom: "8px" }}>
            SMC<span style={{ color: colors.text }}> LENS</span>
          </div>
          <div style={{ color: colors.textMuted, fontSize: "13px" }}>
            {mode === "login" ? "Welcome back, trader" : "Start your 30-day free trial"}
          </div>
        </div>

        <div style={styles.card}>
          {mode === "signup" && (
            <div style={{ marginBottom: "16px" }}>
              <label style={{ fontSize: "11px", color: colors.textMuted, letterSpacing: "1px", display: "block", marginBottom: "6px" }}>FULL NAME</label>
              <input style={styles.input} placeholder="Harold Manduna" value={form.fullName}
                onChange={e => setForm(f => ({ ...f, fullName: e.target.value }))} />
            </div>
          )}
          <div style={{ marginBottom: "16px" }}>
            <label style={{ fontSize: "11px", color: colors.textMuted, letterSpacing: "1px", display: "block", marginBottom: "6px" }}>EMAIL</label>
            <input style={styles.input} type="email" placeholder="trader@email.com" value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
          </div>
          <div style={{ marginBottom: "24px" }}>
            <label style={{ fontSize: "11px", color: colors.textMuted, letterSpacing: "1px", display: "block", marginBottom: "6px" }}>PASSWORD</label>
            <input style={styles.input} type="password" placeholder="••••••••" value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              onKeyDown={e => e.key === "Enter" && handleSubmit()} />
          </div>

          {error && <div style={{ background: colors.redDim, color: colors.red, padding: "10px 14px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px" }}>{error}</div>}
          {success && <div style={{ background: colors.greenDim, color: colors.green, padding: "10px 14px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px" }}>{success}</div>}

          <button style={{ ...styles.btn.primary, width: "100%", padding: "14px" }} onClick={handleSubmit} disabled={loading}>
            {loading ? "LOADING..." : mode === "login" ? "LOGIN" : "CREATE ACCOUNT"}
          </button>
        </div>

        <div style={{ textAlign: "center", marginTop: "20px", color: colors.textMuted, fontSize: "12px" }}>
          {mode === "login" ? (
            <span>No account? <span style={{ color: colors.accent, cursor: "pointer" }} onClick={() => onNav("signup")}>Sign up free</span></span>
          ) : (
            <span>Have an account? <span style={{ color: colors.accent, cursor: "pointer" }} onClick={() => onNav("login")}>Login</span></span>
          )}
        </div>
        <div style={{ textAlign: "center", marginTop: "12px" }}>
          <span style={{ color: colors.textMuted, fontSize: "12px", cursor: "pointer" }} onClick={() => onNav("landing")}>← Back to home</span>
        </div>
      </div>
    </div>
  );
}

// ── Signal Card ────────────────────────────────────────────────────────────────
function SignalCard({ result, plan }) {
  const isPro = plan === "pro";

  if (!result) return null;

  const biasColor = result.overall_bias === "BULLISH" ? colors.green :
    result.overall_bias === "BEARISH" ? colors.red : colors.orange;

  return (
    <div style={{ ...styles.card, border: `1px solid ${biasColor}33` }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "800", fontSize: "22px" }}>{result.pair}</div>
          <div style={{ color: colors.textMuted, fontSize: "11px" }}>{result.entry_timeframe?.toUpperCase()} · {new Date().toLocaleTimeString()}</div>
        </div>
        <BiasBadge bias={result.overall_bias} />
      </div>

      {/* Conflict Warning */}
      {result.conflict_check?.has_conflict && (
        <div style={{ background: colors.redDim, border: `1px solid ${colors.red}44`, borderRadius: "8px", padding: "12px", marginBottom: "16px" }}>
          <div style={{ color: colors.red, fontSize: "12px", fontWeight: "700", marginBottom: "4px" }}>⚠ HTF CONFLICT</div>
          {result.conflict_check.conflicts.map((c, i) => (
            <div key={i} style={{ color: colors.red, fontSize: "11px" }}>{c}</div>
          ))}
        </div>
      )}

      {/* Trade Levels */}
      {result.entry_price ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "16px" }}>
          {[
            { label: "ENTRY", value: result.entry_price, color: colors.accent },
            { label: "STOP LOSS", value: result.stop_loss, color: colors.red },
            { label: "TP 1", value: result.take_profit_1, color: colors.green },
            { label: "TP 2", value: result.take_profit_2, color: colors.green }
          ].map((item, i) => (
            <div key={i} style={{ background: colors.surface, borderRadius: "8px", padding: "12px", border: `1px solid ${colors.border}` }}>
              <div style={{ fontSize: "10px", color: colors.textMuted, letterSpacing: "1px", marginBottom: "4px" }}>{item.label}</div>
              <div style={{ fontSize: "18px", fontWeight: "700", color: item.color }}>{item.value?.toFixed(5) || "—"}</div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ background: colors.goldDim, border: `1px solid ${colors.gold}44`, borderRadius: "8px", padding: "16px", marginBottom: "16px", color: colors.gold, fontSize: "13px" }}>
          ⚡ {result.entry_data?.error || "No valid entry zone found at current price"}
        </div>
      )}

      {/* RR + Confluence Row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px", marginBottom: "16px" }}>
        <div style={{ background: colors.surface, borderRadius: "8px", padding: "10px", textAlign: "center", border: `1px solid ${colors.border}` }}>
          <div style={{ fontSize: "10px", color: colors.textMuted, marginBottom: "4px" }}>RR RATIO</div>
          <div style={{ fontSize: "16px", fontWeight: "700", color: result.rr1 >= 2 ? colors.green : colors.orange }}>
            1:{result.rr1 || "—"}
          </div>
        </div>
        <div style={{ background: colors.surface, borderRadius: "8px", padding: "10px", textAlign: "center", border: `1px solid ${colors.border}` }}>
          <div style={{ fontSize: "10px", color: colors.textMuted, marginBottom: "4px" }}>CONFLUENCE</div>
          <div style={{ fontSize: "16px", fontWeight: "700", color: result.confluence?.score >= 8 ? colors.green : colors.red }}>
            {result.confluence?.score || 0}/13
          </div>
        </div>
        <div style={{ background: colors.surface, borderRadius: "8px", padding: "10px", textAlign: "center", border: `1px solid ${colors.border}` }}>
          <div style={{ fontSize: "10px", color: colors.textMuted, marginBottom: "4px" }}>SL PIPS</div>
          <div style={{ fontSize: "16px", fontWeight: "700", color: colors.text }}>{result.sl_pips || "—"}</div>
        </div>
      </div>

      {/* Quality Badge */}
      {result.confluence && (
        <div style={{ marginBottom: "16px" }}>
          <div style={{
            background: result.confluence.quality === "HIGH_PROBABILITY" ? colors.greenDim :
              result.confluence.quality === "VALID" ? colors.accentDim : colors.redDim,
            border: `1px solid ${result.confluence.quality === "HIGH_PROBABILITY" ? colors.green :
              result.confluence.quality === "VALID" ? colors.accent : colors.red}44`,
            borderRadius: "8px", padding: "10px 14px",
            color: result.confluence.quality === "HIGH_PROBABILITY" ? colors.green :
              result.confluence.quality === "VALID" ? colors.accent : colors.red,
            fontSize: "12px", fontWeight: "700"
          }}>
            {result.confluence.quality === "HIGH_PROBABILITY" ? "🔥 " : result.confluence.quality === "VALID" ? "✓ " : "✗ "}
            {result.confluence.quality_label}
          </div>
        </div>
      )}

      {/* Candlestick + Volume */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "16px" }}>
        <div style={{ background: colors.surface, borderRadius: "8px", padding: "10px", border: `1px solid ${colors.border}` }}>
          <div style={{ fontSize: "10px", color: colors.textMuted, marginBottom: "4px" }}>PATTERN</div>
          <div style={{ fontSize: "12px", color: colors.text }}>{result.candlestick_pattern?.pattern || "None"}</div>
        </div>
        <div style={{ background: colors.surface, borderRadius: "8px", padding: "10px", border: `1px solid ${colors.border}` }}>
          <div style={{ fontSize: "10px", color: colors.textMuted, marginBottom: "4px" }}>VOLUME</div>
          <div style={{ fontSize: "12px", color: result.volume?.status === "STRONG" ? colors.green : colors.textMuted }}>
            {result.volume?.status || "N/A"}
          </div>
        </div>
      </div>

      {/* AI Narrative */}
      {result.ai_narrative && (
        <div style={{ background: colors.surface, borderRadius: "8px", padding: "14px", border: `1px solid ${colors.border}`, marginBottom: "8px" }}>
          <div style={{ fontSize: "10px", color: colors.accent, letterSpacing: "1px", marginBottom: "8px", fontWeight: "700" }}>
            AI ANALYSIS {!isPro && <span style={{ color: colors.gold }}>(TRIAL — 2 SENTENCES)</span>}
          </div>
          <div style={{ fontSize: "12px", color: colors.textMuted, lineHeight: "1.7" }}>{result.ai_narrative}</div>
        </div>
      )}

      {/* Trial upgrade prompt */}
      {!isPro && (
        <div style={{ background: colors.goldDim, border: `1px solid ${colors.gold}44`, borderRadius: "8px", padding: "12px", textAlign: "center" }}>
          <div style={{ color: colors.gold, fontSize: "12px", fontWeight: "700" }}>🔒 PRO: Full narrative + Top-down analysis + Unlimited history</div>
        </div>
      )}
    </div>
  );
}

// ── Top Down Card ──────────────────────────────────────────────────────────────
function TopDownCard({ topDown, plan }) {
  const isPro = plan === "pro";

  const roleConfig = {
    monthly: { label: "HTF Bias (Primary)", sublabel: "Monthly", description: "Overall directional bias" },
    weekly: { label: "HTF Bias (Secondary)", sublabel: "Weekly", description: "Confirms Monthly bias" },
    daily: { label: "HTF Bias (Tertiary)", sublabel: "Daily", description: "Narrows bias direction" },
    h4: { label: "Confirmation TF", sublabel: "4H", description: "Confirms before entry" },
    entry: { label: "Entry TF", sublabel: "Entry", description: "Trigger only — no bias override" }
  };

  if (!isPro) {
    return (
      <div style={{ ...styles.card, position: "relative", overflow: "hidden" }}>
        <div style={{ filter: "blur(4px)", opacity: 0.3 }}>
          {Object.entries(roleConfig).map(([role, config]) => (
            <div key={role} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: `1px solid ${colors.border}` }}>
              <div>
                <div style={{ fontSize: "11px", color: colors.accent }}>{config.label}</div>
                <div style={{ fontSize: "13px", fontWeight: "700" }}>{config.sublabel}</div>
              </div>
              <BiasBadge bias="BULLISH" />
            </div>
          ))}
        </div>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: `${colors.bg}99` }}>
          <div style={{ fontSize: "24px", marginBottom: "8px" }}>🔒</div>
          <div style={{ color: colors.gold, fontWeight: "700", marginBottom: "4px", fontFamily: "'Syne', sans-serif" }}>PRO FEATURE</div>
          <div style={{ color: colors.textMuted, fontSize: "12px" }}>Upgrade for full top-down analysis</div>
        </div>
      </div>
    );
  }

  if (!topDown) return null;

  const structures = topDown.structures || {};

  return (
    <div style={styles.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "700", fontSize: "16px" }}>Top-Down Analysis</div>
        <span style={{ background: colors.goldDim, color: colors.gold, padding: "3px 10px", borderRadius: "4px", fontSize: "10px", fontWeight: "700", border: `1px solid ${colors.gold}44` }}>PRO</span>
      </div>

      {Object.entries(roleConfig).map(([role, config], i) => {
        const structure = structures[role] || {};
        const bias = structure.bias || "UNAVAILABLE";
        const isEntry = role === "entry";

        return (
          <div key={role} style={{ padding: "14px 0", borderBottom: i < 4 ? `1px solid ${colors.border}` : "none" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                  <span style={{ background: isEntry ? colors.accentDim : colors.goldDim, color: isEntry ? colors.accent : colors.gold, padding: "2px 8px", borderRadius: "4px", fontSize: "9px", fontWeight: "700", fontFamily: "'Space Mono', monospace" }}>
                    {config.label}
                  </span>
                </div>
                <div style={{ fontWeight: "700", fontSize: "15px", marginBottom: "2px" }}>{config.sublabel}</div>
                <div style={{ fontSize: "11px", color: colors.textMuted }}>{config.description}</div>
                {structure.reason && bias !== "UNAVAILABLE" && (
                  <div style={{ fontSize: "10px", color: colors.textDim, marginTop: "4px", fontStyle: "italic" }}>{structure.reason}</div>
                )}
              </div>
              <BiasBadge bias={bias} />
            </div>
          </div>
        );
      })}

      {/* HTF Summary */}
      {topDown.htf_summary && (
        <div style={{ background: colors.surface, borderRadius: "8px", padding: "14px", marginTop: "16px", border: `1px solid ${colors.border}` }}>
          <div style={{ fontSize: "10px", color: colors.accent, letterSpacing: "1px", marginBottom: "8px", fontWeight: "700" }}>HTF BIAS SUMMARY</div>
          <div style={{ fontSize: "12px", color: colors.textMuted, lineHeight: "1.8" }}>{topDown.htf_summary}</div>
        </div>
      )}
    </div>
  );
}

// ── Confluence Breakdown ───────────────────────────────────────────────────────
function ConfluenceBreakdown({ confluence }) {
  if (!confluence?.breakdown) return null;

  return (
    <div style={styles.card}>
      <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "700", fontSize: "16px", marginBottom: "16px" }}>
        Confluence Score: <span style={{ color: confluence.score >= 8 ? colors.green : colors.red }}>{confluence.score}/13</span>
      </div>
      {Object.entries(confluence.breakdown).map(([key, data]) => (
        <div key={key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: `1px solid ${colors.border}` }}>
          <div>
            <div style={{ fontSize: "12px", color: colors.text }}>{key.replace(/_/g, " ").toUpperCase()}</div>
            <div style={{ fontSize: "10px", color: colors.textMuted }}>{data.detail}</div>
          </div>
          <div style={{ fontSize: "14px", fontWeight: "700", color: data.score === data.max ? colors.green : data.score > 0 ? colors.orange : colors.textDim }}>
            {data.score}/{data.max}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Dashboard ──────────────────────────────────────────────────────────────────
function Dashboard() {
  const { profile, signOut, apiCall } = useAuth();
  const [pair, setPair] = useState("EUR/USD");
  const [tf, setTf] = useState("1h");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("analysis");
  const [history, setHistory] = useState([]);
  const [paymentInfo, setPaymentInfo] = useState(null);
  const [ecocashRef, setEcocashRef] = useState("");
  const [payMsg, setPayMsg] = useState("");
  const [announcements, setAnnouncements] = useState([]);

  const PAIRS = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD","USD/CHF","NZD/USD","GBP/JPY","EUR/JPY","EUR/GBP","AUD/JPY","GBP/AUD","EUR/AUD","XAU/USD","XAG/USD"];
  const TFS = ["15min","30min","1h","4h"];

  useEffect(() => {
    if (tab === "history") loadHistory();
    if (tab === "upgrade") loadPaymentInfo();
    loadAnnouncements();
  }, [tab]);

  const loadHistory = async () => {
    try {
      const data = await apiCall("/api/analysis/history");
      setHistory(data.signals || []);
    } catch (e) { console.error(e); }
  };

  const loadPaymentInfo = async () => {
    try {
      const data = await apiCall("/api/payments/info");
      setPaymentInfo(data);
    } catch (e) { console.error(e); }
  };

  const loadAnnouncements = async () => {
    try {
      const res = await fetch(`${API_URL}/api/auth/announcements`);
      const data = await res.json();
      setAnnouncements(data.announcements || []);
    } catch (e) {}
  };

  const runAnalysis = async () => {
    setLoading(true); setError(""); setResult(null);
    try {
      const data = await apiCall("/api/analysis/run", {
        method: "POST",
        body: JSON.stringify({ pair, entry_timeframe: tf })
      });
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const submitPayment = async () => {
    setPayMsg("");
    try {
      const data = await apiCall("/api/payments/submit", {
        method: "POST",
        body: JSON.stringify({ ecocash_reference: ecocashRef })
      });
      setPayMsg(data.message);
      setEcocashRef("");
    } catch (e) {
      setPayMsg(`Error: ${e.message}`);
    }
  };

  const planColor = profile?.plan === "pro" ? colors.green : colors.gold;

  return (
    <div style={{ minHeight: "100vh", background: colors.bg, color: colors.text, fontFamily: "'Space Mono', monospace" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap'); * { box-sizing: border-box; }`}</style>

      {/* Header */}
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 24px", borderBottom: `1px solid ${colors.border}`, background: colors.surface }}>
        <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "800", fontSize: "20px", color: colors.accent }}>
          SMC<span style={{ color: colors.text }}> LENS</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <span style={{ background: planColor + "22", color: planColor, padding: "4px 12px", borderRadius: "20px", fontSize: "11px", fontWeight: "700", border: `1px solid ${planColor}44` }}>
            {profile?.plan?.toUpperCase()}
          </span>
          <span style={{ color: colors.textMuted, fontSize: "12px" }}>{profile?.email}</span>
          {profile?.role === "super_admin" || profile?.role === "admin" ? (
            <button style={{ ...styles.btn.ghost, padding: "6px 14px", fontSize: "11px" }} onClick={() => setTab("admin")}>ADMIN</button>
          ) : null}
          <button style={{ ...styles.btn.danger, padding: "6px 14px", fontSize: "11px" }} onClick={signOut}>LOGOUT</button>
        </div>
      </header>

      {/* Announcements */}
      {announcements.map(a => (
        <div key={a.id} style={{ background: colors.accentDim, borderBottom: `1px solid ${colors.accent}33`, padding: "10px 24px", display: "flex", gap: "12px", alignItems: "center" }}>
          <span style={{ color: colors.accent, fontSize: "11px", fontWeight: "700" }}>📢 {a.title}:</span>
          <span style={{ color: colors.textMuted, fontSize: "11px" }}>{a.message}</span>
        </div>
      ))}

      {/* Tab Nav */}
      <div style={{ display: "flex", gap: "4px", padding: "16px 24px 0", borderBottom: `1px solid ${colors.border}` }}>
        {["analysis", "history", "upgrade", ...(profile?.role !== "user" ? ["admin"] : [])].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{ background: tab === t ? colors.accentDim : "transparent", color: tab === t ? colors.accent : colors.textMuted, border: "none", padding: "10px 20px", cursor: "pointer", fontSize: "12px", fontWeight: "700", fontFamily: "'Space Mono', monospace", borderBottom: tab === t ? `2px solid ${colors.accent}` : "2px solid transparent", letterSpacing: "1px" }}>
            {t.toUpperCase()}
          </button>
        ))}
      </div>

      <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "24px" }}>

        {/* ── Analysis Tab ─────────────────────────────────────── */}
        {tab === "analysis" && (
          <div>
            {/* Controls */}
            <div style={{ ...styles.card, marginBottom: "20px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: "16px", alignItems: "end" }}>
                <div>
                  <label style={{ fontSize: "11px", color: colors.textMuted, letterSpacing: "1px", display: "block", marginBottom: "6px" }}>PAIR</label>
                  <select style={{ ...styles.input }} value={pair} onChange={e => setPair(e.target.value)}>
                    {PAIRS.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: "11px", color: colors.textMuted, letterSpacing: "1px", display: "block", marginBottom: "6px" }}>ENTRY TIMEFRAME</label>
                  <select style={{ ...styles.input }} value={tf} onChange={e => setTf(e.target.value)}>
                    {TFS.map(t => <option key={t} value={t}>{t.toUpperCase()}</option>)}
                  </select>
                </div>
                <button style={{ ...styles.btn.primary, padding: "12px 32px", height: "44px" }} onClick={runAnalysis} disabled={loading}>
                  {loading ? "SCANNING..." : "ANALYSE"}
                </button>
              </div>
            </div>

            {error && (
              <div style={{ background: colors.redDim, color: colors.red, padding: "14px", borderRadius: "8px", marginBottom: "20px", fontSize: "13px" }}>{error}</div>
            )}

            {loading && (
              <div style={{ textAlign: "center", padding: "60px", color: colors.accent }}>
                <div style={{ fontSize: "24px", marginBottom: "12px" }}>⟳</div>
                <div style={{ fontSize: "13px" }}>Fetching price data across all timeframes...</div>
              </div>
            )}

            {result && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  <SignalCard result={result} plan={profile?.plan} />
                  <ConfluenceBreakdown confluence={result.confluence} />
                </div>
                <div>
                  <TopDownCard topDown={result.top_down} plan={profile?.plan} />
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── History Tab ──────────────────────────────────────── */}
        {tab === "history" && (
          <div>
            <div style={{ marginBottom: "16px", display: "flex", justifyContent: "space-between" }}>
              <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "700", fontSize: "20px" }}>Signal History</div>
              {profile?.plan === "trial" && (
                <span style={{ color: colors.gold, fontSize: "12px" }}>Showing last 3 — upgrade for unlimited</span>
              )}
            </div>
            {history.length === 0 ? (
              <div style={{ ...styles.card, textAlign: "center", padding: "40px", color: colors.textMuted }}>No signals yet. Run your first analysis.</div>
            ) : (
              history.map(s => (
                <div key={s.id} style={{ ...styles.card, marginBottom: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                      <span style={{ fontWeight: "700", fontSize: "16px" }}>{s.pair}</span>
                      <span style={{ color: colors.textMuted, fontSize: "12px" }}>{s.entry_timeframe}</span>
                      <BiasBadge bias={s.bias} />
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "11px", color: colors.textMuted }}>{new Date(s.created_at).toLocaleDateString()}</div>
                      <div style={{ fontSize: "11px", color: s.confluence_score >= 8 ? colors.green : colors.red }}>{s.confluence_score}/13</div>
                    </div>
                  </div>
                  {s.entry_price && (
                    <div style={{ display: "flex", gap: "20px", marginTop: "10px", fontSize: "12px" }}>
                      <span>Entry: <span style={{ color: colors.accent }}>{s.entry_price?.toFixed(5)}</span></span>
                      <span>SL: <span style={{ color: colors.red }}>{s.stop_loss?.toFixed(5)}</span></span>
                      <span>TP1: <span style={{ color: colors.green }}>{s.take_profit_1?.toFixed(5)}</span></span>
                      <span>RR: <span style={{ color: colors.green }}>1:{s.rr_ratio}</span></span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* ── Upgrade Tab ──────────────────────────────────────── */}
        {tab === "upgrade" && (
          <div style={{ maxWidth: "560px", margin: "0 auto" }}>
            {profile?.plan === "pro" ? (
              <div style={{ ...styles.card, textAlign: "center", padding: "40px" }}>
                <div style={{ fontSize: "40px", marginBottom: "16px" }}>✅</div>
                <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "700", fontSize: "22px", color: colors.green, marginBottom: "8px" }}>You're on Pro</div>
                <div style={{ color: colors.textMuted }}>Full access to all SMC Lens features.</div>
              </div>
            ) : (
              <div>
                <div style={{ ...styles.card, marginBottom: "20px" }}>
                  <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "700", fontSize: "22px", marginBottom: "20px" }}>Upgrade to Pro</div>
                  {paymentInfo && (
                    <div>
                      <div style={{ background: colors.surface, borderRadius: "8px", padding: "16px", marginBottom: "20px", border: `1px solid ${colors.border}` }}>
                        <div style={{ fontSize: "11px", color: colors.textMuted, marginBottom: "8px" }}>PAYMENT DETAILS</div>
                        {paymentInfo.instructions?.map((inst, i) => (
                          <div key={i} style={{ fontSize: "13px", color: colors.text, padding: "4px 0", lineHeight: "1.6" }}>{inst}</div>
                        ))}
                      </div>
                      <div style={{ marginBottom: "16px" }}>
                        <label style={{ fontSize: "11px", color: colors.textMuted, letterSpacing: "1px", display: "block", marginBottom: "6px" }}>ECOCASH TRANSACTION REFERENCE</label>
                        <input style={styles.input} placeholder="Enter your EcoCash reference number" value={ecocashRef}
                          onChange={e => setEcocashRef(e.target.value)} />
                      </div>
                      {payMsg && (
                        <div style={{ background: payMsg.startsWith("Error") ? colors.redDim : colors.greenDim, color: payMsg.startsWith("Error") ? colors.red : colors.green, padding: "10px 14px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px" }}>
                          {payMsg}
                        </div>
                      )}
                      <button style={{ ...styles.btn.primary, width: "100%" }} onClick={submitPayment}>
                        SUBMIT PAYMENT REFERENCE
                      </button>
                      <div style={{ color: colors.textMuted, fontSize: "11px", textAlign: "center", marginTop: "12px" }}>
                        Manual verification within 24 hours
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Admin Tab ────────────────────────────────────────── */}
        {tab === "admin" && <AdminPanel profile={profile} apiCall={apiCall} />}
      </div>
    </div>
  );
}

// ── Admin Panel ────────────────────────────────────────────────────────────────
function AdminPanel({ profile, apiCall }) {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [payments, setPayments] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [flags, setFlags] = useState([]);
  const [admins, setAdmins] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [adminTab, setAdminTab] = useState("dashboard");
  const [newAdminEmail, setNewAdminEmail] = useState("");
  const [annTitle, setAnnTitle] = useState(""); const [annMsg, setAnnMsg] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => { loadData(); }, [adminTab]);

  const loadData = async () => {
    try {
      if (adminTab === "dashboard") { const d = await apiCall("/api/admin/dashboard"); setStats(d); }
      if (adminTab === "users") { const d = await apiCall("/api/admin/users"); setUsers(d.users); }
      if (adminTab === "payments") { const d = await apiCall("/api/admin/payments"); setPayments(d.payments); }
      if (adminTab === "tickets") { const d = await apiCall("/api/admin/tickets"); setTickets(d.tickets); }
      if (adminTab === "flags" && profile?.role === "super_admin") { const d = await apiCall("/api/admin/feature-flags"); setFlags(d.flags); }
      if (adminTab === "admins" && profile?.role === "super_admin") { const d = await apiCall("/api/admin/admins"); setAdmins(d.admins); }
      if (adminTab === "announcements") { const d = await apiCall("/api/admin/announcements"); setAnnouncements(d.announcements || []); }
    } catch (e) { console.error(e); }
  };

  const approvePayment = async (id) => {
    try { await apiCall(`/api/admin/payments/${id}/approve`, { method: "PATCH" }); loadData(); } catch (e) { setMsg(e.message); }
  };

  const rejectPayment = async (id) => {
    const reason = prompt("Rejection reason:");
    if (!reason) return;
    try { await apiCall(`/api/admin/payments/${id}/reject?notes=${encodeURIComponent(reason)}`, { method: "PATCH" }); loadData(); } catch (e) { setMsg(e.message); }
  };

  const upgradePlan = async (userId, plan) => {
    try { await apiCall(`/api/admin/users/${userId}/plan?plan=${plan}`, { method: "PATCH" }); loadData(); setMsg(`User updated to ${plan}`); } catch (e) { setMsg(e.message); }
  };

  const suspendUser = async (userId) => {
    try { await apiCall(`/api/admin/users/${userId}/suspend`, { method: "PATCH" }); loadData(); } catch (e) { setMsg(e.message); }
  };

  const addAdmin = async () => {
    try { const d = await apiCall("/api/admin/admins/add", { method: "POST", body: JSON.stringify({ email: newAdminEmail }) }); setMsg(d.message); setNewAdminEmail(""); loadData(); } catch (e) { setMsg(e.message); }
  };

  const removeAdmin = async (email) => {
    try { const d = await apiCall("/api/admin/admins/remove", { method: "POST", body: JSON.stringify({ email }) }); setMsg(d.message); loadData(); } catch (e) { setMsg(e.message); }
  };

  const postAnnouncement = async () => {
    try { await apiCall("/api/admin/announcements", { method: "POST", body: JSON.stringify({ title: annTitle, message: annMsg }) }); setAnnTitle(""); setAnnMsg(""); loadData(); setMsg("Announcement posted"); } catch (e) { setMsg(e.message); }
  };

  const toggleFlag = async (name) => {
    try { await apiCall(`/api/admin/feature-flags/${name}`, { method: "PATCH" }); loadData(); } catch (e) { setMsg(e.message); }
  };

  const adminTabs = ["dashboard", "users", "payments", "tickets", "announcements",
    ...(profile?.role === "super_admin" ? ["admins", "flags"] : [])];

  return (
    <div>
      <div style={{ display: "flex", gap: "4px", marginBottom: "20px", flexWrap: "wrap" }}>
        {adminTabs.map(t => (
          <button key={t} onClick={() => setAdminTab(t)} style={{ background: adminTab === t ? colors.accentDim : colors.surface, color: adminTab === t ? colors.accent : colors.textMuted, border: `1px solid ${adminTab === t ? colors.accent + "44" : colors.border}`, padding: "8px 16px", cursor: "pointer", fontSize: "11px", fontWeight: "700", fontFamily: "'Space Mono', monospace", borderRadius: "6px", letterSpacing: "1px" }}>
            {t.toUpperCase()}
          </button>
        ))}
      </div>

      {msg && <div style={{ background: colors.accentDim, color: colors.accent, padding: "10px 14px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px" }}>{msg}</div>}

      {/* Dashboard */}
      {adminTab === "dashboard" && stats && (
        <div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "24px" }}>
            {[
              { label: "TOTAL USERS", value: stats.stats.total_users, color: colors.accent },
              { label: "PRO USERS", value: stats.stats.pro_users, color: colors.green },
              { label: "TRIAL USERS", value: stats.stats.trial_users, color: colors.gold },
              { label: "MONTHLY REVENUE", value: `$${stats.stats.monthly_revenue_usd}`, color: colors.green },
              { label: "PENDING PAYMENTS", value: stats.stats.pending_payments, color: colors.orange },
              { label: "OPEN TICKETS", value: stats.stats.open_tickets, color: colors.red }
            ].map((s, i) => (
              <div key={i} style={{ ...styles.card, textAlign: "center" }}>
                <div style={{ fontSize: "10px", color: colors.textMuted, letterSpacing: "1px", marginBottom: "8px" }}>{s.label}</div>
                <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "800", fontSize: "28px", color: s.color }}>{s.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Users */}
      {adminTab === "users" && (
        <div>
          {users.map(u => (
            <div key={u.id} style={{ ...styles.card, marginBottom: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: "700", fontSize: "14px" }}>{u.email}</div>
                  <div style={{ fontSize: "11px", color: colors.textMuted }}>{u.full_name} · {u.role} · {new Date(u.created_at).toLocaleDateString()}</div>
                </div>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <BiasBadge bias={u.plan === "pro" ? "BULLISH" : "RANGING"} />
                  {u.role !== "super_admin" && (
                    <>
                      <button style={{ ...styles.btn.ghost, padding: "4px 10px", fontSize: "10px" }} onClick={() => upgradePlan(u.id, u.plan === "pro" ? "trial" : "pro")}>
                        {u.plan === "pro" ? "DOWNGRADE" : "UPGRADE"}
                      </button>
                      <button style={{ ...styles.btn.danger, padding: "4px 10px", fontSize: "10px" }} onClick={() => suspendUser(u.id)}>
                        {u.is_suspended ? "UNSUSPEND" : "SUSPEND"}
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Payments */}
      {adminTab === "payments" && (
        <div>
          {payments.map(p => (
            <div key={p.id} style={{ ...styles.card, marginBottom: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: "700" }}>{p.users?.email}</div>
                  <div style={{ fontSize: "12px", color: colors.textMuted }}>Ref: {p.ecocash_reference} · ${p.amount} · {new Date(p.created_at).toLocaleDateString()}</div>
                </div>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <span style={{ color: p.status === "approved" ? colors.green : p.status === "rejected" ? colors.red : colors.gold, fontSize: "11px", fontWeight: "700" }}>
                    {p.status.toUpperCase()}
                  </span>
                  {p.status === "pending" && (
                    <>
                      <button style={{ ...styles.btn.primary, padding: "6px 14px", fontSize: "11px" }} onClick={() => approvePayment(p.id)}>APPROVE</button>
                      <button style={{ ...styles.btn.danger, padding: "6px 14px", fontSize: "11px" }} onClick={() => rejectPayment(p.id)}>REJECT</button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tickets */}
      {adminTab === "tickets" && (
        <div>
          {tickets.map(t => (
            <div key={t.id} style={{ ...styles.card, marginBottom: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <div style={{ fontWeight: "700" }}>{t.subject}</div>
                <span style={{ color: t.status === "resolved" ? colors.green : colors.orange, fontSize: "11px" }}>{t.status.toUpperCase()}</span>
              </div>
              <div style={{ fontSize: "12px", color: colors.textMuted, marginBottom: "8px" }}>{t.users?.email} · {new Date(t.created_at).toLocaleDateString()}</div>
              <div style={{ fontSize: "13px", marginBottom: "12px" }}>{t.message}</div>
              {t.status === "open" && (
                <button style={{ ...styles.btn.ghost, padding: "6px 14px", fontSize: "11px" }} onClick={async () => {
                  const reply = prompt("Your reply:");
                  if (reply) { await apiCall(`/api/admin/tickets/${t.id}/resolve`, { method: "PATCH", body: JSON.stringify({ reply }) }); loadData(); }
                }}>RESOLVE</button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Announcements */}
      {adminTab === "announcements" && (
        <div>
          <div style={{ ...styles.card, marginBottom: "20px" }}>
            <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "700", marginBottom: "16px" }}>Post Announcement</div>
            <input style={{ ...styles.input, marginBottom: "10px" }} placeholder="Title" value={annTitle} onChange={e => setAnnTitle(e.target.value)} />
            <textarea style={{ ...styles.input, minHeight: "80px", resize: "vertical" }} placeholder="Message" value={annMsg} onChange={e => setAnnMsg(e.target.value)} />
            <button style={{ ...styles.btn.primary, marginTop: "12px" }} onClick={postAnnouncement}>POST</button>
          </div>
        </div>
      )}

      {/* Super Admin: Add/Remove Admins */}
      {adminTab === "admins" && profile?.role === "super_admin" && (
        <div>
          <div style={{ ...styles.card, marginBottom: "20px" }}>
            <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: "700", marginBottom: "16px" }}>Add Admin</div>
            <div style={{ display: "flex", gap: "12px" }}>
              <input style={{ ...styles.input }} placeholder="admin@email.com" value={newAdminEmail} onChange={e => setNewAdminEmail(e.target.value)} />
              <button style={styles.btn.primary} onClick={addAdmin}>ADD</button>
            </div>
          </div>
          {admins.map(a => (
            <div key={a.id} style={{ ...styles.card, marginBottom: "10px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: "700" }}>{a.email}</div>
                <div style={{ fontSize: "11px", color: colors.textMuted }}>{a.role} · {a.full_name}</div>
              </div>
              {a.role !== "super_admin" && (
                <button style={styles.btn.danger} onClick={() => removeAdmin(a.email)}>REMOVE</button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Super Admin: Feature Flags */}
      {adminTab === "flags" && profile?.role === "super_admin" && (
        <div>
          {flags.map(f => (
            <div key={f.id} style={{ ...styles.card, marginBottom: "10px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: "700" }}>{f.feature_name}</div>
                <div style={{ fontSize: "11px", color: colors.textMuted }}>{f.description} · Applies to: {f.applies_to}</div>
              </div>
              <button style={{ background: f.is_enabled ? colors.greenDim : colors.redDim, color: f.is_enabled ? colors.green : colors.red, border: `1px solid ${f.is_enabled ? colors.green : colors.red}44`, padding: "6px 16px", borderRadius: "6px", cursor: "pointer", fontSize: "12px", fontWeight: "700", fontFamily: "'Space Mono', monospace" }} onClick={() => toggleFlag(f.feature_name)}>
                {f.is_enabled ? "ENABLED" : "DISABLED"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── App Router ─────────────────────────────────────────────────────────────────
function App() {
  const { user, loading } = useAuth();
  const [page, setPage] = useState("landing");

  useEffect(() => {
    if (user) setPage("dashboard");
  }, [user]);

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", background: colors.bg, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Space Mono', monospace", color: colors.accent }}>
        Loading...
      </div>
    );
  }

  if (user) return <Dashboard />;

  if (page === "landing") return <Landing onNav={setPage} />;
  if (page === "login" || page === "signup") return <AuthPage mode={page} onNav={setPage} />;

  return <Landing onNav={setPage} />;
}

export default function Root() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}
