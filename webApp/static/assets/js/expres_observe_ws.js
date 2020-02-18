/*global $*/
function socketMessageRouter(e) {
	if (typeof e.data == "string") {
		var packet = $.parseJSON(e.data);
		if ((typeof packet !== "object") || (! packet.hasOwnProperty("packet_type"))) { return; }

		if ( packet["packet_type"] == "meter-counts") {
			updateMeter(packet);
		} else if (packet["packet_type"] == "camera-time") {
			updateElapsed(packet);
		} else if (packet["packet_type"] == "status") {
			updateStatus(packet); 
		} else if (packet["packet_type"].startsWith("observer-")) {
			setObserverState(packet);
		} else if (packet["packet_type"] == "shutter-error") {
			alertShutterError(packet);
		} else if (packet["packet_type"].startsWith("integration-") || packet["packet_type"].startsWith("observation-")) {
			updateIntegration(packet);
		} else if (packet["packet_type"] == "clock-time") {
			updateClock(packet);
		} else if (packet["packet_type"] == "tcs_status") {
			updateTCS(packet);
		} else if (packet["packet_type"] == "fci-status") {
			updateCalInjectionMirrorStatus(packet);
		} else if (packet["packet_type"] == "envcover-status") {
			update_env_cover_status(packet);
		} else if (packet["packet_type"] == "adc-status") {
			updateAdcStatus(packet);
		} else if (packet["packet_type"] == "foc-status") {
			updateFocusMotorStatus(packet);
		} else if (packet["packet_type"] == "efi-status") {
			updateExtendedFlatMotorStatus(packet);
		} else if (packet["packet_type"] == "agitator-status") {
			updateAgitatorStatus(packet);
		} else if (packet["packet_type"] == "readout-complete") {
			readout_complete(packet);
		} else if (packet["packet_type"].startsWith("error-")) {
			error_message(packet);
		} else if (packet["packet_type"].startsWith("warning-")) {
			warning_message(packet);
		} else if (packet["packet_type"] == "fitsfile-opened") {
			notify_observing(packet);
		} else if (packet["packet_type"] == "tcs-pointing") {
			// ignore it
		} else {
			// console.log(packet);
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
var initiated_mgr_request = false;
var page_finished_setup = false;

var _idNum = 0;
function getNextID() {
	nextNum = _idNum;
	_idNum += 1;
	return "webclient:"+_idNum;
}

function almost_done(remaining){
	playSound("almost_done");
}

function startObservation() {
	meterData = []; // zero out the data in the meter.  We will need to set this to at least 1 element later
	setExposure(); /* set up the exposure meter for this observation */
	
	obj = prepareObject(); /* Get all of the object info to send to Expres Manager */
	
	/* Prepare the info as a json 2.0 packet */
	obs = {
		"method": "macros-observe",
		"params": {"object": obj},
		"jsonrpc": "2.0",
		"id": getNextID(),
		};
	payload = JSON.stringify(obs);
	console.log("Get Status payload:");
	console.log("Get Status payload:");
	console.log("Get Status payload:");
	console.log("Get Status payload:");
	console.log("Get Status payload:");
	console.log("Get Status payload:");
	console.log("Get Status payload:");
	console.log("Get Status payload:");
	console.log("Get Status payload:");
	console.log("Get Status payload:");

	console.log(payload)
	/* Initialize the meter to start receiving the new data */
	shutterOpen = true;
	
	/* Send the command to start the observation to Expres Manager
	
		In general, the command will _always_ succeed since the jsonRPC request
		just launches a job to say that it has _started_ an exposure.  If expres
		was ready, then this will start.  However, if the camera can't communicate
		or something else goes wrong, the error will come back as a separate message.
		
		This means that we should not set the button to 'stop' but to some
		intermediate state until we get the message that integration has started.
		
		It also means that the other error messages will have to take care of restoring
		the interface to the proper settings.
	
	*/
	cmdHeard = $.post(expresMgr, payload,
			function(results){
				console.log(results);
				if (typeof results.data == "string") {
					packet = $.parseJSON(results.data);
					if ( ("result" in packet) && ( "error" in packet.result ) ) {
						errorStartingObs( results );
					}
				}
			} /* Success */
		)
		.done(finishStartExposure) /* update the interface to show we are observing */
		.fail(errorStartingObsRaw)
		.always();
}

function askNextPackage( id, script_id ) {
	/*	ask Expres Manager to set the Next Package ID
		IF it is OK (i.e. we have permission to set the next package ID)
		then Manager will broadcast the next package ID to all connected clients
		so that they can all load the next package together.
	*/
	request = "observer-ask-next-package";
	params = {"package_id": id, "script_id": script_id};
	
	askExpresTo( request, params, "Next Package" );
}

function askCurrentPackage( id, script_id ) {
	/*	ask Expres Manager to set the Current Package ID
		IF it is OK (i.e. we have permission to set the current package ID)
		then Manager will broadcast the current package ID to all connected clients
		so that they can all load the current package together.
	*/
	request = "observer-ask-current-package";
	params = {"package_id": id, "script_id": script_id};
	
	askExpresTo( request, params, "Current Package");
}

function askCurrentObject( id, script_id ) {
	/*	ask Expres Manager to set the Current Object ID
		IF it is OK (i.e. we have permission to set the current object ID)
		then Manager will broadcast the current object ID to all connected clients
		so that they can all load the current object together.
	*/
	request = "observer-ask-current-object";
	params = {"object_id": id, "script_id": script_id};
	
	askExpresTo( request, params, "Current Object");
}

function askUpdateObject( id, changes ) {
	request = "observer-update-current-object";
	params = {	"object_id": id,
				"object_deltas": changes,
			};
	
	askExpresTo( request, params, "Update Object");
}

function askUpdatePrefs( changes ) {
	request = "observer-update-observing-prefs";
	params = {	"prefs": changes, };
	
	askExpresTo( request, params, "Update Observing Prefs");
}

function askExpresTo( request, params, reqType ){
	payload = {
		"method": request,
		"params": params,
		"jsonrpc": "2.0",
		"id": getNextID(),
		};
	payload = JSON.stringify(payload);
	
	/* Note that we did the asking.  In the case of auto-slew, we don't want
		every client to then try slewing to the target when loading up the
		current object.  We will set this to true, and set it back to false
		when handling the websocket message.
	*/
	initiated_mgr_request = true;
	
	cmdHeard = $.post(expresMgr, payload,
		function(results){
			console.log(results);
			if (typeof results.data == "string") {
				packet = $.parseJSON(results.data);
				if ( ("result" in packet) && ("error" in packet.result) ) {
					errorAsking(reqType, packet);
				}
			}
		} /* success */ 
	)
	.done()
	.fail(function(results){
		alert("Unable to set " + reqType + ", trouble communicating with manager.");
		}
	)
	.always();
}

function setObserverState( packet ){
	if ( packet.packet_type == "observer-set-current-package") {
		setCurrentPackage( packet.package_id, packet.script_id, ask_mgr=false, initiated_request=initiated_mgr_request );
	} else if ( packet.packet_type == "observer-set-next-package") {
		setNextPackage( packet.package_id, packet.script_id, ask_mgr=false, initiated_request=initiated_mgr_request );
	} else if ( packet.packet_type == "observer-set-current-object") {
		setCurrentTarget( packet.object_id, packet.script_id, ask_mgr=false, initiated_request=initiated_mgr_request );
	} else if ( packet.packet_type == "observer-update-current-object") {
		updateCurrentTarget( packet.object_id, packet.object_deltas, ask_mgr=false, initiated_request=initiated_mgr_request );
	} else if ( packet.packet_type == "observer-update-observing-prefs") {
		updateObservingPrefs( packet.observing_prefs, ask_mgr=false, initiated_request=initiated_mgr_request );
	} 
	
	/* Clear the request state after every response from manager
		This could actually fail if two users do something and the results come back in a different order.
		Better to send the ID of the request and have the responses return it.  If you don't recognize
		the ID then assume that you didn't send it.
	 */
	initiated_mgr_request = false;
}

function errorAsking( type, packet ){
	alert("Had trouble setting " + type + ": " + packet.result.error);
}

function prepareObject() {
	targetData = $("#target_info").data();
	tObj = targetData.target;
	
	eqPrefix = "J";
	eqYear = tObj.epoch;
	
	if (tObj.frame == "fk4") {
		eqPrefix = "B";
	}
	
	/* The user may have clicked again.  If they did this accidentally, then the succesful exp number
		and the total exp number should be the same.  We should warn them elsewhere.  However, if
		we do send the exposure anyway, the expres_manager should notices that succesful_exps == num_exp
		and just return.
	*/
	if ("succesful_exps" in tObj) {
		succesful_exps = tObj.succesful_exps;
	} else {
		succesful_exps = 0;
	}
	
	/* Add any non-empty comment to the logsheet */
	log_comment = $("#lline_note").val();
	/* Also include that comment in the FITS header */
	add_comment_to_fits = $("#lline_add_to_fits").prop("checked");
	
	/* Should this exposure be stopped on 'time' (default), 'snr', or 'counts' */
	stop_condition = $("span#integration_stop_condition").attr("stop_condition");
	if ( (stop_condition) && (! stop_condition in ["time","snr","counts"]) ){
		stop_condition = "time";
	}
	
	// For now, just one object, but we might send a package
	/*
		The proper motion is stored in the same format as SIMBAD, which is
		mas/year for both RA and DEC.  However, the TCS wants it in 
		
		seconds/year for RA 
		arcseconds/year for DEC
		
		So, mas/year * 1as/1000mas * 1s/15as == s/year
	*/
	pkgObject = {
		"object_id": tObj.object_id,
		"package_id": tObj.package_id,
		"program_id": tObj.program_id,
		"object_type": tObj.object_type,
		"preset_mode": tObj.preset_mode.toLowerCase(),
		"preset_uses_sim": tObj.preset_uses_sim.toLowerCase(),
		"pmode_id": tObj.pmode_id,
		"script_id": tObj.script_id,
		"nos_version": tObj.nos_version,
		"name": tObj.object_name,
		
		"plx_mas": tObj.plx_mas,
		"pm": {
			"epoch": 2000.0,
			"ra_secs": tObj.pm_ra_masyr * (1/1000.) * (1/15), // secs / year
			"dec_arcsecs": tObj.pm_dec_masyr / 1000., // arcsecs / year
			},
			
		"rv": 0.0, // km/s
		
		"radec_required": true,
		"ra": tObj.ra,
		"dec": tObj.dec,
		"equinoxPrefix": eqPrefix,
		"equinoxYear": eqYear,
		"epoch": tObj.epoch,
		"frame": tObj.frame,
		"rotator": {
			"rotPA": 0.0,
			"rotFrame": "Target"
		},
		"vmag": tObj.vmag,
		"exp_time": tObj.exp_time,
		"sim_time": tObj.sim_time,
		"sim_mode": tObj.sim_mode,
		"succesful_exps": succesful_exps,
		"num_exp": tObj.num_exp,
		"snr": tObj.snr,
		"setpoint": tObj.setpoint,
		"stop_condition": stop_condition,
		
		"log_comment": log_comment,
		"add_comment_to_fits": add_comment_to_fits,
		
		"do_cal_mirror_check": $('#do_cal_mirror_check').hasClass('enabled'), /* These should be pulled from the interface */
		"do_ext_flat_check":  $('#do_ext_flat_check').hasClass('enabled'),
		"do_exp_meter_check":  $('#do_exp_meter_check').hasClass('enabled'),
		"do_agitator_check":  $('#do_agitator_check').hasClass('enabled'),
	};
	
	return pkgObject;
}

function errorStartingObs( jsonObj ){
	result = jsonObj.result;
	
	alert("ERROR: " + result.error);
	finishStopObservation( jsonObj );
}

function errorStartingObsRaw( jsonStr ){
	packet = $.parseJSON(jsonStr.data);
	errorStartingObs( packet );
}

function finishStartExposure( jsonObj, statusCode, jqXHR ){
	// Get the "object" and package out of the jsonObj
	console.log(jsonObj);
	
	/* Change the "Start" button to an "Abort" button */
 	$("#target_start")
 		.removeClass("fa-play")
 		.addClass("fa-stop")
 		.html("Abort")
 		.prop("href","javascript:stopExposure();void(0);");
}
   

function updateElapsed( timeData ){
	/* The camera keeps track of when the shutter was opened,
		how much time has elapsed, and how much time is remaining.
		
		The meter tracks the counts and the estimated time to reach
		the desired counts.  That gives us two different "remaining"
		times.  This function is just to update the elapsed time
		from the camera.
	*/
	/* Update the "Elapsed Time" and "Remaining Time" areas */
	$("#tinfo_elapsed_time").text(timeData.elapsed_time);
	$("#status_elapsed_time").text(timeData.elapsed_time);
	
	if ( timeData.remaining_time < 10.0 ){
		almost_done(timeData);
	}
}

function getStatus( moduleName, submodule, func=function(r){console.log(r); } ){
	if ( submodule == undefined ){ submodule = ""; }
	if ( moduleName == undefined ){ moduleName = "expres"; }
	
	payload = JSON.stringify( {
		"method": "expres-status",
		"params": {"moduleName": moduleName, "submodule": submodule},
		"jsonrpc": "2.0",
		"id": getNextID(),
		});
	
	/* Tell expres we want the status, return the status over the websocket */
	cmdHeard = $.post(expresMgr, payload, func)
				.done()
				.fail()
				.always();
}

function updateIntegration( status ){
	console.log(status);
	
	if ( "succesful_exps" in status ) {
		// set the "succesful_exps" value of the observing object to this number
		// If the user attempts additional observations without re-loading the
		// object, then manager will pick up where it left off.
		// This is in both the integration-finished and observation-finished packets
		tInfo = $("#target_info").data();
		tInfo.target.succesful_exps = status["succesful_exps"];
	}
	
	if (status["packet_type"] == "integration-finished"){
		// "Exposure Complete"
	} else if (status["packet_type"] == "observation-finished"){
		finishStopObservation(); /* we stopped the exposure, update the button */
	} else if (status["packet_type"] == "integration-count"){
		$("#status_current_exp_num").text(status["this_exp"]);
		$("#status_num_exp_in_set").text(status["num_exp"]); /* shouldn't change */
		$("#tinfo_current_exp_num").text(status["this_exp"]);
		$("#tinfo_num_exp_in_set").text(status["num_exp"]); /* shouldn't change */
		/* We updated the current exposure number, set the elapsed time for this new exposure to 0 */
		$("#tinfo_elapsed_time").text(0);
		$("#status_elapsed_time").text(0);
	} else if (status["packet_type"] == "observation-setup"){
		/* Set the "Elapsed Time" and "Remaining Time" areas to zero before we start the exposure */
		setExposure(); /* set up the exposure meter titles for this observation */
		$("#tinfo_elapsed_time").text(0);
		$("#status_elapsed_time").text(0);
		
		/* Also set the filename to empty...we don't know which one we are on yet */
		$("#tinfo_current_file").text("");
		
		/* Reset the exposure meter for this exposure */
		startMeter(); // in exposure_meter_ws.js
	}
}

function readout_complete(status){
	/*	We already played the sound with the status message
		This is just to put the final integration time in elapsed time area
		in case we didn't send the last update message.
	*/
	finalTime = parseFloat(status["integrate_secs"]);
	if (finalTime < 1){
		finalTime = Math.round(finalTime * 100) / 100;
	} else {
		finalTime = Math.round(finalTime);
	}
	$("#tinfo_elapsed_time").text(finalTime);
	$("#status_elapsed_time").text(finalTime);
}

function error_message( error ){
	/* We can get fancy later, but for now this will do */
	alert(error["error"]);
}

function warning_message( warning ){
	console.log(warning);
	if ("cleared" in warning){
		$("#tiny_message").html("");
	} else {
		$("#tiny_message").html(warning["warning"]);
		playSound("alert");
	}
}

function startClock() {
	payload = JSON.stringify( {
		"method": "clock-start-time",
		"params": {},
		"jsonrpc": "2.0",
		"id": getNextID(),
		});
	
	cmdHeard = $.post(expresMgr, payload,
		function(results){ console.log(results); } /* Success */
		)
		.done()
		.fail()
		.always();
}

var prevClockMJD = 0;
function updateClock( tick ){
	//console.log(tick);
	
	timeSpan = $("#status_time");
	
	if ($(timeSpan).hasClass("lmst")) {
		$(timeSpan).text(tick["lmst"]);
	} else if ( $(timeSpan).hasClass("utc")) {
		$(timeSpan).text(tick["utc"]);
	} else if ( $(timeSpan).hasClass("local")) {
		$(timeSpan).text(tick["local"]);
	} else if ( $(timeSpan).hasClass("gmst")) {
		$(timeSpan).text(tick["gmst"]);
	} else if ( $(timeSpan).hasClass("mjd")) {
		$(timeSpan).text(tick["mjd"]);
	} else {
		$(timeSpan).text("UNKNOWN");
	}
	
	if (typeof update_all_airmasses === "function") {
		if ((tick["mjd"] - prevClockMJD)*24*3600 > 30){
			prevClockMJD = tick["mjd"];
			update_all_airmasses(tick["lmst"]);
		}
	}
}

function updateTCS( tcs ){
	$("#tcs_cur_radec").html("<span class='ra'>"+tcs["ra"].replace(" ",":")+"</span> <span class='dec'>"+tcs["dec"].replace(" ",":")+"</span>");
}

function alertShutterError( error ){
	console.log(error);
	if ("cleared" in error){
		$("#tiny_message").html("");
	} else {
		$("#tiny_message").html("Shutter Not Responding");
		playSound("alert");
	}
}

 

function notify_observing( fitsinfo ){
	/* tell user name of fits file currently being written */
	/* fitsinfo contains:
		"lline_id": log_line["lline_id"], "file_path": file_path, "file_name": file_name
	*/
	$("#tinfo_current_file").text(fitsinfo.file_name);	
}

function getRPCCommands() {
	payload = JSON.stringify( {
			"method": "expres-methods",
			"jsonrpc": "2.0",
			"id": getNextID(),
		});
	
	cmdHeard = $.post(expresMgr, payload,
		function(results){ console.log(results); } /* Success ... only needed for debugging since we use done, fail, always below */
		)
		.done()		/* Callback methods attached to the returned data object */
		.fail()
		.always();
}
 
function getCurrentState() {
	payload = JSON.stringify( {
		"method": "observer-get-current-state",
		"jsonrpc": "2.0",
		"id": getNextID(),
	});
	
	cmdHeard = $.post(expresMgr, payload,
		function(results){ console.log(results); } /* Success ... only needed for debugging since we use done, fail, always below */
		)
		.done(setCurrentState)		/* Callback methods attached to the returned data object */
		.fail()
		.always();
}

function setCurrentState( jsonObj, statusCode, jqXHR ){
	console.log(jsonObj);
	
	if (typeof jsonObj == "string") {
		packet = $.parseJSON(jsonObj);
		if ( ("result" in packet) && ( "error" in packet.result ) ) {
			errorStartingObs( results );
		} else if (("result" in packet) && ("state" in packet.result )) {
			// Set each of the state items we find in order
			var state = packet.result.state;
			console.log(state);
			
			/* These need to execute in order, but other than calling them in order,
				there is no reason they should come back in order.  This could cause
				errors if the object_deltas packet returns before the setCurrentTarget
				is done.
			*/
			
			if (("package_id" in state) && (state.package_id > 0)){
				setCurrentPackage( state.package_id, state.script_id, ask_mgr=false, initiated_request=false );
			}
			
			if (("object_id" in state) && (state.object_id > 0)){
				setCurrentTarget( state.object_id, state.script_id, ask_mgr=false, initiated_request=false, ignore_state=true );
				
				if (("object_deltas" in state) && (state.object_deltas != {})){
					
					updateCurrentTarget( state.object_id, state.object_deltas, ask_mgr=false, initiated_request=false );
				}			
			}
			
			if (("next_package_id" in state) && (state.next_package_id > 0)){
				setNextPackage( state.next_package_id, state.next_script_id, ask_mgr=false, initiated_request=false );
			}
			
			if (("next_object_id" in state) && (state.next_object_id > 0)){
				// Doesn't exist yet
			}
			
			if (("observing_prefs" in state) && (state.observing_prefs != {})){
				updateObservingPrefs( state.observing_prefs, ask_mgr=false, initiated_request=false );
			}
		}
	}
}

/*
	*******************************************************
	FEM Cal Injection Mirror Functions
	*******************************************************
*/
function cal_injection_mirror(cmd) {
	if (! ["in","out","stat","home"].includes(cmd)) {
		alert("The Cal Injection Mirror only understands the commands 'in', 'out', 'stat', and 'home'");
		return;
	}
	
	wsCmd = "adc-fci-"+cmd;
	
	payload = JSON.stringify( {
	"method": wsCmd,
	"params": {},
	"jsonrpc": "2.0",
	"id": getNextID(),
	});
	
	cmdHeard = $.post(expresMgr, payload,
		function(results){ console.log(wsCmd + ": " + results); } /* Success */
		)
		.done()
		.fail()
		.always(
			function(results){
				if  ( cmd != "stat" ){
					/* Get the status immediately, then after 1, 2, and 5 seconds */
					cal_injection_mirror("stat")
					update1 = window.setTimeout(cal_injection_mirror, 2000, "stat");
					update2 = window.setTimeout(cal_injection_mirror, 5000, "stat");
					update5 = window.setTimeout(cal_injection_mirror, 7000, "stat");
				}
			}
		);
}

function updateCalInjectionMirrorStatus( status ){
	console.log(status);
	
	/* Packet should be defined as follows:
		packet_type: "fci-status"
		finPos: 0			# Motor position when mirror is IN
		foutPos: 37600		# Motor position when mirror is OUT
		lastCmd: ""			# Last command sent to motor
		sw1: 1 or 0			# Mirror is in
		sw2: 1 or 0         # Mirror is out
		ready: "T" or "F"	# Whether or not the motor is ready for commands?
		homing_started:	"T" or "F" # Whether or not the motor is currently re-homing
	*/
	if (status["sw1"] == 1) {
		state = "in";
	} else if (status["sw2"] == 1) {
		state = "out";
	} else if (status["homing_started"] == "T") {
		state = "homing";
	} else if (status["ready"] == "F") {
		state = "Not Ready";
	} else {
		state = "Unknown";
	}
	$("#status_fem_cim").text("Cal Mirror: "+state);
	
	if ((state == "Unknown") || (state == "Not Ready") || (state == "homing")) {
		$("#status_fem_cim").removeClass().addClass("unknown");
	} else {
		$("#status_fem_cim").removeClass().addClass("ready");
	}
	$("#m_cal_inj_status a").text("Status: "+state);
}

/*
	*******************************************************
	Exposure Meter Functions
	*******************************************************
*/
function exp_meter_start_service() {
	exp_meter_service("start");
}

function exp_meter_stop_service() {
	exp_meter_service("stop");
}

function exp_meter_service( cmd ) {
	if (! ["start","stop"].includes(cmd)) {
		alert("The Exposure Meter only understands the commands 'start' and 'stop'");
		return;
	}
	
	if ( cmd == "start" ){
		method = "meter-start-meter-service";
	} else {
		method = "meter-stop-meter-service";
	}
	
	payload = JSON.stringify( {
		"method": method,
		"params": {},
		"jsonrpc": "2.0",
		"id": getNextID(),
		});
	
	/* Tell expres what to do, return the status over the websocket */
	cmdHeard = $.post(expresMgr, payload,
				function(results){ console.log(method + ": " + results); }
				)
				.done()
				.fail()
				.always();
}

/*
	*******************************************************
	Environment Cover Functions
	*******************************************************
*/
function get_env_cover_status() {
	env_cover( "status" );
}
function env_cover_open() {
	env_cover( "open" );
}
function env_cover_close() {
	env_cover( "close" );
}

function env_cover( cmd ){
	if (! ["open","close","status"].includes(cmd)) {
		alert("The Environment Cover only understands the commands 'open', 'close', and 'status'");
		return
	}
	
	if ( cmd == "status" ){
		method = "envcover-get-status";
	} else if ( cmd == "open" ){
		method = "envcover-open";
	} else {
		method = "envcover-close";
	}
	
	payload = JSON.stringify( {
		"method": method,
		"params": {},
		"jsonrpc": "2.0",
		"id": getNextID(),
		});
	
	/* Tell expres we want the status, return the status over the websocket */
	cmdHeard = $.post(expresMgr, payload,
				function(results){ console.log(method + ": " + results); }
				)
				.done()
				.fail()
				.always();
}

function update_env_cover_status( status ){
	console.log(status);
	
	if ( status["status"].includes("moving close") ){
		state = "* Closing *";
	} else if ( status["status"].includes("moving open") ){
		state = "* Opening *";
	} else {
		state = status["status"];
	}

	$("#m_env_cover_status a").text("Status: "+state);
	if ( state == "error" ){
		alert(status["error"]);
	}
}

/*
	*******************************************************
	ADC Functions
	*******************************************************
*/
function adc_control(cmd) {
	if (! ["on","off","home","status"].includes(cmd)) {
		alert("The ADC only understands the commands 'on', 'off', and 'status'");
		return;
	};

	// Send command
	if ( cmd == "on"){
		wsCmd = "adc-lwr_cont";
	} else if (cmd == "off"){
		// wsCmd = "adc-lwr_off";
		wsCmd = "adc-lwr_off_null";
	} else if (cmd == "home"){
		wsCmd = "adc-home";
	} else {
		wsCmd = "adc-send_status";
	};
	
	payload = JSON.stringify( {
	"method": wsCmd,
	"params": {},
	"jsonrpc": "2.0",
	"id": getNextID(),
	});
	
	cmdHeard = $.post(expresMgr, payload,
	function(results){ console.log(cmd + ": " + results); } /* Success */
	)
		.done()
		.fail()
		.always();
}

function updateAdcStatus( status ){
	console.log(status);
	
	// Retrieve ADC 1 Home Status (if it was homed since manager restart)
	if (status["adc1rdy"] == "n"){
		stat1 = "homing";
	} else if (status["adc1rdy"] == "y"){
		stat1 = "ready";
	} else {
		stat1 = "n/a";
	};

	// Retrieve ADC 2 Home Status (Active ADC corrections)
	if (status["adc2rdy"] == "n"){
		stat2 = "homing";
	} else if (status["adc2rdy"] == "y"){
		stat2 = "ready";
	} else {
		stat2 = "n/a";
	};
	
	// Retrieve TCS Status (Continuous TCS monitoring)
	if (status["uprMode"] == 0) {
		tcs = "No TCS";
	} else if (status["uprMode"] == 1){
		tcs = "Listening";
	} else {
		tcs = "unknown";
	};
	
	if (status["lwrMode"] == 0) {
		correcting = "Stationary";
	} else if (status["lwrMode"] == 1){
		correcting = "Correcting";
	} else {
		correcting = "unknown";
	};
	$("#m_adc_status a").text("ADC Status: "+tcs+": "+correcting);
	$("#m_adc_home a").text("Home ADC ("+stat1+":"+stat2+")");
}

/*
	*******************************************************
	Focus Motor Functions
	*******************************************************
*/
function foc_control(cmd) {
	if (! ["forward","backward","absolute","home","status"].includes(cmd)) {
		alert("The Focus Motor only understands the commands 'forward', 'backward', 'absolute', 'home', and 'status'");
		return
	};

	if (["forward","backward","absolute"].includes(cmd)){
		if (["absolute"].includes(cmd)){
			msg = "Absolute position to Move Focus Motor";
		} else {
			msg = "Number of Steps to Move Focus Motor";
		}
		steps = prompt(msg, 0)
			
		if ((steps == null) || (steps == 0)) { return; }
		steps = parseFloat(steps);

		if (isNaN(steps)){
			alert("Steps not set to a number")
		}
	}

	// Send command
	if ( cmd == "forward"){
		wsCmd = "adc-foc-step";
		params = {
		"direction":"P",
		"steps":steps,
		};
	} else if (cmd == "backward"){
		wsCmd = "adc-foc-step";
		params = {
		"direction":"D",
		"steps":steps,
		};
	} else if (cmd == "absolute"){
		wsCmd = "adc-foc-step";
		params = {
		"direction":"A",
		"steps":steps,
		};
	} else if (cmd == "home"){
		wsCmd = "adc-foc-home";
		params = {};
	} else {
		wsCmd = "adc-foc-stat";
		params = {};
	}
	
	payload = JSON.stringify( {
	"method": wsCmd,
	"params": params,
	"jsonrpc": "2.0",
	"id": getNextID(),
	});
	
	cmdHeard = $.post(expresMgr, payload,
	function(results){ console.log(cmd + ": " + results); } /* Success */
	)
		.done()
		.fail()
		.always();
}

/*
	*******************************************************
	LFC Functions
	*******************************************************
*/
function lfc_control(cmd) {
	if (! ["on","off"].includes(cmd)) {
		alert("The LFC only understands the commands 'on', and 'off'");
		return
	};

	// Send command
	if ( cmd == "on"){
		wsCmd = "lfc-to-on";
		params = {};
	} else if (cmd == "off"){
		wsCmd = "lfc-to-standby";
		params = {};
	}
    
	payload = JSON.stringify( {
	"method": wsCmd,
	"params": params,
	"jsonrpc": "2.0",
	"id": getNextID(),
	});
	
	cmdHeard = $.post(expresMgr, payload,
	function(results){ console.log(cmd + ": " + results); } /* Success */
	)
		.done()
		.fail()
		.always();
}

/*
	*******************************************************
	Extended Flat Motor Functions
	*******************************************************
*/
function efi_control(cmd) {
	if (! ["out","forward","backward","absolute","home","status"].includes(cmd)) {
		alert("The Extended Flat Motor only understands the commands 'out', 'forward', 'backward', 'absolute', 'home', and 'status'");
		return
	}

	if (["forward","backward","absolute"].includes(cmd)){
		if ( ["absolute"].includes(cmd) ){
			msg = "Absolute position to Move Extended Flat Motor";
		} else {
			msg = "Number of Steps to Move Extended Flat Motor";
		}
		steps = prompt(msg, 0)
		if ((steps == null) || (steps == 0)) { return; }
		steps = parseFloat(steps);

		if (isNaN(steps)){
			alert("Steps not set to a number")
		}
	}

	// Send command
	if ( cmd == "out"){
		wsCmd = "adc-efi-step";
		params = {
			"direction": "A",
			"steps": 34000,	/* shortcut for moving the ext flat mirror out...should bet this number from somewhere rather than hard-coding it since it can change */
		};
	} else if ( cmd == "forward"){
		wsCmd = "adc-efi-step";
		params = {
		"direction":"P",
		"steps":steps,
		};
	} else if (cmd == "backward"){
		wsCmd = "adc-efi-step";
		params = {
		"direction":"D",
		"steps":steps,
		};
	} else if (cmd == "absolute"){
		wsCmd = "adc-efi-step";
		params = {
		"direction":"A",
		"steps":steps,
		};
	} else if (cmd == "home"){
		wsCmd = "adc-efi-home";
		params = {};
	} else {
		wsCmd = "adc-efi-stat";
		params = {};
	}
	
	payload = JSON.stringify( {
	"method": wsCmd,
	"params": params,
	"jsonrpc": "2.0",
	"id": getNextID(),
	});
	
	cmdHeard = $.post(expresMgr, payload,
	function(results){ console.log(cmd + ": " + results); } /* Success */
	)
		.done()
		.fail()
		.always();
}

function updateExtendedFlatMotorStatus( status ){
	console.log(status);

	pos = status["ecurPos"];
	if (status["statchar"]=="t") {
		state = " (ready)";
	} else if (status["statchar"]=="f") {
		state = " (homing)";
	} else {
		state = " (n/a)";
	}

	$("#m_efi_status a").text("Status: "+pos+state);
}

/*
	*******************************************************
	Agitator Functions
	*******************************************************
*/
function agitator_control(cmd) {
	if (! ["on","off","status"].includes(cmd)) {
		alert("The Agitator only understands the commands 'on', 'off', and 'status'");
		return;
	};

	// Send command
	params = {};
	if ( cmd == "on"){
		wsCmd = "agitator-start-agitator-service";
	} else if (cmd == "off"){
		wsCmd = "agitator-stop-agitator-service";
	} else {
		wsCmd = "agitator-send-status";
	};
	
	payload = JSON.stringify( {
	"method": wsCmd,
	"params": {},
	"jsonrpc": "2.0",
	"id": getNextID(),
	});
	
	cmdHeard = $.post(expresMgr, payload,
	function(results){ console.log(cmd + ": " + results); } /* Success */
	)
		.done()
		.fail()
		.always();
}

function updateAgitatorStatus( status ){
	console.log(status);
	$("#m_agitator_status a").text("Status: "+status["status"]);
}
