var expresStatusExpanded = true;
var logStatusExpanded = true;
var expresStatus = true;
function showHideExpres() {
	if (expresStatusExpanded == false) {
		toggle_by_class('hideExpres');
		expresStatusExpanded = true;
		document.getElementById('expresTableToggle').innerHTML = '<i class="now-ui-icons arrows-1_minimal-up"></i>';
	} else {
		toggle_by_class('hideExpres');
		document.getElementById('expresTableToggle').innerHTML = '<i class="now-ui-icons arrows-1_minimal-down"></i>';		
		expresStatusExpanded = false;
	}
}

function pausePlayExpres() { 
    if (expresStatus == true) {
        expresStatus = false;
        document.getElementById('expresPlayPause').innerHTML = '<i class="now-ui-icons media-1_button-play"></i>'        
    } else {
        expresStatus = true;
        document.getElementById('expresPlayPause').innerHTML = '<i class="now-ui-icons media-1_button-pause"></i>'        
    }
}


function showHideConsole() {
	if (logStatusExpanded == false) {
		toggle_by_class('hideConsole');
		logStatusExpanded = true;
		document.getElementById('hideLog').innerHTML = '<i class="now-ui-icons arrows-1_minimal-up"></i>';
	} else {
		toggle_by_class('hideConsole');
		document.getElementById('hideLog').innerHTML = '<i class="now-ui-icons arrows-1_minimal-down"></i>';		
		logStatusExpanded = false;
	}
}

function toggle_by_class(cls, on) {
    var lst = document.getElementsByClassName(cls);
    for(var i = 0; i < lst.length; ++i) {
    	if (lst[i].style.display == 'none') {
    		lst[i].style.display = '';
    	} else {
    		lst[i].style.display = 'none';
    	}
    }
}

showHideExpres()
 