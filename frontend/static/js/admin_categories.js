(() => {
  const modal=document.querySelector('[data-category-modal]');
  const form=document.querySelector('[data-category-form]');
  if(!modal||!form)return;
  const title=document.querySelector('[data-category-modal-title]');
  const open=()=>{modal.hidden=false;document.body.style.overflow='hidden';};
  const close=()=>{modal.hidden=true;document.body.style.overflow='';form.reset();form.action='/admin/categories';title.textContent='Add Category';};
  document.querySelectorAll('[data-open-category-modal]').forEach(button=>button.addEventListener('click',open));
  document.querySelectorAll('[data-close-category-modal]').forEach(button=>button.addEventListener('click',close));
  modal.addEventListener('click',event=>{if(event.target===modal)close();});
  document.querySelectorAll('[data-edit-category]').forEach(button=>button.addEventListener('click',async()=>{
    const id=button.dataset.editCategory;
    const response=await fetch(`/admin/categories/${id}/json`);
    if(!response.ok){alert('Could not load category details.');return;}
    const category=await response.json();
    form.elements.name.value=category.name??'';
    form.elements.slug.value=category.slug??'';
    form.elements.description.value=category.description??'';
    form.action=`/admin/categories/${id}/update`;
    title.textContent='Edit Category';
    open();
  }));
})();
