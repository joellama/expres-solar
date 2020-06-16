/* Set up global variables and defaults */
if (! expresMgr) {
    var expresMgr = "http://expres-test.local:5164/";
}
if (! expresWS) {
    var expresWS = "ws://expres-test.local:8842/ws/";
}

/*  observer_id is a global variable that is set by the HTML template.
    If it exists, then it notifies expres that there is an 'active' observer.
*/

/* When the page loads, create a websocket connection and connect to the exposure meter.
*/
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

function openSocket(serverInfo) {
    expresMgr = serverInfo.expresMgr;
    expresWS = serverInfo.expresWS;

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
        
        /* Request the currently connected TCS and display the name */
        getTCSName();
        setActiveObserverID(); /* This also calls expres-add-active-observer */
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

function getTCSName(){
    payload = JSON.stringify( {
            "method": "tcs-get-server-name",
            "jsonrpc": "2.0",
            "id": getNextID(),
        });
    
    cmdHeard = $.post(expresMgr, payload,
        function(results){ console.log(results); } /* Success ... only needed for debugging since we use done, fail, always below */
        )
        .done(setTCSName)       /* Callback methods attached to the returned data object */
        .fail()
        .always();
}

function setActiveObserverID(){
    if (typeof observer_id === 'undefined'){ return; }
    
    payload = JSON.stringify( {
        "method": "expres-add-active-observer",
        "params": {"user_id": parseInt(observer_id)},
        "jsonrpc": "2.0",
        "id": getNextID(),
        });
    
    /* When sent through the websocket, the socket will update observer_id for that
        websocket and also call the method.
    */
    sendText(payload);
}

function addActiveObserver(){
    if (typeof observer_id === 'undefined'){ return; /* not actively observing */ }
    
    payload = JSON.stringify( {
        "method": "expres-add-active-observer",
        "params": {"user_id": parseInt(observer_id)},
        "jsonrpc": "2.0",
        "id": getNextID(),
        });
    
    cmdHeard = $.post(expresMgr, payload,
        function(results){ console.log(results); }
        )
        .done(function( result ){
            result = JSON.parse(result);
            if ("error" in result){
                if ("msg" in result.error) {
                    alert(result.error.msg);
                } else {
                    alert(result.error);
                }
            }
        })
        .fail()
        .always();
}

function removeActiveObserver(){
    if (typeof observer_id === 'undefined'){ return; /* not actively observing */ }
    
    payload = JSON.stringify( {
        "method": "expres-remove-active-observer",
        "jsonrpc": "2.0",
        "id": getNextID(),
        });
    
    cmdHeard = $.post(expresMgr, payload,
        function(results){ console.log(results); }
        )
        .done(function( result ){
            if ("error" in result){
                alert(result.error);
            }
        })
        .fail()
        .always();
}

/* If this element doesn't exist, it just fails silently */
function setTCSName( data ){
    jsonObj = $.parseJSON(data);
    $('#tcs_name').text(jsonObj.result.name);
    $("#tcs_name").removeClass("autoslew");
    
    slewStatus = $("#auto_slew_status").text();
    if (slewStatus && (slewStatus.toLowerCase() == 'on')){
        $("#tcs_name").addClass("autoslew");
    }
}

/*  If wsMessageHandler is not set (or is not a function) then this basic
    prototype will be set up as the message handler.  You can change the
    handler using socket.onmessage = someFunctionName, but remember that
    the reconnection script will try using whatever is in wsMessageHandler.
*/
function messageHandlerPrototype( e ) {
    if (typeof e.data == "string") {
        packet = $.parseJSON(e.data);
        if ((typeof packet !== 'object') || (! packet.hasOwnProperty('packet_type'))) { return; }
        socketMessageRouter(packet);
        console.log(packet);
    } else {
        var arr = new Uint8Array(e.data);
        var hex = "";
        for (var i = 0; i < arr.length; i++) {
            hex += ("00" + arr[i].toString(16)).substr(-2);
        }
        console.log("Binary message received: " + hex);
    }
}

/* send text to the websocket */
function sendText(msg) {
    if (isopen) {
       socket.send(msg);
       console.log("Text message sent.");               
    } else {
       console.log("Connection not opened.")
    }
}

/* send JSON data to the websocket */
function sendJSON(msg) {
    sendText(JSON.stringify(msg));
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

var success = openSocket({'expresMgr':expresMgr, 'expresWS':expresWS})