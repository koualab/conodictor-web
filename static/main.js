function emailCheck() {
    if (document.getElementById('emailcheck').checked) {
        document.getElementById('reveal-if-active').style.visibility = 'block';
    }
    else {
        document.getElementById('reveal-if-active').style.visibility = 'none';
    }
}