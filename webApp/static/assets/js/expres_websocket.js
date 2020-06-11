/* Set up global variables and defaults */
 
if (! expresWS) {
	var expresWS = "ws://expres.lowell.edu:8842/ws/";
}
function socketMessageRouter(e) {
	if (typeof e.data == "string") {
		packet = $.parseJSON(e.data);
		if ((typeof packet !== 'object') || (! packet.hasOwnProperty('packet_type'))) { return; }
		
		if ( packet['packet_type'] == 'status') {
 
			update_status([packet]); /* just one status, wrap it in an array and re-use the same method */
		} else if ( packet['packet_type'] == 'all-systems-status') {
			update_status(packet);
		} else if (packet['packet_type'] == 'readout-complete') {
			// readout_complete(packet);
		} else if (packet['packet_type'].startsWith("error-")) {
			error_message(packet);
		} else if (packet['packet_type'].startsWith("warning-")) {
			warning_message(packet);
		} else if (packet['packet_type'].startsWith("clock")) {
			updateClock( packet );
		} else if ((packet['packet_type'] == 'active-observer') || (packet['packet_type'] == 'inactive-observer')) {
			console.log(packet);
			update_observers([packet]);
		} else if (packet['packet_type'] == 'disconnect-observer') {
			console.log(packet);
			remove_observers([packet]);
		} else if (packet['packet_type'] == 'disk-space') {
			updateDiskSpace(packet);
		} else {
			console.log(packet);
		}
	} else {
		var arr = new Uint8Array(e.data);
		var hex = "";
		for (var i = 0; i < arr.length; i++) {
			hex += ("00" + arr[i].toString(16)).substr(-2);
		}
		console.log("Binary message received: " + hex);
	}
}

wsMessageHandler = socketMessageRouter;
 
var socket = null;
var isopen = false;
// var wsMessageHandler = "undefined";

var reconnectTryInterval = 1500; /* milliseconds (1.5 seconds) */
var reconnectTryAttempts = 0;
var reconnectMaxAttempts = 40;   /* Try to reconnect for 1 minute */

function reconnect(){
	reconnectTryAttempts += 1;
	
	if ( reconnectTryAttempts < reconnectMaxAttempts ){
		$("#tiny_message").html("Reconnecting");
		configInfo = $.getJSON('/config/js',
		function(results){ console.log(results); } /* Success ... only needed for debugging since we use done, fail, always below */
		)
		.done(openSocket)
		.fail(getServerFail)
		.always();
	} else {
		playSound('expres_error');
		$("#tiny_message").html("Disconnected");
		$("#tiny_message").css("color","#ec5b2f"); /* Remove! belongs in css */
		alert("ERROR: No longer connect to EXPRES.  The WebSocket has been disconnected for " + (reconnectTryAttempts * reconnectTryInterval / 1000) + " seconds.  Check connection, you will have to log in again to re-establish connection.");
	}
}

function getServerFail(){
	$("#tiny_message").html("Disconnected");
	$("#tiny_message").css("color","#ec5b2f"); /* Remove! belongs in css */
	alert("ERROR: Unable to open WebSocket Connection to Expres Manager.  Check that Expres Manager is running then try logging in again.");
}

function openSocket() {
	expresWS = "ws://expres.lowell.edu:8842/ws/";;

	if (isopen && socket != null){
		alert("Websocket already Open");
		return;
	}

	socket = new WebSocket(expresWS);
	socket.binaryType = "arraybuffer";

	socket.onopen = function() {
		console.log("Connected!");
		isopen = true;
		reconnectTryAttempts = 0; /* reset the counter */
		$("#tiny_message").html("");
		
 
	}

	if ( typeof wsMessageHandler === 'function' ){
		socket.onmessage = wsMessageHandler;
	} else {
		socket.onmessage = messageHandlerPrototype;
	}

	socket.onclose = function(event) {
		socket = null;
		isopen = false;
		
		if ( event.wasClean == true ){
			console.log("WebSocket connection to '" + event.target.url + "' closed nicely: " + event.reason)
		} else {
			console.log("WebSocket connection closed unexpectedly, reconnecting...");
			setTimeout( reconnect, reconnectTryInterval );
		}
	}
}
 
/* wait for websocket to open */
function waitForWebSocket(fcn, timeout, elapsed){
	if (isopen) {
		fcn();
	} else {
		if (timeout == undefined) {timeout = 10000}
		if (timeout <= 0) {
			window.alert('Still waiting for websocket...')
			var delay = 2000; //ms
		} else {
			var delay = 500; //ms
		}
		console.log('Waiting for websocket..');
		setTimeout(function(){waitForWebSocket(fcn, timeout-delay)}, delay);
	}
}
function update_status( stats ){
	Object.keys(stats).forEach(function(key,index) {
    	console.log(stats);
    	
    	stat = stats[key];
    	
    	modrow = $('#expres_status_list tbody tr[module="'+stat.module+'"]');
    	if (modrow.length == 0){
    		console.log("Status row not found for " + stat.module);
    		return;
    	} 
    	
    	if ((! stat.subsystem) || (stat.subsystem == '') || (stat.subsystem.toLowerCase() == 'none')) {
    		/* This is the primary module status, not a subsystem */
    		dClass = disposition_to_class(stat.disposition);
    		$(modrow).find('td[class="module_status"]').html('<span class="'+dClass+'" desc="'+stat.desc+'">'+stat.name+'</span>');
    	} else {
    		/* For subsystems, update an existing div or append a new one */
    		dClass = disposition_to_class(stat.disposition);
    		
    		existingStatus = $(modrow).find('td[class="subsystems"] div[subsystem="'+stat.subsystem+'"]');
    		
    		if (existingStatus.length){
    			$(existingStatus).html(
    				'<span class="name">'+stat.subsystem+'</span>' +
    				'<span class="'+dClass+'" desc="'+stat.desc+'">'+stat.name+'</span>');
    		} else {
    			$(modrow).find('td[class="subsystems"]').append(
    				'<div class="subsystem" ' +
    				'subsystem="'+stat.subsystem +'">' +
    				'<span class="name">'+stat.subsystem+'</span>' +
    				'<span class="'+dClass+'" desc="'+stat.desc+'">'+stat.name+'</span></div>');
    		}
    	}
	});
}

function disposition_to_class( disposition ){
	switch (disposition) {
		case 'Ready':
			return 'ready';
		case 'Not Ready':
			return 'not_ready';
		case 'Busy':
			return 'busy';
		case 'Timed Out':
			return 'timed_out';
		case 'Waiting':
			return 'waiting';
		case 'Physical':
			return 'physical';
		default:
			return 'unknown';
	};
}

var expresSocket = openSocket();