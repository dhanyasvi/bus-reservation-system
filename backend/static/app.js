// OmniBus AI — Frontend Application Logic

const API_BASE = '';
let chatHistory = [];
let availableSeatsList = [];
let bookedSeatsMap = {};
let selectedSeatNo = null;
let currentAgentMode = 'multi'; // 'multi' or 'single'
let currentUserToken = localStorage.getItem('omnibus_token') || null;
let currentUsername = localStorage.getItem('omnibus_user') || null;

// DOM Elements
const seatGrid = document.getElementById('seatGrid');
const statTotalSeats = document.getElementById('statTotalSeats');
const statAvailableSeats = document.getElementById('statAvailableSeats');
const statBookedSeats = document.getElementById('statBookedSeats');
const statRoutes = document.getElementById('statRoutes');
const aiStatusText = document.getElementById('aiStatusText');
const aiSubtext = document.getElementById('aiSubtext');

const modeSingleBtn = document.getElementById('modeSingleBtn');
const modeMultiBtn = document.getElementById('modeMultiBtn');

const sourceCitySelect = document.getElementById('sourceCitySelect');
const destCitySelect = document.getElementById('destCitySelect');
const passengerNameInput = document.getElementById('passengerNameInput');
const seatNoInput = document.getElementById('seatNoInput');
const reservationForm = document.getElementById('reservationForm');
const formAlert = document.getElementById('formAlert');

const bookingsTableBody = document.getElementById('bookingsTableBody');
const noBookingsMsg = document.getElementById('noBookingsMsg');
const bookingSearchInput = document.getElementById('bookingSearchInput');

const chatMessages = document.getElementById('chatMessages');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const chatSendBtn = document.getElementById('chatSendBtn');
const clearChatBtn = document.getElementById('clearChatBtn');

// Modals
const schedulesModal = document.getElementById('schedulesModal');
const openSchedulesBtn = document.getElementById('openSchedulesBtn');
const closeSchedulesBtn = document.getElementById('closeSchedulesBtn');
const cancelSchedulesBtn = document.getElementById('cancelSchedulesBtn');
const schedulesTableBody = document.getElementById('schedulesTableBody');

const settingsModal = document.getElementById('settingsModal');
const openSettingsBtn = document.getElementById('openSettingsBtn');
const closeSettingsBtn = document.getElementById('closeSettingsBtn');
const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
const saveConfigBtn = document.getElementById('saveConfigBtn');
const testPingBtn = document.getElementById('testPingBtn');
const pingResult = document.getElementById('pingResult');
const cfgApiKey = document.getElementById('cfgApiKey');
const cfgBaseUrl = document.getElementById('cfgBaseUrl');
const cfgModel = document.getElementById('cfgModel');
const cfgCurrentKeyHint = document.getElementById('cfgCurrentKeyHint');
const toggleApiKeyVis = document.getElementById('toggleApiKeyVis');

const authModal = document.getElementById('authModal');
const openAuthBtn = document.getElementById('openAuthBtn');
const closeAuthBtn = document.getElementById('closeAuthBtn');
const cancelAuthBtn = document.getElementById('cancelAuthBtn');
const loginUsername = document.getElementById('loginUsername');
const submitLoginBtn = document.getElementById('submitLoginBtn');
const authAlert = document.getElementById('authAlert');
const authBtnText = document.getElementById('authBtnText');

const adminModal = document.getElementById('adminModal');
const openAdminBtn = document.getElementById('openAdminBtn');
const closeAdminBtn = document.getElementById('closeAdminBtn');
const cancelAdminBtn = document.getElementById('cancelAdminBtn');
const adminKeyInput = document.getElementById('adminKeyInput');
const adminPurgeBtn = document.getElementById('adminPurgeBtn');
const adminAlert = document.getElementById('adminAlert');

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  if (currentUsername) {
    authBtnText.textContent = currentUsername.split('@')[0];
    passengerNameInput.value = currentUsername.split('@')[0];
  }
  loadConfig();
  refreshAllData();
  setupEventListeners();
});

