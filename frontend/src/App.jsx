import { useEffect, useMemo, useState } from 'react';
import { api, setAuthToken } from './api';

const emptyLine = { product_id: '', quantity: 1 };
const roleLabels = {
  super_admin: 'Super Admin',
  store_manager: 'Store Manager',
  inventory_manager: 'Inventory Manager',
  cashier: 'Cashier',
  accountant: 'Accountant',
  viewer: 'Viewer',
};

const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'inventory', label: 'Inventory' },
  { id: 'catalog', label: 'Catalog' },
  { id: 'billing', label: 'Billing' },
  { id: 'movements', label: 'Movements' },
  { id: 'admin', label: 'Admin' },
];

const currency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
});

export default function App() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [loginForm, setLoginForm] = useState({ email: 'superadmin@example.com', password: 'admin123' });
  const [stores, setStores] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [lowStock, setLowStock] = useState([]);
  const [movements, setMovements] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [summary, setSummary] = useState(null);
  const [users, setUsers] = useState([]);
  const [paymentOptions, setPaymentOptions] = useState(null);
  const [refunds, setRefunds] = useState([]);
  const [ledgers, setLedgers] = useState([]);
  const [reports, setReports] = useState(null);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('PhonePe UPI');
  const [activePayment, setActivePayment] = useState(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [storeForm, setStoreForm] = useState({ name: '', code: '', address: '' });
  const [customerForm, setCustomerForm] = useState({ name: '', phone: '', email: '' });
  const [productForm, setProductForm] = useState({
    store_id: '',
    name: '',
    sku: '',
    barcode: '',
    category: '',
    price: 0,
    stock: 0,
    reorder_level: 5,
    aisle: '',
    rack: '',
    shelf: '',
    bin: '',
    location_code: '',
  });
  const [stockForm, setStockForm] = useState({
    product_id: '',
    quantity: 1,
    movement_type: 'receive',
    notes: '',
  });
  const [userForm, setUserForm] = useState({
    name: '',
    email: '',
    password: 'password123',
    role: 'viewer',
    store_id: '',
  });
  const [refundForm, setRefundForm] = useState({
    amount: '',
    reason: 'Customer return',
    requested_by: 'admin',
  });
  const [invoiceForm, setInvoiceForm] = useState({
    store_id: '',
    customer_id: '',
    tax_amount: 0,
    discount_amount: 0,
    items: [{ ...emptyLine }],
  });

  const [inventoryQuery, setInventoryQuery] = useState('');
  const [inventoryStoreFilter, setInventoryStoreFilter] = useState('all');
  const [inventoryCategoryFilter, setInventoryCategoryFilter] = useState('all');
  const [inventoryOnlyLow, setInventoryOnlyLow] = useState(false);

  const [catalogQuery, setCatalogQuery] = useState('');
  const [catalogStoreFilter, setCatalogStoreFilter] = useState('all');

  const [billingQuery, setBillingQuery] = useState('');
  const [billingStatusFilter, setBillingStatusFilter] = useState('all');

  const [movementQuery, setMovementQuery] = useState('');
  const [movementTypeFilter, setMovementTypeFilter] = useState('all');

  const [staffQuery, setStaffQuery] = useState('');

  async function refresh() {
    const [
      storesData,
      customersData,
      productsData,
      lowStockData,
      movementData,
      invoicesData,
      summaryData,
      optionsData,
      refundsData,
      ledgersData,
      reportsData,
    ] = await Promise.all([
      api.stores(),
      api.customers(),
      api.products(),
      api.lowStockProducts(),
      api.stockMovements(),
      api.invoices(),
      api.summary(),
      api.paymentOptions(),
      api.refunds(),
      api.ledgers(),
      api.reports(),
    ]);

    setStores(storesData);
    setCustomers(customersData);
    setProducts(productsData);
    setLowStock(lowStockData);
    setMovements(movementData);
    setInvoices(invoicesData);
    setSummary(summaryData);
    setPaymentOptions(optionsData);
    setRefunds(refundsData);
    setLedgers(ledgersData);
    setReports(reportsData);

    if (user?.role === 'super_admin') {
      api.users().then(setUsers).catch(() => setUsers([]));
    } else {
      setUsers([]);
    }

    if (storesData.length) {
      setProductForm((current) => (current.store_id ? current : { ...current, store_id: String(storesData[0].id) }));
      setInvoiceForm((current) => (current.store_id ? current : { ...current, store_id: String(storesData[0].id) }));
      setUserForm((current) => (current.store_id ? current : { ...current, store_id: String(storesData[0].id) }));
    }
    if (customersData.length) {
      setInvoiceForm((current) => (current.customer_id ? current : { ...current, customer_id: String(customersData[0].id) }));
    }
    if (productsData.length) {
      setStockForm((current) => (current.product_id ? current : { ...current, product_id: String(productsData[0].id) }));
    }
  }

  useEffect(() => {
    api.me()
      .then((me) => {
        setUser(me);
        setMessage(`Logged in as ${me.name}`);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!user) return;
    refresh().catch((error) => setMessage(error.message));
  }, [user]);

  useEffect(() => {
    if (!user) return;
    const allowedTabs = getAllowedTabs(user.role);
    if (!allowedTabs.some((tab) => tab.id === activeTab)) {
      setActiveTab(allowedTabs[0]?.id || 'overview');
    }
  }, [user, activeTab]);

  async function login(event) {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      const result = await api.login(loginForm);
      setAuthToken(result.token);
      setUser(result.user);
      setMessage(`Welcome ${result.user.name}`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    setAuthToken('');
    setUser(null);
    setActiveTab('overview');
    setMessage('Logged out.');
  }

  async function run(callback) {
    setBusy(true);
    setMessage('');
    try {
      await callback();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitStore(event) {
    event.preventDefault();
    await run(async () => {
      await api.createStore(storeForm);
      setStoreForm({ name: '', code: '', address: '' });
      await refresh();
      setMessage('Store created.');
    });
  }

  async function submitCustomer(event) {
    event.preventDefault();
    await run(async () => {
      await api.createCustomer(customerForm);
      setCustomerForm({ name: '', phone: '', email: '' });
      await refresh();
      setMessage('Customer created.');
    });
  }

  async function submitProduct(event) {
    event.preventDefault();
    await run(async () => {
      const location_code =
        productForm.location_code || [productForm.aisle, productForm.rack, productForm.shelf, productForm.bin]
          .filter(Boolean)
          .join('-');
      await api.createProduct({
        ...productForm,
        store_id: Number(productForm.store_id),
        price: Number(productForm.price),
        stock: Number(productForm.stock),
        reorder_level: Number(productForm.reorder_level),
        location_code,
      });
      setProductForm((current) => ({
        ...current,
        name: '',
        sku: '',
        barcode: '',
        category: '',
        price: 0,
        stock: 0,
        aisle: '',
        rack: '',
        shelf: '',
        bin: '',
        location_code: '',
      }));
      await refresh();
      setMessage('Product created.');
    });
  }

  async function adjustStock(event) {
    event.preventDefault();
    await run(async () => {
      await api.adjustStock(stockForm.product_id, {
        quantity: Number(stockForm.quantity),
        movement_type: stockForm.movement_type,
        notes: stockForm.notes,
      });
      setStockForm((current) => ({ ...current, quantity: 1, notes: '' }));
      await refresh();
      setMessage('Stock updated.');
    });
  }

  async function createStaff(event) {
    event.preventDefault();
    await run(async () => {
      await api.createUser({
        ...userForm,
        store_id: userForm.store_id ? Number(userForm.store_id) : null,
      });
      setUserForm({
        name: '',
        email: '',
        password: 'password123',
        role: 'viewer',
        store_id: stores[0]?.id ? String(stores[0].id) : '',
      });
      await refresh();
      setMessage('Staff user created.');
    });
  }

  function updateLine(index, patch) {
    setInvoiceForm((current) => ({
      ...current,
      items: current.items.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)),
    }));
  }

  function addLine() {
    setInvoiceForm((current) => ({ ...current, items: [...current.items, { ...emptyLine }] }));
  }

  function removeLine(index) {
    setInvoiceForm((current) => ({
      ...current,
      items: current.items.length === 1 ? [{ ...emptyLine }] : current.items.filter((_, itemIndex) => itemIndex !== index),
    }));
  }

  async function submitInvoice(event) {
    event.preventDefault();
    await run(async () => {
      const payload = {
        store_id: Number(invoiceForm.store_id),
        customer_id: Number(invoiceForm.customer_id),
        tax_amount: Number(invoiceForm.tax_amount),
        discount_amount: Number(invoiceForm.discount_amount),
        items: invoiceForm.items
          .filter((item) => item.product_id)
          .map((item) => ({
            product_id: Number(item.product_id),
            quantity: Number(item.quantity),
          })),
      };
      await api.createInvoice(payload);
      setInvoiceForm((current) => ({ ...current, tax_amount: 0, discount_amount: 0, items: [{ ...emptyLine }] }));
      await refresh();
      setMessage('Invoice created. Inventory will reduce automatically when payment is completed.');
    });
  }

  async function collectPayment(invoice, paymentMethod) {
    await run(async () => {
      const session = await api.createPaymentSession({
        invoice_id: invoice.id,
        amount: invoice.remaining_amount,
        payment_method: paymentMethod,
        provider: paymentMethod.toLowerCase() === 'cash' ? 'cash' : 'phonepe',
        remarks: `Payment for ${invoice.invoice_number}`,
        metadata: { invoice_number: invoice.invoice_number },
      });
      setActivePayment(session.payment);
      await refresh();
      setMessage(`Payment session created for ${invoice.invoice_number}.`);
    });
  }

  async function simulatePayment(status) {
    if (!activePayment) return;
    await run(async () => {
      await api.simulatePayment(activePayment.payment_id, { status });
      setActivePayment(await api.payment(activePayment.payment_id));
      await refresh();
      setMessage(`Payment marked ${status.toLowerCase()}.`);
    });
  }

  async function requestRefund(event) {
    event.preventDefault();
    if (!activePayment) return;
    await run(async () => {
      await api.requestRefund({
        payment_id: activePayment.payment_id,
        amount: Number(refundForm.amount || activePayment.amount),
        reason: refundForm.reason,
        requested_by: refundForm.requested_by,
      });
      setRefundForm({ amount: '', reason: 'Customer return', requested_by: 'admin' });
      await refresh();
      setMessage('Refund requested.');
    });
  }

  async function approveRefund(refundId) {
    await run(async () => {
      await api.approveRefund(refundId, { approved_by: user.email });
      await refresh();
      setMessage('Refund approved and processed.');
    });
  }

  const allowedTabs = useMemo(() => getAllowedTabs(user?.role), [user]);

  const productMap = useMemo(
    () => new Map(products.map((product) => [product.id, product])),
    [products],
  );
  const storeMap = useMemo(
    () => new Map(stores.map((store) => [store.id, store])),
    [stores],
  );
  const customerMap = useMemo(
    () => new Map(customers.map((customer) => [customer.id, customer])),
    [customers],
  );

  const totals = useMemo(() => (
    invoices.reduce(
      (acc, invoice) => ({
        total: acc.total + invoice.total_amount,
        paid: acc.paid + invoice.paid_amount,
        remaining: acc.remaining + invoice.remaining_amount,
      }),
      { total: 0, paid: 0, remaining: 0 },
    )
  ), [invoices]);

  const filteredProducts = useMemo(() => {
    const query = inventoryQuery.trim().toLowerCase();
    return products.filter((product) => {
      const matchesQuery =
        !query ||
        [product.name, product.sku, product.barcode, product.location_code, product.category]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query));
      const matchesStore = inventoryStoreFilter === 'all' || String(product.store_id) === inventoryStoreFilter;
      const matchesCategory = inventoryCategoryFilter === 'all' || product.category === inventoryCategoryFilter;
      const matchesLow = !inventoryOnlyLow || product.stock <= product.reorder_level;
      return matchesQuery && matchesStore && matchesCategory && matchesLow;
    });
  }, [products, inventoryQuery, inventoryStoreFilter, inventoryCategoryFilter, inventoryOnlyLow]);

  const filteredCatalog = useMemo(() => {
    const query = catalogQuery.trim().toLowerCase();
    return products.filter((product) => {
      const matchesQuery =
        !query ||
        [product.name, product.sku, product.barcode, product.location_code, product.category]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query));
      const matchesStore = catalogStoreFilter === 'all' || String(product.store_id) === catalogStoreFilter;
      return matchesQuery && matchesStore;
    });
  }, [products, catalogQuery, catalogStoreFilter]);

  const filteredInvoices = useMemo(() => {
    const query = billingQuery.trim().toLowerCase();
    return invoices.filter((invoice) => {
      const customer = customerMap.get(invoice.customer_id);
      const matchesQuery =
        !query ||
        [invoice.invoice_number, invoice.status, invoice.payment_status, customer?.name, customer?.email]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query));
      const matchesStatus = billingStatusFilter === 'all' || invoice.payment_status === billingStatusFilter;
      return matchesQuery && matchesStatus;
    });
  }, [invoices, billingQuery, billingStatusFilter, customerMap]);

  const filteredMovements = useMemo(() => {
    const query = movementQuery.trim().toLowerCase();
    return movements.filter((movement) => {
      const product = productMap.get(movement.product_id);
      const matchesQuery =
        !query ||
        [movement.movement_type, movement.reference, movement.notes, product?.name, product?.sku, product?.location_code]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query));
      const matchesType = movementTypeFilter === 'all' || movement.movement_type === movementTypeFilter;
      return matchesQuery && matchesType;
    });
  }, [movements, movementQuery, movementTypeFilter, productMap]);

  const filteredRefunds = useMemo(() => {
    const query = billingQuery.trim().toLowerCase();
    return refunds.filter((refund) => {
      if (!query) return true;
      return [refund.refund_id, refund.reason, refund.status, refund.requested_by]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(query));
    });
  }, [refunds, billingQuery]);

  const filteredStaff = useMemo(() => {
    const query = staffQuery.trim().toLowerCase();
    return users.filter((staff) => {
      if (!query) return true;
      return [staff.name, staff.email, staff.role].some((value) => value?.toLowerCase().includes(query));
    });
  }, [users, staffQuery]);

  const inventoryByStore = useMemo(() => {
    const counts = new Map();
    products.forEach((product) => {
      counts.set(product.store_id, (counts.get(product.store_id) || 0) + 1);
    });
    return counts;
  }, [products]);

  const categoryOptions = useMemo(() => {
    return Array.from(new Set(products.map((product) => product.category).filter(Boolean))).sort();
  }, [products]);

  if (!user) {
    return (
      <div className="login-page">
        <form className="login-panel" onSubmit={login}>
          <div className="hero-copy">
            <span className="eyebrow">Inventory command center</span>
            <h1>Inventory Operations</h1>
            <p>Manage stock, billing, refunds, and stores from a role-aware dashboard built for faster daily work.</p>
          </div>
          <label className="field">
            <span>Email</span>
            <input
              value={loginForm.email}
              onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
              placeholder="Email"
              autoComplete="email"
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={loginForm.password}
              onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
              placeholder="Password"
              autoComplete="current-password"
            />
          </label>
          <button disabled={busy}>Login</button>
          <div className="hint">Seed login: superadmin@example.com / admin123</div>
          <div className="status">{message || 'Ready'}</div>
        </form>
      </div>
    );
  }

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="eyebrow">Operational dashboard</span>
          <h1>Inventory Operations</h1>
          <p>
            {user.name} - {roleLabels[user.role] || user.role}
          </p>
        </div>
        <div className="topbar-actions">
          <div className="status">{message || 'Ready'}</div>
          <button className="ghost" onClick={logout} type="button">Logout</button>
        </div>
      </header>

      <nav className="tabbar" aria-label="Main navigation">
        {allowedTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={activeTab === tab.id ? 'tab active' : 'tab'}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === 'overview' ? (
        <section className="page">
          <div className="page-header">
            <div>
              <span className="eyebrow">At a glance</span>
              <h2>Overview</h2>
              <p>Quick operational readout with inventory health, billing status, and movement activity.</p>
            </div>
            <div className="page-actions">
              <div className="status compact">{stores.length} stores live</div>
              <div className="status compact">{products.length} products tracked</div>
            </div>
          </div>

          <section className="metrics">
            <Metric label="Today Collections" value={summary ? currency.format(summary.today_collections) : '...'} />
            <Metric label="Pending Payments" value={summary ? summary.pending_payments : '...'} />
            <Metric label="Success Rate" value={summary ? `${summary.payment_success_rate}%` : '...'} />
            <Metric label="Products" value={summary ? summary.product_count : '...'} />
            <Metric label="Low Stock" value={lowStock.length} />
            <Metric label="Open Amount" value={currency.format(totals.remaining)} />
          </section>

          <div className="overview-grid">
            <article className="panel accent">
              <h3>Inventory Health</h3>
              <p>
                {lowStock.length
                  ? `${lowStock.length} products need attention before they interrupt billing or replenishment.`
                  : 'No products are currently below the reorder level.'}
              </p>
              <div className="stack compact-stack">
                {lowStock.slice(0, 4).map((product) => (
                  <div className="mini-row" key={product.id}>
                    <strong>{product.name}</strong>
                    <span>{product.location_code}</span>
                    <span>{product.stock}/{product.reorder_level}</span>
                  </div>
                ))}
              </div>
            </article>

            <article className="panel">
              <h3>Billing Pipeline</h3>
              <p>Invoices reduce inventory automatically once payment completes, keeping stock and billing in sync.</p>
              <div className="stats-pills">
                <span>Invoices: {summary?.invoice_count ?? '...'}</span>
                <span>Customers: {summary?.customer_count ?? '...'}</span>
                <span>Part paid: {summary?.partially_paid_invoices ?? '...'}</span>
              </div>
            </article>

            <article className="panel">
              <h3>Operations Shortcuts</h3>
              <p>Use the dedicated tabs for stock movement, catalog, billing, and administration.</p>
              <div className="stack compact-stack">
                <button type="button" className="ghost" onClick={() => setActiveTab('inventory')}>Go to Inventory</button>
                <button type="button" className="ghost" onClick={() => setActiveTab('billing')}>Go to Billing</button>
                {user.role === 'super_admin' ? (
                  <button type="button" className="ghost" onClick={() => setActiveTab('admin')}>Go to Admin</button>
                ) : null}
              </div>
            </article>
          </div>
        </section>
      ) : null}

      {activeTab === 'inventory' ? (
        <section className="page">
          <div className="page-header">
            <div>
              <span className="eyebrow">Stock control</span>
              <h2>Inventory</h2>
              <p>Search stock by SKU, barcode, category, store, or location and adjust damaged, received, or transferred items.</p>
            </div>
            <div className="page-actions">
              <div className="status compact">{inventoryByStore.size} active stock stores</div>
              <div className="status compact">{filteredProducts.length} matching products</div>
            </div>
          </div>

          <div className="filters panel">
            <label className="field">
              <span>Search inventory</span>
              <input value={inventoryQuery} onChange={(e) => setInventoryQuery(e.target.value)} placeholder="Name, SKU, barcode, location" />
            </label>
            <label className="field">
              <span>Store</span>
              <select value={inventoryStoreFilter} onChange={(e) => setInventoryStoreFilter(e.target.value)}>
                <option value="all">All stores</option>
                {stores.map((store) => <option key={store.id} value={store.id}>{store.name}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Category</span>
              <select value={inventoryCategoryFilter} onChange={(e) => setInventoryCategoryFilter(e.target.value)}>
                <option value="all">All categories</option>
                {categoryOptions.map((category) => <option key={category} value={category}>{category}</option>)}
              </select>
            </label>
            <label className="check">
              <input type="checkbox" checked={inventoryOnlyLow} onChange={(e) => setInventoryOnlyLow(e.target.checked)} />
              <span>Show low stock only</span>
            </label>
          </div>

          <div className="two-col">
            <article className="panel">
              <h3>Adjust stock</h3>
              <p className="subtle">Damage and transfer-out reduce inventory. Receive and transfer-in increase it.</p>
              <form className="stack" onSubmit={adjustStock}>
                <label className="field">
                  <span>Product</span>
                  <select value={stockForm.product_id} onChange={(e) => setStockForm({ ...stockForm, product_id: e.target.value })}>
                    {products.map((product) => (
                      <option key={product.id} value={product.id}>
                        {product.name} - {product.location_code}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="row">
                  <label className="field">
                    <span>Movement type</span>
                    <select value={stockForm.movement_type} onChange={(e) => setStockForm({ ...stockForm, movement_type: e.target.value })}>
                      <option value="receive">Receive</option>
                      <option value="adjust">Adjust</option>
                      <option value="damage">Damage / Defective</option>
                      <option value="transfer_in">Transfer In</option>
                      <option value="transfer_out">Transfer Out</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>Quantity</span>
                    <input type="number" min="1" value={stockForm.quantity} onChange={(e) => setStockForm({ ...stockForm, quantity: e.target.value })} />
                  </label>
                </div>
                <label className="field">
                  <span>Notes</span>
                  <input value={stockForm.notes} onChange={(e) => setStockForm({ ...stockForm, notes: e.target.value })} placeholder="Reason, location, or batch note" />
                </label>
                <button disabled={busy}>Update Inventory</button>
              </form>
            </article>

            <article className="panel">
              <h3>Inventory list</h3>
              <div className="table">
                <div className="table-head inventory-head">
                  <span>Product</span>
                  <span>Store</span>
                  <span>Stock</span>
                  <span>Location</span>
                  <span>Status</span>
                </div>
                {filteredProducts.map((product) => {
                  const isLow = product.stock <= product.reorder_level;
                  return (
                    <div className="table-row inventory-row" key={product.id}>
                      <div>
                        <strong>{product.name}</strong>
                        <div className="muted">{product.sku}</div>
                      </div>
                      <span>{storeMap.get(product.store_id)?.name || 'Store'}</span>
                      <span>{product.stock}</span>
                      <span>{product.location_code}</span>
                      <span className={isLow ? 'pill danger' : 'pill success'}>{isLow ? 'Low stock' : 'Healthy'}</span>
                    </div>
                  );
                })}
              </div>
            </article>
          </div>
        </section>
      ) : null}

      {activeTab === 'catalog' ? (
        <section className="page">
          <div className="page-header">
            <div>
              <span className="eyebrow">Product master</span>
              <h2>Catalog</h2>
              <p>Maintain product definitions, location codes, barcode data, and opening stock in a single place.</p>
            </div>
            <div className="page-actions">
              <div className="status compact">{filteredCatalog.length} catalog matches</div>
            </div>
          </div>

          <div className="filters panel">
            <label className="field">
              <span>Search catalog</span>
              <input value={catalogQuery} onChange={(e) => setCatalogQuery(e.target.value)} placeholder="Name, SKU, category, barcode" />
            </label>
            <label className="field">
              <span>Store</span>
              <select value={catalogStoreFilter} onChange={(e) => setCatalogStoreFilter(e.target.value)}>
                <option value="all">All stores</option>
                {stores.map((store) => <option key={store.id} value={store.id}>{store.name}</option>)}
              </select>
            </label>
          </div>

          <div className="two-col">
            <article className="panel">
              <h3>Create product</h3>
              <form className="stack" onSubmit={submitProduct}>
                <label className="field">
                  <span>Store</span>
                  <select value={productForm.store_id} onChange={(e) => setProductForm({ ...productForm, store_id: e.target.value })}>
                    {stores.map((store) => <option key={store.id} value={store.id}>{store.name}</option>)}
                  </select>
                </label>
                <div className="row">
                  <label className="field">
                    <span>Name</span>
                    <input value={productForm.name} onChange={(e) => setProductForm({ ...productForm, name: e.target.value })} placeholder="Product name" />
                  </label>
                  <label className="field">
                    <span>SKU</span>
                    <input value={productForm.sku} onChange={(e) => setProductForm({ ...productForm, sku: e.target.value })} placeholder="SKU" />
                  </label>
                </div>
                <div className="row">
                  <label className="field">
                    <span>Barcode</span>
                    <input value={productForm.barcode} onChange={(e) => setProductForm({ ...productForm, barcode: e.target.value })} placeholder="Barcode" />
                  </label>
                  <label className="field">
                    <span>Category</span>
                    <input value={productForm.category} onChange={(e) => setProductForm({ ...productForm, category: e.target.value })} placeholder="Category" />
                  </label>
                </div>
                <div className="row">
                  <label className="field">
                    <span>Price</span>
                    <input type="number" value={productForm.price} onChange={(e) => setProductForm({ ...productForm, price: e.target.value })} placeholder="Price" />
                  </label>
                  <label className="field">
                    <span>Opening stock</span>
                    <input type="number" value={productForm.stock} onChange={(e) => setProductForm({ ...productForm, stock: e.target.value })} placeholder="Opening stock" />
                  </label>
                  <label className="field">
                    <span>Reorder</span>
                    <input type="number" value={productForm.reorder_level} onChange={(e) => setProductForm({ ...productForm, reorder_level: e.target.value })} placeholder="Reorder level" />
                  </label>
                </div>
                <div className="row">
                  <label className="field">
                    <span>Aisle</span>
                    <input value={productForm.aisle} onChange={(e) => setProductForm({ ...productForm, aisle: e.target.value })} placeholder="A1" />
                  </label>
                  <label className="field">
                    <span>Rack</span>
                    <input value={productForm.rack} onChange={(e) => setProductForm({ ...productForm, rack: e.target.value })} placeholder="22" />
                  </label>
                  <label className="field">
                    <span>Shelf</span>
                    <input value={productForm.shelf} onChange={(e) => setProductForm({ ...productForm, shelf: e.target.value })} placeholder="4" />
                  </label>
                  <label className="field">
                    <span>Bin</span>
                    <input value={productForm.bin} onChange={(e) => setProductForm({ ...productForm, bin: e.target.value })} placeholder="C" />
                  </label>
                </div>
                <label className="field">
                  <span>Location code</span>
                  <input value={productForm.location_code} onChange={(e) => setProductForm({ ...productForm, location_code: e.target.value })} placeholder="A1-22-4-C" />
                </label>
                <button disabled={busy}>Create Product</button>
              </form>
            </article>

            <article className="panel">
              <h3>Catalog browse</h3>
              <div className="catalog-grid">
                {filteredCatalog.map((product) => (
                  <div className="catalog-card" key={product.id}>
                    <div className="catalog-top">
                      <strong>{product.name}</strong>
                      <span className="pill">{product.category || 'Uncategorized'}</span>
                    </div>
                    <div className="muted">{product.sku}</div>
                    <div className="catalog-meta">
                      <span>{storeMap.get(product.store_id)?.name || 'Store'}</span>
                      <span>{product.location_code}</span>
                      <span>{currency.format(product.price)}</span>
                      <span>Stock {product.stock}</span>
                    </div>
                  </div>
                ))}
              </div>
            </article>
          </div>
        </section>
      ) : null}

      {activeTab === 'billing' ? (
        <section className="page">
          <div className="page-header">
            <div>
              <span className="eyebrow">Cashier flow</span>
              <h2>Billing</h2>
              <p>Create invoices, collect payment, and let inventory move automatically when a bill is completed.</p>
            </div>
            <div className="page-actions">
              <div className="status compact">{filteredInvoices.length} matching invoices</div>
              <div className="status compact">{filteredRefunds.length} refunds shown</div>
            </div>
          </div>

          <div className="filters panel">
            <label className="field">
              <span>Search invoices</span>
              <input value={billingQuery} onChange={(e) => setBillingQuery(e.target.value)} placeholder="Invoice number, customer, status" />
            </label>
            <label className="field">
              <span>Payment status</span>
              <select value={billingStatusFilter} onChange={(e) => setBillingStatusFilter(e.target.value)}>
                <option value="all">All statuses</option>
                <option value="Pending">Pending</option>
                <option value="Partial">Partial</option>
                <option value="Success">Success</option>
                <option value="Failed">Failed</option>
                <option value="Refunded">Refunded</option>
                <option value="Partially Refunded">Partially Refunded</option>
              </select>
            </label>
          </div>

          <div className="two-col">
            <article className="panel">
              <h3>Create customer</h3>
              <form className="stack" onSubmit={submitCustomer}>
                <div className="row">
                  <label className="field">
                    <span>Name</span>
                    <input value={customerForm.name} onChange={(e) => setCustomerForm({ ...customerForm, name: e.target.value })} placeholder="Customer name" />
                  </label>
                  <label className="field">
                    <span>Phone</span>
                    <input value={customerForm.phone} onChange={(e) => setCustomerForm({ ...customerForm, phone: e.target.value })} placeholder="Phone" />
                  </label>
                </div>
                <label className="field">
                  <span>Email</span>
                  <input value={customerForm.email} onChange={(e) => setCustomerForm({ ...customerForm, email: e.target.value })} placeholder="Email" />
                </label>
                <button disabled={busy}>Create Customer</button>
              </form>

              <div className="billing-note">
                Inventory is reduced automatically only after a payment succeeds. Damage and return adjustments stay in the Inventory tab.
              </div>
            </article>

            <article className="panel">
              <h3>New invoice</h3>
              <form className="stack invoice-form" onSubmit={submitInvoice}>
                <div className="row">
                  <label className="field">
                    <span>Store</span>
                    <select value={invoiceForm.store_id} onChange={(e) => setInvoiceForm({ ...invoiceForm, store_id: e.target.value })}>
                      {stores.map((store) => <option key={store.id} value={store.id}>{store.name}</option>)}
                    </select>
                  </label>
                  <label className="field">
                    <span>Customer</span>
                    <select value={invoiceForm.customer_id} onChange={(e) => setInvoiceForm({ ...invoiceForm, customer_id: e.target.value })}>
                      {customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}
                    </select>
                  </label>
                </div>

                {invoiceForm.items.map((line, index) => (
                  <div className="row line" key={index}>
                    <label className="field grow">
                      <span>Product</span>
                      <select value={line.product_id} onChange={(e) => updateLine(index, { product_id: e.target.value })}>
                        <option value="">Select product</option>
                        {products.map((product) => (
                          <option key={product.id} value={product.id}>
                            {product.name} - {product.location_code} - Stock {product.stock}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field compact-input">
                      <span>Qty</span>
                      <input type="number" min="1" value={line.quantity} onChange={(e) => updateLine(index, { quantity: e.target.value })} />
                    </label>
                    <button type="button" className="ghost" onClick={() => removeLine(index)}>Remove</button>
                  </div>
                ))}

                <button type="button" className="ghost" onClick={addLine}>Add line</button>
                <div className="row">
                  <label className="field">
                    <span>Tax</span>
                    <input type="number" value={invoiceForm.tax_amount} onChange={(e) => setInvoiceForm({ ...invoiceForm, tax_amount: e.target.value })} placeholder="Tax" />
                  </label>
                  <label className="field">
                    <span>Discount</span>
                    <input type="number" value={invoiceForm.discount_amount} onChange={(e) => setInvoiceForm({ ...invoiceForm, discount_amount: e.target.value })} placeholder="Discount" />
                  </label>
                </div>
                <button disabled={busy}>Create Invoice</button>
              </form>
            </article>
          </div>

          <div className="billing-grid">
            <article className="panel">
              <h3>Invoices</h3>
              <div className="list">
                {filteredInvoices.map((invoice) => (
                  <div className="invoice-card" key={invoice.id}>
                    <div className="invoice-summary">
                      <strong>{invoice.invoice_number}</strong>
                      <span>{customerMap.get(invoice.customer_id)?.name || 'Customer'}</span>
                      <span>{storeMap.get(invoice.store_id)?.name || 'Store'}</span>
                    </div>
                    <div className="invoice-finance">
                      <span>{currency.format(invoice.total_amount)}</span>
                      <span>Open {currency.format(invoice.remaining_amount)}</span>
                      <span className={invoice.payment_status === 'Success' ? 'pill success' : 'pill'}>{invoice.payment_status}</span>
                    </div>
                    <div className="payment-list">
                      <button className="ghost" type="button" onClick={() => collectPayment(invoice, selectedPaymentMethod)} disabled={busy || invoice.remaining_amount <= 0}>
                        Collect {selectedPaymentMethod}
                      </button>
                      <button className="ghost" type="button" onClick={() => collectPayment(invoice, 'Cash')} disabled={busy || invoice.remaining_amount <= 0}>
                        Collect Cash
                      </button>
                      {invoice.payments?.map((payment) => (
                        <button key={payment.payment_id} type="button" className="link-button" onClick={() => setActivePayment(payment)}>
                          {payment.payment_method} - {payment.payment_status}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </article>

            <article className="panel">
              <h3>Payment and refunds</h3>
              <label className="field">
                <span>Payment method</span>
                <select value={selectedPaymentMethod} onChange={(e) => setSelectedPaymentMethod(e.target.value)}>
                  {(paymentOptions?.providers?.[0]?.methods || ['PhonePe UPI', 'Cash']).map((method) => <option key={method} value={method}>{method}</option>)}
                </select>
              </label>

              {activePayment ? (
                <div className="stack">
                  <div className="payment-hero">
                    <strong>{activePayment.payment_id}</strong>
                    <span>{activePayment.payment_method} - {activePayment.payment_status}</span>
                    <span>{currency.format(activePayment.amount)}</span>
                  </div>
                  <div className="row">
                    <button onClick={() => simulatePayment('SUCCESS')} disabled={busy || activePayment.payment_status === 'SUCCESS'}>Mark Success</button>
                    <button className="ghost" onClick={() => simulatePayment('FAILED')} disabled={busy}>Mark Failed</button>
                  </div>
                  <form className="stack refund-form" onSubmit={requestRefund}>
                    <label className="field">
                      <span>Refund amount</span>
                      <input
                        type="number"
                        min="1"
                        step="0.01"
                        value={refundForm.amount}
                        onChange={(e) => setRefundForm({ ...refundForm, amount: e.target.value })}
                        placeholder={`Max ${activePayment.amount}`}
                      />
                    </label>
                    <label className="field">
                      <span>Reason</span>
                      <input value={refundForm.reason} onChange={(e) => setRefundForm({ ...refundForm, reason: e.target.value })} placeholder="Refund reason" />
                    </label>
                    <button
                      disabled={busy || !['SUCCESS', 'COMPLETED', 'PARTIALLY REFUNDED'].includes(activePayment.payment_status)}
                    >
                      Request Refund
                    </button>
                  </form>
                </div>
              ) : (
                <p className="subtle">Select a payment from an invoice to manage settlement or refunds.</p>
              )}
            </article>
          </div>

          <div className="billing-grid secondary">
            <article className="panel">
              <h3>Refund queue</h3>
              <div className="list">
                {filteredRefunds.map((refund) => (
                  <div className="refund-row" key={refund.refund_id}>
                    <div>
                      <strong>{refund.refund_id}</strong>
                      <div className="muted">{refund.reason}</div>
                    </div>
                    <span>{currency.format(refund.amount)}</span>
                    <span className="pill">{refund.status}</span>
                    <button className="ghost" onClick={() => approveRefund(refund.refund_id)} disabled={busy || refund.status === 'Processed'} type="button">
                      Approve
                    </button>
                  </div>
                ))}
              </div>
            </article>

            <article className="panel">
              <h3>Billing summary</h3>
              {reports ? (
                <div className="report-grid">
                  <Metric label="Pending Amount" value={currency.format(reports.pending_amount)} />
                  <Metric label="Failed Amount" value={currency.format(reports.failed_amount)} />
                  <Metric label="Refund Amount" value={currency.format(reports.refund_amount)} />
                  <Metric label="Net Settlement" value={currency.format(reports.settlement_summary.net_settlement)} />
                </div>
              ) : (
                <p>Reports loading.</p>
              )}
            </article>
          </div>
        </section>
      ) : null}

      {activeTab === 'movements' ? (
        <section className="page">
          <div className="page-header">
            <div>
              <span className="eyebrow">Movement ledger</span>
              <h2>Stock Movements</h2>
              <p>Inspect receive, damage, transfer, and opening movements with search and filters for faster reconciliation.</p>
            </div>
            <div className="page-actions">
              <div className="status compact">{filteredMovements.length} movements shown</div>
            </div>
          </div>

          <div className="filters panel">
            <label className="field">
              <span>Search movements</span>
              <input value={movementQuery} onChange={(e) => setMovementQuery(e.target.value)} placeholder="Product, reference, notes, location" />
            </label>
            <label className="field">
              <span>Type</span>
              <select value={movementTypeFilter} onChange={(e) => setMovementTypeFilter(e.target.value)}>
                <option value="all">All types</option>
                <option value="opening">Opening</option>
                <option value="receive">Receive</option>
                <option value="adjust">Adjust</option>
                <option value="damage">Damage</option>
                <option value="transfer_in">Transfer In</option>
                <option value="transfer_out">Transfer Out</option>
              </select>
            </label>
          </div>

          <article className="panel">
            <div className="table">
              <div className="table-head movement-head">
                <span>Product</span>
                <span>Type</span>
                <span>Before</span>
                <span>After</span>
                <span>Notes</span>
              </div>
              {filteredMovements.map((movement) => {
                const product = productMap.get(movement.product_id);
                return (
                  <div className="table-row movement-row" key={movement.id}>
                    <div>
                      <strong>{product?.name || `Product ${movement.product_id}`}</strong>
                      <div className="muted">{product?.location_code || movement.reference}</div>
                    </div>
                    <span className="pill">{movement.movement_type}</span>
                    <span>{movement.before_quantity}</span>
                    <span>{movement.after_quantity}</span>
                    <span>{movement.notes || 'No note'}</span>
                  </div>
                );
              })}
            </div>
          </article>
        </section>
      ) : null}

      {activeTab === 'admin' ? (
        <section className="page">
          <div className="page-header">
            <div>
              <span className="eyebrow">Administrative control</span>
              <h2>Admin</h2>
              <p>Store creation stays with super admin only. Staff assignment is also managed here.</p>
            </div>
          </div>

          <div className="two-col">
            <article className="panel">
              <h3>Store setup</h3>
              <p className="subtle">Only super admin can create new stores.</p>
              <form className="stack" onSubmit={submitStore}>
                <label className="field">
                  <span>Store name</span>
                  <input value={storeForm.name} onChange={(e) => setStoreForm({ ...storeForm, name: e.target.value })} placeholder="Store name" />
                </label>
                <label className="field">
                  <span>Store code</span>
                  <input value={storeForm.code} onChange={(e) => setStoreForm({ ...storeForm, code: e.target.value })} placeholder="Store code" />
                </label>
                <label className="field">
                  <span>Address</span>
                  <input value={storeForm.address} onChange={(e) => setStoreForm({ ...storeForm, address: e.target.value })} placeholder="Address" />
                </label>
                <button disabled={busy}>Create Store</button>
              </form>
            </article>

            <article className="panel">
              <h3>Staff and roles</h3>
              <form className="stack" onSubmit={createStaff}>
                <label className="field">
                  <span>Name</span>
                  <input value={userForm.name} onChange={(e) => setUserForm({ ...userForm, name: e.target.value })} placeholder="Name" />
                </label>
                <label className="field">
                  <span>Email</span>
                  <input value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} placeholder="Email" />
                </label>
                <label className="field">
                  <span>Password</span>
                  <input value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} placeholder="Password" />
                </label>
                <div className="row">
                  <label className="field">
                    <span>Role</span>
                    <select value={userForm.role} onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}>
                      {Object.keys(roleLabels).map((role) => <option key={role} value={role}>{roleLabels[role]}</option>)}
                    </select>
                  </label>
                  <label className="field">
                    <span>Store</span>
                    <select value={userForm.store_id} onChange={(e) => setUserForm({ ...userForm, store_id: e.target.value })}>
                      <option value="">All stores</option>
                      {stores.map((store) => <option key={store.id} value={store.id}>{store.name}</option>)}
                    </select>
                  </label>
                </div>
                <button disabled={busy}>Create Staff</button>
              </form>
            </article>
          </div>

          <article className="panel">
            <div className="page-header tight">
              <div>
                <h3>Existing staff</h3>
                <p className="subtle">Search and review role assignments.</p>
              </div>
              <label className="field search-inline">
                <span className="sr-only">Search staff</span>
                <input value={staffQuery} onChange={(e) => setStaffQuery(e.target.value)} placeholder="Search staff" />
              </label>
            </div>
            <div className="list">
              {filteredStaff.map((staff) => (
                <div className="staff-row" key={staff.id}>
                  <div>
                    <strong>{staff.name}</strong>
                    <div className="muted">{staff.email}</div>
                  </div>
                  <span className="pill">{roleLabels[staff.role] || staff.role}</span>
                  <span>{staff.store_id ? storeMap.get(staff.store_id)?.name || `Store ${staff.store_id}` : 'No store'}</span>
                </div>
              ))}
            </div>
          </article>
        </section>
      ) : null}

      <section className="footer-bar">
        <div className="status compact">Payment ledgers: {ledgers.length}</div>
        <div className="status compact">Refunds: {refunds.length}</div>
        <div className="status compact">Movements: {movements.length}</div>
      </section>
    </div>
  );
}

function getAllowedTabs(role) {
  const map = {
    super_admin: ['overview', 'inventory', 'catalog', 'billing', 'movements', 'admin'],
    store_manager: ['overview', 'inventory', 'catalog', 'billing', 'movements'],
    inventory_manager: ['overview', 'inventory', 'catalog', 'movements'],
    cashier: ['overview', 'inventory', 'catalog', 'billing', 'movements'],
    accountant: ['overview', 'billing'],
    viewer: ['overview', 'inventory', 'catalog', 'billing', 'movements'],
  };
  return tabs.filter((tab) => (map[role] || ['overview']).includes(tab.id));
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
