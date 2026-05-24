document.addEventListener('click', function (e) {
  var wrapper = document.getElementById('search-wrapper');
  if (wrapper && !wrapper.contains(e.target)) {
    document.getElementById('search-results').innerHTML = '';
  }
});
