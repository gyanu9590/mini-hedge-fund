import { useEffect, useState } from "react"
import axios from "axios"
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer
} from "recharts"

function EquityChart(){

const [data,setData] = useState([])

useEffect(()=>{

axios.get("http://127.0.0.1:8000/performance")
.then(res=>{
setData(res.data)
})

},[])

return(

<div className="bg-slate-800 p-4 rounded-lg">
<h2 className="mb-4">Portfolio Equity Curve</h2>

<ResponsiveContainer width="100%" height={300}>
<LineChart data={data}>
<XAxis dataKey="index" />
<YAxis />
<Tooltip />
<Line type="monotone" dataKey="portfolio_value" stroke="#22c55e" />
</LineChart>
</ResponsiveContainer>

</div>

)

}

export default EquityChart