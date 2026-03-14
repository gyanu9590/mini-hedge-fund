import { useEffect, useState } from "react"
import axios from "axios"

function Signals(){

const [signals,setSignals] = useState([])

function fetchSignals(){

axios.get("http://localhost:8001/signals")
.then(res=>{
setSignals(res.data)
})
.catch(err=>{
console.error("Error fetching signals:",err)
})

}

useEffect(()=>{

fetchSignals()

const interval = setInterval(fetchSignals,10000)

return ()=>clearInterval(interval)

},[])

function getSignalText(signal){

if(signal === 1) return "BUY"
if(signal === -1) return "SELL"
return "HOLD"

}

return(

<div>

<h2 className="text-lg font-semibold mb-4">
Trading Signals
</h2>

<table className="w-full text-left border-collapse">

<thead>

<tr className="border-b border-gray-600 text-gray-300">

<th className="px-4 py-2">Date</th>
<th className="px-4 py-2">Symbol</th>
<th className="px-4 py-2">Signal</th>

</tr>

</thead>

<tbody>

{signals.map((s,i)=>{

const signalText = getSignalText(s.signal)

return(

<tr key={i} className="border-b border-gray-700 hover:bg-slate-700">

<td className="px-4 py-2">
{new Date(s.date).toLocaleDateString()}
</td>

<td className="px-4 py-2">
{s.symbol}
</td>

<td className="px-4 py-2 font-semibold text-yellow-400">
{signalText}
</td>

</tr>

)

})}

</tbody>

</table>

</div>

)

}

export default Signals