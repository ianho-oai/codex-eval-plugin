exports.selectProducts = (items, options = {}) => {
  const {query = '', categories = [], minPrice, maxPrice, sort, page = 1, pageSize = 10} = options;
  if (!Number.isInteger(page) || page < 1 || !Number.isInteger(pageSize) || pageSize < 1) throw new RangeError('pagination');
  const q = query.trim().toLowerCase();
  const selected = items.filter(p => p.name.toLowerCase().includes(q) &&
    (!categories.length || categories.includes(p.category)) &&
    (minPrice === undefined || p.price >= minPrice) && (maxPrice === undefined || p.price <= maxPrice));
  if (sort === 'price-asc') selected.sort((a,b) => a.price-b.price);
  if (sort === 'price-desc') selected.sort((a,b) => b.price-a.price);
  if (sort === 'name') selected.sort((a,b) => {
    const x = a.name.toLowerCase(), y = b.name.toLowerCase();
    return x < y ? -1 : x > y ? 1 : 0;
  });
  return {items: selected.slice((page-1)*pageSize, page*pageSize), total: selected.length, page, pageSize};
};