// Load Config & Cities
async function loadConfig() {
  try {
    const res = await fetch(`${API_BASE}/api/config`);
    if (!res.ok) return;
    const data = await res.json();

    if (data.cities && data.cities.length) {
      sourceCitySelect.innerHTML = '';
      destCitySelect.innerHTML = '';
      data.cities.forEach((city, index) => {
        const opt1 = new Option(city, city, false, index === 0);
        const opt2 = new Option(city, city, false, index === 1);
        sourceCitySelect.add(opt1);
        destCitySelect.add(opt2);
      });
    }

    updateAiBadge(data.llm_status, data.llm_model);

    cfgBaseUrl.value = data.llm_base_url || 'https://api.openai.com/v1';
    cfgModel.value = data.llm_model || 'gpt-4o-mini';
    cfgCurrentKeyHint.textContent = `Current Key: ${data.llm_api_key_masked}`;
  } catch (err) {
    console.error('Error loading config:', err);
  }
}

function updateAiBadge(statusInfo, model) {
  const modeLabel = currentAgentMode === 'multi' ? 'Multi-Agent Team' : 'Single-Agent';
  if (statusInfo && statusInfo.available) {
    aiStatusText.textContent = `AI: ${model} Online (${modeLabel})`;
    aiSubtext.textContent = `Active Mode: ${modeLabel} with OpenAI-Compatible Tool Calling`;
  } else {
    aiStatusText.textContent = `AI: Resilient Engine (${modeLabel})`;
    aiSubtext.textContent = `Active Mode: ${modeLabel} (No API Credit Required, 100% Operational)`;
  }
}

// Refresh Both Seats, Bookings & Schedules
async function refreshAllData() {
  await Promise.all([fetchSeats(), fetchBookings()]);
}

// Fetch Seat Layout
async function fetchSeats() {
  try {
    const res = await fetch(`${API_BASE}/seats/available`);
    if (!res.ok) return;
    const data = await res.json();

    availableSeatsList = data.available_seats || [];
    bookedSeatsMap = data.booked_details || {};

    statTotalSeats.textContent = data.total_seats || 40;
    statAvailableSeats.textContent = data.available_count || 0;
    statBookedSeats.textContent = data.booked_count || 0;

    renderCoach(data.total_seats || 40);
  } catch (err) {
    console.error('Error fetching seats:', err);
  }
}

// Render 40 Seats
function renderCoach(totalSeats) {
  seatGrid.innerHTML = '';
  const rows = Math.ceil(totalSeats / 4);

  for (let r = 0; r < rows; r++) {
    const rowDiv = document.createElement('div');
    rowDiv.className = 'seat-row';

    const seat1 = r * 4 + 1;
    const seat2 = r * 4 + 2;
    const seat3 = r * 4 + 3;
    const seat4 = r * 4 + 4;

    rowDiv.appendChild(createSeatElement(seat1));
    rowDiv.appendChild(createSeatElement(seat2));

    const aisleDiv = document.createElement('div');
    aisleDiv.className = 'aisle-spacer';
    aisleDiv.textContent = `R${r + 1}`;
    rowDiv.appendChild(aisleDiv);

    rowDiv.appendChild(createSeatElement(seat3));
    rowDiv.appendChild(createSeatElement(seat4));

    seatGrid.appendChild(rowDiv);
  }
}

function createSeatElement(seatNum) {
  const el = document.createElement('div');
  const isBooked = !availableSeatsList.includes(seatNum);
  const isSelected = selectedSeatNo === seatNum;

  el.className = `seat-item ${isBooked ? 'booked' : 'available'} ${isSelected ? 'selected' : ''}`;
  el.dataset.seat = seatNum;

  const numSpan = document.createElement('span');
  numSpan.className = 'seat-num';
  numSpan.textContent = seatNum;

  const tagSpan = document.createElement('span');
  tagSpan.className = 'seat-tag';

  if (isBooked) {
    const info = bookedSeatsMap[seatNum];
    tagSpan.textContent = 'Booked';
    el.title = info ? `Seat ${seatNum} — ${info.passenger_name} (${info.source} ➔ ${info.destination})` : `Seat ${seatNum} is booked`;
  } else {
    tagSpan.textContent = isSelected ? 'Chosen' : 'Free';
    el.title = `Seat ${seatNum} is available — Click to select`;

    el.addEventListener('click', () => {
      selectSeat(seatNum);
    });
  }

  el.appendChild(numSpan);
  el.appendChild(tagSpan);
  return el;
}

