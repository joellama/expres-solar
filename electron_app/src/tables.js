// const io = require('socket.io-client');
// const socket = io('http://localhost:8081');
require('datatables.net')();

window.$ = window.jquery = require('jquery');

$(document).ready(function() {

 var dataSet = [];

  var GuidercolumnDefs = [{
    title: "Time"
  }, {
    title: "Mode"
  }, {
    title: "Sun vis."
  }, {
    title: "X (RA)"
  }, {
    title: "Y (Dec)"
  }, {
    title: "Message"
  }];

  var guiderTable = $('#guiderTable').DataTable({
    "sPaginationType": "full_numbers",
    data: [],
    columns: GuidercolumnDefs,
    dom: 'Bfrtip', // Needs button container
    select: 'single',
    responsive: true,
    altEditor: true, // Enable altEditor
    searching:false,
   "pageLength": 5,
   order: [[0, "desc"]]
  });

  socket.on('guiderUpdate', function(arr) {
    console.log('updating guider');
    var azdate = new Date(Date.now() - 25200000.0).toISOString().substr(11, 8);
    guiderTable.row.add([azdate, arr['mode'], arr['sun_vis'], arr['XCORR'], arr['YCORR'], 'message']).draw( false );
  });
  
  var TelescopecolumnDefs = [{
    title: "Time"
  }, {
    title: "RA"
  }, {
    title: "DEC"
  }, {
    title: "Orientation"
  }, {
    title: "Mode"
  }];

  var telescopeTable = $('#telescopeTable').DataTable({
    "sPaginationType": "full_numbers",
    data: [],
    columns: TelescopecolumnDefs,
    dom: 'Bfrtip', // Needs button container
    select: 'single',
    responsive: true,
    altEditor: true, // Enable altEditor
    searching:false,
   "pageLength": 5,
   order: [[0, "desc"]]
  });

  socket.on('telescopeStatus', function(arr) {
    console.log('updating telescopeTable');
    var azdate = new Date(Date.now() - 25200000.0).toISOString().substr(11, 8);
    if (arr['MOUNT_SIDE'] == "E") {
      var mount_side = "East (PM)";
    } else {
      var mount_side = "West (AM)";
    }
    if (arr['MODE'] == "N") {
      var mode = "Not Tracking";
    } else if (arr['MODE'] == 'T') {
      var mode = "Tracking";
    } else if (arr['MODE'] == 'G') {
      var mode = 'Guiding';
    } else if (arr['MDOE'] == 'C') {
      var mode = 'Centering';
    } else if (arr['MDOE'] == 'S') {
      var mode = 'Slewing';
    } else {
      var mode = 'Unknown';
    }
    telescopeTable.row.add([azdate, arr['RA'], arr['DEC'], mount_side, mode]).draw( false );
  });

  socket.on('clearTables', function(arr) {
    console.log('clearing data tables');
    guiderTable.clear().draw( false );
    telescopeTable.clear().draw( false );
  });
});
 
