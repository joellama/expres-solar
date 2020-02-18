/* Set up global variables and defaults */
 

var _idNum = 0;
function getNextID() {
	nextNum = _idNum;
	_idNum += 1;
	return 'webclient:'+_idNum;
}

 
function setServer( serverInfo ){
	expresMgr = serverInfo.expresMgr;
	expresWS = serverInfo.expresWS;
}
 
function newNight(){
	script_id = $('#form_night_choice select[name="script_id_new"]').find(":selected").val();
	user_id = $('#form_night_choice input[name="user_id"]').val();
	
	if (script_id == 0){
		alert("You must choose a script to start a night");
		return;
	}
	
	payload = JSON.stringify( {
			"method": "logsheet-start",
			"jsonrpc": "2.0",
			"id": getNextID(),
			"params": {"script_id": script_id, "user_id": user_id},
		});
	
	nightSet = $.post(expresMgr, payload,
		function(jsonObj){ console.log(jsonObj); } /* Success ... only needed for debugging since we use done, fail, always below */
		)
		.done(goToNight)		/* Callback methods attached to the returned data object */
		.fail(unableToStart)
		.always();
}

function joinNight(){
	logsheet_id = $('#form_night_choice input[name="logsheet_id_current"]').val();
	script_id = $('#form_night_choice input[name="script_id_current"]').val();
	user_id = $('#form_night_choice input[name="user_id"]').val();
	
	payload = JSON.stringify( {
			"method": "logsheet-join",
			"jsonrpc": "2.0",
			"id": getNextID(),
			"params": {"logsheet_id": logsheet_id, "script_id": script_id, "user_id": user_id},
		});
	
	nightSet = $.post(expresMgr, payload,
		function(jsonObj){ console.log(jsonObj); }
		)
		.done(goToNight)
		.fail(unableToJoin)
		.always();
}

function unableToJoin( jsonStr ){
	console.log(JSON.parse(jsonStr));
	alert("Unable to join night in progress");
}

function unableToStart( jsonStr ){
	console.log(JSON.parse(jsonStr));
	alert("Unable to Start New Night");
}

function goToNight( jsonStr ){
	jsonObj = JSON.parse(jsonStr);
	if (jsonObj.hasOwnProperty("result")){
		result = jsonObj.result;
	} else {
		result = {"error": "Unknown Error starting night"};
	}
	
	if (result.hasOwnProperty("error")){
		return unableToStart( jsonStr );
	}
	$(location).attr('href', $('#form_night_choice').attr('action') );
}

function getRPCCommands() {
	payload = JSON.stringify( {
			"method": "expres-methods",
			"jsonrpc": "2.0",
			"id": getNextID(),
		});
	
	cmdHeard = $.post(expresMgr, payload,
		function(jsonObj){ console.log(jsonObj); } /* Success ... only needed for debugging since we use done, fail, always below */
		)
		.done()		/* Callback methods attached to the returned data object */
		.fail()
		.always();
}
