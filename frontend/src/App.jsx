import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import Overview from "./pages/Overview";
import RecoveryCasesList from "./pages/RecoveryCasesList";
import RecoveryCaseDetail from "./pages/RecoveryCaseDetail";
import ReviewQueue from "./pages/ReviewQueue";
import Transactions from "./pages/Transactions";
import Policies from "./pages/Policies";
import AuditTrail from "./pages/AuditTrail";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Overview />} />
          <Route path="/recovery-cases" element={<RecoveryCasesList />} />
          <Route
            path="/recovery-cases/:transactionId"
            element={<RecoveryCaseDetail />}
          />
          <Route path="/review-queue" element={<ReviewQueue />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/audit" element={<AuditTrail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
