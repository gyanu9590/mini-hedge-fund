import { useEffect, useState } from "react"
import axios from "axios"

function Metrics(){

const [metrics,setMetrics] = useState({})

function fetchMetrics(){

axios.get("http://localhost:8001/metrics")
.then(res=>{
setMetrics(res.data)
})
}

useEffect(()=>{

fetchMetrics()

const interval = setInterval(fetchMetrics,10000)

return ()=>clearInterval(interval)

},[])

return(

<div className="grid grid-cols-4 gap-6 mb-8">

<div className="bg-slate-800 p-4 rounded-lg">
<p className="text-gray-400">Portfolio Value</p>
<p className="text-2xl font-bold text-green-400">
₹{metrics.portfolio_value}
</p>
</div>

<div className="bg-slate-800 p-4 rounded-lg">
<p className="text-gray-400">CAGR</p>
<p className="text-2xl font-bold">
{metrics.cagr}%
</p>
</div>

<div className="bg-slate-800 p-4 rounded-lg">
<p className="text-gray-400">Sharpe Ratio</p>
<p className="text-2xl font-bold">
{metrics.sharpe}
</p>
</div>

<div className="bg-slate-800 p-4 rounded-lg">
<p className="text-gray-400">Max Drawdown</p>
<p className="text-2xl font-bold text-red-400">
{metrics.drawdown}%
</p>
</div>

</div>

)

}

export default Metrics