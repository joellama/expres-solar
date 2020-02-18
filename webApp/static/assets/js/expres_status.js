 function socketMessageRouter(e) {
	if (typeof e.data == "string") {
		packet = $.parseJSON(e.data);
		if ((typeof packet !== 'object') || (! packet.hasOwnProperty('packet_type'))) { return; }
		
		if ( packet['packet_type'] == 'status') {
			console.log(packet);
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
			// do nothing
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

var expres_modules = [];
var expres_observers = [];

var _idNum = 0;
function getNextID() {
	nextNum = _idNum;
	_idNum += 1;
	return 'webclient:'+_idNum;
}

function error_message( error ){
	/* We can get fancy later, but for now this will do */
	//alert(error['error']);
	console.log(error);
}

function warning_message( warning ){
	console.log(warning);
	if ('cleared' in warning){
		$("#tiny_message").html("");
	} else {
		$("#tiny_message").html(warning['warning']);
		playSound('alert');
	}
}

function update_status( stats ){
	Object.keys(stats).forEach(function(key,index) {
    	// console.log(key + ": " + stats[key]);
    	
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

function update_observers( observerList ){
	obsArea = $('#observers');
	
	Object.keys(observerList).forEach(function(key,index) {
    	//console.log(key + ": " + stats[key]);
    	observer = observerList[key];
    	
    	/* update an existing div or append a new one */
    	existingObserver = $(obsArea).find('div.observer[observer_id="'+observer.id+'"]');
    		
		if (existingObserver.length){
			$(existingObserver).find('span.timestamp').html(observer.last_active);
		} else {
			$(obsArea).append(observerRow(observer));
		}
	});
}

function remove_observers( observerList ){
	console.log("removing observers");
	console.log(observerList);
	
	obsArea = $('#observers');
	
	Object.keys(observerList).forEach(function(key,index) {
    	//console.log(key + ": " + stats[key]);
    	observer = observerList[key];
    	
    	/* remove an existing div with the user in it */
    	existingObserver = $(obsArea).find('div.observer[observer_id="'+observer.id+'"]');
    		
		if (existingObserver.length){
			$(existingObserver).remove();
		} else {
			// row wasn't there to delete
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
function get_modules() {
	/* On Startup, once we determine that expres_mgr is up and
		running we need to get a list of the modules that _should_
		have status.  These will remain 'offline' until we receive
		actual status updates from it.
	*/
	payload = JSON.stringify( {
		"method": "expres-modules",
		"params": {},
		"jsonrpc": "2.0",
		"id": getNextID(),
		});
	
	/* Tell expres we want the status, return the status over the websocket */
	cmdHeard = $.post(expresMgr, payload)
				.done(function(results){
					r = JSON.parse(results);
					expres_modules = r.result;
					build_status_table();})		/* When we receive the result, build/rebuild the status table */
				.fail(function(result){
					console.log(result);
					alert("Unable to retrieve list of EXPRES Modules from EXPRES Manager.  Check the server logs.");
					})
				.always();
}

function getStatus( moduleName, subsystem ){
	if ( subsystem == undefined ){ subsystem = ''; }
	if ( moduleName == undefined ){ moduleName = 'expres'; }
	
	payload = JSON.stringify( {
		"method": "expres-status",
		"params": {"moduleName": moduleName, "subsystem": subsystem},
		"jsonrpc": "2.0",
		"id": getNextID(),
		});

	/* Tell expres we want the status, return the status over the websocket */
	cmdHeard = $.post(expresMgr, payload,
				function(results){ console.log(results); }
				)
				.done()
				.fail()
				.always();
}

function getAllStatus() {
	payload = JSON.stringify( {
			"method": "expres-all_status",
			"jsonrpc": "2.0",
			"id": getNextID(),
		});
	
	cmdHeard = $.post(expresMgr, payload,
		function(results){ 
			// console.log(results);
		} /* Success ... only needed for debugging since we use done, fail, always below */
		)
		.done(function(results){
			r = JSON.parse(results);
			update_status(r.result);})		/* Callback methods attached to the returned data object */
		.fail()
		.always();
}

//  

function getAllObservers() {
	payload = JSON.stringify( {
			"method": "expres-get-active-observers",
			"jsonrpc": "2.0",
			"id": getNextID(),
		});
	
	cmdHeard = $.post(expresMgr, payload,
		function(results){ 
			console.log(results);
		} /* Success ... only needed for debugging since we use done, fail, always below */
		)
		.done(function(results){
			r = JSON.parse(results);
			update_observers(r.result);})		/* Callback methods attached to the returned data object */
		.fail()
		.always();
}

function moduleRow( module ){
	row = $('<tr></tr>');
	console.log(module);
	row.attr('module',module.name);
	
	/* Build a string for a button to promote _this_ target as the current target */
	btnStr = '<a href="javascript:getStatus(' + module.name + ');void(0);" class="button small icon fa fa-info-circle"><span class="label">Get Status</span></a> ';
	
	$(row)
		.append('<td >'+ btnStr + '</td>')
		.append('<td class="module_name">'+ module.pretty + '</td>')
		.append('<td class="module_status">'+ '<span class="unknown">Unknown</span>' + '</td>')
		.append('<td class="subsystems">'+ '<div class="subsystem" subsystem=""></div>' + '</td>');
	
	return(row);
}

function observerRow( observer ){
	row = $("<div></div>")
			.attr('observer_id', observer.id)
			.addClass("observer");
	
	$(row)
		.append('<a href="mailto:' + observer.email + '">' + observer.name + '</a> ')
		.append('<span class="timestamp">' + observer.last_active + '</span>');
	
	return row
}

getAllStatus();


  

var _idNum = 0;
function getNextID() {
	nextNum = _idNum;
	_idNum += 1;
	return 'webstatus:'+_idNum;
}

// $(document).ready(function() {
//     configInfo = $.getJSON('/config/js',
// 	function(jsonObj){ console.log(jsonObj); } /* Success ... only needed for debugging since we use done, fail, always below */
// 	)
// 	.done(function( result ){
// 		console.log("Getting server addresses");
// 		setServer(result);
// 		console.log("Retrieving modules");
// 		waitForWebSocket(function(){
// 			get_modules(); // calls build_status_table when it returns;
// 			$('#observers').html(""); // erase the list of observers
// 			getAllObservers(); // calls build_observer_table when it returns;
// 			getDiskSpace();
// 		})
// 	})
// 	.fail()
// 	.always();
// } );