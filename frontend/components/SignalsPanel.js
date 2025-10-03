// path: frontend/components/SignalsPanel.js
"use client";
import { useEffect, useState, useRef } from "react";

export default function SignalsPanel() {
  const [signal, setSignal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const lastIdRef = useRef(null);

  const API_BASE = "http://127.0.0.1:8000";

  const playBeep = () => {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioContext();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = "sine";
      o.frequency.value = 880;
      g.gain.value = 0.03;
      o.connect(g);
      g.connect(ctx.destination);
      o.start();
      setTimeout(() => {
        o.stop();
        try { ctx.close(); } catch (e) {}
      }, 350);
    } catch (e) {
      // fallback: alert
      try { window.alert("🔔 New signal!"); } catch (e) {}
    }
  };

  const fetchSignal = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/signals?symbol=BTC/USDT&timeframe=5m`);
      if (!res.ok) throw new Error("Failed to fetch");
      const data = await res.json();
      setSignal(data.signal);
      // if new valid signal ID appears, beep
      if (data.signal && data.signal.id && lastIdRef.current !== data.signal.id) {
        lastIdRef.current = data.signal.id;
        // only beep for real entries (not placeholder rows)
        if (data.signal.side && data.signal.side !== "none") {
          playBeep();
        }
      }
    } catch (err) {
      setError(err.message || "fetch error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSignal();
    const pid = setInterval(fetchSignal, 10000); // poll every 10 seconds
    return () => clearInterval(pid);
  }, []);

  return (
    <div className="p-4 bg-white rounded shadow">
      <h3 className="text-xl font-semibold">Latest SMC Signal</h3>
      {loading && <p>Checking for entry — please wait...</p>}
      {error && <p className="text-red-500">Failed to fetch: {error}</p>}
      {!loading && !signal && <p className="text-gray-500">No signal available</p>}
      {signal && (
        <div className="mt-2">
          {(!signal.side || signal.side === "none") ? (
            <div>
              <p className="text-yellow-600 font-semibold">No Entry</p>
              <p className="text-sm text-gray-500">Strategy did not find a valid SMC setup yet.</p>
            </div>
          ) : (
            <div>
              <p className="text-green-700 font-bold">ENTRY — {signal.side.toUpperCase()}</p>
              <p><b>Symbol:</b> {signal.symbol}</p>
              <p><b>Entry:</b> {signal.entry}</p>
              <p><b>Stop Loss:</b> {signal.stop_loss}</p>
              <p><b>Take Profit:</b> {signal.take_profit}</p>
              <p><b>RR:</b> {signal.rr}</p>
              <p><b>Confidence:</b> {signal.confidence}</p>
              <p><b>SMC Confirmed:</b> {signal.smc_confirmed ? "Yes" : "No"}</p>
              <p><b>Reason:</b> {signal.reason}</p>
            </div>
          )}
        </div>
      )}
      <button onClick={fetchSignal} className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded">
        🔄 Refresh
      </button>
    </div>
  );
}
