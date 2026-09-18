(() => {
  const modal = document.querySelector('[data-product-modal]');
  const form = document.querySelector('[data-product-form]');
  if (!modal || !form) return;
  const title = modal.querySelector('[data-modal-title]');
  const open = () => { modal.hidden = false; document.body.style.overflow = 'hidden'; };
  const close = () => { modal.hidden = true; document.body.style.overflow = ''; form.reset(); form.action = '/admin/products'; title.textContent = 'Add Product'; };
  document.querySelectorAll('[data-open-product-modal]').forEach(b => b.addEventListener('click', open));
  document.querySelectorAll('[data-close-product-modal]').forEach(b => b.addEventListener('click', close));
  modal.addEventListener('click', e => { if (e.target === modal) close(); });
  document.querySelectorAll('[data-edit-product]').forEach(button => button.addEventListener('click', async () => {
    const id = button.dataset.editProduct;
    const response = await fetch(`/admin/products/${id}/json`);
    if (!response.ok) { alert('Could not load product details.'); return; }
    const p = await response.json();
    ['name','sku','category_id','brand','price','stock','short_description','image_url'].forEach(key => { const field = form.elements[key]; if (field) field.value = p[key] ?? ''; });
    form.action = `/admin/products/${id}/update`;
    title.textContent = 'Edit Product';
    open();
  }));
  if (new URLSearchParams(location.search).get('open') === 'create') open();
})();
