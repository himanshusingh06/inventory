const base = import.meta.env.VITE_API_BASE_URL || '';
let authToken = localStorage.getItem('inventory_token') || '';

export function setAuthToken(token) {
  authToken = token || '';
  if (authToken) {
    localStorage.setItem('inventory_token', authToken);
  } else {
    localStorage.removeItem('inventory_token');
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${base}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export const api = {
  health: () => request('/api/health'),
  login: (data) => request('/api/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  me: () => request('/api/auth/me'),
  users: () => request('/api/auth/users'),
  createUser: (data) => request('/api/auth/users', { method: 'POST', body: JSON.stringify(data) }),
  summary: () => request('/api/payments/dashboard'),
  stores: () => request('/api/stores'),
  customers: () => request('/api/customers'),
  products: () => request('/api/products'),
  lowStockProducts: () => request('/api/products/low-stock'),
  stockMovements: () => request('/api/stock-movements'),
  invoices: () => request('/api/invoices'),
  paymentOptions: () => request('/api/payments/options'),
  ledgers: () => request('/api/payments/ledgers'),
  refunds: () => request('/api/payments/refunds'),
  reports: () => request('/api/payments/reports'),
  expirePayments: () => request('/api/payments/expire', { method: 'POST' }),
  createStore: (data) => request('/api/stores', { method: 'POST', body: JSON.stringify(data) }),
  createCustomer: (data) => request('/api/customers', { method: 'POST', body: JSON.stringify(data) }),
  createProduct: (data) => request('/api/products', { method: 'POST', body: JSON.stringify(data) }),
  adjustStock: (productId, data) => request(`/api/products/${productId}/stock`, { method: 'POST', body: JSON.stringify(data) }),
  createInvoice: (data) => request('/api/invoices', { method: 'POST', body: JSON.stringify(data) }),
  createPaymentSession: (data) => request('/api/payments/create-session', { method: 'POST', body: JSON.stringify(data) }),
  simulatePayment: (paymentId, data) => request(`/api/payments/${paymentId}/simulate`, { method: 'POST', body: JSON.stringify(data) }),
  requestRefund: (data) => request('/api/payments/refunds', { method: 'POST', body: JSON.stringify(data) }),
  approveRefund: (refundId, data) => request(`/api/payments/refunds/${refundId}/approve`, { method: 'POST', body: JSON.stringify(data) }),
  payment: (paymentId) => request(`/api/payments/${paymentId}`),
};