function selectSeat(seatNum) {
  selectedSeatNo = seatNum;
  seatNoInput.value = seatNum;

  document.querySelectorAll('.seat-item').forEach(s => {
    const num = parseInt(s.dataset.seat, 10);
    if (num === seatNum) {
      s.classList.add('selected');
      const tag = s.querySelector('.seat-tag');
      if (tag) tag.textContent = 'Chosen';
    } else {
      s.classList.remove('selected');
      if (s.classList.contains('available')) {
        const tag = s.querySelector('.seat-tag');
        if (tag) tag.textContent = 'Free';
      }
    }
  });

  if (window.innerWidth < 800) {
    reservationForm.scrollIntoView({ behavior: 'smooth' });
  }
}

// Fetch Bookings List with Fare & Payment / Refund Status
async function fetchBookings() {
  try {
    const query = bookingSearchInput.value.trim();
    const url = query ? `${API_BASE}/bookings?passenger_name=${encodeURIComponent(query)}` : `${API_BASE}/bookings`;
    const res = await fetch(url);
    if (!res.ok) return;
    const bookings = await res.json();
    renderBookingsTable(bookings);
  } catch (err) {
    console.error('Error fetching bookings:', err);
  }
}

function renderBookingsTable(bookings) {
  bookingsTableBody.innerHTML = '';
  if (!bookings || bookings.length === 0) {
    noBookingsMsg.classList.remove('hidden');
    return;
  }
  noBookingsMsg.classList.add('hidden');

  bookings.forEach(b => {
    const tr = document.createElement('tr');

    const statusBadgeClass = b.status === 'CONFIRMED' ? 'badge-confirmed' : 'badge-cancelled';
    const seatDisplay = b.seat_no ? `Seat ${b.seat_no}` : '<span style="color:#94a3b8">Freed</span>';
    
    // Payment status & refund
    let paymentBadge = `<span class="badge badge-paid">PAID • ₹${b.fare_amount || 750}</span>`;
    if (b.status === 'CANCELLED') {
      const refAmt = b.refund_amount ? ` (Refund ₹${b.refund_amount})` : '';
      paymentBadge = `<span class="badge badge-refunded">REFUNDED${refAmt}</span>`;
    }

    tr.innerHTML = `
      <td><strong>#${b.id}</strong></td>
      <td>
        <strong>${escapeHtml(b.passenger_name)}</strong>
        <div style="font-size:0.7rem; color:var(--text-dim)">Txn: ${b.transaction_id || 'TXN_DIRECT'}</div>
      </td>
      <td>${escapeHtml(b.source)} ➔ ${escapeHtml(b.destination)}</td>
      <td>${seatDisplay}</td>
      <td><strong>₹${b.fare_amount || 750}</strong></td>
      <td>
        <div><span class="badge ${statusBadgeClass}">${b.status}</span></div>
        <div style="margin-top:4px">${paymentBadge}</div>
      </td>
      <td>
        <div class="table-actions">
          ${b.status === 'CONFIRMED' ? `
            <button class="btn btn-secondary btn-sm" onclick="promptModifyBooking(${b.id}, ${b.seat_no || "null"}, '${escapeHtml(b.destination)}')">Modify</button>
            <button class="btn btn-danger btn-sm" onclick="cancelBookingDirect(${b.id})">Cancel</button>
          ` : `
            <button class="btn btn-secondary btn-sm" onclick="viewRefundStatus(${b.id})">Refund Info</button>
          `}
        </div>
      </td>
    `;
    bookingsTableBody.appendChild(tr);
  });
}

