const $ = (selector) => document.querySelector(selector);
const money = (value) => Number(value).toLocaleString("pt-BR", {
  style: "currency",
  currency: "BRL",
});
const LABEL = {
  pending: "Aguardando pagamento",
  confirmed: "Aguardando separação",
  preparing: "Em separação",
  ready: "Pronto para retirada",
  completed: "Retirado",
  cancelled: "Cancelado",
};
const PRODUCT_ICONS = {
  Celulares: "📱",
  Áudio: "🎧",
  Informática: "💻",
  TV: "📺",
  Casa: "☕",
};
const API = (new URLSearchParams(location.search).get("api") || window.API_BASE || "")
  .replace(/\/$/, "");

let products = [];
let availabilityByProduct = {};
let cart = {};
let selectedStore = null;
let pickupLocation = null;
let currentProduct = null;

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API}/api/v1${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new Error(
      `Não consegui falar com a API (${API || "mesma origem"}). Confira se ela está no ar e a URL em docs/config.js.`,
    );
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string" ? data.detail : `Erro ${response.status}. Verifique os dados.`,
    );
  }
  return data;
}

function flash(message, success = false) {
  const container = $("#msg");
  container.replaceChildren();
  if (!message) return;

  const notice = document.createElement("div");
  notice.className = success ? "okmsg" : "err";
  notice.textContent = message;
  container.append(notice);
}

function showScreen(screenId) {
  const visibleNav = ["orders", "confirmation"].includes(screenId) ? "shop" : screenId;
  document.querySelectorAll(".screen").forEach((section) => {
    section.classList.toggle("hide", section.id !== screenId);
  });
  document.querySelectorAll(".main-nav [data-t]").forEach((button) => {
    button.classList.toggle("on", button.dataset.t === visibleNav);
  });

  flash("");
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (screenId === "orders") loadMyOrders();
  if (screenId === "store") loadStoreOrders();
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-t]");
  if (!button) return;
  event.preventDefault();
  showScreen(button.dataset.t);
});

function productIcon(product) {
  return PRODUCT_ICONS[product.category] || "🛍️";
}

function renderProducts() {
  const query = $("#productSearch").value.trim().toLocaleLowerCase("pt-BR");
  const visibleProducts = products.filter((product) =>
    `${product.name} ${product.description} ${product.category}`
      .toLocaleLowerCase("pt-BR")
      .includes(query),
  );

  $("#products").innerHTML = visibleProducts.length
    ? visibleProducts.map((product) => {
      const availability = availabilityByProduct[product.id] || [];
      const stores = availability.map(({ store, quantity }) => {
        const shortName = store.name.replace("MegaLoja ", "");
        return `<span class="stock-chip ${quantity > 0 ? "in-stock" : "out-of-stock"}">${shortName}<b>${quantity}</b></span>`;
      }).join("");

      return `
        <article class="product-card">
          <div class="product-art art-${product.category.toLowerCase().replace(/\s+/g, "-")}" aria-hidden="true">
            <span>${productIcon(product)}</span>
            <span class="art-sparkle">✦</span>
          </div>
          <div class="product-card-body">
            <p class="product-category">${product.category}</p>
            <h2>${product.name}</h2>
            <p class="product-description">${product.description}</p>
            <p class="product-price">${money(product.price)}</p>
            <div class="stock-summary">
              <span class="stock-title">Estoque por loja</span>
              <div class="stock-chips">${stores || '<span class="muted">Indisponível</span>'}</div>
            </div>
            <div class="product-actions">
              <button type="button" class="button button-outline" onclick="openProduct('${product.id}')">Ver retirada</button>
              <button type="button" class="button button-primary" onclick="add('${product.id}')">Adicionar</button>
            </div>
          </div>
        </article>`;
    }).join("")
    : '<p class="empty-state">Nenhum produto encontrado. Tente outra busca.</p>';
}

async function loadProducts() {
  products = await api("/products");
  const availability = await Promise.all(
    products.map((product) => api(`/products/${product.id}/availability`)),
  );
  availabilityByProduct = Object.fromEntries(
    products.map((product, index) => [product.id, availability[index]]),
  );
  renderProducts();
}

function setLocationStatus(message) {
  $("#locationStatus").textContent = message;
}

