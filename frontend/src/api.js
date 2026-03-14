import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000"
});

export const getSignals = () => API.get("/signals");
export const getOrders = () => API.get("/orders");
export const getPerformance = () => API.get("/performance");