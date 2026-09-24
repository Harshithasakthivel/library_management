// =====================================================
// DELETE CONFIRMATION
// =====================================================

function confirmDelete() {

    return confirm(
        "Are you sure you want to delete this book?"
    );

}


// =====================================================
// RETURN CONFIRMATION
// =====================================================

function confirmReturn() {

    return confirm(
        "Are you sure you want to return this book?"
    );

}


// =====================================================
// AUTO HIDE ALERTS
// =====================================================

setTimeout(function () {

    const alerts =
        document.querySelectorAll(
            ".alert"
        );


    alerts.forEach(function (alert) {

        alert.style.transition =
            "opacity 0.5s";


        alert.style.opacity =
            "0";


        setTimeout(function () {

            alert.remove();

        }, 500);

    });

}, 4000);