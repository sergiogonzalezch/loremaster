import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import CollectionsPage from "./pages/CollectionsPage";
import CollectionDetailPage from "./pages/CollectionDetailPage";
import EntityDetailPage from "./pages/EntityDetailPage";
import GeneratePage from "./pages/GeneratePage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<CollectionsPage />} />
            <Route
              path="/collections/:collectionId"
              element={<CollectionDetailPage />}
            />
            <Route
              path="/collections/:collectionId/entities/:entityId"
              element={<EntityDetailPage />}
            />
            <Route
              path="/collections/:collectionId/generate"
              element={<GeneratePage />}
            />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
