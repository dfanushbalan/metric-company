/**
 * Appointment Slot Booker - Frontend Application Controller
 * Handles REST API communication, concurrency testing, slot booking,
 * and double-booking conflict mitigation.
 */

// Dynamic API Base URL determination (supports Unified Flask serving, Separated Vercel/Netlify, or local dev)
function getApiBase() {
  // 1. Explicit window.BACKEND_API_URL set in config.js
  if (window.BACKEND_API_URL && typeof window.BACKEND_API_URL === 'string' && window.BACKEND_API_URL.trim() !== '') {
    return window.BACKEND_API_URL.trim().replace(/\/+$/, '');
  }
  // 2. URL search param: ?api=https://...
  try {
    const params = new URLSearchParams(window.location.search);
    const queryApi = params.get('api');
    if (queryApi) {
      localStorage.setItem('SLOT_BOOKER_API_BASE', queryApi.trim().replace(/\/+$/, ''));
      return queryApi.trim().replace(/\/+$/, '');
    }
  } catch (e) {}

  // 3. User customized in localStorage
  try {
    const saved = localStorage.getItem('SLOT_BOOKER_API_BASE');
    if (saved && saved.trim() !== '') {
      return saved.trim().replace(/\/+$/, '');
    }
  } catch (e) {}

  // 4. Standalone development / local preview static servers
  const origin = window.location.origin;
  if (!origin || origin.startsWith('file:') || origin.includes(':3000') || origin.includes(':5500') || origin.includes(':5173') || origin.includes(':8080')) {
    return 'http://127.0.0.1:5000';
  }

  // 5. Default: same origin (unified Flask production deployment or reverse proxy)
  return origin;
}

let API_BASE = getApiBase();


// Application State
const state = {
  slots: [],
  bookings: [],
  activeTab: 'tab-slots',
  selectedSlotForBooking: null,
  selectedBookingForCancel: null,
  filterDate: '',
  filterStatus: 'AVAILABLE',
  searchBookings: '',
  filterBookingStatus: 'CONFIRMED'
};

// ============================================================================
// Initialization & Lifecycle
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
  initDOMReferences();
  initEventListeners();
  setDefaultDates();
  checkSystemHealth();
  refreshAllData();
});

function initDOMReferences() {
  // Tabs
  window.tabButtons = document.querySelectorAll('.tab-btn');
  window.tabPanes = document.querySelectorAll('.tab-pane');

  // Metrics
  window.elTotalSlots = document.getElementById('metric-total-slots');
  window.elAvailableSlots = document.getElementById('metric-available-slots');
  window.elBookedSlots = document.getElementById('metric-booked-slots');
  window.elBadgeAvailable = document.getElementById('badge-available-count');
  window.elBadgeBookings = document.getElementById('badge-bookings-count');

  // Containers
  window.slotsGrid = document.getElementById('slots-grid-container');
  window.bookingsList = document.getElementById('bookings-list-container');
  window.simConsole = document.getElementById('sim-output-console');
  window.simSlotSelect = document.getElementById('sim-slot-select');

  // Modals
  window.modalBooking = document.getElementById('modal-booking');
  window.modalCancel = document.getElementById('modal-cancel-confirm');
  window.modalApi = document.getElementById('modal-api-settings');
  window.inputApiUrl = document.getElementById('input-api-url');
  window.apiTestStatus = document.getElementById('api-test-status');
}

