import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import axios from "axios";

function EquityChart() {

  const [data, setData] = useState([]);

  useEffect(() => {

    axios.get("http://localhost:8001/performance")
      .then(res => {
        setData(res.data);
      })
      .catch(err => {
        console.error("Error loading performance data:", err);
      });

  }, []);

  return (

    <div style={{marginTop:"40px"}}>

      <h2>Portfolio Equity Curve</h2>

      <LineChart width={650} height={300} data={data}>

        <CartesianGrid strokeDasharray="3 3" />

        <XAxis dataKey="date" />

        <YAxis />

        <Tooltip />

        <Line type="monotone" dataKey="equity" stroke="#2aa3d7" strokeWidth={2} />

      </LineChart>

    </div>

  );

}

export default EquityChart;