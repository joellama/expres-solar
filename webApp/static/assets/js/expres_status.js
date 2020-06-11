/* Set up global variables and defaults */
if (! expresMgr) {
	var expresMgr = "http://expres-test.local:5164/"
	var expresWS = "ws://expres-test.local:8842/ws/"
}

// window.onload = function() {
// 	configInfo = $.getJSON('/config/js',
// 	function(results){ console.log(results); }  Success ... only needed for debugging since we use done, fail, always below 
// 	)
// 	.done(openSocket)
// 	.fail(getServerFail)
// 	.always();
// }

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
// 			console.log("HEREERERE")
// 			$('#observers').html(""); // erase the list of observers
// 			getAllObservers(); // calls build_observer_table when it returns;
// 			getDiskSpace();
// 		})
// 	})
// 	.fail(getServerFail)
// 	.always();
// } );

$(document).ready(function() {
		console.log("HJERE");
		setServer({'expresMgr':'http://expres-test.local:5164', 'expresWS':"ws://expres-test.local:8842/ws/"});
		console.log("Retrieving modules");
		waitForWebSocket(function(){
			get_modules(); // calls build_status_table when it returns;
			console.log("HEREERERE");
		});
	});

function setServer( serverInfo ){
	expresMgr = serverInfo.expresMgr;
	expresWS = serverInfo.expresWS;
}

function getServerFail(){
	alert("ERROR: Unable to get server configuration settings.  Check that Expres Manager is running then try logging in again.");
}
