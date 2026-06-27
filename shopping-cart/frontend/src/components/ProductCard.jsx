import { useState } from 'react';
import { useCart } from '../context/CartContext';

function ProductCard({ product }) {
  const { addItem, loading } = useCart();
  const [quantity, setQuantity] = useState(1);

  function handleAdd() {
    addItem(product.productId, quantity);
    setQuantity(1);
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
          <button onClick={() => setQuantity(q => Math.max(1, q - 1))} disabled={loading}>−</button>
          <span>{quantity}</span>
          <button onClick={() => setQuantity(q => q + 1)} disabled={loading}>+</button>
        </div>
        <button
          className="btn btn-primary"
          onClick={handleAdd}
          disabled={loading}
        >
          Add to Cart
        </button>
      </div>
    </div>
  );
}

export default ProductCard;
