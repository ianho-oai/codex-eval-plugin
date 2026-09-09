exports.createSearch = ({fetchResults, onState}) => ({
  search(query) { fetchResults(query, {}).then(items => onState({status:'success', query, items})); },
  dispose() {}
});
