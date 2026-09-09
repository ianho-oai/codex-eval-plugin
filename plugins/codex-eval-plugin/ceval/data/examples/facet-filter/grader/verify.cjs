const assert = require('node:assert/strict');
const path = require('node:path');
const {selectProducts: select} = require(path.join(process.argv[2], 'filter.cjs'));
try {
  const products = Object.freeze([
    {id: 1, name: 'Alpha', category: 'a', price: 0},
    {id: 2, name: 'beta', category: 'b', price: 20},
    {id: 3, name: 'ALPHA mini', category: 'a', price: 10},
    {id: 4, name: 'Beta', category: 'a', price: 20},
    {id: 5, name: 'omega', category: 'b', price: 10}
  ].map(Object.freeze));
  const ids = result => result.items.map(x => x.id);
  assert.deepEqual(ids(select(products, {query:'  ALPHA  '})), [1,3]);
  assert.deepEqual(ids(select(products, {categories:['b'], minPrice:10, maxPrice:20, sort:'price-desc'})), [2,5]);
  assert.deepEqual(ids(select(products, {maxPrice:0})), [1]);
  assert.deepEqual(ids(select(products, {sort:'price-asc'})), [1,3,5,2,4]);
  assert.deepEqual(ids(select(products, {sort:'name'})), [1,3,2,4,5]);
  assert.deepEqual(select(products, {page:3, pageSize:2}), {items:[products[4]],total:5,page:3,pageSize:2});
  assert.deepEqual(ids(select(products, {page:9, pageSize:2})), []);
  assert.equal(select(products, {query:'absent'}).total, 0);
  assert.deepEqual(ids(select(products, {categories:[], sort:'unknown'})), [1,2,3,4,5]);
  assert.deepEqual(select([]), {items:[],total:0,page:1,pageSize:10});
  for (const v of [0,-1,1.5,'2',null,NaN,Infinity]) {
    assert.throws(() => select(products, {page:v}), RangeError);
    assert.throws(() => select(products, {pageSize:v}), RangeError);
  }
  for (let page=1; page<=8; page++) for (let size=1;size<=6;size++) {
    const options = Object.freeze({page,pageSize:size,sort:'price-asc',minPrice:10});
    const r = select(products, options);
    assert.equal(r.total,4);
    assert.deepEqual(ids(r), [3,5,2,4].slice((page-1)*size,page*size));
  }
  console.log('PASS: filtering, stable sort, pagination, boundaries, immutability');
} catch(e) { console.log('FAIL:', e.message); process.exit(1); }
