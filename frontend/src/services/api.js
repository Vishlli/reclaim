
import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// ---------- Dashboard ----------
export const getDashboard = () => client.get("/dashboard").then((r) => r.data);

// ---------- Transactions ----------
export const getTransactions = () => client.get("/transactions").then((r) => r.data);
export const getTransaction = (transactionId) =>
  client.get(`/transactions/${transactionId}`).then((r) => r.data);

// ---------- Recovery cases ----------
export const getRecoveryCases = () => client.get("/recovery/cases").then((r) => r.data);
export const getRecoveryCase = (transactionId) =>
  client.get(`/recovery/cases/${transactionId}`).then((r) => r.data);
export const analyzeTransaction = (transactionId) =>
  client.post(`/recovery/analyze/${transactionId}`).then((r) => r.data);
export const executeTransaction = (transactionId) =>
  client.post(`/recovery/execute/${transactionId}`).then((r) => r.data);

// ---------- Reviews ----------
export const getReviews = () => client.get("/reviews").then((r) => r.data);
export const approveReview = (reviewId) =>
  client.post(`/reviews/${reviewId}/approve`).then((r) => r.data);
export const rejectReview = (reviewId) =>
  client.post(`/reviews/${reviewId}/reject`).then((r) => r.data);

// ---------- Policies ----------
export const getPolicies = () => client.get("/policies").then((r) => r.data);
export const updatePolicy = (updates) =>
  client.put("/policies", updates).then((r) => r.data);

// ---------- Audit ----------
export const getAuditTrail = () => client.get("/audit").then((r) => r.data);