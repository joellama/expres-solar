
// Highcharts.chart('sunPosition', {
//     chart: {
//         type: 'spline',
//         animation: Highcharts.svg, // don't animate in old IE
//         marginRight: 0,
//         events: {
//             load: function () {
//                 // set up the updating of the chart each second
//                 var series = this.series[0];
//                 maxSamples = 10;
//                 count = 0;                
//                 socket.on('sunIntensity', function(data){
//                     var x = (new Date()).getTime() // current time
//                         y = data;
//                     series.addPoint([x, y], true, (++count >= maxSamples));
//                 });
//             }
//         }
//     },

//     time: {
//         useUTC: false
//     },
//     title: {
//         text: ''
//     },
//     xAxis: {
//         type: 'datetime',
//         tickPixelInterval: 10,
//         labels: {
//             rotation: 0,
//         },
//         dateTimeLabelFormats: {
//               second: '%H:%M<br/>%S', 
//         }       
//     },
//     yAxis: {
//         title: {
//             text: ''
//         },
//         plotLines: [{
//             value: 0,
//             width: 1,
//             color: '#F26522'
//         }]
//     },
//     tooltip: {
//         headerFormat: '<b>{series.name}</b><br/>',
//         pointFormat: '{point.x:%Y-%m-%d %H:%M<br%S}<br/>{point.y:.2f}'
//     },
//     legend: {
//         enabled: false
//     },
//     exporting: {
//         enabled: false
//     },
//     series: {
//         name: 'Sun Intensity',
//         data: [],
//         color: '#F26522',
//         type:'spline'
//     }
// });

Highcharts.chart('sunPosition', {
    chart: {
        type: 'spline',
        animation: Highcharts.svg, // don't animate in old IE
        // marginRight: 0,
        events: {
            load: function () {
                // set up the updating of the chart each second
                var series_SI = this.series[0];
                maxSamples_SI = 10;
                count_SI = 0;
                socket.on('sunIntensity', function(data){
                    var x = (new Date()).getTime() // current time
                        y = data;
                    series_SI.addPoint([x, y], true, (++count_SI >= maxSamples_SI));                     
                });
            }
        }
    },
    time: {
        useUTC: false
    },

    title: {
        text: ''
    },
 legend: {
        layout: 'vertical',
        align: 'left',
        x: 120,
        verticalAlign: 'top',
        y: 100,
        floating: true,
        backgroundColor:
            Highcharts.defaultOptions.legend.backgroundColor || // theme
            'rgba(255,255,255,0.25)'
    },    
    xAxis: {
        type: 'datetime',
        tickPixelInterval: 10,
        labels: {
            rotation: 0,
        },
        dateTimeLabelFormats: {
              second: '%H:%M<br/>%S', 
        }       
    },
    yAxis: [{
        labels: {
            format: '{value}%',
            style: {
                color: '#F26522'
            }
        }, 
        title: {
            text: 'Sun Intensity',
            style: {
                color: '#F26522'
            },
        },
        min: 0,
        max: 100,
    }],
    tooltip: {
        shared: true
    },

    tooltip: {
        headerFormat: '<b>{series.name}</b><br/>',
        pointFormat: '{point.x:%Y-%m-%d %H:%M<br%S}<br/>{point.y:.2f}'
    },
    legend: {
        enabled: true
    },
    exporting: {
        enabled: false
    },
    series: [{
        name: 'Sun Intensity',
        type: 'spline',
        data: [],
        color: '#F26522',
        tooltip: {
            valueSuffix: '°C'
        }

    }]
});

Highcharts.chart('environmentPlot', {
    chart: {
        type: 'spline',
        animation: Highcharts.svg, // don't animate in old IE
        // marginRight: 0,
        events: {
            load: function () {
                // set up the updating of the chart each second
                var series_T = this.series[0];
                var series_H = this.series[1];
                maxSamples = 5;
                count_T = 0;
                count_H = 0;
                socket.on('updateEnv', function(data){
                    var x = Date.parse(data['Time'])
                        y = data['Temp']
                        z = data['Humidity'];
                    series_T.addPoint([x, y], true, (++count_T >= maxSamples));
                    series_H.addPoint([x, z], true, (++count_H >= maxSamples));
                    console.log(count_H);
                    console.log(count_T);

                });
            }
        }
    },

    time: {
        useUTC: false
    },

    title: {
        text: ''
    },
 legend: {
        layout: 'vertical',
        align: 'left',
        x: 120,
        verticalAlign: 'top',
        y: 100,
        floating: true,
        backgroundColor:
            Highcharts.defaultOptions.legend.backgroundColor || // theme
            'rgba(255,255,255,0.25)'
    },    
    xAxis: {
        type: 'datetime',
        tickPixelInterval: 10,
        labels: {
            rotation: 0,
        },
        dateTimeLabelFormats: {
              second: '%H:%M<br/>%S', 
        }       
    },
    yAxis: [{
        labels: {
            format: '{value}°C',
            style: {
                color: '#D3322E'
            }
        }, 
        min: -20.0,
        max: 50.0,
        title: {
            text: 'Dome Temperature',
            style: {
                color: '#D3322E'
            }
        },

    }, { // Secondary yAxis
        title: {
            text: 'Humidity',
            style: {
                color: '#03A2D9',
            }
        },
        labels: {
            format: '{value} %',
            style: {
                color: '#03A2D9',
            }
        },
        min: 0,
        max: 100,
        opposite: true
    }],
    tooltip: {
        shared: true
    },

    tooltip: {
        headerFormat: '<b>{series.name}</b><br/>',
        pointFormat: '{point.x:%Y-%m-%d %H:%M<br%S}<br/>{point.y:.2f}'
    },
    legend: {
        enabled: true
    },
    exporting: {
        enabled: false
    },
    series: [{
        name: 'Temperature',
        type: 'spline',
        data: [],
        color: '#D3322E',
        tooltip: {
            valueSuffix: '°C'
        }

    }, {
        name: 'Humidity',
        type: 'spline',
        yAxis: 1,
        data: [],
        color: '#03A2D9',
        tooltip: {
            valueSuffix: ' %'
        }
    }]
});