import { useState } from 'react';
import { useCart } from '../context/CartContext';
import { useWishlist } from '../context/WishlistContext';

function ProductCard({ product }) {
  const { addItem, loading: cartLoading } = useCart();
  const { addToWishlist, removeFromWishlist, isInWishlist, loading: wishlistLoading } = useWishlist();
  const [quantity, setQuantity] = useState(1);

  const inWishlist = isInWishlist(product.productId);

  function handleAdd() {
    addItem(product.productId, quantity);
    setQuantity(1);
  }

  function handleWishlist() {
    if (inWishlist) {
      removeFromWishlist(product.productId);
    } else {
      addToWishlist(product.productId);
    }
  }

  return (
    <div className="product-card">
      <div className="product-emoji">{product.image}</div>
      <div className="product-category">{product.category}</div>
      <div className="product-name">{product.name}</div>
      <div className="product-description">{product.description}</div>
      <div className="product-price">${product.price.toFixed(2)}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.75rem' }}>
        <div className="quantity-controls">
          <button onClick={() => setQuantity(q => Math.max(1, q - 1))} disabled={cartLoading}>−</button>
          <span>{quantity}</span>
          <button onClick={() => setQuantity(q => q + 1)} disabled={cartLoading}>+</button>
        </div>
        <button
          className="btn btn-primary"
          onClick={handleAdd}
          disabled={cartLoading}
        >
          Add to Cart
        </button>
        <button
          onClick={handleWishlist}
          disabled={wishlistLoading}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '1.4rem',
            lineHeight: 1,
            padding: '0.2rem',
          }}
          title={inWishlist ? 'Remove from wishlist' : 'Save to wishlist'}
        >
          {inWishlist ? '♥' : '♡'}
        </button>
      </div>
    </div>
  );
}

export default ProductCard;
