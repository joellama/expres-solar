var expresStatusExpanded = true;

function showHide() {
	if (expresStatusExpanded == false) {
		toggle_by_class('hide');
		expresStatusExpanded = true;
		document.getElementById('expresTableToggle').innerHTML = '<i class="now-ui-icons arrows-1_minimal-up"></i>';
	} else {
		toggle_by_class('hide');
		document.getElementById('expresTableToggle').innerHTML = '<i class="now-ui-icons arrows-1_minimal-down"></i>';		
		expresStatusExpanded = false;
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

showHide()