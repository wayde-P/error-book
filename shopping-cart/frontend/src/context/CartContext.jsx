import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import * as api from '../services/api';

const CartContext = createContext();

export function CartProvider({ children }) {
  const [cart, setCart] = useState({ items: [], itemCount: 0, subtotal: 0, tax: 0, total: 0 });
  const [loading, setLoading] = useState(false);
  const [discount, setDiscount] = useState(null);

  const fetchCart = useCallback(async (code) => {
    try {
      const data = await api.getCart(code || (discount?.code));
      setCart(data);
    } catch (err) {
      console.error('Failed to fetch cart:', err);
    }
  }, [discount]);

  useEffect(() => {
    fetchCart();
  }, [fetchCart]);

  // After every mutation, re-fetch the full cart from the server so totals
  // and item counts stay in sync without duplicating calculation logic client-side.
  const addItem = async (productId, quantity = 1) => {
    setLoading(true);
    try {
      await api.addToCart(productId, quantity);
      await fetchCart();
    } finally {
      setLoading(false);
    }
  };

  const updateQuantity = async (productId, quantity) => {
    setLoading(true);
    try {
      await api.updateCartItem(productId, quantity);
      await fetchCart();
    } finally {
      setLoading(false);
    }
  };

  const removeItem = async (productId) => {
    setLoading(true);
    try {
      await api.removeFromCart(productId);
      await fetchCart();
    } finally {
      setLoading(false);
    }
  };

  const clearAll = async () => {
    setLoading(true);
    try {
      await api.clearCart();
      setDiscount(null);
      await fetchCart();
    } finally {
      setLoading(false);
    }
  };

  const applyDiscount = async (code) => {
    const result = await api.validateDiscount(code, cart.subtotal);
    setDiscount(result);
    await fetchCart(result.code);
    return result;
  };

  const removeDiscount = async () => {
    setDiscount(null);
    await fetchCart(null);
  };

  return (
    <CartContext.Provider value={{ cart, loading, discount, addItem, updateQuantity, removeItem, clearAll, fetchCart, applyDiscount, removeDiscount }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error('useCart must be used within CartProvider');
  return context;
}
