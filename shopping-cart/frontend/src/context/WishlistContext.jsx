import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import * as api from '../services/api';

const WishlistContext = createContext();

export function WishlistProvider({ children }) {
  const [wishlist, setWishlist] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchWishlist = useCallback(async () => {
    try {
      const data = await api.getWishlist();
      setWishlist(data);
    } catch (err) {
      console.error('Failed to fetch wishlist:', err);
    }
  }, []);

  useEffect(() => {
    fetchWishlist();
  }, [fetchWishlist]);

  const addToWishlist = async (productId) => {
    setLoading(true);
    try {
      await api.addToWishlist(productId);
      await fetchWishlist();
    } finally {
      setLoading(false);
    }
  };

  const removeFromWishlist = async (productId) => {
    setLoading(true);
    try {
      await api.removeFromWishlist(productId);
      await fetchWishlist();
    } finally {
      setLoading(false);
    }
  };

  const moveToCart = async (productId, keepInWishlist) => {
    setLoading(true);
    try {
      await api.moveToCart(productId, keepInWishlist);
      await fetchWishlist();
    } finally {
      setLoading(false);
    }
  };

  const isInWishlist = (productId) =>
    wishlist.some((item) => item.productId === productId);

  return (
    <WishlistContext.Provider value={{ wishlist, loading, addToWishlist, removeFromWishlist, moveToCart, isInWishlist }}>
      {children}
    </WishlistContext.Provider>
  );
}

export function useWishlist() {
  const context = useContext(WishlistContext);
  if (!context) throw new Error('useWishlist must be used within WishlistProvider');
  return context;
}
