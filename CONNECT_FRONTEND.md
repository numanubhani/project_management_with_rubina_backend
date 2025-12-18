# 🚀 Connect Frontend to Backend - Quick Guide

## ✅ Backend Status
- **Running on:** http://localhost:8000
- **API Base:** http://localhost:8000/api
- **CORS:** Configured for all localhost ports

## 📋 Quick Setup (3 Steps)

### Step 1: Copy API Configuration

Copy `frontend-api-config.js` to your frontend project:
- React: `src/services/api.js`
- Vue: `src/services/api.js`
- Or any location you prefer

### Step 2: Install Axios (if not installed)

```bash
npm install axios
# or
yarn add axios
```

### Step 3: Use in Your Components

```javascript
import apiClient, { authAPI, projectAPI } from './services/api';

// Login example
const handleLogin = async (email, password) => {
  try {
    const response = await authAPI.login({ email, password });
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('user', JSON.stringify(response.data.user));
    // Redirect to dashboard
  } catch (error) {
    console.error('Login failed:', error);
  }
};

// Get projects example
const fetchProjects = async () => {
  try {
    const response = await projectAPI.getAll();
    setProjects(response.data);
  } catch (error) {
    console.error('Failed to fetch projects:', error);
  }
};
```

## 🔑 Authentication Flow

1. **Register/Login** → Get `access_token`
2. **Store token** → `localStorage.setItem('access_token', token)`
3. **Include in requests** → Automatically via interceptor
4. **Token expires** → Auto-redirect to login (handled by interceptor)

## 📝 Example: Complete Login Component

```javascript
import { useState } from 'react';
import { authAPI } from './services/api';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await authAPI.login({ email, password });
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      // Redirect to dashboard
      window.location.href = '/dashboard';
    } catch (error) {
      alert('Login failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      <button type="submit">Login</button>
    </form>
  );
}
```

## 🧪 Test Connection

Run this in your browser console (on your frontend):

```javascript
fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'test@example.com',
    password: 'test123456'
  })
})
.then(r => r.json())
.then(console.log)
.catch(console.error);
```

## ✅ Checklist

- [ ] Backend running on http://localhost:8000
- [ ] Frontend API config file created
- [ ] Axios installed
- [ ] API client imported in components
- [ ] Token stored after login
- [ ] API calls working

## 🎯 That's It!

Your frontend is now connected to the backend! 🎉

For detailed API documentation, visit: http://localhost:8000/api/docs/