function initEventListeners() {
  // Tab switching
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabTarget = btn.getAttribute('data-tab');
      switchTab(tabTarget);
    });
  });

  // Global Refresh
  document.getElementById('btn-refresh-all').addEventListener('click', () => {
    refreshAllData();
    showToast('Data refreshed successfully', 'info');
  });

  // API Settings Modal
  const btnApiSettings = document.getElementById('btn-api-settings');
  if (btnApiSettings) {
    btnApiSettings.addEventListener('click', () => {
      if (window.inputApiUrl) {
        window.inputApiUrl.value = localStorage.getItem('SLOT_BOOKER_API_BASE') || window.BACKEND_API_URL || '';
      }
      if (window.apiTestStatus) {
        window.apiTestStatus.textContent = `Current Active Server: ${API_BASE}`;
        window.apiTestStatus.style.color = 'var(--text-muted)';
      }
      if (window.modalApi) window.modalApi.classList.add('active');
    });
  }

  const btnCloseApiModal = document.getElementById('btn-close-api-modal');
  if (btnCloseApiModal) {
    btnCloseApiModal.addEventListener('click', () => {
      if (window.modalApi) window.modalApi.classList.remove('active');
    });
  }

  const btnTestApi = document.getElementById('btn-test-api');
  if (btnTestApi) {
    btnTestApi.addEventListener('click', async () => {
      const targetUrl = (window.inputApiUrl.value.trim() || window.location.origin).replace(/\/+$/, '');
      window.apiTestStatus.textContent = 'Testing connection...';
      window.apiTestStatus.style.color = 'var(--text-muted)';
      try {
        const res = await fetch(`${targetUrl}/api/health`, { method: 'GET' });
        if (res.ok) {
          const data = await res.json();
          window.apiTestStatus.textContent = `Connected! (${data.database || 'Database OK'})`;
          window.apiTestStatus.style.color = 'var(--status-available)';
        } else {
          window.apiTestStatus.textContent = `Server responded with status ${res.status}`;
          window.apiTestStatus.style.color = 'var(--status-error)';
        }
      } catch (err) {
        window.apiTestStatus.textContent = `Failed to connect: ${err.message}`;
        window.apiTestStatus.style.color = 'var(--status-error)';
      }
    });
  }

  const btnSaveApi = document.getElementById('btn-save-api');
  if (btnSaveApi) {
    btnSaveApi.addEventListener('click', () => {
      const newUrl = window.inputApiUrl.value.trim().replace(/\/+$/, '');
      if (newUrl) {
        localStorage.setItem('SLOT_BOOKER_API_BASE', newUrl);
      } else {
        localStorage.removeItem('SLOT_BOOKER_API_BASE');
      }
      API_BASE = getApiBase();
      if (window.modalApi) window.modalApi.classList.remove('active');
      showToast(`Connected to API: ${API_BASE}`, 'success');
      checkSystemHealth();
      refreshAllData();
    });
  }

  // Date Filters
  const dateInput = document.getElementById('filter-date-input');
  dateInput.addEventListener('change', (e) => {
    state.filterDate = e.target.value;
    loadSlots();
  });

  document.getElementById('btn-quick-today').addEventListener('click', () => {
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
    state.filterDate = today;
    loadSlots();
  });

  document.getElementById('btn-quick-tomorrow').addEventListener('click', () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomStr = tomorrow.toISOString().split('T')[0];
    dateInput.value = tomStr;
    state.filterDate = tomStr;
    loadSlots();
  });

  document.getElementById('btn-quick-all').addEventListener('click', () => {
    dateInput.value = '';
    state.filterDate = '';
    loadSlots();
  });

  // Status Filter
  document.getElementById('filter-status-select').addEventListener('change', (e) => {
    state.filterStatus = e.target.value;
    loadSlots();
  });

  // Bookings Filters
  document.getElementById('search-bookings-input').addEventListener('input', (e) => {
    state.searchBookings = e.target.value.toLowerCase();
    renderBookings();
  });

  document.getElementById('filter-booking-status').addEventListener('change', (e) => {
    state.filterBookingStatus = e.target.value;
    loadBookings();
  });

  // Modal Closures
  document.getElementById('btn-close-booking-modal').addEventListener('click', closeBookingModal);
  document.getElementById('btn-cancel-modal').addEventListener('click', closeBookingModal);
  document.getElementById('btn-close-cancel-modal').addEventListener('click', closeCancelModal);
  document.getElementById('btn-abort-cancel').addEventListener('click', closeCancelModal);

  // Forms
  document.getElementById('form-confirm-booking').addEventListener('submit', handleBookingSubmit);
  document.getElementById('btn-confirm-cancel-action').addEventListener('click', handleCancelSubmit);
  document.getElementById('form-create-slot').addEventListener('submit', handleCreateSlotSubmit);
  document.getElementById('form-batch-slots').addEventListener('submit', handleBatchSlotsSubmit);

  // Concurrency Simulator
  document.getElementById('btn-run-race-sim').addEventListener('click', runDoubleBookingSimulation);
}

