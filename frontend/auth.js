/**
 * Authentication Service
 * Handles user signup, login, logout, and token storage
 */

class AuthService {
  constructor() {
    this.apiBase = 'http://127.0.0.1:8000/api';
    this.tokenKey = 'learnascent_token';
    this.userKey = 'learnascent_user';
  }

  /**
   * Sign up a new user
   */
  async signup(email, password) {
    try {
      const response = await fetch(`${this.apiBase}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Signup failed');
      }

      const data = await response.json();
      this.setToken(data.access_token);
      this.setUser(data.user_id);
      return data;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Log in an existing user
   */
  async login(email, password) {
    try {
      const response = await fetch(`${this.apiBase}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      this.setToken(data.access_token);
      this.setUser(data.user_id);
      return data;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get current authenticated user
   */
  async getCurrentUser() {
    const token = this.getToken();
    if (!token) return null;

    try {
      const response = await fetch(`${this.apiBase}/auth/me`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        this.logout();
        return null;
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching current user:', error);
      return null;
    }
  }

  /**
   * Log out (call backend and clear local state)
   */
  async logout() {
    const token = this.getToken();
    if (token) {
      try {
        await fetch(`${this.apiBase}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });
      } catch (error) {
        console.error('Error calling logout endpoint:', error);
      }
    }
    this.clearToken();
    this.clearUser();
  }

  /**
   * Get stored token
   */
  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  /**
   * Store token
   */
  setToken(token) {
    localStorage.setItem(this.tokenKey, token);
  }

  /**
   * Clear token
   */
  clearToken() {
    localStorage.removeItem(this.tokenKey);
  }

  /**
   * Get stored user ID
   */
  getUser() {
    const user = localStorage.getItem(this.userKey);
    return user ? JSON.parse(user) : null;
  }

  /**
   * Store user
   */
  setUser(userId) {
    localStorage.setItem(this.userKey, JSON.stringify(userId));
  }

  /**
   * Clear user
   */
  clearUser() {
    localStorage.removeItem(this.userKey);
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    return !!this.getToken();
  }
}

// Export as global for use in HTML
const auth = new AuthService();
