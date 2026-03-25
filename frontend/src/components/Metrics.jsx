import { useEffect, useState } from "react"
import axios from "axios"

function Metrics(){

const [metrics,setMetrics] = useState({})

function fetchMetrics(){

axios.get("http://127.0.0.1:8000/metrics")
.then(res=>{
setMetrics(res.data)
})
.catch(err=>{
console.error("Error fetching metrics:", err)
})

}

useEffect(()=>{

fetchMetrics()

const interval = setInterval(fetchMetrics,10000)

return ()=>clearInterval(interval)

},[])

return(

<div className="grid grid-cols-4 gap-6 mb-8">

{/* Portfolio Value */}
<div className="bg-slate-800 p-4 rounded-lg">
<p className="text-gray-400">Portfolio Value</p>
<p className="text-2xl font-bold text-green-400">
₹ {metrics.final_capital?.toFixed(0) || "-"}
</p>
</div>

{/* CAGR */}
<div className="bg-slate-800 p-4 rounded-lg">
<p className="text-gray-400">CAGR</p>
<p className="text-2xl font-bold">
{metrics.cagr_pct !== undefined ? `${metrics.cagr_pct}%` : "-"}
</p>
</div>

{/* Sharpe */}
<div className="bg-slate-800 p-4 rounded-lg">
<p className="text-gray-400">Sharpe Ratio</p>
<p className="text-2xl font-bold">
{metrics.sharpe !== undefined ? metrics.sharpe : "-"}
</p>
</div>

{/* Max Drawdown */}
<div className="bg-slate-800 p-4 rounded-lg">
<p className="text-gray-400">Max Drawdown</p>
<p className="text-2xl font-bold text-red-400">
{metrics.max_drawdown_pct !== undefined ? `${metrics.max_drawdown_pct}%` : "-"}
</p>
</div>

</div>

)

}

export default Metrics