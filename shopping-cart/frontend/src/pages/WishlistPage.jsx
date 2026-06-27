import { useState } from 'react';
import { useWishlist } from '../context/WishlistContext';

function WishlistPage() {
  const { wishlist, loading, removeFromWishlist, moveToCart } = useWishlist();
  const [movingId, setMovingId] = useState(null);

  async function handleMoveToCart(productId) {
    const keep = window.confirm('Keep this item in your wishlist after adding to cart?');
    setMovingId(productId);
    try {
      await moveToCart(productId, keep);
    } finally {
      setMovingId(null);
    }
  }

  if (wishlist.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-emoji">♡</div>
        <h2>Your wishlist is empty</h2>
        <p>Browse products and click the heart icon to save items for later!</p>
      </div>
    );
  }

  return (
    <div className="cart-container">
      <h2>Wishlist ({wishlist.length} items)</h2>
      <div style={{ marginTop: '1rem' }}>
        {wishlist.map((item) => (
          <div
            key={item.productId}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '1rem',
              padding: '1rem',
              borderBottom: '1px solid #eee',
            }}
          >
            <span style={{ fontSize: '2rem' }}>{item.image}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>{item.name}</div>
              <div style={{ color: '#666' }}>${item.price.toFixed(2)}</div>
            </div>
            <button
              className="btn btn-primary"
              onClick={() => handleMoveToCart(item.productId)}
              disabled={loading || movingId === item.productId}
            >
              {movingId === item.productId ? 'Adding...' : 'Add to Cart'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => removeFromWishlist(item.productId)}
              disabled={loading}
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default WishlistPage;
