const input01 = document.getElementById("id-01");
const input02 = document.getElementById("id-02");
const input03 = document.getElementById("id-03");
const input04 = document.getElementById("id-04");
const button = document.getElementById("submitButton");

input01.onkeyup = function() {
    if (input01.value.length > 0){
        input02.focus();
    }
}

input02.onkeyup = function(q) {
    if (q.code = "Backspace"){
        input01.focus();
    }
    if (input02.value.length > 0){
        input03.focus();
    }
}

input03.onkeyup = function(q) {
    if (q.code = "Backspace"){
        input02.focus();
    }
    if (input03.value.length > 0){
        input04.focus();
    }
}

input04.onkeyup = function(q) {
    if (q.code = "Backspace"){
        input03.focus();
    }
    if (input04.value.length > 0){
        button.focus();
    }
}

button.onclick = function() {
    var base = "/onboard/";
    base += input01.value;
    base += input02.value;
    base += input03.value;
    base += input04.value;
    window.location.href = base;
};