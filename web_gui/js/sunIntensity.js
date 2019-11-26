Highcharts.chart('sunIntensity', {
    chart: {
        type: 'spline',
        spacingBottom: 3,
        marginRight: 30,
        marginBottom: 30,
        reflow: true,        
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
            format: '{value} EV',
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
        min: -10,
        max: 0,
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