function useMyLocation() {
  if (!navigator.geolocation) {
    setLocationStatus("Seu navegador não oferece localização. As lojas serão exibidas por disponibilidade.");
    flash("Não foi possível acessar a localização neste navegador.");
    return;
  }

  setLocationStatus("Buscando sua localização...");
  navigator.geolocation.getCurrentPosition(
    (position) => {
      pickupLocation = {
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      };
      setLocationStatus("Lojas ordenadas pela distância da sua localização.");
      if (currentProduct) {
        loadProductOptions();
      } else if (Object.keys(cart).length) {
        loadPickupOptions();
      }
    },
    (error) => {
      const messages = {
        1: "Permissão de localização negada. Você ainda pode escolher uma loja pela disponibilidade.",
        2: "Localização indisponível. Você ainda pode escolher uma loja pela disponibilidade.",
        3: "A busca pela localização demorou demais. Tente novamente ou escolha uma loja pela disponibilidade.",
      };
      setLocationStatus("Lojas exibidas por disponibilidade.");
      flash(messages[error.code] || "Não foi possível obter sua localização.");
    },
    { enableHighAccuracy: false, maximumAge: 60000, timeout: 10000 },
  );
}

function pickupItems(includeProduct = null) {
  const quantities = { ...cart };
  if (includeProduct) {
    quantities[includeProduct.id] = (quantities[includeProduct.id] || 0) + 1;
  }
  return Object.entries(quantities).map(([product_id, quantity]) => ({
    product_id,
    quantity,
  }));
}

async function requestPickupOptions(items) {
  const body = { items };
  if (pickupLocation) {
    body.lat = pickupLocation.lat;
    body.lng = pickupLocation.lng;
  }
  return api("/pickup/options", { method: "POST", body });
}

function storeOptionMarkup(option, groupName, selectedId) {
  const selected = option.store.id === selectedId;
  const missingNames = (option.missing || []).map((productId) =>
    products.find((product) => product.id === productId)?.name || productId,
  );
  const availability = option.can_fulfill
    ? "Disponível para retirada"
    : `Sem estoque: ${missingNames.join(", ")}`;
  const distance = option.distance_km === null || option.distance_km === undefined
    ? ""
    : `<span class="store-distance">${Number(option.distance_km).toLocaleString("pt-BR")} km</span>`;

  return `
    <label class="store-option ${option.can_fulfill ? "" : "is-unavailable"} ${selected ? "is-selected" : ""}">
      <input type="radio" name="${groupName}" value="${option.store.id}" ${selected ? "checked" : ""} ${option.can_fulfill ? "" : "disabled"}>
      <span class="store-radio" aria-hidden="true"></span>
      <span class="store-option-copy">
        <strong>${option.store.name}</strong>
        <span>${option.store.address}</span>
        <small>${availability}</small>
      </span>
      <span class="store-option-meta">
        ${option.recommended && option.can_fulfill ? '<span class="recommended-badge">Recomendada</span>' : ""}
        ${distance}
      </span>
    </label>`;
}

function renderStoreOptions(container, options, groupName, selectedId, onSelect) {
  container.innerHTML = options.length
    ? options.map((option) => storeOptionMarkup(option, groupName, selectedId)).join("")
    : '<p class="empty-state">Nenhuma loja encontrada.</p>';
  container.querySelectorAll('input[type="radio"]').forEach((radio) => {
    radio.addEventListener("change", () => onSelect(radio.value));
  });
}

async function openProduct(productId) {
  currentProduct = products.find((product) => product.id === productId);
  if (!currentProduct) return;

  $("#products").classList.add("hide");
  const detail = $("#productDetail");
  detail.classList.remove("hide");
  detail.innerHTML = `
    <button type="button" id="detailBack" class="text-button back-button"><span aria-hidden="true">←</span> Voltar aos produtos</button>
    <div class="product-detail-main">
      <div class="product-detail-art" aria-hidden="true"><span>${productIcon(currentProduct)}</span></div>
      <div class="product-detail-copy">
        <p class="product-category">${currentProduct.category}</p>
        <h2>${currentProduct.name}</h2>
        <p class="product-description">${currentProduct.description}</p>
        <p class="product-price">${money(currentProduct.price)}</p>
        <span class="free-pickup-pill"><span aria-hidden="true">✓</span> Click & Collect gratuito</span>
      </div>
    </div>
    <div class="product-pickup">
      <div class="pickup-heading">
        <div><p class="eyebrow">RETIRE PERTO DE VOCÊ</p><h3>Retirar em qual loja?</h3></div>
        <button type="button" id="detailLocation" class="text-button">Usar minha localização</button>
      </div>
      <div id="detailOptions" class="store-list"></div>
      <button type="button" id="detailAdd" class="button button-primary" disabled>Adicionar ao carrinho <span aria-hidden="true">→</span></button>
    </div>`;

  $("#detailBack").addEventListener("click", closeProduct);
  $("#detailLocation").addEventListener("click", useMyLocation);
  $("#detailAdd").addEventListener("click", () => {
    if (!selectedStore) {
      flash("Escolha uma loja com todos os itens disponíveis.");
      return;
    }
    add(currentProduct.id);
    closeProduct();
    $("#cart").scrollIntoView({ behavior: "smooth", block: "center" });
  });

  await loadProductOptions();
  detail.scrollIntoView({ behavior: "smooth", block: "start" });
}

