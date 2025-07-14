import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [activeTab, setActiveTab] = useState('home');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Auth states
  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [registerData, setRegisterData] = useState({ email: '', password: '' });

  // API key states
  const [apiKeys, setApiKeys] = useState([]);
  const [newKeyName, setNewKeyName] = useState('');

  // Weather testing states
  const [weatherLocation, setWeatherLocation] = useState('London');
  const [weatherData, setWeatherData] = useState(null);
  const [testApiKey, setTestApiKey] = useState('');

  // Usage states
  const [usage, setUsage] = useState(null);

  // Subscription tiers
  const [subscriptionTiers, setSubscriptionTiers] = useState([]);

  useEffect(() => {
    if (token) {
      fetchUserData();
      fetchApiKeys();
      fetchUsage();
      fetchSubscriptionTiers();
    }
  }, [token]);

  const fetchUserData = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/health`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        // Token is valid, user is logged in
        setUser({ token });
      }
    } catch (err) {
      console.error('Error fetching user data:', err);
    }
  };

  const fetchApiKeys = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/api-keys`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setApiKeys(data);
      }
    } catch (err) {
      console.error('Error fetching API keys:', err);
    }
  };

  const fetchUsage = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/usage`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setUsage(data);
      }
    } catch (err) {
      console.error('Error fetching usage:', err);
    }
  };

  const fetchSubscriptionTiers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/subscription-tiers`);
      if (response.ok) {
        const data = await response.json();
        setSubscriptionTiers(data.tiers);
      }
    } catch (err) {
      console.error('Error fetching subscription tiers:', err);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginData)
      });

      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('token', data.token);
        setToken(data.token);
        setUser(data.user);
        setSuccess('Login successful!');
        setActiveTab('dashboard');
      } else {
        setError(data.detail || 'Login failed');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(registerData)
      });

      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('token', data.token);
        setToken(data.token);
        setUser(data.user);
        setTestApiKey(data.api_key.key);
        setSuccess('Registration successful! Your API key has been generated.');
        setActiveTab('dashboard');
        fetchApiKeys();
      } else {
        setError(data.detail || 'Registration failed');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setActiveTab('home');
  };

  const handleCreateApiKey = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/api-keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ name: newKeyName })
      });

      const data = await response.json();
      if (response.ok) {
        setSuccess('API key created successfully!');
        setNewKeyName('');
        fetchApiKeys();
      } else {
        setError(data.detail || 'Failed to create API key');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteApiKey = async (keyId) => {
    if (!window.confirm('Are you sure you want to delete this API key?')) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok) {
        setSuccess('API key deleted successfully!');
        fetchApiKeys();
      } else {
        setError('Failed to delete API key');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    }
  };

  const handleWeatherTest = async (endpoint) => {
    setLoading(true);
    setError('');
    setWeatherData(null);

    if (!testApiKey) {
      setError('Please enter your API key first');
      setLoading(false);
      return;
    }

    try {
      let url = `${API_BASE_URL}/api/weather/${endpoint}?location=${weatherLocation}`;
      if (endpoint === 'forecast') {
        url += '&days=3';
      } else if (endpoint === 'history' || endpoint === 'astronomy') {
        url += '&date=2024-01-01';
      }

      const response = await fetch(url, {
        headers: { 'X-API-Key': testApiKey }
      });

      const data = await response.json();
      if (response.ok) {
        setWeatherData(data);
        setSuccess('Weather data fetched successfully!');
      } else {
        setError(data.detail || 'Failed to fetch weather data');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const HomePage = () => (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Hero Section */}
      <div className="relative bg-gradient-to-r from-blue-600 to-indigo-800 text-white">
        <div className="absolute inset-0 bg-black opacity-20"></div>
        <div className="relative max-w-7xl mx-auto px-4 py-24 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h1 className="text-5xl font-bold mb-6 leading-tight">
                SKYCASTER
                <span className="block text-3xl font-normal text-blue-200 mt-2">
                  Weather API as a Service
                </span>
              </h1>
              <p className="text-xl mb-8 text-blue-100">
                Access comprehensive weather data through our managed API platform. 
                Authentication, rate limiting, billing, and analytics - all handled for you.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <button
                  onClick={() => setActiveTab('register')}
                  className="bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-blue-50 transition-colors"
                >
                  Get Started Free
                </button>
                <button
                  onClick={() => setActiveTab('pricing')}
                  className="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-blue-600 transition-colors"
                >
                  View Pricing
                </button>
              </div>
            </div>
            <div className="hidden lg:block">
              <img 
                src="https://images.unsplash.com/photo-1530563885674-66db50a1af19?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwyfHx3ZWF0aGVyJTIwdGVjaG5vbG9neXxlbnwwfHx8fDE3NTI1MTkzNTF8MA&ixlib=rb-4.1.0&q=85"
                alt="Weather API Technology"
                className="rounded-lg shadow-2xl"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">Why Choose SKYCASTER?</h2>
            <p className="text-xl text-gray-600">Everything you need to integrate weather data into your applications</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center p-6 bg-blue-50 rounded-lg">
              <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-white text-2xl">🔑</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">API Key Management</h3>
              <p className="text-gray-600">Create, manage, and monitor your API keys with built-in security features</p>
            </div>
            
            <div className="text-center p-6 bg-indigo-50 rounded-lg">
              <div className="w-16 h-16 bg-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-white text-2xl">⚡</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">Rate Limiting</h3>
              <p className="text-gray-600">Intelligent rate limiting based on your subscription tier</p>
            </div>
            
            <div className="text-center p-6 bg-purple-50 rounded-lg">
              <div className="w-16 h-16 bg-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-white text-2xl">📊</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">Usage Analytics</h3>
              <p className="text-gray-600">Detailed analytics and usage tracking for optimization</p>
            </div>
          </div>
        </div>
      </div>

      {/* API Endpoints Section */}
      <div className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">Available Weather Endpoints</h2>
            <p className="text-xl text-gray-600">Access comprehensive weather data through our RESTful API</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { name: 'Current Weather', endpoint: '/weather/current', desc: 'Real-time weather conditions' },
              { name: 'Weather Forecast', endpoint: '/weather/forecast', desc: 'Multi-day weather predictions' },
              { name: 'Historical Data', endpoint: '/weather/history', desc: 'Past weather information' },
              { name: 'Location Search', endpoint: '/weather/search', desc: 'Find locations for weather data' },
              { name: 'Astronomy Data', endpoint: '/weather/astronomy', desc: 'Sunrise, sunset, moon phases' },
              { name: 'Marine Weather', endpoint: '/weather/marine', desc: 'Marine and tide information' }
            ].map((endpoint, index) => (
              <div key={index} className="bg-white p-6 rounded-lg shadow-sm border">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-gray-900">{endpoint.name}</h3>
                  <span className="text-sm text-blue-600 font-mono">{endpoint.endpoint}</span>
                </div>
                <p className="text-gray-600 text-sm">{endpoint.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  const PricingPage = () => (
    <div className="min-h-screen bg-gray-50 py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">Simple, Transparent Pricing</h2>
          <p className="text-xl text-gray-600">Choose the plan that fits your needs</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {subscriptionTiers.map((tier, index) => (
            <div key={index} className={`bg-white rounded-lg shadow-lg p-8 ${tier.key === 'developer' ? 'border-2 border-blue-500 transform scale-105' : ''}`}>
              {tier.key === 'developer' && (
                <div className="bg-blue-500 text-white text-center py-2 px-4 rounded-t-lg -mt-8 -mx-8 mb-6">
                  Most Popular
                </div>
              )}
              <h3 className="text-2xl font-bold text-gray-900 mb-2">{tier.name}</h3>
              <div className="text-4xl font-bold text-gray-900 mb-4">
                ₹{tier.price_monthly}
                <span className="text-lg font-normal text-gray-600">/month</span>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <span className="text-green-500 mr-3">✓</span>
                  <span>{tier.requests_per_month.toLocaleString()} requests/month</span>
                </li>
                <li className="flex items-center">
                  <span className="text-green-500 mr-3">✓</span>
                  <span>{tier.requests_per_minute} requests/minute</span>
                </li>
                <li className="flex items-center">
                  <span className="text-green-500 mr-3">✓</span>
                  <span>API Key Management</span>
                </li>
                <li className="flex items-center">
                  <span className="text-green-500 mr-3">✓</span>
                  <span>Usage Analytics</span>
                </li>
              </ul>
              <button
                onClick={() => setActiveTab('register')}
                className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors ${
                  tier.key === 'developer' 
                    ? 'bg-blue-600 text-white hover:bg-blue-700' 
                    : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                }`}
              >
                Get Started
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const LoginPage = () => (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
        <h2 className="text-2xl font-bold text-center mb-6">Login to SKYCASTER</h2>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        {success && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
            {success}
          </div>
        )}
        
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
            <input
              type="email"
              value={loginData.email}
              onChange={(e) => setLoginData({...loginData, email: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
            <input
              type="password"
              value={loginData.password}
              onChange={(e) => setLoginData({...loginData, password: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        
        <p className="text-center mt-4 text-sm text-gray-600">
          Don't have an account? 
          <button
            onClick={() => setActiveTab('register')}
            className="text-blue-600 hover:text-blue-700 ml-1"
          >
            Sign up
          </button>
        </p>
      </div>
    </div>
  );

  const RegisterPage = () => (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
        <h2 className="text-2xl font-bold text-center mb-6">Create SKYCASTER Account</h2>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        {success && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
            {success}
          </div>
        )}
        
        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
            <input
              type="email"
              value={registerData.email}
              onChange={(e) => setRegisterData({...registerData, email: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
            <input
              type="password"
              value={registerData.password}
              onChange={(e) => setRegisterData({...registerData, password: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>
        
        <p className="text-center mt-4 text-sm text-gray-600">
          Already have an account? 
          <button
            onClick={() => setActiveTab('login')}
            className="text-blue-600 hover:text-blue-700 ml-1"
          >
            Sign in
          </button>
        </p>
      </div>
    </div>
  );

  const DashboardPage = () => (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            <button
              onClick={handleLogout}
              className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Usage Overview */}
        {usage && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Usage Overview</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{usage.current_month_usage}</div>
                <div className="text-sm text-gray-600">Requests This Month</div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-green-600">{usage.monthly_limit}</div>
                <div className="text-sm text-gray-600">Monthly Limit</div>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">{usage.usage_percentage.toFixed(1)}%</div>
                <div className="text-sm text-gray-600">Usage Percentage</div>
              </div>
              <div className="bg-orange-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-orange-600">{usage.subscription_tier}</div>
                <div className="text-sm text-gray-600">Current Plan</div>
              </div>
            </div>
          </div>
        )}
        
        {/* API Keys Management */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">API Keys</h2>
            <button
              onClick={() => setActiveTab('create-key')}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
            >
              Create New Key
            </button>
          </div>
          
          <div className="space-y-4">
            {apiKeys.map((key, index) => (
              <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <div className="font-medium">{key.name}</div>
                  <div className="text-sm text-gray-600 font-mono">{key.key}</div>
                  <div className="text-xs text-gray-500">Created: {new Date(key.created_at).toLocaleDateString()}</div>
                </div>
                <button
                  onClick={() => handleDeleteApiKey(key.id)}
                  className="text-red-600 hover:text-red-700"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        </div>
        
        {/* Weather API Testing */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-4">Test Weather API</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
                  <input
                    type="text"
                    value={testApiKey}
                    onChange={(e) => setTestApiKey(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter your API key"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Location</label>
                  <input
                    type="text"
                    value={weatherLocation}
                    onChange={(e) => setWeatherLocation(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter location (e.g., London)"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => handleWeatherTest('current')}
                    disabled={loading}
                    className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    Current Weather
                  </button>
                  <button
                    onClick={() => handleWeatherTest('forecast')}
                    disabled={loading}
                    className="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:opacity-50"
                  >
                    Forecast
                  </button>
                  <button
                    onClick={() => handleWeatherTest('search')}
                    disabled={loading}
                    className="bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 disabled:opacity-50"
                  >
                    Search Location
                  </button>
                  <button
                    onClick={() => handleWeatherTest('astronomy')}
                    disabled={loading}
                    className="bg-orange-600 text-white py-2 px-4 rounded-md hover:bg-orange-700 disabled:opacity-50"
                  >
                    Astronomy
                  </button>
                </div>
              </div>
            </div>
            
            <div>
              <h3 className="text-lg font-medium mb-2">Response</h3>
              <div className="bg-gray-100 p-4 rounded-lg h-64 overflow-auto">
                {loading ? (
                  <div className="text-center text-gray-500">Loading...</div>
                ) : weatherData ? (
                  <pre className="text-sm">{JSON.stringify(weatherData, null, 2)}</pre>
                ) : (
                  <div className="text-gray-500">No data yet. Test an endpoint above.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const CreateKeyPage = () => (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <h1 className="text-2xl font-bold text-gray-900">Create API Key</h1>
            <button
              onClick={() => setActiveTab('dashboard')}
              className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
      
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold mb-4">Create New API Key</h2>
          
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}
          
          {success && (
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
              {success}
            </div>
          )}
          
          <form onSubmit={handleCreateApiKey} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Key Name</label>
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter a name for your API key"
                required
              />
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create API Key'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );

  const Navigation = () => (
    <nav className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <button
              onClick={() => setActiveTab('home')}
              className="text-2xl font-bold text-blue-600"
            >
              SKYCASTER
            </button>
          </div>
          
          <div className="flex items-center space-x-4">
            {!user ? (
              <>
                <button
                  onClick={() => setActiveTab('pricing')}
                  className="text-gray-700 hover:text-gray-900"
                >
                  Pricing
                </button>
                <button
                  onClick={() => setActiveTab('login')}
                  className="text-gray-700 hover:text-gray-900"
                >
                  Login
                </button>
                <button
                  onClick={() => setActiveTab('register')}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                >
                  Sign Up
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setActiveTab('dashboard')}
                  className="text-gray-700 hover:text-gray-900"
                >
                  Dashboard
                </button>
                <button
                  onClick={handleLogout}
                  className="text-gray-700 hover:text-gray-900"
                >
                  Logout
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );

  const renderCurrentTab = () => {
    switch (activeTab) {
      case 'home':
        return <HomePage />;
      case 'pricing':
        return <PricingPage />;
      case 'login':
        return <LoginPage />;
      case 'register':
        return <RegisterPage />;
      case 'dashboard':
        return <DashboardPage />;
      case 'create-key':
        return <CreateKeyPage />;
      default:
        return <HomePage />;
    }
  };

  return (
    <div className="App">
      {activeTab !== 'home' && <Navigation />}
      {renderCurrentTab()}
    </div>
  );
}

export default App;