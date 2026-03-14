import Signals from "./components/Signals"
import EquityChart from "./components/EquityChart"
import Metrics from "./components/Metrics"
import LivePrices from "./components/LivePrices"

function App() {

return (

<div className="min-h-screen bg-slate-900 text-white p-10">

<h1 className="text-4xl font-bold mb-8">
Quant Edge ML Trading System
</h1>

<Metrics/>

<div className="grid grid-cols-2 gap-8">

<div className="bg-slate-800 p-6 rounded-xl">
<Signals/>
</div>

<div className="bg-slate-800 p-6 rounded-xl">
<EquityChart/>
</div>

</div>
<LivePrices/>
</div>

)

}

export default App