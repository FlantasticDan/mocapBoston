if (!hasProcessed) {
    const gifPlayer = document.getElementById("playerSource");
    var db = firebase.firestore();

    var unsubscribe = db.collection("dev").doc("{{id}}")
        .onSnapshot(function (doc){
            if (doc.get("processed")) {
                location.reload();
            }
        });
}