// View Refund Status
async function viewRefundStatus(bookingId) {
  try {
    const res = await fetch(`${API_BASE}/bookings/${bookingId}/refund`);
    const data = await res.json();
    alert(`Refund Details for Booking #${bookingId}:\n- Status: ${data.status}\n- Total Fare: ₹${data.fare_amount}\n- Refund Initiated: ₹${data.refund_amount}\n- Policy: ${data.refund_policy}`);
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

// Cancel Booking via API
async function cancelBookingDirect(bookingId) {
  if (!confirm(`Are you sure you want to cancel booking #${bookingId}? 90% refund will be automatically processed.`)) return;

  try {
    const res = await fetch(`${API_BASE}/bookings/${bookingId}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) {
      alert(`Could not cancel: ${data.detail || 'Error'}`);
      return;
    }
    const refMsg = data.refund_amount ? ` ₹${data.refund_amount} refund initiated.` : '';
    appendChatMessage('assistant', `✅ **Booking #${bookingId} has been cancelled.** Seat ${data.seat_no || ''} has been released.${refMsg}`, 'Ticket Management Specialist Agent');
    refreshAllData();
  } catch (err) {
    alert(`Network error: ${err}`);
  }
}

// Prompt to Modify Booking
async function promptModifyBooking(bookingId, currentSeat, currentDst) {
  const newSeatStr = prompt(`Enter new seat number (1-40) for Booking #${bookingId}:`, currentSeat || '');
  if (newSeatStr === null) return;
  const newSeat = parseInt(newSeatStr, 10);
  if (isNaN(newSeat) || newSeat < 1 || newSeat > 40) {
    alert('Please enter a valid seat number between 1 and 40.');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/bookings/${bookingId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ seat_no: newSeat })
    });
    const data = await res.json();
    if (!res.ok) {
      alert(`Update failed: ${data.detail || 'Error'}`);
      return;
    }
    appendChatMessage('assistant', `✅ **Booking #${bookingId} updated.** New seat is **${newSeat}**.`, 'Ticket Management Specialist Agent');
    refreshAllData();
  } catch (err) {
    alert(`Network error: ${err}`);
  }
}

// Direct Reservation Form Submit
reservationForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  formAlert.className = 'alert-box hidden';

  const name = passengerNameInput.value.trim();
  const seatNo = parseInt(seatNoInput.value, 10);
  const src = sourceCitySelect.value;
  const dst = destCitySelect.value;

  if (src === dst) {
    showFormAlert('Departure and destination cities must be different.', false);
    return;
  }

  try {
    const headers = { 'Content-Type': 'application/json' };
    if (currentUserToken) {
      headers['Authorization'] = `Bearer ${currentUserToken}`;
    }

    const res = await fetch(`${API_BASE}/bookings`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        passenger_name: name,
        source: src,
        destination: dst,
        seat_no: seatNo
      })
    });

    const data = await res.json();

    if (!res.ok) {
      showFormAlert(data.detail || 'Booking failed.', false);
      return;
    }

    showFormAlert(`🎉 Booking #${data.id} Confirmed! Seat ${data.seat_no} reserved for ${data.passenger_name} (Fare: ₹${data.fare_amount}, Txn: ${data.transaction_id}).`, true);
    
    appendChatMessage('assistant', `🎉 **Direct Reservation Confirmed!**\n- **Booking ID**: #${data.id}\n- **Passenger**: ${data.passenger_name}\n- **Route**: ${data.source} ➔ ${data.destination}\n- **Seat**: ${data.seat_no}\n- **Fare Paid**: ₹${data.fare_amount}\n- **Transaction ID**: ${data.transaction_id}`, 'Reservation Specialist Agent');

    passengerNameInput.value = currentUsername ? currentUsername.split('@')[0] : '';
    seatNoInput.value = '';
    selectedSeatNo = null;
    refreshAllData();
  } catch (err) {
    showFormAlert(`Error: ${err}`, false);
  }
});

function showFormAlert(msg, isSuccess) {
  formAlert.textContent = msg;
  formAlert.className = `alert-box ${isSuccess ? 'alert-success' : 'alert-error'}`;
}

