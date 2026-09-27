
window.onerror = function(msg, url, lineNo, columnNo, error) {
    document.body.innerHTML = "<div style='color:red; font-size:30px; padding:50px; background:white; z-index:99999; position:absolute;'>" + msg + " at line " + lineNo + "</div>" + document.body.innerHTML;
    return false;
};
