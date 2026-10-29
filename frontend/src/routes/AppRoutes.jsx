import React from 'react';
import { Route, Routes } from 'react-router-dom';
import Home from '../pages/Home';
import Post from '../pages/Post';
import Profile from '../pages/Profile';
import Settings from '../pages/Settings';
import EditProfile from '../pages/EditProfile';
import Signup from '../pages/Signup';
import Login from '../pages/Login';
import PostDetail from '../pages/PostDetail';
import NotFound from '../pages/NotFound';
import ProtectedRoute from './ProtectedRoute';

const AppRoutes = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/signup" element={<Signup />} />
      <Route path="/login" element={<Login />} />

      {/* Protected Routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Home />
          </ProtectedRoute>
        }
      />
      <Route
        path="/post"
        element={
          <ProtectedRoute>
            <Post />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile/:authorId"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile/:authorId/edit"
        element={
          <ProtectedRoute>
            <EditProfile />
          </ProtectedRoute>
        }
      />
       <Route
        path="/authors/:authorId/profile/edit"
        element={
          <ProtectedRoute>
            <EditProfile />
          </ProtectedRoute>
        } />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        }
      />
      <Route
        path="/post/:postId/edit"
        element={
          <ProtectedRoute>
            <Post />
          </ProtectedRoute>
        }
      />
       <Route
        path="/post/:postId/"
        element={
          <ProtectedRoute>
            <PostDetail />
          </ProtectedRoute>
        }
      />

      {/* anything else: a friendly "not found" page instead of an empty screen */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
};

export default AppRoutes;
