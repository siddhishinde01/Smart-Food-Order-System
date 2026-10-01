/* ─────────────────────────────────────────────────────────────────────────────
   FoodTech — Shared JavaScript Utilities
───────────────────────────────────────────────────────────────────────────── */

// ── Cart helpers ──────────────────────────────────────────────────────────────
// ── Cart helpers ──────────────────────────────────────────────────────────────
function getCart() {
  try {
    const data = JSON.parse(localStorage.getItem('ft_cart') || '[]');
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

function saveCart(cart) {
  if (!Array.isArray(cart)) cart = [];
  localStorage.setItem('ft_cart', JSON.stringify(cart));
}

function updateCartBadge() {
  const cart  = getCart();
  const total = cart.reduce((s, i) => s + (Number(i.qty) || 0), 0);
  document.querySelectorAll('#cart-count').forEach(el => {
    el.textContent = total;
    el.style.display = total > 0 ? '' : 'none';
  });
}

function addToCart(id, name, price, restId, restName) {
  let cart = getCart();

  // Prevent mixing items from different restaurants if restaurant_id is present
  if (cart.length > 0 && cart[0].restaurant_id && restId && cart[0].restaurant_id !== restId) {
    const existingRestName = cart[0].restaurant_name || 'another restaurant';
    if (!confirm(`Your cart has items from ${existingRestName}. Clear cart and start fresh?`)) {
      return false;
    }
    cart = [];
  }

  const itemId = String(id);
  const existing = cart.find(i => (i.menu_id === itemId || i.id === itemId));
  if (existing) {
    existing.qty = (Number(existing.qty) || 0) + 1;
  } else {
    cart.push({
      id: itemId,
      menu_id: itemId,
      name: String(name),
      price: Number(price) || 0,
      qty: 1,
      restaurant_id: restId || (cart[0] ? cart[0].restaurant_id : ''),
      restaurant_name: restName || (cart[0] ? cart[0].restaurant_name : '')
    });
  }

  saveCart(cart);
  updateCartBadge();

  if (typeof renderCartDrawer === 'function') {
    renderCartDrawer();
  }
  showToast(`✅ ${name} added to cart`, 'success');
  if (typeof openCart === 'function') {
    openCart();
  }
  return true;
}

// ── Toast notifications ───────────────────────────────────────────────────────
function showToast(message, type = '') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast ' + type;
  const icons = { success: '✅', error: '❌', warning: '⚠️' };
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span> ${message}`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// ── Format helpers ────────────────────────────────────────────────────────────
function statusLabel(s) {
  const map = {
    pending:          'Pending',
    preparing:        'Preparing',
    out_for_delivery: 'Out for Delivery',
    delivered:        'Delivered',
  };
  return map[s] || s;
}

function priorityColor(cls) {
  return { CRITICAL: '#dc2626', HIGH: '#ea580c', NORMAL: '#16a34a', LOW: '#2563eb' }[cls] || '#6b7280';
}

function timeAgo(isoStr) {
  const diff = (Date.now() - new Date(isoStr).getTime()) / 60000;
  if (diff < 1) return 'just now';
  return Math.round(diff) + ' min ago';
}
