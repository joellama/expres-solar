function generateData() {
      function randomNumber(min, max) {
        return Math.random() * (max - min) + min;
      }
 
      var start = moment('2020-02-10 09:23:00');
      var end = moment('2020-02-10 16:00:00');
      var data = [];
      while(start < end){
            data.push({t:start.format(), y:randomNumber(0, 1)});
            start = start.add(1,  'minutes');
          };
          data.push({t:moment('2020-02-10 18:00:00').format(), y:NaN});
          console.log(data);
          return data;
  };

  function generateLabels() {
        var start = moment('2020-02-10 08:00:00');
        var end = moment('2020-02-10 20:00:00');
        var labels = [];
        while (start < end) {
          labels.push(start.format());
          start = start.add(30, 'minutes');
        }
        return labels;
  }