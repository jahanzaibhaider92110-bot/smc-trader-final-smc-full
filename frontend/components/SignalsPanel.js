"use client";
import { useEffect, useState } from "react";

export default function SignalsPanel() {
  const [signal, setSignal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const API_BASE = "http://127.0.0.1:8000";

  const fetchSignal = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/signals?symbol=BTC/USDT&timeframe=1m`);
      if (!res.ok) throw new Error("Failed to fetch");
      const data = await res.json();
      setSignal(data.signal);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSignal();
    const interval = setInterval(fetchSignal, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-4 bg-gray-900 rounded shadow-lg text-white">
      <h2 className="text-xl font-bold mb-4">📊 Latest Signal</h2>

      {loading && <p className="text-yellow-400">Fetching latest signal...</p>}
      {error && <p className="text-red-400">Error: {error}</p>}

      {signal && (
        <div className="space-y-2 text-sm">
          <p><b>Label:</b> {signal.label || "-"}</p>
          <p><b>Reason:</b> {signal.reason || "-"}</p>
          <p><b>ML Label:</b> {signal.ml_label ?? "-"}</p>
          <p><b>Confidence:</b> {signal.ml_confidence ? signal.ml_confidence.toFixed(2) : "-"}</p>
          <p><b>Created At:</b> {signal.created_at || "-"}</p>
        </div>
      )}

      <button
        onClick={fetchSignal}
        className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded"
      >
        🔄 Refresh
      </button>
    </div>
  );
}
