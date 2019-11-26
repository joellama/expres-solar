const key = 'ec05c9f96f55bb12b2ac3b1e332c3112';

function weatherBallon( ) {
    fetch('https://api.openweathermap.org/data/2.5/weather'+ '?appid=' + key + '&lat=34.7444004&lon=-111.4244857')  
    .then(function(resp) { return resp.json() }) // Convert data to json
    .then(function(data) {
        var description = data.weather[0].description; 
        document.getElementById('weather').innerHTML = description;
    })
    .catch(function() {
        // catch any errors
    });
    setTimeout(weatherBallon, 300000);
}

weatherBallon();