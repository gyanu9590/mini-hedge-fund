import { useEffect, useState } from "react"
import axios from "axios"

function LivePrices(){

const [prices,setPrices] = useState([])
const [lastUpdate,setLastUpdate] = useState("")

function fetchPrices(){

axios.get("http://127.0.0.1:8000/live_prices")
.then(res=>{

setPrices(res.data)

const now = new Date()

setLastUpdate(now.toLocaleString())

})
.catch(err=>{
console.error("Error fetching prices:",err)
})

}

useEffect(()=>{

fetchPrices()

const interval = setInterval(fetchPrices,10000)

return ()=>clearInterval(interval)

},[])

return(

<div className="bg-slate-800 p-6 rounded-xl">

<h2 className="text-lg font-semibold mb-2">
Live Market Prices
</h2>

<p className="text-sm text-gray-400 mb-4">
Last Updated: {lastUpdate}
</p>

<table className="w-full">

<thead>

<tr className="text-gray-400 border-b border-gray-600">

<th className="text-left py-2">Symbol</th>
<th className="text-right py-2">Price</th>

</tr>

</thead>

<tbody>

{prices.map((p,i)=>(
<tr key={i} className="border-b border-gray-700">

<td className="py-2">{p.symbol}</td>

<td className="py-2 text-right text-green-400 font-semibold">
₹ {p.price?.toFixed(2)}
</td>

</tr>
))}

</tbody>

</table>

</div>

)

}

export default LivePrices