function closeProduct() {
  currentProduct = null;
  $("#productDetail").classList.add("hide");
  $("#products").classList.remove("hide");
}

async function loadProductOptions() {
  if (!currentProduct) return;
  const container = $("#detailOptions");
  container.innerHTML = '<p class="muted">Buscando disponibilidade nas lojas...</p>';
  try {
    const options = await requestPickupOptions(pickupItems(currentProduct));
    const recommended = options.find((option) =>
      option.store.id === selectedStore && option.can_fulfill,
    ) || options.find((option) => option.recommended && option.can_fulfill)
      || options.find((option) => option.can_fulfill);
    selectedStore = recommended ? recommended.store.id : null;
    const selectStore = (storeId) => {
      selectedStore = storeId;
      renderStoreOptions(container, options, "productStore", selectedStore, selectStore);
      $("#detailAdd").disabled = !selectedStore;
    };
    renderStoreOptions(container, options, "productStore", selectedStore, selectStore);
    $("#detailAdd").disabled = !selectedStore;
  } catch (error) {
    container.innerHTML = '<p class="empty-state">Não foi possível carregar as lojas.</p>';
    $("#detailAdd").disabled = true;
    flash(error.message);
  }
}

function add(productId) {
  if ((cart[productId] || 0) >= 50) {
    flash("O limite é de 50 unidades por produto.");
    return;
  }
  cart[productId] = (cart[productId] || 0) + 1;
  renderCart();
  flash("Produto adicionado ao carrinho.", true);
}

function setQuantity(productId, value) {
  const quantity = Math.min(50, Math.max(1, Number(value) || 1));
  cart[productId] = quantity;
  renderCart();
}

function changeQuantity(productId, delta) {
  setQuantity(productId, (cart[productId] || 1) + delta);
}

function removeFromCart(productId) {
  delete cart[productId];
  renderCart();
}

function renderCart() {
  const cartItems = Object.entries(cart);
  const count = cartItems.reduce((sum, [, quantity]) => sum + quantity, 0);
  $("#cartCount").textContent = `${count} ${count === 1 ? "item" : "itens"}`;

  if (!cartItems.length) {
    $("#cart").innerHTML = `
      <div class="cart-empty">
        <span aria-hidden="true">🛍️</span>
        <p>Seu carrinho está vazio.</p>
        <small>Adicione produtos para escolher uma loja.</small>
      </div>`;
    $("#checkout").classList.add("hide");
    $("#checkoutDetails").classList.add("hide");
    return;
  }

  let total = 0;
  $("#cart").innerHTML = cartItems.map(([productId, quantity]) => {
    const product = products.find((item) => item.id === productId);
    if (!product) return "";
    const subtotal = Number(product.price) * quantity;
    total += subtotal;
    return `
      <article class="cart-item">
        <span class="cart-item-icon" aria-hidden="true">${productIcon(product)}</span>
        <div class="cart-item-copy">
          <strong>${product.name}</strong>
          <span>${money(product.price)} cada</span>
          <div class="quantity-control">
            <button type="button" aria-label="Diminuir quantidade" onclick="changeQuantity('${productId}', -1)">−</button>
            <input type="number" min="1" max="50" value="${quantity}" aria-label="Quantidade de ${product.name}" onchange="setQuantity('${productId}', this.value)">
            <button type="button" aria-label="Aumentar quantidade" onclick="changeQuantity('${productId}', 1)">+</button>
          </div>
        </div>
        <div class="cart-item-total">
          <strong>${money(subtotal)}</strong>
          <button type="button" class="remove-button" onclick="removeFromCart('${productId}')">Remover</button>
        </div>
      </article>`;
  }).join("") + `<div class="cart-total"><span>Total</span><strong>${money(total)}</strong></div>`;

  $("#checkout").classList.remove("hide");
  $("#checkoutDetails").classList.add("hide");
  loadPickupOptions();
}