function setDefaultDates() {
  const today = new Date().toISOString().split('T')[0];
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const tomStr = tomorrow.toISOString().split('T')[0];

  const slotDateInput = document.getElementById('slot-date');
  const batchDateInput = document.getElementById('batch-date');
  if (slotDateInput) {
    slotDateInput.value = tomStr;
    slotDateInput.min = today;
  }
  if (batchDateInput) {
    batchDateInput.value = tomStr;
    batchDateInput.min = today;
  }
}

function switchTab(tabId) {
  state.activeTab = tabId;
  tabButtons.forEach(btn => {
    const isTarget = btn.getAttribute('data-tab') === tabId;
    btn.classList.toggle('active', isTarget);
    btn.setAttribute('aria-selected', isTarget);
  });

  tabPanes.forEach(pane => {
    pane.classList.toggle('active', pane.id === tabId);
  });

  if (tabId === 'tab-concurrency') {
    populateConcurrencySlotsDropdown();
  }
}

// ============================================================================
// API Calls & Data Fetching
// ============================================================================
async function checkSystemHealth() {
  const pillText = document.getElementById('system-status-text');
  const dot = document.getElementById('system-status-dot');

  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (res.ok) {
      const data = await res.json();
      dot.classList.remove('offline');
      const dbType = data.database && data.database.includes('mysql') ? 'MySQL' : 'SQLite (Active)';
      pillText.textContent = `Online • ${dbType}`;
    } else {
      dot.classList.add('offline');
      pillText.textContent = 'API Error';
    }
  } catch (err) {
    dot.classList.add('offline');
    pillText.textContent = 'Backend Offline';
  }
}

async function refreshAllData() {
  await Promise.all([loadSlots(), loadBookings()]);
  updateMetrics();
}