// Fetch Schedules
async function fetchSchedules() {
  try {
    schedulesTableBody.innerHTML = '<tr><td colspan="6" style="text-align:center">Loading schedules...</td></tr>';
    const res = await fetch(`${API_BASE}/schedules`);
    const schedules = await res.json();
    schedulesTableBody.innerHTML = '';
    
    if (!schedules || schedules.length === 0) {
      schedulesTableBody.innerHTML = '<tr><td colspan="6" style="text-align:center">No schedules found.</td></tr>';
      return;
    }

    schedules.forEach(sc => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${sc.bus_number}</strong></td>
        <td>${sc.source} ➔ ${sc.destination}</td>
        <td>${sc.departure_time} - ${sc.arrival_time}</td>
        <td>${sc.bus_type}</td>
        <td><strong>₹${sc.fare}</strong></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="selectRouteFromSchedule('${sc.source}', '${sc.destination}')">Select Route</button>
        </td>
      `;
      schedulesTableBody.appendChild(tr);
    });
  } catch (err) {
    schedulesTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#f43f5e">Error: ${err.message}</td></tr>`;
  }
}

function selectRouteFromSchedule(src, dst) {
  sourceCitySelect.value = src;
  destCitySelect.value = dst;
  schedulesModal.classList.add('hidden');
  reservationForm.scrollIntoView({ behavior: 'smooth' });
}

// AI Chat Interaction (Supporting Single & Multi-Agent)
chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  chatInput.value = '';
  appendChatMessage('user', message);
  chatHistory.push({ role: 'user', content: message });

  const typingEl = document.createElement('div');
  typingEl.className = 'chat-bubble assistant typing-bubble';
  typingEl.innerHTML = `
    <div class="bubble-avatar">🤖</div>
    <div class="bubble-content"><p>${currentAgentMode === 'multi' ? 'Multi-Agent Team orchestrating...' : 'Assistant thinking...'}</p></div>
  `;
  chatMessages.appendChild(typingEl);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const headers = { 'Content-Type': 'application/json' };
    if (currentUserToken) {
      headers['Authorization'] = `Bearer ${currentUserToken}`;
    }

    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message,
        history: chatHistory,
        mode: currentAgentMode
      })
    });

    typingEl.remove();

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      appendChatMessage('assistant', `❌ Error: ${errData.detail || 'Could not complete request'}`);
      return;
    }

    const data = await res.json();
    const reply = data.reply || '';
    const agentName = data.agent || (currentAgentMode === 'multi' ? 'Reservation Specialist Agent' : 'Single Agent');
    
    appendChatMessage('assistant', reply, agentName);
    chatHistory.push({ role: 'assistant', content: reply });

    if (
      reply.includes('Confirmed') ||
      reply.includes('Booking #') ||
      reply.includes('cancelled') ||
      reply.includes('Cancelled') ||
      reply.includes('Updated') ||
      reply.includes('updated')
    ) {
      refreshAllData();
    }
  } catch (err) {
    typingEl.remove();
    appendChatMessage('assistant', `❌ Connection error: ${err.message}`);
  }
});

