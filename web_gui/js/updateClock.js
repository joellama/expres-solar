function updateClock() {
        // a cleaner way than string concatenation
        var str = new Date().toISOString().substr(0, 19);
        var str2 = str.replace("T", " ");
        document.getElementById('time').innerHTML = str2;
        var azdate = new Date(Date.now() - 25200000.0).toISOString().substr(0, 19);
        var azdate2 = azdate.replace("T", " ");
        document.getElementById('aztime').innerHTML = azdate2;
        // call this function again in 1000ms
        setTimeout(updateClock, 1000);
}

updateClock(); // initial call