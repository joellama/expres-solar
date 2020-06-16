var ctx = document.getElementById('bigDashboardChart').getContext('2d');
    
chartColor = "#FFFFFF";
    
ctx.canvas.width = 1000;
ctx.canvas.height = 200;
    
var gradientFill = ctx.createLinearGradient(0, 200, 0, 50);
    
gradientFill.addColorStop(0, "rgba(128, 182, 244, 0)");
gradientFill.addColorStop(1, "rgba(255, 255, 255, 0.24)");    
    
var gradientStroke = ctx.createLinearGradient(500, 0, 100, 0);
gradientStroke.addColorStop(0, '#80b6f4');
gradientStroke.addColorStop(1, chartColor);
    
var color = Chart.helpers.color;
var cfg = {
    data: {
      datasets: [{
        label: 'Solar intensity: ',
        // backgroundColor: color(window.chartColors.red).alpha(0.5).rgbString(),
        // borderColor: window.chartColors.red,
        data: generateData(),
        type: 'line',
        pointRadius: 0,
        fill: true,
        lineTension: 0,
        borderWidth: 1,
        borderColor: chartColor,
        pointBorderColor: chartColor,
        pointBackgroundColor: "#1e3d60",
        pointHoverBackgroundColor: "#1e3d60",
        pointHoverBorderColor: chartColor,
        pointBorderWidth: 1,
        pointHoverRadius: 1,
        pointHoverBorderWidth: 1,
        pointRadius: 1,
        backgroundColor: gradientFill,
        borderWidth: 0.5,
      }]
    },
    options: {
      layout: {
        padding: {
          left: 40,
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
              fontColor: "rgba(255,255,255, 0.7)",
              labelString: 'Time',
            },
            fontSize: 14,
            // source: 'data',
            // labels: generateLabels(),
            autoSkip: true,
            autoSkipPadding: 75,
            maxRotation: 0,
            sampleSize: 100,
            fontColor: "rgba(255,255,255,0.9)"
          }
        }],
        yAxes: [{
          gridLines: {
            drawBorder: false,
            display:false
          },
          ticks: {
            fontColor: "rgba(255,255,255,0.7)",
            fontSize: 16,
            min:0,
            max:100,
          },
          scaleLabel: {
            display: true,
            labelString: 'Solar intensity',
            fontColor: "rgba(255,255,255,0.9)",
            fontSize: 16,
          }
        }]
      },
      tooltips: {
        backgroundColor: '#fff',
        titleFontColor: '#fff',
        bodyFontColor: '#000',
        bodySpacing: 4,
        xPadding: 12,
        mode: "nearest",
        intersect: 0,
        position: "nearest",
 
      },
      legend: {
        position: "bottom",
        fillStyle: "#FFF",
        display: false
      }
    }
};

var chart = new Chart(ctx, cfg);

function formatNumber(number, decimalsLength, decimalSeparator, thousandSeparator) {
       var n = number,
           decimalsLength = isNaN(decimalsLength = Math.abs(decimalsLength)) ? 2 : decimalsLength,
           decimalSeparator = decimalSeparator == undefined ? "," : decimalSeparator,
           thousandSeparator = thousandSeparator == undefined ? "." : thousandSeparator,
           sign = n < 0 ? "-" : "",
           i = parseInt(n = Math.abs(+n || 0).toFixed(decimalsLength)) + "",
           j = (j = i.length) > 3 ? j % 3 : 0;

       return sign +
           (j ? i.substr(0, j) + thousandSeparator : "") +
           i.substr(j).replace(/(\d{3})(?=\d)/g, "$1" + thousandSeparator) +
           (decimalsLength ? decimalSeparator + Math.abs(n - i).toFixed(decimalsLength).slice(2) : "");
}