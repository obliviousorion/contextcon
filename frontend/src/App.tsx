import { lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";

const HomePage = lazy(() => import("./pages/HomePage"));
const ResolvePage = lazy(() => import("./pages/ResolvePage"));
const ClearPage = lazy(() => import("./pages/ClearPage"));
const DisputePage = lazy(() => import("./pages/DisputePage"));
const FilesPage = lazy(() => import("./pages/FilesPage"));
const FileDetailPage = lazy(() => import("./pages/FileDetailPage"));
const AuditPage = lazy(() => import("./pages/AuditPage"));
const WatchPage = lazy(() => import("./pages/WatchPage"));
const LedgerPage = lazy(() => import("./pages/LedgerPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="resolve" element={<ResolvePage />} />
        <Route path="clear/:domain" element={<ClearPage />} />
        <Route path="dispute/:domain" element={<DisputePage />} />
        <Route path="files" element={<FilesPage />} />
        <Route path="files/:id" element={<FileDetailPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="watch" element={<WatchPage />} />
        <Route path="ledger" element={<LedgerPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
