document.addEventListener('DOMContentLoaded', function() {
    // Wait for 5 seconds after the page is fully loaded before showing the popup
    setTimeout(function() {
        var userResponse = confirm("Would you like to see the Interactive Map ?");
        if (userResponse) {
            // User clicked "OK"; redirect them to Google
            window.location.href = "https://pace-risk-map-x35exdywcq-ue.a.run.app/";
        }
    }, 30000); // 5000 milliseconds = 5 seconds
});


document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
            var hiddenButton = document.getElementById('hidden_but');
            if (hiddenButton) {
                hiddenButton.style.display = 'block'; // Make the element visible
            }
        }
    , 30000);
});

document.addEventListener('DOMContentLoaded', function() {
    fetch('https://pace-risk-map-x35exdywcq-ue.a.run.app/', {
        mode: 'no-cors' // This mode allows the request to be made but does not allow access to the response.
    })
    },);