async function loadPickupOptions() {
  if (!Object.keys(cart).length) return;
  const container = $("#options");
  container.innerHTML = '<p class="muted">Buscando disponibilidade nas lojas...</p>';
  $("#continueCheckout").disabled = true;
  try {
    const options = await requestPickupOptions(pickupItems());
    const recommended = options.find((option) =>
      option.store.id === selectedStore && option.can_fulfill,
    ) || options.find((option) => option.recommended && option.can_fulfill)
      || options.find((option) => option.can_fulfill);
    selectedStore = recommended ? recommended.store.id : null;
    const selectStore = (storeId) => {
      selectedStore = storeId;
      renderStoreOptions(container, options, "pickupStore", selectedStore, selectStore);
      $("#continueCheckout").disabled = !selectedStore;
    };
    renderStoreOptions(container, options, "pickupStore", selectedStore, selectStore);
    $("#continueCheckout").disabled = !selectedStore;
  } catch (error) {
    container.innerHTML = '<p class="empty-state">Não foi possível carregar as lojas.</p>';
    $("#continueCheckout").disabled = true;
    flash(error.message);
  }
}

$("#productSearch").addEventListener("input", renderProducts);
$("#useLocation").addEventListener("click", useMyLocation);
$("#continueCheckout").addEventListener("click", () => {
  if (!selectedStore) {
    flash("Escolha uma loja com todos os itens disponíveis.");
    return;
  }
  $("#checkoutDetails").classList.remove("hide");
  $("#checkoutDetails").scrollIntoView({ behavior: "smooth", block: "center" });
  $("#c_name").focus({ preventScroll: true });
});

$("#checkoutDetails").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedStore || !Object.keys(cart).length) {
    flash("Escolha uma loja e adicione itens antes de finalizar a compra.");
    return;
  }

  const button = $("#buy");
  button.disabled = true;
  try {
    const order = await api("/orders", {
      method: "POST",
      body: {
        customer: {
          name: $("#c_name").value.trim(),
          email: $("#c_email").value.trim(),
          phone: $("#c_phone").value.trim(),
        },
        store_id: selectedStore,
        items: pickupItems(),
        payment: {
          method: $("#pay").value,
          token: $("#tok").value.trim() || null,
        },
      },
    });
    cart = {};
    selectedStore = null;
    currentProduct = null;
    $("#checkoutDetails").reset();
    renderCart();
    await loadProducts();
    $("#q_email").value = order.customer_email;
    $("#confirmationContent").innerHTML = `
      <div class="confirmation-card">
        <div class="celebration" aria-hidden="true"><span>✦</span><span>✧</span><span>✦</span><span>✧</span><span>✦</span></div>
        <span class="confirmation-check" aria-hidden="true">✓</span>
        <p class="eyebrow">PEDIDO CONFIRMADO</p>
        <h1>Compra feita,<br><em>agora é só retirar.</em></h1>
        <p class="confirmation-copy">Seu pedido <strong>${order.id}</strong> foi confirmado. Você receberá uma atualização quando ele estiver pronto.</p>
        <div class="confirmation-summary">
          <div><span>Loja de retirada</span><strong>${order.store.name}</strong></div>
          <div><span>Total pago</span><strong>${money(order.total)}</strong></div>
        </div>
        <p class="pickup-code-label">Seu código de retirada</p>
        <div class="code">${order.pickup_code}</div>
        <p class="muted">Apresente este código no balcão Click & Collect quando o pedido estiver pronto.</p>
        <div class="confirmation-actions">
          <button type="button" class="button button-primary" data-t="orders">Acompanhar pedido</button>
          <button type="button" class="button button-outline" data-t="shop">Continuar comprando</button>
        </div>
      </div>`;
    showScreen("confirmation");
  } catch (error) {
    flash(error.message);
  } finally {
    button.disabled = false;
  }
});

function orderCard(order, actions = "") {
  const items = order.items.map((item) =>
    `<span>${item.quantity}× ${item.product_name}</span>`,
  ).join("");
  const statusLabel = LABEL[order.status] || order.status;
  return `
    <article class="card order-card">
      <div class="order-card-top">
        <div>
          <p class="order-id">${order.id}</p>
          <span class="badge status-${order.status}">${statusLabel}</span>
        </div>
        <div class="order-total">${money(order.total)}</div>
      </div>
      <div class="order-customer">${order.store.name} <span>·</span> ${order.customer_name}</div>
      <div class="order-items">${items}</div>
      <div class="order-card-bottom">
        <span class="order-pickup-code">Código <strong>${order.pickup_code}</strong></span>
        ${actions ? `<div class="order-actions">${actions}</div>` : ""}
      </div>
    </article>`;
}

