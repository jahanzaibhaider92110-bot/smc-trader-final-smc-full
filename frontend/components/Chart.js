"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

// TradingView Widget ko sirf client pe import karo
const AdvancedRealTimeChart = dynamic(
  () =>
    import("react-ts-tradingview-widgets").then(
      (mod) => mod.AdvancedRealTimeChart
    ),
  {
    ssr: false,
    loading: () => <p className="text-white">Loading chart...</p>,
  }
);

export default function Chart({ symbol = "BINANCE:BTCUSDT" }) {
  const [interval, setInterval] = useState("1");

  return (
    <div className="bg-gray-800 p-3 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-lg font-semibold text-white">{symbol} Chart</h3>
        <select
          value={interval}
          onChange={(e) => setInterval(e.target.value)}
          className="ml-auto bg-gray-700 p-1 rounded text-white"
        >
          <option value="1">1m</option>
          <option value="5">5m</option>
          <option value="15">15m</option>
          <option value="60">1h</option>
          <option value="240">4h</option>
          <option value="1D">1d</option>
        </select>
      </div>
      <div style={{ height: "560px" }}>
        <AdvancedRealTimeChart
          symbol={symbol}
          theme="dark"
          autosize
          interval={interval}
        />
      </div>
    </div>
  );
}
