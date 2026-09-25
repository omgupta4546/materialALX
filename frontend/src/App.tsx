import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppShell } from './layouts/AppShell';
import { ProtectedRoute } from './layouts/ProtectedRoute';
import { Dashboard } from './pages/Dashboard';
import { Materials } from './pages/Materials';
import { Approvals } from './pages/Approvals';
import { Analytics } from './pages/Analytics';
import { Login } from './pages/Login';
import { Upload } from './pages/Upload';
import { Matches } from './pages/Matches';
import { NationalMaterials } from './pages/NationalMaterials';
import TaxonomyManagement from './pages/TaxonomyManagement';
import RuleManagement from './pages/RuleManagement';
import AdminConsole from './pages/AdminConsole';
import { Profile } from './pages/Profile';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          {/* Protected Routes enclosed in AppShell */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<AppShell />}>
              <Route index element={<Dashboard />} />
              <Route path="materials" element={<Materials />} />
              <Route path="matches" element={<Matches />} />
              <Route path="national-materials" element={<NationalMaterials />} />
              <Route path="approvals" element={<Approvals />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="profile" element={<Profile />} />
              <Route path="taxonomy" element={<TaxonomyManagement />} />
              <Route path="rules" element={<RuleManagement />} />
              <Route path="admin" element={<AdminConsole />} />
              <Route path="upload" element={<Upload />} />
            </Route>
          </Route>
          
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
