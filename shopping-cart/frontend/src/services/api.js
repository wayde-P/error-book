/**
 * API service - handles all HTTP requests to the backend.
 * Uses the API Gateway URL configured at build time.
 */
// Falls back to /api for local dev — Vite proxies /api to localhost:5000
// (see vite.config.js). VITE_API_URL is injected at build time for production.
const API_BASE = import.meta.env.VITE_API_URL || '/api';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  return response.json();
}

// Product endpoints
export const getProducts = (category) => {
  const params = category ? `?category=${encodeURIComponent(category)}` : '';
  return request(`/products${params}`);
};

export const getProduct = (id) => request(`/products/${id}`);
export const getCategories = () => request('/products/categories');
export const searchProducts = (query) => request(`/products/search?q=${encodeURIComponent(query)}`);

// Cart endpoints
export const getCart = (code) => {
  const params = code ? `?code=${encodeURIComponent(code)}` : '';
  return request(`/cart${params}`);
};

export const addToCart = (productId, quantity = 1) =>
  request('/cart/items', {
    method: 'POST',
    body: JSON.stringify({ productId, quantity }),
  });

export const updateCartItem = (productId, quantity) =>
  request(`/cart/items/${productId}`, {
    method: 'PUT',
    body: JSON.stringify({ quantity }),
  });

export const removeFromCart = (productId) =>
  request(`/cart/items/${productId}`, { method: 'DELETE' });

export const clearCart = () => request('/cart', { method: 'DELETE' });

// Discount endpoints
export const validateDiscount = (code, subtotal) =>
  request('/discounts/validate', {
    method: 'POST',
    body: JSON.stringify({ code, subtotal }),
  });

// Order endpoints
export const createOrder = (shippingAddress, discountCode) =>
  request('/orders', {
    method: 'POST',
    body: JSON.stringify({ shippingAddress, ...(discountCode && { discountCode }) }),
  });

export const getOrders = () => request('/orders');
export const getOrder = (orderId) => request(`/orders/${orderId}`);

// Wishlist endpoints
export const getWishlist = () => request('/wishlist');

export const addToWishlist = (productId) =>
  request('/wishlist/items', {
    method: 'POST',
    body: JSON.stringify({ productId }),
  });

export const removeFromWishlist = (productId) =>
  request(`/wishlist/items/${productId}`, { method: 'DELETE' });

export const moveToCart = (productId, keepInWishlist) =>
  request(`/wishlist/items/${productId}/move-to-cart`, {
    method: 'POST',
    body: JSON.stringify({ keepInWishlist }),
  });