async function loadSlots() {
  let url = `${API_BASE}/slots?`;
  if (state.filterStatus === 'ALL') {
    url += 'all=true';
  } else if (state.filterStatus) {
    url += `status=${encodeURIComponent(state.filterStatus)}`;
  }

  if (state.filterDate) {
    url += `&date=${encodeURIComponent(state.filterDate)}`;
  }

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.slots = data.slots || [];
    renderSlots();
    populateConcurrencySlotsDropdown();
  } catch (err) {
    console.error('Error fetching slots:', err);
    slotsGrid.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⚠️</div>
        <h3 class="empty-title">Failed to Load Slots</h3>
        <p class="empty-desc">Could not connect to backend at ${API_BASE}. Make sure the Flask server is running.</p>
        <button class="btn btn-secondary" onclick="loadSlots()">Retry</button>
      </div>
    `;
  }
}

async function loadBookings() {
  let url = `${API_BASE}/bookings`;
  if (state.filterBookingStatus) {
    url += `?status=${encodeURIComponent(state.filterBookingStatus)}`;
  }

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.bookings = data.bookings || [];
    renderBookings();
  } catch (err) {
    console.error('Error fetching bookings:', err);
  }
}

// ============================================================================
// Renderers
// ============================================================================
function updateMetrics() {
  const total = state.slots.length;
  const available = state.slots.filter(s => s.status === 'AVAILABLE').length;
  const confirmedBookings = state.bookings.filter(b => b.booking_status === 'CONFIRMED').length;

  elTotalSlots.textContent = total;
  elAvailableSlots.textContent = available;
  elBookedSlots.textContent = confirmedBookings;

  elBadgeAvailable.textContent = available;
  elBadgeBookings.textContent = confirmedBookings;
}

function formatDateDisplay(dateStr) {
  if (!dateStr) return '';
  const [y, m, d] = dateStr.split('-');
  const dt = new Date(y, m - 1, d);
  return dt.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
}

function renderSlots() {
  if (state.slots.length === 0) {
    slotsGrid.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🔍</div>
        <h3 class="empty-title">No Slots Found</h3>
        <p class="empty-desc">No appointment slots match the selected date or filter. Use the 'Create Slots' tab to add new slots.</p>
      </div>
    `;
    return;
  }

  slotsGrid.innerHTML = state.slots.map(slot => {
    const isAvailable = slot.status === 'AVAILABLE';
    const isBooked = slot.status === 'BOOKED';
    const statusClass = isAvailable ? 'available' : (isBooked ? 'booked' : 'cancelled');
    const statusLabel = isAvailable ? 'Open Slot' : (isBooked ? 'Reserved' : 'Cancelled');

    return `
      <div class="slot-card ${statusClass}" data-slot-id="${slot.id}">
        <div>
          <div class="slot-header">
            <span class="slot-date-badge">📅 ${formatDateDisplay(slot.slot_date)}</span>
            <span class="status-tag ${statusClass}">
              ● ${statusLabel}
            </span>
          </div>

          <div class="slot-time">${slot.formatted_time || `${slot.start_time} - ${slot.end_time}`}</div>
          <div class="slot-duration">Slot ID: #${slot.id} • 30 mins appointment</div>
        </div>

        <div class="slot-actions">
          ${isAvailable ? `
            <button class="btn btn-primary" onclick="openBookingModal(${slot.id})">
              Book Appointment
            </button>
          ` : `
            <button class="btn btn-secondary" disabled style="opacity: 0.55; cursor: not-allowed;">
              ${isBooked ? 'Already Booked' : 'Slot Closed'}
            </button>
          `}
        </div>
      </div>
    `;
  }).join('');
}

