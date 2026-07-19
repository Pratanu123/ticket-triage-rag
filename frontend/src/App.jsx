import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import NewTicket from "./pages/NewTicket";
import TicketDetail from "./pages/TicketDetail";
import TicketList from "./pages/TicketList";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<TicketList />} />
        <Route path="new" element={<NewTicket />} />
        <Route path="tickets/:id" element={<TicketDetail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