function appendChatMessage(role, text, agentName = null) {
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'bubble-avatar';
  avatar.innerHTML = role === 'user'
    ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'
    : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="8" width="16" height="12" rx="2"></rect><circle cx="9" cy="13" r="1"></circle><circle cx="15" cy="13" r="1"></circle></svg>';

  const content = document.createElement('div');
  content.className = 'bubble-content';

  if (role === 'assistant' && agentName) {
    const tag = document.createElement('div');
    tag.className = 'agent-tag';
    tag.textContent = agentName;
    content.appendChild(tag);
  }

  const textWrap = document.createElement('div');
  textWrap.innerHTML = formatMarkdown(text);
  content.appendChild(textWrap);

  bubble.appendChild(avatar);
  bubble.appendChild(content);

  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Markdown Formatter
function formatMarkdown(text) {
  if (!text) return '';
  let html = escapeHtml(text);

  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.1);padding:2px 4px;border-radius:4px;font-family:var(--font-mono)">$1</code>');
  html = html.replace(/^- (.*)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
  html = html.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');

  return `<p>${html}</p>`;
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

// Event Listeners Setup
function setupEventListeners() {
  // Agent Mode Switcher (Single vs Multi)
  modeSingleBtn.addEventListener('click', () => {
    currentAgentMode = 'single';
    modeSingleBtn.classList.add('active');
    modeMultiBtn.classList.remove('active');
    aiSubtext.textContent = 'Active Mode: Single-Agent (Unified Assistant)';
  });

  modeMultiBtn.addEventListener('click', () => {
    currentAgentMode = 'multi';
    modeMultiBtn.classList.add('active');
    modeSingleBtn.classList.remove('active');
    aiSubtext.textContent = 'Active Mode: 👥 Multi-Agent Team (Supervisor, Booking, Ticket, Schedule)';
  });

  // Schedules Modal
  openSchedulesBtn.addEventListener('click', () => {
    schedulesModal.classList.remove('hidden');
    fetchSchedules();
  });
  closeSchedulesBtn.addEventListener('click', () => schedulesModal.classList.add('hidden'));
  cancelSchedulesBtn.addEventListener('click', () => schedulesModal.classList.add('hidden'));

  // Auth Modal
  openAuthBtn.addEventListener('click', () => {
    authModal.classList.remove('hidden');
    authAlert.className = 'alert-box hidden';
  });
  closeAuthBtn.addEventListener('click', () => authModal.classList.add('hidden'));
  cancelAuthBtn.addEventListener('click', () => authModal.classList.add('hidden'));

  submitLoginBtn.addEventListener('click', async () => {
    const u = loginUsername.value.trim();
    if (!u) {
      authAlert.textContent = 'Please enter a passenger username or email.';
      authAlert.className = 'alert-box alert-error';
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u })
      });
      const data = await res.json();
      if (res.ok) {
        currentUserToken = data.access_token;
        currentUsername = data.username;
        localStorage.setItem('omnibus_token', currentUserToken);
        localStorage.setItem('omnibus_user', currentUsername);
        authBtnText.textContent = currentUsername.split('@')[0];
        passengerNameInput.value = currentUsername.split('@')[0];
        authModal.classList.add('hidden');
        alert(`Signed in as ${currentUsername}! JWT access token stored.`);
      }
    } catch (err) {
      authAlert.textContent = `Login error: ${err.message}`;
      authAlert.className = 'alert-box alert-error';
    }
  });

  // Swap cities button
  document.getElementById('swapCitiesBtn').addEventListener('click', () => {
    const s = sourceCitySelect.value;
    sourceCitySelect.value = destCitySelect.value;
    destCitySelect.value = s;
  });

  // Clear Form
  document.getElementById('clearFormBtn').addEventListener('click', () => {
    passengerNameInput.value = currentUsername ? currentUsername.split('@')[0] : '';
    seatNoInput.value = '';
    selectedSeatNo = null;
    formAlert.className = 'alert-box hidden';
    renderCoach(parseInt(statTotalSeats.textContent, 10) || 40);
  });

  bookingSearchInput.addEventListener('input', () => {
    fetchBookings();
  });

  document.getElementById('refreshBookingsBtn').addEventListener('click', () => {
    refreshAllData();
  });

  clearChatBtn.addEventListener('click', () => {
    chatHistory = [];
    chatMessages.innerHTML = `
      <div class="chat-bubble assistant">
        <div class="bubble-avatar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="8" width="16" height="12" rx="2"></rect></svg>
        </div>
        <div class="bubble-content">
          <p>Conversation history cleared. Ready for your next request!</p>
        </div>
      </div>
    `;
  });

  document.querySelectorAll('.chip-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const promptText = btn.dataset.prompt;
      if (promptText) {
        chatInput.value = promptText;
        chatForm.dispatchEvent(new Event('submit'));
      }
    });
  });

  // Settings Modal
  openSettingsBtn.addEventListener('click', () => {
    settingsModal.classList.remove('hidden');
    pingResult.textContent = '';
  });
  closeSettingsBtn.addEventListener('click', () => settingsModal.classList.add('hidden'));
  cancelSettingsBtn.addEventListener('click', () => settingsModal.classList.add('hidden'));

  // Admin Modal
  openAdminBtn.addEventListener('click', () => {
    adminModal.classList.remove('hidden');
    adminAlert.className = 'alert-box hidden';
  });
  closeAdminBtn.addEventListener('click', () => adminModal.classList.add('hidden'));
  cancelAdminBtn.addEventListener('click', () => adminModal.classList.add('hidden'));

  toggleApiKeyVis.addEventListener('click', () => {
    cfgApiKey.type = cfgApiKey.type === 'password' ? 'text' : 'password';
  });

  document.querySelectorAll('[data-preset]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-preset]').forEach(b => b.classList.remove('active-preset'));
      btn.classList.add('active-preset');

      const preset = btn.dataset.preset;
      if (preset === 'resilient') {
        cfgApiKey.value = '';
        cfgBaseUrl.value = 'https://api.openai.com/v1';
        cfgModel.value = 'resilient-agent';
      } else if (preset === 'groq') {
        cfgBaseUrl.value = 'https://api.groq.com/openai/v1';
        cfgModel.value = 'llama-3.3-70b-versatile';
      } else if (preset === 'gemini') {
        cfgBaseUrl.value = 'https://generativelanguage.googleapis.com/v1beta/openai/';
        cfgModel.value = 'gemini-1.5-flash';
      } else if (preset === 'openai') {
        cfgBaseUrl.value = 'https://api.openai.com/v1';
        cfgModel.value = 'gpt-4o-mini';
      }
    });
  });

  testPingBtn.addEventListener('click', async () => {
    pingResult.innerHTML = '<span style="color:#94a3b8">Testing...</span>';
    try {
      const res = await fetch(`${API_BASE}/health/llm`);
      const data = await res.json();
      if (data.status === 'ok') {
        pingResult.innerHTML = `<span style="color:#10b981">✓ Online (${data.provider})</span>`;
      } else {
        pingResult.innerHTML = `<span style="color:#38bdf8">⚡ Built-in Agent Ready (${data.message || 'Active'})</span>`;
      }
    } catch (err) {
      pingResult.innerHTML = `<span style="color:#f43f5e">✗ Error: ${err.message}</span>`;
    }
  });

  saveConfigBtn.addEventListener('click', async () => {
    saveConfigBtn.textContent = 'Saving...';
    try {
      const payload = {
        base_url: cfgBaseUrl.value.trim(),
        model: cfgModel.value.trim()
      };
      if (cfgApiKey.value.trim() !== '') {
        payload.api_key = cfgApiKey.value.trim();
      }

      const res = await fetch(`${API_BASE}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      saveConfigBtn.textContent = 'Save Configuration';
      if (res.ok) {
        settingsModal.classList.add('hidden');
        loadConfig();
        alert('Configuration saved and active!');
      } else {
        alert('Error saving configuration.');
      }
    } catch (err) {
      saveConfigBtn.textContent = 'Save Configuration';
      alert(`Error: ${err.message}`);
    }
  });

  adminPurgeBtn.addEventListener('click', async () => {
    const key = adminKeyInput.value.trim();
    if (!key) {
      adminAlert.textContent = 'Please enter the Admin API Key.';
      adminAlert.className = 'alert-box alert-error';
      return;
    }

    if (!confirm('WARNING: This will permanently delete ALL bookings in the database. Proceed?')) {
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/admin/bookings`, {
        method: 'DELETE',
        headers: { 'X-Admin-Key': key }
      });
      const data = await res.json();
      if (!res.ok) {
        adminAlert.textContent = data.detail || 'Purge failed. Invalid admin key.';
        adminAlert.className = 'alert-box alert-error';
        return;
      }
      adminAlert.textContent = `Success! Deleted ${data.deleted} bookings.`;
      adminAlert.className = 'alert-box alert-success';
      refreshAllData();
      appendChatMessage('assistant', `⚠️ **Admin Alert**: All bookings have been purged from the database.`, 'Administrator');
    } catch (err) {
      adminAlert.textContent = `Error: ${err.message}`;
      adminAlert.className = 'alert-box alert-error';
    }
  });
}
