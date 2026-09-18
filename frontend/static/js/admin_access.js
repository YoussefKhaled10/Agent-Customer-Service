(() => {
  const TOKEN_KEY = 'pharmacare_token';
  const adminLink = document.querySelector('[data-admin-link]');
  if (!adminLink) return;
  adminLink.hidden = true;
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return;
  fetch('/api/admin/session', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` }
  }).then(response => {
    if (response.ok) adminLink.hidden = false;
  }).catch(() => {});
  adminLink.addEventListener('click', async event => {
    event.preventDefault();
    const response = await fetch('/api/admin/session', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    });
    if (response.ok) location.assign('/admin');
  });
})();