function renderBookings() {
  let filtered = [...state.bookings];

  if (state.searchBookings) {
    filtered = filtered.filter(b => 
      (b.customer_name && b.customer_name.toLowerCase().includes(state.searchBookings)) ||
      (b.customer_email && b.customer_email.toLowerCase().includes(state.searchBookings)) ||
      (b.customer_phone && b.customer_phone.toLowerCase().includes(state.searchBookings))
    );
  }

  if (filtered.length === 0) {
    bookingsList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📋</div>
        <h3 class="empty-title">No Bookings Found</h3>
        <p class="empty-desc">${state.searchBookings ? 'No reservations match your search term.' : 'There are currently no recorded bookings.'}</p>
      </div>
    `;
    return;
  }

  bookingsList.innerHTML = filtered.map(b => {
    const slot = b.slot || {};
    const isConfirmed = b.booking_status === 'CONFIRMED';
    const initials = b.customer_name ? b.customer_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : 'CU';

    return `
      <div class="booking-item ${isConfirmed ? 'confirmed' : 'cancelled'}" data-booking-id="${b.id}">
        <div class="booking-meta-primary">
          <div class="booking-avatar">${initials}</div>
          <div>
            <div class="booking-customer-name">${escapeHtml(b.customer_name)}</div>
            <div class="booking-contacts">
              ${b.customer_email ? `<span>✉️ ${escapeHtml(b.customer_email)}</span>` : ''}
              ${b.customer_phone ? `<span>📞 ${escapeHtml(b.customer_phone)}</span>` : ''}
              <span>🔖 Booking #${b.id}</span>
            </div>
          </div>
        </div>

        <div class="booking-slot-info">
          <div class="booking-slot-date">📅 ${formatDateDisplay(slot.slot_date)}</div>
          <div class="booking-slot-time">⏰ ${slot.formatted_time || `${slot.start_time} - ${slot.end_time}`} (Slot #${b.slot_id})</div>
        </div>

        <div class="booking-actions">
          <span class="status-tag ${isConfirmed ? 'available' : 'cancelled'}">
            ${b.booking_status}
          </span>
          ${isConfirmed ? `
            <button class="btn btn-danger btn-sm" onclick="openCancelModal(${b.id})">
              Cancel & Release
            </button>
          ` : `
            <span style="font-size: 0.8rem; color: var(--text-dim);">Released</span>
          `}
        </div>
      </div>
    `;
  }).join('');
}

async function populateConcurrencySlotsDropdown() {
  try {
    const res = await fetch(`${API_BASE}/slots?status=AVAILABLE`);
    if (res.ok) {
      const data = await res.json();
      const availableSlots = data.slots || [];
      if (availableSlots.length > 0) {
        simSlotSelect.innerHTML = availableSlots.map(s => `
          <option value="${s.id}">Slot #${s.id} — ${s.slot_date} (${s.formatted_time || s.start_time})</option>
        `).join('');
        return;
      }
    }
  } catch (err) {
    console.warn('Could not fetch available slots for simulation:', err);
  }

  const availableSlots = state.slots.filter(s => s.status === 'AVAILABLE');
  if (availableSlots.length === 0) {
    simSlotSelect.innerHTML = '<option value="">No available slots (click Refresh or create one)</option>';
    return;
  }

  simSlotSelect.innerHTML = availableSlots.map(s => `
    <option value="${s.id}">Slot #${s.id} — ${s.slot_date} (${s.formatted_time || s.start_time})</option>
  `).join('');
}

// ============================================================================
// Modal & Action Handlers
// ============================================================================
window.openBookingModal = function(slotId) {
  const slot = state.slots.find(s => s.id === slotId);
  if (!slot) return;

  state.selectedSlotForBooking = slot;
  document.getElementById('booking-slot-id').value = slot.id;
  document.getElementById('customer-name').value = '';
  document.getElementById('customer-email').value = '';
  document.getElementById('customer-phone').value = '';

  const detailsEl = document.getElementById('modal-slot-details');
  detailsEl.innerHTML = `
    <div>
      <div style="font-size: 0.82rem; color: var(--text-muted);">Selected Slot #${slot.id}</div>
      <div style="font-size: 1.15rem; font-weight: 700; color: #fff;">${formatDateDisplay(slot.slot_date)}</div>
      <div style="font-size: 0.88rem; color: var(--text-muted);">${slot.formatted_time || `${slot.start_time} - ${slot.end_time}`}</div>
    </div>
    <span class="status-tag available">Available</span>
  `;

  modalBooking.classList.add('open');
};

function closeBookingModal() {
  modalBooking.classList.remove('open');
  state.selectedSlotForBooking = null;
}

async function handleBookingSubmit(e) {
  e.preventDefault();
  const slotId = parseInt(document.getElementById('booking-slot-id').value, 10);
  const name = document.getElementById('customer-name').value.trim();
  const email = document.getElementById('customer-email').value.trim();
  const phone = document.getElementById('customer-phone').value.trim();

  if (!name) {
    showToast('Customer name is required', 'error');
    return;
  }

  const submitBtn = document.getElementById('btn-submit-booking');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Securing Slot...';

  try {
    const res = await fetch(`${API_BASE}/bookings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        slot_id: slotId,
        customer_name: name,
        customer_email: email || undefined,
        customer_phone: phone || undefined
      })
    });

    const data = await res.json();

    if (res.status === 201) {
      showToast('🎉 Appointment booked successfully!', 'success');
      closeBookingModal();
      await refreshAllData();
      switchTab('tab-bookings');
    } else if (res.status === 409) {
      // DOUBLE-BOOKING CONFLICT
      showToast('⚠️ Conflict! This slot is already reserved. Double-booking prevented.', 'error');
      closeBookingModal();
      await refreshAllData();
    } else {
      showToast(data.error || 'Failed to book slot', 'error');
    }
  } catch (err) {
    showToast('Network error while booking appointment', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Confirm Booking';
  }
}

