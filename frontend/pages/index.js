"use client";
import Navbar from '../components/Navbar'
import Chart from '../components/Chart'
import SignalsPanel from '../components/SignalsPanel'
export default function Home(){
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="p-6 grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <Chart symbol={'BINANCE:BTCUSDT'} />
        </div>
        <div>
          <SignalsPanel />
        </div>
        <div className="col-span-3 mt-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-gray-800 rounded">Model Status Card (calls /model/status)</div>
            <div className="p-4 bg-gray-800 rounded">Controls / Train Model / Execute Simulation</div>
            <div className="p-4 bg-gray-800 rounded">Recent Executions & Logs</div>
          </div>
        </div>
      </main>
    </div>
  )
}
