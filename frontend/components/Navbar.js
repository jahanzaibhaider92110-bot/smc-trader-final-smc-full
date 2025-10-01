export default function Navbar(){ 
  return (
    <nav className="w-full p-4 flex items-center justify-between bg-gray-800">
      <div className="flex items-center gap-3">
        <div className="text-xl font-bold">SMC-Trader</div>
        <div className="text-sm text-gray-400">Live SMC Dashboard</div>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-sm text-gray-400">Profile</div>
        <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center">U</div>
      </div>
    </nav>
  )
}
