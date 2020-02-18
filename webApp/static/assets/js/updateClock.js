function updateClock(packet) {
	document.getElementById('utc').innerHTML = 'UTC: ' + packet['utc'].substring(11, 19);
	document.getElementById('local_time').innerHTML = 'AZ: ' + packet['local'].substring(11, 19);
	document.getElementById('mjd').innerHTML = 'AZ: ' + packet['mjd'].toFixed(5);
}