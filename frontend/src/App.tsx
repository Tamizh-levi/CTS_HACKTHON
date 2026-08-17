import React from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom';

import Login from './pages/Login';
import NocDashboard from './pages/Nocdashboard';
import NocDetails from './pages/Nocdetails';
import AdminDashboard from './pages/Admindashboard';
import AdminPredict from './pages/AdminPredict';



// ============================================================
// PROTECTED ROUTE
// ============================================================

interface ProtectedRouteProps {
  children: React.ReactNode;
}

function ProtectedRoute({ children }: ProtectedRouteProps) {
  const token = localStorage.getItem('authToken');

  if (!token) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  return <>{children}</>;
}

// ============================================================
// APP
// ============================================================

function App() {
  const isAuthenticated = Boolean(localStorage.getItem('authToken'));

  return (
    <BrowserRouter>
      <Routes>
        {/* ==================================================
            LOGIN
        ================================================== */}
        <Route
          path="/login"
          element={<Login />}
        />

        {/* ==================================================
            NOC COMMAND DASHBOARD
        ================================================== */}
        <Route
          path="/noc-dashboard"
          element={
            <ProtectedRoute>
              <NocDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin-dashboard"
          element={
            <ProtectedRoute>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin-predict"
          element={
            <ProtectedRoute>
              <AdminPredict />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/predict"
          element={
            <ProtectedRoute>
              <AdminPredict />
            </ProtectedRoute>
          }
        />
        <Route
          path="/field"
          element={
            <ProtectedRoute>
              <NocDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/field-dashboard"
          element={
            <ProtectedRoute>
              <NocDashboard />
            </ProtectedRoute>
          }
        />

        {/* ==================================================
            NOC DETAILS & RAG RCA CONSOLE (YES / NO REVIEW)
        ================================================== */}
        <Route
          path="/noc"
          element={
            <ProtectedRoute>
              <NocDetails />
            </ProtectedRoute>
          }
        />
        <Route
          path="/noc/:incidentId"
          element={
            <ProtectedRoute>
              <NocDetails />
            </ProtectedRoute>
          }
        />
        <Route
          path="/noc-details/:incidentId"
          element={
            <ProtectedRoute>
              <NocDetails />
            </ProtectedRoute>
          }
        />
        <Route
          path="/incident/:incidentId"
          element={
            <ProtectedRoute>
              <NocDetails />
            </ProtectedRoute>
          }
        />

        {/* ==================================================
            DEFAULT / FALLBACK ROUTE
        ================================================== */}
        <Route
          path="/"
          element={
            <Navigate
              to={isAuthenticated ? '/noc-dashboard' : '/login'}
              replace
            />
          }
        />
        <Route
          path="*"
          element={
            <Navigate
              to={isAuthenticated ? '/noc-dashboard' : '/login'}
              replace
            />
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;