# Repair the catalog filter

Implement the existing CommonJS `selectProducts(items, options = {})` in `filter.cjs`. Product records have `id`, `name`, `category`, and numeric `price`.

- `query` matches a trimmed, case-insensitive substring of name; blank means all.
- `categories` is an optional array; empty/missing means all, otherwise match any listed category exactly.
- `minPrice`/`maxPrice` are optional inclusive bounds, including zero.
- `sort` is `price-asc`, `price-desc`, or `name` (case-insensitive ASCII order); missing/unrecognized means preserve source order. Equal sort values preserve source order.
- `page` defaults to 1 and `pageSize` to 10; both must be positive integers when supplied, otherwise raise RangeError.
- Return `{items, total, page, pageSize}`, with total after filtering and before pagination. An out-of-range page has empty items.
- Do not mutate inputs/options or add dependencies. Preserve the export signature.
