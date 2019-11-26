socket.on('update', function(data) {
  console.log('updating sidebar');
  for (var key in data) {
      var variable = data[key];
      document.getElementById(key).innerHTML = data[key];
  }
});  