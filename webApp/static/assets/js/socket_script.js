console.log('socket_script.js');
console.log("opening connection to solar server");
const solarSocket = io('http://0.0.0.0:8081');
solarSocket.emit('newWebClient', 'hello');
console.log('connected to solar server');
var environmentDataLoaded = false;
 
var ctx = document.getElementById('environmentChart').getContext('2d');
    
 
var cfg = {
	data: {
      datasets: [{
        label: 'Temperature',
        yAxisID: 'y-axis-1',
        // backgroundColor: color(window.chartColors.red).alpha(0.5).rgbString(),
        // borderColor: window.chartColors.red,
        data: [],
        type: 'line',
        pointRadius: 0,
        lineTension: 0,
        borderWidth: 1,
		borderColor: "#d3322f",
 		backgroundColor:"#d3322f",
		fill: false,
        pointBorderWidth: 0,
        pointHoverRadius: 0,
        pointHoverBorderWidth: 0,
        pointRadius: 0,
        borderWidth: 2,
      }, {
        label: 'Humidity',
        yAxisID: 'y-axis-2',
        // backgroundColor: color(window.chartColors.red).alpha(0.5).rgbString(),
        // borderColor: window.chartColors.red,
        data: [],
        type: 'line',
        pointRadius: 0,
        lineTension: 0,
        borderWidth: 1,
		borderColor: "#104886",
 		backgroundColor:"#104886",
		fill: false,
        pointBorderWidth: 0,
        pointHoverRadius: 0,
        pointHoverBorderWidth: 0,
        pointRadius: 0,
        borderWidth: 2,
      }]},
    options: {
      layout: {
        padding: {
          left: 0,
          right: 40,
          top: 0,
          bottom: 0
        }
      },
      maintainAspectRatio: false,
      scales: {
        xAxes: [{
          gridLines: {
            display:false
          },
          type: 'time',
          // distribution: 'series',
          offset: false,
          ticks: {
            major: {
              enabled: true,
              // fontStyle: 'bold',
              labelString: 'Time',
            },
            fontSize: 14,
            // source: 'data',
            // labels: generateLabels(),
            autoSkip: true,
            autoSkipPadding: 75,
            maxRotation: 0,
            sampleSize: 100
          }
        }],
        yAxes: [{
          id: 'y-axis-1',
          gridLines: {
            drawBorder: false,
            display:false
          },
          ticks: {
            fontSize: 16
          },
          scaleLabel: {
            display: true,
            labelString: 'Temperature [°C]',
            fontSize: 16,
          },
          position: 'left',
        },
        {
          id: 'y-axis-2',
          position: 'right',
          gridLines: {
            drawBorder: false,
            display:false
          },
          ticks: {
            fontSize: 16
          },
          scaleLabel: {
            display: true,
            labelString: 'Humidity [%]',
            fontSize: 16,
          }
        }]
      },
      tooltips: {
        bodyFontColor: '#000',
        bodySpacing: 4,
        xPadding: 12,
        mode: "nearest",
        intersect: 0,
        position: "nearest"
      },
      legend: {
        position: "top",
        fillStyle: "#FFF",
        display: true
      }
    }
};

var environmentChart = new Chart(ctx, cfg);

solarSocket.on('updateWebcam', function(data) {
  document.getElementById('webcamUpdateTime').innerHTML = 'Updated: ' + data;
  document.getElementById('webcamImage').src = "/static/assets/img/webcam_latest.jpg?random="+new Date().getTime();
});

solarSocket.on('environmentData', function(data) {
	var temperatureData = [];
	var humidityData = [];
	var i; 
	for (i = 0; i < data['time'].length; i++) {
		temperatureData.push({'t':data['time'][i], 'y':data['t0'][i]});
		humidityData.push({'t':data['time'][i], 'y':data['h0'][i]});
	};
	environmentChart.data.datasets[0].data = temperatureData;
	environmentChart.data.datasets[1].data = humidityData;
	environmentChart.update();
});


solarSocket.on('updatePlan', function(data) {
  console.log("Updating day plan");
  document.getElementById('utdate').innerHTML = 'Plan for '+ data['utdate'];
  document.getElementById('sunup').innerHTML = 'sun up: ' +  data['sun_up'].substring(11, 16);
  document.getElementById('medflip').innerHTML = 'Med flip: ' +  data['meridian_flip'].substring(11, 16);
  document.getElementById('sundown').innerHTML = 'sun down: ' +  data['sun_down'].substring(11, 16);
});