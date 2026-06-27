import { Link } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useWishlist } from '../context/WishlistContext';

function Header() {
  const { cart } = useCart();
  const { wishlist } = useWishlist();

  return (
    <header className="header">
      <Link to="/">
        <h1>🛒 Workshop Shop</h1>
      </Link>
      <nav className="nav-links">
        <Link to="/">Products</Link>
        <Link to="/cart">
          Cart
          {cart.itemCount > 0 && <span className="cart-badge">{cart.itemCount}</span>}
        </Link>
        <Link to="/wishlist">
          Wishlist
          {wishlist.length > 0 && <span className="cart-badge">{wishlist.length}</span>}
        </Link>
        <Link to="/orders">Orders</Link>
      </nav>
    </header>
  );
}

export default Header;