window.openCancelModal = function(bookingId) {
  const booking = state.bookings.find(b => b.id === bookingId);
  if (!booking) return;

  state.selectedBookingForCancel = booking;
  const slot = booking.slot || {};
  const detailsEl = document.getElementById('modal-cancel-details');
  detailsEl.innerHTML = `
    <div>
      <div style="font-weight: 700; color: #fff;">${escapeHtml(booking.customer_name)}</div>
      <div style="font-size: 0.85rem; color: var(--text-muted);">${formatDateDisplay(slot.slot_date)} • ${slot.formatted_time || ''}</div>
    </div>
    <span class="status-tag booked">Booking #${booking.id}</span>
  `;

  modalCancel.classList.add('open');
};

function closeCancelModal() {
  modalCancel.classList.remove('open');
  state.selectedBookingForCancel = null;
}

async function handleCancelSubmit() {
  if (!state.selectedBookingForCancel) return;
  const bookingId = state.selectedBookingForCancel.id;
  const confirmBtn = document.getElementById('btn-confirm-cancel-action');
  confirmBtn.disabled = true;
  confirmBtn.textContent = 'Releasing Slot...';

  try {
    const res = await fetch(`${API_BASE}/bookings/${bookingId}`, {
      method: 'DELETE'
    });

    const data = await res.json();
    if (res.ok) {
      showToast('Booking cancelled & slot released back to Available', 'success');
      closeCancelModal();
      await refreshAllData();
    } else {
      showToast(data.error || 'Failed to cancel booking', 'error');
    }
  } catch (err) {
    showToast('Network error while cancelling booking', 'error');
  } finally {
    confirmBtn.disabled = false;
    confirmBtn.textContent = 'Yes, Cancel Booking';
  }
}

async function handleCreateSlotSubmit(e) {
  e.preventDefault();
  const dateVal = document.getElementById('slot-date').value;
  const startTime = document.getElementById('slot-start-time').value;
  const endTime = document.getElementById('slot-end-time').value;

  if (!dateVal || !startTime || !endTime) {
    showToast('Please fill in all date and time fields', 'error');
    return;
  }

  const btn = document.getElementById('btn-submit-single-slot');
  btn.disabled = true;
  btn.textContent = 'Creating...';

  try {
    const res = await fetch(`${API_BASE}/slots`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        date: dateVal,
        start_time: startTime,
        end_time: endTime
      })
    });

    const data = await res.json();
    if (res.status === 201) {
      showToast('Appointment slot created successfully!', 'success');
      await refreshAllData();
      switchTab('tab-slots');
    } else {
      showToast(data.error || 'Failed to create slot', 'error');
    }
  } catch (err) {
    showToast('Network error creating slot', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '➕ Add Appointment Slot';
  }
}