async function loadMyOrders() {
  const email = $("#q_email").value.trim();
  if (!email) {
    $("#myorders").innerHTML = '<p class="empty-state">Informe seu e-mail para consultar pedidos.</p>';
    return;
  }
  try {
    const orders = await api(`/orders?email=${encodeURIComponent(email)}`);
    $("#myorders").innerHTML = orders.length
      ? orders.slice().reverse().map((order) => orderCard(
        order,
        ["confirmed", "preparing", "ready"].includes(order.status)
          ? `<button type="button" class="button button-outline button-small" onclick="cancelOrder('${order.id}')">Cancelar pedido</button>`
          : "",
      )).join("")
      : '<p class="empty-state">Nenhum pedido encontrado para este e-mail.</p>';
  } catch (error) {
    flash(error.message);
  }
}

$("#ordersForm").addEventListener("submit", (event) => {
  event.preventDefault();
  loadMyOrders();
});

async function cancelOrder(orderId) {
  try {
    await api(`/orders/${orderId}/cancel`, { method: "POST" });
    flash("Pedido cancelado. O estoque foi liberado.", true);
    await loadMyOrders();
    await loadProducts();
  } catch (error) {
    flash(error.message);
  }
}

async function loadStores() {
  const stores = await api("/stores");
  $("#st").innerHTML = stores.map((store) =>
    `<option value="${store.id}">${store.name}</option>`,
  ).join("");
  $("#st").addEventListener("change", loadStoreOrders);
}

async function loadStoreOrders() {
  const storeId = $("#st").value;
  if (!storeId) return;

  try {
    const orders = await api(`/stores/${storeId}/orders`);
    const pending = orders.filter((order) => order.status === "confirmed").length;
    const preparing = orders.filter((order) => order.status === "preparing").length;
    const ready = orders.filter((order) => order.status === "ready").length;
    $("#storeSummary").innerHTML = `
      <div class="summary-card"><span>Aguardando separação</span><strong>${pending}</strong></div>
      <div class="summary-card"><span>Em separação</span><strong>${preparing}</strong></div>
      <div class="summary-card"><span>Prontos para retirada</span><strong>${ready}</strong></div>
      <p class="queue-note">Pedidos mais antigos primeiro</p>`;

    const openOrders = orders
      .filter((order) => ["confirmed", "preparing", "ready"].includes(order.status))
      .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    const actionFor = (order) => ({
      confirmed: `<button type="button" class="button button-primary button-small" onclick="step('${order.id}', 'start-preparing')">Iniciar separação</button>`,
      preparing: `<button type="button" class="button button-primary button-small" onclick="step('${order.id}', 'ready')">Marcar como pronto</button>`,
    })[order.status] || "";
    $("#storeorders").innerHTML = openOrders.length
      ? openOrders.map((order) => orderCard(order, actionFor(order))).join("")
      : '<p class="empty-state">Nenhum pedido em andamento nesta loja.</p>';
  } catch (error) {
    flash(error.message);
  }
}

async function step(orderId, action) {
  try {
    await api(`/orders/${orderId}/${action}`, { method: "POST" });
    flash("Status do pedido atualizado.", true);
    await loadStoreOrders();
  } catch (error) {
    flash(error.message);
  }
}

$("#validateForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const storeId = $("#st").value;
  if (!storeId) {
    flash("Selecione uma loja antes de validar a retirada.");
    return;
  }
  try {
    const order = await api(`/stores/${storeId}/pickup/validate`, {
      method: "POST",
      body: { code: $("#vcode").value.trim() },
    });
    $("#validateForm").reset();
    flash(`Pedido ${order.id} entregue a ${order.customer_name}.`, true);
    await loadStoreOrders();
    await loadProducts();
  } catch (error) {
    flash(error.message);
  }
});

$("#productSearch").value = "";
renderCart();
loadProducts().catch((error) => flash(error.message));
loadStores().catch((error) => flash(error.message));

setInterval(() => {
  if (!$("#orders").classList.contains("hide") && $("#q_email").value.trim()) {
    loadMyOrders();
  }
  if (!$("#store").classList.contains("hide") && $("#st").value) {
    loadStoreOrders();
  }
}, 5000);
