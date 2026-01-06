function selectCheckboxes(value){
  var els = document.getElementsByName('payed_for');
  for(var i = 0; i < els.length; i++){
    els[i].checked = value;
  }
}

function localizeTime(utcTimestamp) {
    return new Date(utcTimestamp).toLocaleString()
}
