// Validating form for submitting a task //

document.querySelector("#task").onkeyup = function() {
    if (document.querySelector("#task").value === "") {
        document.querySelector("#submit").disabled = true;
    } else {
        document.querySelector("#submit").disabled = false;
    }
}