async function handleBatchSlotsSubmit(e) {
  e.preventDefault();
  const dateVal = document.getElementById('batch-date').value;
  const startHour = parseInt(document.getElementById('batch-start-hour').value, 10);
  const endHour = parseInt(document.getElementById('batch-end-hour').value, 10);
  const duration = parseInt(document.getElementById('batch-duration').value, 10);

  const btn = document.getElementById('btn-submit-batch-slots');
  btn.disabled = true;
  btn.textContent = 'Generating Slots...';

  try {
    const res = await fetch(`${API_BASE}/slots/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        date: dateVal,
        start_hour: startHour,
        end_hour: endHour,
        duration_minutes: duration
      })
    });

    const data = await res.json();
    if (res.status === 201) {
      showToast(data.message, 'success');
      await refreshAllData();
      switchTab('tab-slots');
    } else {
      showToast(data.error || 'Failed to batch generate slots', 'error');
    }
  } catch (err) {
    showToast('Network error generating batch slots', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '⚡ Generate Working Day Slots';
  }
}

// ============================================================================
// Concurrency & Double-Booking Simulation (Live UI Race Condition Tester)
// ============================================================================
async function runDoubleBookingSimulation() {
  const slotId = parseInt(simSlotSelect.value, 10);
  if (!slotId) {
    showToast('Please select an available slot to test', 'warning');
    return;
  }

  const btn = document.getElementById('btn-run-race-sim');
  btn.disabled = true;
  btn.textContent = 'Firing Simultaneous Requests...';

  simConsole.innerHTML = `
    <div class="sim-log-item sim-log-info">
      [Init] Targeting Slot #${slotId}. Firing 2 simultaneous asynchronous requests...
    </div>
  `;

  const makeReq = async (userName, userEmail) => {
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE}/bookings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slot_id: slotId,
          customer_name: userName,
          customer_email: userEmail
        })
      });
      const elapsed = Math.round(performance.now() - start);
      const json = await res.json();
      return { status: res.status, ok: res.ok, json, elapsed };
    } catch (err) {
      return { status: 0, ok: false, error: err.message };
    }
  };

  // Launch both requests simultaneously
  const [resA, resB] = await Promise.all([
    makeReq('Concurrent Customer A (Thread 1)', 'customerA@sim.test'),
    makeReq('Concurrent Customer B (Thread 2)', 'customerB@sim.test')
  ]);

  let logsHtml = '';

  // Log Request A
  if (resA.status === 201) {
    logsHtml += `<div class="sim-log-item sim-log-success">✅ Request A (Customer A): HTTP 201 CREATED (${resA.elapsed}ms) — Booking confirmed!</div>`;
  } else if (resA.status === 409) {
    logsHtml += `<div class="sim-log-item sim-log-conflict">🛡️ Request A (Customer A): HTTP 409 CONFLICT (${resA.elapsed}ms) — Double-booking rejected!</div>`;
  } else {
    logsHtml += `<div class="sim-log-item">❌ Request A: HTTP ${resA.status} (${JSON.stringify(resA.json || resA.error)})</div>`;
  }

  // Log Request B
  if (resB.status === 201) {
    logsHtml += `<div class="sim-log-item sim-log-success">✅ Request B (Customer B): HTTP 201 CREATED (${resB.elapsed}ms) — Booking confirmed!</div>`;
  } else if (resB.status === 409) {
    logsHtml += `<div class="sim-log-item sim-log-conflict">🛡️ Request B (Customer B): HTTP 409 CONFLICT (${resB.elapsed}ms) — Double-booking rejected!</div>`;
  } else {
    logsHtml += `<div class="sim-log-item">❌ Request B: HTTP ${resB.status} (${JSON.stringify(resB.json || resB.error)})</div>`;
  }

  // Evaluation
  const hasOne201 = (resA.status === 201 && resB.status === 409) || (resB.status === 201 && resA.status === 409);
  if (hasOne201) {
    logsHtml += `
      <div class="sim-log-item sim-log-info" style="font-weight: bold; margin-top: 0.5rem; color: #10b981;">
        🎉 VERIFICATION PASSED: Exactly ONE booking succeeded, and the duplicate was rejected with 409 Conflict!
      </div>
      <div class="sim-log-item sim-log-info" style="font-size: 0.78rem; opacity: 0.85;">
        Row-level locking (SELECT ... FOR UPDATE) ensured serialized transaction execution.
      </div>
    `;
    showToast('Simulation passed: Double-booking successfully blocked!', 'success');
  } else {
    logsHtml += `
      <div class="sim-log-item" style="color: #f59e0b; margin-top: 0.5rem;">
        Notice: Slot might have already been booked or encountered an unexpected state.
      </div>
    `;
  }

  simConsole.innerHTML += logsHtml;
  simConsole.scrollTop = simConsole.scrollHeight;

  btn.disabled = false;
  btn.textContent = '🚀 Launch 2 Simultaneous Bookings';

  await refreshAllData();
}

// ============================================================================
// Toast Notification Engine
// ============================================================================
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : (type === 'warning' ? '⚠️' : 'ℹ️'));

  toast.innerHTML = `
    <span>${icon}</span>
    <div class="toast-message">${escapeHtml(message)}</div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(120%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
