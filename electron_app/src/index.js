const electron = require('electron');
const path = require('path');
const Highcharts = require('highcharts');





Highcharts.chart('tempHumidity', {
    chart: {
        type: 'spline',
        animation: Highcharts.svg, // don't animate in old IE
        marginRight: 30,
        spacingLeft: 0,
        width: null,
        styledMode: true,
        events: {
            load: function () {
                var chart = this;
                socket.on('sunIntensity', function(arr){
                    var data = JSON.parse(arr);
                    var x = [];
                    for (var i = 0; i < data.length; i++) {
                        x.push([Date.parse(data[i]['T']),data[i]['ALT']] );
                    }                
                    chart.series[0].setData(x, true);
                    chart.redraw();
                    
                })
            }    
        }
    },

    time: {
        useUTC: false
    },

    title: {
        text: ''
    },
    xAxis: {
        type: 'datetime',
        tickPixelInterval: 90,
        labels: {
            "format": "{value:%Y-%m-%d<br/>%H:%I}"
        }
    },
    yAxis: {
        title: {
            text: 'Altitude (degrees)'
        },
        min: 0,
        max: 85,
        plotLines: [{
            value: 0,
            width: 1,
            color: '#808080'
        }]
    },
   defs: {
        gradient0: {
            tagName: 'linearGradient',
            id: 'gradient-0',
            x1: 0,
            y1: 0,
            x2: 0,
            y2: 1,
            children: [{
                tagName: 'stop',
                offset: 0
            }, {
                tagName: 'stop',
                offset: 1
            }]
        },
        gradient1: {
            tagName: 'linearGradient',
            id: 'gradient-1',
            x1: 0,
            y1: 0,
            x2: 0,
            y2: 1,
            children: [{
                tagName: 'stop',
                offset: 0
            }, {
                tagName: 'stop',
                offset: 1
            }]
        }
    },
    tooltip: {
        headerFormat: '<b>{Sun Altitude}</b><br/>',
        pointFormat: '{point.x:%Y-%m-%d %H:%M:%S}<br/>{point.y:.2f}'
    },
    legend: {
        enabled: false
    },
    exporting: {
        enabled: false
    },
    series: [{
        type: 'area',
        name: 'sunPosition',
        data: []
    }]
});

 